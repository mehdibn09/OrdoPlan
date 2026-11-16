"""API de démonstration intégrée. Démarrer le serveur MCP avant un calcul."""
import asyncio
import hashlib
import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, model_validator
from langgraph.types import Command
from src.auth.auth_service import authenticate, bootstrap, login
from src.storage.store import Store
from src.config import ROOT, MAX_UPLOAD, MODEL_MODE, RETRIEVAL_MODE
from src.agent.graph import build_graph, context, RunContext
from src.mcp_server.client import Budget, MCPClient
from src.rag.retriever import get_retriever
from src.ingestion.pdf_parser import parse_erp, extract_pdf
from src.llm.client import analyze_image


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class Event(BaseModel):
    kind: Literal["breakdown", "urgent", "material_delay"]
    start: int = Field(ge=0, le=1440)
    duration: int | None = Field(default=None, gt=0, le=1440)
    machine_id: str | None = Field(default=None, max_length=20)
    order_id: str | None = Field(default=None, max_length=20)


class AssistantRequest(BaseModel):
    workshop_id: str = Field(default="ATELIER-1", max_length=30)
    mode: Literal["question", "plan"] = "question"
    question: str = Field(default="", max_length=4000)
    instance_id: str = Field(default="demo", max_length=40)
    import_id: str | None = Field(default=None, max_length=64)
    baseline_draft_id: str | None = Field(default=None, max_length=64)
    event: Event | None = None
    prepare: bool = True

    @model_validator(mode="after")
    def coherent(self):
        if self.mode == "question" and not self.question.strip():
            raise ValueError("Question vide")
        return self


class ApprovalRequest(BaseModel):
    hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirmed: Literal[True]


class PublicationRequest(BaseModel):
    approval_token: str = Field(min_length=20, max_length=200)


class LinkRequest(BaseModel):
    code: str = Field(min_length=8, max_length=64)
    telegram_id: str = Field(pattern=r"^\d{1,20}$")


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        consumed = 0

        async def bounded_receive():
            nonlocal consumed
            message = await receive()
            consumed += len(message.get("body", b""))
            if consumed > MAX_UPLOAD + 100_000:
                raise HTTPException(413, "Requête supérieure à 8 Mo")
            return message
        await self.app(scope, bounded_receive, send)


