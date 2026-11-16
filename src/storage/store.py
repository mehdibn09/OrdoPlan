"""Persistance chiffrée, approbations atomiques et publication MES simulée."""
import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from cryptography.fernet import Fernet
import portalocker
from src.config import runtime_dir


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Store:
    def __init__(self, path=None):
        root = runtime_dir() if path is None else path.parent
        root.mkdir(parents=True, exist_ok=True)
        self.path = path or root / "ordoplan.sqlite3"
        keyfile = root / "storage.key"
        with portalocker.Lock(str(root/"storage-key.lock"), timeout=10):
            if not keyfile.exists():
                fd = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(Fernet.generate_key())
            self.fernet = Fernet(keyfile.read_bytes())
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, salt TEXT, password TEXT, role TEXT, workshop TEXT);
            CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS drafts(id TEXT PRIMARY KEY, workshop TEXT, author TEXT, hash TEXT, payload BLOB, revision INTEGER, created REAL, cancelled INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS approvals(token TEXT PRIMARY KEY, draft TEXT, user_id TEXT, hash TEXT, expires REAL, used INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS publications(id INTEGER PRIMARY KEY AUTOINCREMENT, workshop TEXT, draft TEXT UNIQUE, user_id TEXT, payload BLOB, previous INTEGER, created REAL);
            CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, actor TEXT, event TEXT, resource TEXT);
            CREATE TABLE IF NOT EXISTS telegram_links(telegram_id TEXT PRIMARY KEY, user_id TEXT);
            CREATE TABLE IF NOT EXISTS link_codes(code TEXT PRIMARY KEY, user_id TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS imports(id TEXT PRIMARY KEY, workshop TEXT, author TEXT, payload BLOB, created REAL);
            """)

    @contextmanager
    def db(self):
        connection = sqlite3.connect(self.path, timeout=20, isolation_level="IMMEDIATE")
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def encode(self, value):
        return self.fernet.encrypt(canonical(value).encode())

    def decode(self, value):
        return json.loads(self.fernet.decrypt(value))

    def log(self, user, event, resource):
        with self.db() as db:
            db.execute("INSERT INTO audit(at,actor,event,resource) VALUES(?,?,?,?)", (time.time(), user, event, resource))

    def revision(self, workshop, db):
        row = db.execute("SELECT MAX(id) FROM publications WHERE workshop=?", (workshop,)).fetchone()
        return row[0] or 0

    def prepare(self, user, workshop, payload):
        self.access(user, workshop)
        if user["role"] not in ("chef", "planificateur"):
            raise PermissionError("Rôle de lecture : préparation interdite")
        draft = secrets.token_hex(16)
        with self.db() as db:
            db.execute("INSERT INTO drafts(id,workshop,author,hash,payload,revision,created) VALUES(?,?,?,?,?,?,?)", (draft, workshop, user["id"], digest(payload), self.encode(payload), self.revision(workshop, db), time.time()))
        self.log(user["id"], "prepare", draft)
        return self.get_draft(user, draft)

    @staticmethod
    def access(user, workshop):
        if user["workshop"] != workshop:
            raise PermissionError("Accès refusé à cet atelier")

    def get_draft(self, user, draft_id):
        with self.db() as db:
            row = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
        if not row:
            raise KeyError("Brouillon introuvable")
        self.access(user, row["workshop"])
        return {"id": row["id"], "workshop_id": row["workshop"], "hash": row["hash"], "payload": self.decode(row["payload"]), "revision": row["revision"], "cancelled": bool(row["cancelled"])}

    def approve(self, user, draft_id, approved_hash):
        draft = self.get_draft(user, draft_id)
        if user["role"] != "chef":
            raise PermissionError("Seul le chef d'atelier peut approuver")
        if draft["cancelled"] or approved_hash != draft["hash"] or digest(draft["payload"]) != approved_hash:
            raise ValueError("Contenu différent ou brouillon annulé : nouvelle approbation requise")
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            if self.revision(user["workshop"], db) != draft["revision"]:
                raise ValueError("Planning MES modifié : préparer à nouveau")
            db.execute("INSERT INTO approvals(token,draft,user_id,hash,expires) VALUES(?,?,?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), draft_id, user["id"], approved_hash, time.time()+300))
        self.log(user["id"], "approve", draft_id)
        return token

    def publish(self, user, workshop, draft_id, approval_token):
        self.access(user, workshop)
        if user["role"] != "chef":
            raise PermissionError("Publication réservée au chef d'atelier")
        token_hash = hashlib.sha256(approval_token.encode()).hexdigest()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            d = db.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
            a = db.execute("SELECT * FROM approvals WHERE token=?", (token_hash,)).fetchone()
            if not d or not a or d["workshop"] != workshop or a["draft"] != draft_id or a["user_id"] != user["id"] or a["hash"] != d["hash"]:
                raise PermissionError("Approbation absente ou non liée à ce contenu et cet utilisateur")
            payload = self.decode(d["payload"])
            if digest(payload) != d["hash"] or d["cancelled"]:
                raise PermissionError("Brouillon modifié ou annulé")
            existing = db.execute("SELECT id FROM publications WHERE draft=?", (draft_id,)).fetchone()
            if existing:
                return {"publication_id": existing["id"], "idempotent": True}
            if a["expires"] < time.time() or a["used"]:
                raise PermissionError("Approbation expirée ou consommée")
            if self.revision(workshop, db) != d["revision"]:
                raise ValueError("Révision MES obsolète : revalider un nouveau brouillon")
            from src.schemas.pydantic_models import Instance, Schedule
            from src.solver.checker import check_schedule
            errors = check_schedule(Instance.model_validate(payload["instance"]), Schedule.model_validate(payload["schedule"]).operations)
            if errors:
                raise ValueError("Planning invalide : publication bloquée")
            cur = db.execute("INSERT INTO publications(workshop,draft,user_id,payload,previous,created) VALUES(?,?,?,?,?,?)", (workshop, draft_id, user["id"], self.encode(payload), d["revision"] or None, time.time()))
            db.execute("UPDATE approvals SET used=1 WHERE token=?", (token_hash,))
            db.execute("INSERT INTO audit(at,actor,event,resource) VALUES(?,?,?,?)", (time.time(), user["id"], "publish", str(cur.lastrowid)))
            return {"publication_id": cur.lastrowid, "idempotent": False}

    def cancel(self, user, draft_id):
        draft = self.get_draft(user, draft_id)
        if user["role"] != "chef" and user["id"] != self.author(draft_id):
            raise PermissionError("Annulation non autorisée")
        with self.db() as db:
            db.execute("UPDATE drafts SET cancelled=1 WHERE id=?", (draft["id"],))
        return {"cancelled": True}

    def author(self, draft_id):
        with self.db() as db:
            return db.execute("SELECT author FROM drafts WHERE id=?", (draft_id,)).fetchone()[0]

    def history(self, user, workshop):
        self.access(user, workshop)
        with self.db() as db:
            rows = db.execute("SELECT id,draft,user_id,previous,created FROM publications WHERE workshop=? ORDER BY id DESC LIMIT 100", (workshop,)).fetchall()
        return [dict(r) for r in rows]

    def publication(self, user, publication_id):
        with self.db() as db:
            r = db.execute("SELECT * FROM publications WHERE id=?", (publication_id,)).fetchone()
        if not r:
            raise KeyError("Publication introuvable")
        self.access(user, r["workshop"])
        return self.decode(r["payload"])
