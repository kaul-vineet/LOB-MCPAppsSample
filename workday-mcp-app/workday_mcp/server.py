"""Workday HR MCP server — bootstrap only. Tools in tools.py, client in client.py."""
import structlog
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from .settings import get_settings
from .tools import WORKDAY_TOOL_SPECS

log = structlog.get_logger("workday")
settings = get_settings()

WIDGET_URI = "ui://widget/workday.html"

mcp = FastMCP(
    "workday",
    instructions=(
        "Workday HR — employee self-service for leave balances, pay slips, "
        "learning assignments, feedback, goals, check-ins, org charts, "
        "and manager operations like team analytics and job changes."
    ),
)


@mcp.resource(WIDGET_URI, mime_type="text/html")
def get_widget() -> str:
    return "<html><body>Workday widget</body></html>"


for _spec in WORKDAY_TOOL_SPECS:
    mcp.tool(
        name=f"wday__{_spec['name']}",
        description=_spec["summary"],
        meta={"ui": {"resourceUri": WIDGET_URI}},
    )(_spec["func"])


def main() -> None:
    log.info("starting", port=settings.port)
    print(f"⚓ GTC — Workday HR starting on port {settings.port}")
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
