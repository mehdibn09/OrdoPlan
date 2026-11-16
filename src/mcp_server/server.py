"""Véritable serveur MCP Streamable HTTP (ou stdio), MES/ERP fictifs."""
import json
import os
from contextvars import ContextVar
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from src.auth.auth_service import authenticate
from src.config import DATA
from src.storage.store import Store

session_token = ContextVar("mcp_session_token", default="")


class MESService:
    def __init__(self, store):
        self.store = store

    def get_open_orders(self, user, workshop_id):
        self.store.access(user, workshop_id)
        database = json.loads((DATA / "synthetic/mcp_database.json").read_text())
        return database[workshop_id]

    def get_machine_status(self, user, machine_id):
        database = json.loads((DATA / "synthetic/mcp_database.json").read_text())
        instance = database[user["workshop"]]
        known = {m["id"] for m in instance["machines"]}
        if machine_id not in known:
            raise PermissionError("Machine inconnue ou inaccessible")
        return {"machine_id": machine_id, "state": "available", "unavailable": [], "source": "MES de démonstration ; les photos sont des observations distinctes"}

    def publish_schedule(self, user, workshop_id, schedule_id, approval_token):
        return self.store.publish(user, workshop_id, schedule_id, approval_token)


def create_server(store=None):
    store = store or Store()
    service = MESService(store)
    server = MCPServer("OrdoPlan MES ERP", version="1.0.0")

    def identity():
        token = session_token.get() or os.getenv("ORDOPLAN_MCP_SESSION_TOKEN", "")
        return authenticate(store, token)

    @server.tool()
    def get_open_orders(workshop_id: str) -> dict:
        """Lire le carnet de commandes de l'atelier autorisé."""
        return service.get_open_orders(identity(), workshop_id)

    @server.tool()
    def get_machine_status(machine_id: str) -> dict:
        """Lire un état machine sans commande de pilotage."""
        return service.get_machine_status(identity(), machine_id)

    @server.tool()
    def publish_schedule(workshop_id: str, schedule_id: str, approval_token: str) -> dict:
        """Publier uniquement le contenu préalablement approuvé par le chef."""
        return service.publish_schedule(identity(), workshop_id, schedule_id, approval_token)

    return server


class AuthenticatedMCP:
    def __init__(self, app, store):
        self.app, self.store = app, store

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        auth = dict(scope.get("headers", [])).get(b"authorization", b"").decode()
        token = auth[7:] if auth.lower().startswith("bearer ") else ""
        try:
            authenticate(self.store, token)
        except PermissionError:
            await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
            return
        context = session_token.set(token)
        try:
            await self.app(scope, receive, send)
        finally:
            session_token.reset(context)


_store = Store()
mcp = create_server(_store)
app = AuthenticatedMCP(mcp.streamable_http_app(stateless_http=True, json_response=True, max_request_body_size=2*1024*1024, transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=["127.0.0.1:*", "localhost:*", "mcp:*"], allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://mcp:*"])), _store)

if __name__ == "__main__":
    if os.getenv("MCP_TRANSPORT") == "stdio":
        mcp.run(transport="stdio")
    else:
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8101)