def create_app(store=None):
    store = store or Store()
    graph = None
    limits = defaultdict(deque)
    concurrency = asyncio.Semaphore(2)
    image_concurrency = asyncio.Semaphore(1)

    def quota(key, maximum, window=60):
        now = time.monotonic()
        queue = limits[key]
        while queue and queue[0] < now-window:
            queue.popleft()
        if len(queue) >= maximum:
            raise HTTPException(429, "Quota atteint ; réessayez dans une minute")
        queue.append(now)

    @asynccontextmanager
    async def lifespan(app):
        nonlocal graph
        bootstrap(store)
        graph, connection = await build_graph(store)
        # Un seul index local est ouvert avant d'accepter des requêtes concurrentes.
        await asyncio.to_thread(get_retriever)
        app.state.store = store
        app.state.graph = graph
        yield
        await connection.close()

    app = FastAPI(title="OrdoPlan", description="Assistant d'ordonnancement multimodal et agentique — atelier fictif", version="1.0.0", lifespan=lifespan)
    app.add_middleware(BodyLimit)
    bearer = HTTPBearer(auto_error=False)

    @app.exception_handler(PermissionError)
    async def forbidden(request, exc):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse(status_code=422, content={"detail": str(exc)[:1200]})

    @app.exception_handler(TimeoutError)
    async def timeout(request, exc):
        return JSONResponse(status_code=504, content={"detail": "Budget automatique dépassé ; aucun planning publié"})

    @app.exception_handler(Exception)
    async def unavailable(request, exc):
        # Pas de contenu brut ni secret dans les réponses d'erreur.
        return JSONResponse(status_code=503, content={"detail": "Service indisponible. Vérifiez le démarrage du serveur MCP et les journaux techniques.", "type": type(exc).__name__})

    def identity(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if not credentials:
            raise HTTPException(401, "Authentification requise")
        try:
            user = authenticate(store, credentials.credentials)
        except PermissionError as exc:
            raise HTTPException(401, str(exc)) from exc
        quota("user:"+user["id"], 60)
        return user, credentials.credentials

    @app.get("/health")
    def health():
        return {"status": "ok", "application": "OrdoPlan", "version": "1.0.0", "model_mode": MODEL_MODE, "retrieval_mode": RETRIEVAL_MODE}

    @app.post("/auth/login")
    def auth_login(body: LoginRequest, request: Request):
        quota("login:"+(request.client.host if request.client else "local"), 15)
        try:
            return login(store, body.username, body.password)
        except PermissionError as exc:
            raise HTTPException(401, str(exc)) from exc

    @app.get("/auth/me")
    def me(session=Depends(identity)):
        return session[0]

    @app.post("/auth/logout")
    def logout(session=Depends(identity)):
        with store.db() as db:
            db.execute("DELETE FROM sessions WHERE token=?", (hashlib.sha256(session[1].encode()).hexdigest(),))
        return {"logged_out": True}

    @app.post("/assistant")
    async def assistant(body: AssistantRequest, session=Depends(identity)):
        user, token = session
        store.access(user, body.workshop_id)
        payload = body.model_dump()
        payload["request_id"] = str(uuid.uuid4())
        run = context.set(RunContext(user, token, store, Budget()))
        try:
            async with asyncio.timeout(60):
                async with concurrency:
                    result = await graph.ainvoke({"request": payload, "actor": user["id"], "trace": []}, config={"configurable": {"thread_id": payload["request_id"]}, "recursion_limit": 15})
            answer = result["answer"]
            answer["trace"] = result["trace"]
            answer["versions"] |= {"model": MODEL_MODE, "retrieval": RETRIEVAL_MODE, "instance": result.get("instance", {}).get("id")}
            store.log(user["id"], "assistant:"+answer["status"], payload["request_id"])
            return answer
        finally:
            context.reset(run)

    @app.post("/analyze")
    async def analyze(file: UploadFile = File(...), session=Depends(identity)):
        user, _ = session
        content = await file.read(MAX_UPLOAD+1)
        if len(content) > MAX_UPLOAD:
            raise HTTPException(413, "Fichier supérieur à 8 Mo")
        async with image_concurrency:
            result = await asyncio.wait_for(asyncio.to_thread(analyze_image, content), 60)
        store.log(user["id"], "analyze_image", hashlib.sha256(content).hexdigest()[:16])
        return result

    @app.post("/imports/erp")
    async def import_erp(file: UploadFile = File(...), session=Depends(identity)):
        user, _ = session
        if user["role"] == "lecteur":
            raise PermissionError("Import réservé au planificateur et au chef")
        data = await file.read(MAX_UPLOAD+1)
        orders = await asyncio.to_thread(parse_erp, data, Path(file.filename or "").suffix.lower())
        import_id = secrets.token_hex(16)
        content_hash = hashlib.sha256(data).hexdigest()
        for o in orders:
            for field in ["due", "release"]:
                o.sources[field].document_id = "erp_import_"+import_id
                o.sources[field].version = content_hash
        payload = [o.model_dump() for o in orders]
        with store.db() as db:
            db.execute("INSERT INTO imports VALUES(?,?,?,?,?)", (import_id, user["workshop"], user["id"], store.encode(payload), time.time()))
        return {"import_id": import_id, "sha256": content_hash, "orders": payload}

    @app.post("/imports/pdf")
    async def import_pdf(file: UploadFile = File(...), session=Depends(identity)):
        data = await file.read(MAX_UPLOAD+1)
        pages = await asyncio.wait_for(asyncio.to_thread(extract_pdf, data), 60)
        return {"pages": pages, "needs_validation": True, "message": "Extraction documentaire ; reporter et valider les champs essentiels dans un export ERP avant calcul."}

    @app.get("/documents")
    def documents(session=Depends(identity)):
        return [{k: p[k] for k in ("document_id", "version", "page", "element_id", "title", "machine", "family")} for p in get_retriever().allowed(session[0])]

    @app.get("/documents/{document_id}/{page}")
    def document(document_id: str, page: int, image: bool = False, session=Depends(identity)):
        match = next((p for p in get_retriever().allowed(session[0]) if p["document_id"] == document_id and p["page"] == page), None)
        if not match:
            raise HTTPException(404, "Document absent ou inaccessible")
        path = (ROOT/match["image" if image else "pdf"]).resolve()
        if not path.is_relative_to(ROOT/"data/corpus"):
            raise PermissionError("Chemin documentaire invalide")
        return FileResponse(path, media_type="image/png" if image else "application/pdf", filename=path.name)

    @app.get("/drafts/{draft_id}")
    def draft(draft_id: str, session=Depends(identity)):
        return store.get_draft(session[0], draft_id)

    @app.post("/drafts/{draft_id}/approve")
    def approve(draft_id: str, body: ApprovalRequest, session=Depends(identity)):
        return {"approval_token": store.approve(session[0], draft_id, body.hash), "expires_in": 300}

    @app.post("/drafts/{draft_id}/publish")
    async def publish(draft_id: str, body: PublicationRequest, session=Depends(identity)):
        user, token = session
        draft = store.get_draft(user, draft_id)
        req_id = draft["payload"].get("request_id")
        run = context.set(RunContext(user, token, store, Budget(), body.approval_token))
        try:
            config = {"configurable": {"thread_id": req_id}, "recursion_limit": 15}
            if req_id:
                snapshot = await graph.aget_state(config)
                if snapshot.next:
                    result = await asyncio.wait_for(graph.ainvoke(Command(resume={"approved": True, "hash": draft["hash"]}), config=config), 60)
                    return result["publication"]
            # Réessai idempotent ou brouillon de retour arrière.
            return await MCPClient(token).call("publish_schedule", {"workshop_id": user["workshop"], "schedule_id": draft_id, "approval_token": body.approval_token})
        finally:
            context.reset(run)

    @app.post("/drafts/{draft_id}/cancel")
    def cancel(draft_id: str, session=Depends(identity)):
        return store.cancel(session[0], draft_id)

    @app.get("/publications")
    def history(session=Depends(identity)):
        return store.history(session[0], session[0]["workshop"])

    @app.get("/publications/{publication_id}")
    def publication(publication_id: int, session=Depends(identity)):
        return store.publication(session[0], publication_id)

    @app.post("/publications/{publication_id}/rollback-draft")
    def rollback(publication_id: int, session=Depends(identity)):
        user = session[0]
        payload = store.publication(user, publication_id)
        payload.pop("request_id", None)
        return store.prepare(user, user["workshop"], payload)

    @app.post("/telegram/link-code")
    def link_code(session=Depends(identity)):
        code = secrets.token_urlsafe(12)
        with store.db() as db:
            db.execute("INSERT INTO link_codes VALUES(?,?,?)", (hashlib.sha256(code.encode()).hexdigest(), session[0]["id"], time.time()+300))
        return {"code": code, "expires_in": 300}

    def verify_bot(request):
        expected = os.getenv("TELEGRAM_BRIDGE_SECRET", "")
        supplied = request.headers.get("X-Bot-Secret", "")
        if not expected or not secrets.compare_digest(expected, supplied):
            raise HTTPException(403, "Passerelle non autorisée")

    @app.post("/telegram/link")
    def telegram_link(body: LinkRequest, request: Request):
        verify_bot(request)
        with store.db() as db:
            db.execute("BEGIN IMMEDIATE")
            code_hash = hashlib.sha256(body.code.encode()).hexdigest()
            row = db.execute("SELECT * FROM link_codes WHERE code=? AND expires>?", (code_hash, time.time())).fetchone()
            if not row:
                raise PermissionError("Code invalide ou expiré")
            db.execute("INSERT OR REPLACE INTO telegram_links VALUES(?,?)", (body.telegram_id, row["user_id"]))
            db.execute("DELETE FROM link_codes WHERE code=?", (code_hash,))
        return {"linked": True}

    @app.post("/telegram/session/{telegram_id}")
    def telegram_session(telegram_id: str, request: Request):
        verify_bot(request)
        with store.db() as db:
            row = db.execute("SELECT user_id FROM telegram_links WHERE telegram_id=?", (telegram_id,)).fetchone()
            if not row:
                raise PermissionError("Compte Telegram non associé")
            token = secrets.token_urlsafe(32)
            db.execute("INSERT INTO sessions VALUES(?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), row[0], time.time()+600))
        return {"access_token": token, "user": authenticate(store, token)}

    @app.delete("/telegram/link")
    def unlink(session=Depends(identity)):
        with store.db() as db:
            db.execute("DELETE FROM telegram_links WHERE user_id=?", (session[0]["id"],))
        return {"unlinked": True}

    return app


app = create_app()
