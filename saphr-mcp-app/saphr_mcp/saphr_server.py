"""SAP SuccessFactors HR MCP server — bootstrap only. Tools in tools.py, client in client.py."""
import structlog
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from .saphr_settings import get_settings
from .saphr_tools import TOOL_SPECS

log = structlog.get_logger("saphr")
settings = get_settings()

WIDGET_URI = "ui://widget/saphr.html"

mcp = FastMCP(
    "saphr",
    instructions=(
        "SAP SuccessFactors HR — employee self-service for profiles, "
        "leave management, payslips, org charts, position management, "
        "background checks, and employment documents."
    ),
)


@mcp.resource(WIDGET_URI, mime_type="text/html")
def get_widget() -> str:
    return "<html><body>SAP SuccessFactors HR widget</body></html>"


for _spec in TOOL_SPECS:
    mcp.tool(
        name=f"saphr__{_spec['name']}",
        description=_spec["summary"],
        meta={"ui": {"resourceUri": WIDGET_URI}},
    )(_spec["func"])


def main() -> None:
    log.info("starting", port=settings.port)
    print(f"⚓ GTC — SAP SuccessFactors HR starting on port {settings.port}")
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
