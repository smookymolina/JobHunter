import asyncio
import os
import urllib.request

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server.sse import SseServerTransport

from mcp_server import server  # registers all tools via decorators

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

sse = SseServerTransport("/messages/")


async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


def _post_heartbeat() -> None:
    req = urllib.request.Request(
        f"{API_BASE}/mcp/heartbeat", data=b"{}", method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception:
        pass


async def _heartbeat_loop():
    while True:
        await asyncio.to_thread(_post_heartbeat)
        await asyncio.sleep(30)


async def lifespan(app):
    task = asyncio.create_task(_heartbeat_loop())
    try:
        yield
    finally:
        task.cancel()


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
