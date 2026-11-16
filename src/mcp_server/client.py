import json
import os
import time
from dataclasses import dataclass, field
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import httpx2


@dataclass
class Budget:
    started: float = field(default_factory=time.monotonic)
    mcp_calls: int = 0
    model_calls: int = 0

    def check(self):
        if time.monotonic() - self.started > 60:
            raise TimeoutError("Budget automatique de 60 secondes dépassé")

    def consume_mcp(self):
        self.check()
        self.mcp_calls += 1
        if self.mcp_calls > 3:
            raise RuntimeError("Budget : 3 appels MCP maximum")

    def consume_model(self):
        self.check()
        self.model_calls += 1
        if self.model_calls > 6:
            raise RuntimeError("Budget : 6 appels modèle maximum")


class MCPClient:
    def __init__(self, token, budget=None, url=None):
        self.token = token
        self.budget = budget or Budget()
        self.url = url or os.getenv("MCP_URL", "http://127.0.0.1:8101/mcp")

    async def call(self, name, arguments):
        if name not in {"get_open_orders", "get_machine_status", "publish_schedule"}:
            raise PermissionError("Outil non autorisé")
        self.budget.consume_mcp()
        async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {self.token}"}, timeout=httpx2.Timeout(20, connect=10)) as http_client:
            async with streamable_http_client(self.url, http_client=http_client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
        if result.is_error:
            raise ValueError("MCP a refusé l'appel : " + "; ".join(c.text for c in result.content if hasattr(c, "text")))
        if result.structured_content is not None:
            content = result.structured_content
            return content.get("result", content)
        return json.loads(next(c.text for c in result.content if hasattr(c, "text")))
