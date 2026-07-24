"""HTTP/SSE MCP server for acrux."""

from __future__ import annotations

import logging

from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from acrux.config import AcruxConfig
from acrux.mcp_server import AcruxMCPServer

logger = logging.getLogger("acrux")


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Require a local token for MCP HTTP endpoints when api_auth is enabled."""

    def __init__(self, app, config: AcruxConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        if not self.config.api_auth:
            return await call_next(request)
        if request.url.path == "/health":
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        token = request.headers.get("x-acrux-token") or auth.replace("Bearer ", "")
        if token != self.config.api_token:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        return await call_next(request)


def create_app(config: AcruxConfig) -> Starlette:
    acrux_server = AcruxMCPServer(config)
    sse = SseServerTransport("/messages")

    async def sse_endpoint(request: Request):
        async with sse.connect_sse(request.scope, request.receive, request.send) as (
            read_stream,
            write_stream,
        ):
            await acrux_server.server.run(
                read_stream,
                write_stream,
                acrux_server.server.create_initialization_options(),
            )

    async def messages_endpoint(request: Request):
        return await sse.handle_post_message(request.scope, request.receive, request.send)

    async def health_endpoint(request: Request):
        return PlainTextResponse("ok")

    app = Starlette(
        debug=False,
        routes=[
            Route("/sse", endpoint=sse_endpoint),
            Route("/messages", endpoint=messages_endpoint, methods=["POST"]),
            Route("/health", endpoint=health_endpoint),
        ],
    )
    app.add_middleware(TokenAuthMiddleware, config=config)
    return app


async def run_http_server(config: AcruxConfig) -> None:
    import uvicorn

    app = create_app(config)
    logger.info("Starting acrux HTTP MCP server on port %d", config.mcp.port)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=config.mcp.port, log_level="warning")
    )
    await server.serve()
