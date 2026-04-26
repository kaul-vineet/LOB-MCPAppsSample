"""Jira Project Management MCP server — bootstrap only. Tools in tools.py, client in client.py."""
import structlog
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from .jira_settings import get_settings
from .jira_tools import TOOL_SPECS, PROMPT_SPECS

log = structlog.get_logger("jira")
settings = get_settings()

WIDGET_URI = "ui://widget/jira.html"

mcp = FastMCP(
    "jira",
    instructions=(
        "Jira — issue search, CRUD, workflow transitions, sprint management, "
        "work logging, team workload analysis, and version/release management."
    ),
)


@mcp.resource(WIDGET_URI, mime_type="text/html")
def get_widget() -> str:
    return "<html><body>Jira widget</body></html>"


for _spec in TOOL_SPECS:
    mcp.tool(
        name=f"jira__{_spec['name']}",
        description=_spec["summary"],
        meta={"ui": {"resourceUri": WIDGET_URI}},
    )(_spec["func"])

for _spec in PROMPT_SPECS:
    mcp.prompt(name=_spec["name"], description=_spec["description"])(_spec["handler"])


def main() -> None:
    log.info("starting", port=settings.port)
    print(f"⚓ GTC — Jira Project Management starting on port {settings.port}")
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
