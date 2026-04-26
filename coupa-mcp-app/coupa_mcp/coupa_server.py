"""Coupa Procurement MCP server — bootstrap only. Tools in tools.py, data in client.py."""
import structlog
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from .coupa_settings import get_settings
from .coupa_tools import TOOL_SPECS

log = structlog.get_logger("coupa")
settings = get_settings()

WIDGET_URI = "ui://widget/coupa.html"

mcp = FastMCP(
    "coupa",
    instructions=(
        "Coupa Procurement — invoice management, purchase orders, requisitions, "
        "goods receipts, supplier management, catalog ordering, and approval workflows."
    ),
)


@mcp.resource(WIDGET_URI, mime_type="text/html")
def get_widget() -> str:
    return "<html><body>Coupa Procurement widget</body></html>"


for _spec in TOOL_SPECS:
    mcp.tool(
        name=f"coupa__{_spec['name']}",
        description=_spec["summary"],
        meta={"ui": {"resourceUri": WIDGET_URI}},
    )(_spec["func"])


def main() -> None:
    log.info("starting", port=settings.port)
    print(f"⚓ GTC — Coupa Procurement starting on port {settings.port}")
    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "mcp-session-id"],
        allow_credentials=False,
    )
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
