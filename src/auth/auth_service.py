import hashlib
import hmac
import os
import secrets
import time


DEMO_PASSWORD = "OrdoPlan-demo-2026!"


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


def bootstrap(store):
    if os.getenv("ORDOPLAN_DEMO", "1") != "1":
        return
    for name, role, workshop in [("chef", "chef", "ATELIER-1"), ("planif", "planificateur", "ATELIER-1"), ("lecture", "lecteur", "ATELIER-1"), ("chef2", "chef", "ATELIER-2")]:
        salt = secrets.token_hex(16)
        with store.db() as db:
            db.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?,?)", (name, salt, password_hash(DEMO_PASSWORD, salt), role, workshop))


def login(store, username, password):
    with store.db() as db:
        row = db.execute("SELECT * FROM users WHERE id=?", (username,)).fetchone()
    if not row or not hmac.compare_digest(password_hash(password, row["salt"]), row["password"]):
        raise PermissionError("Identifiants invalides")
    token = secrets.token_urlsafe(32)
    with store.db() as db:
        db.execute("INSERT INTO sessions VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), username, time.time()+3600*8))
    return {"access_token": token, "token_type": "bearer", "user": {k: row[k] for k in ("id", "role", "workshop")}}


def authenticate(store, token):
    with store.db() as db:
        row = db.execute("SELECT u.id,u.role,u.workshop FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.expires>?", (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
    if not row:
        raise PermissionError("Session absente ou expirée")
    return dict(row)
