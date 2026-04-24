"""Jira Project Management MCP Server — issues, projects, sprints, and workflows."""
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware


def _load_env() -> None:
    explicit = os.environ.get("MCP_SERVERS_ENV_FILE")
    if explicit:
        load_dotenv(explicit, override=True)
        return
    env = Path(__file__).parent.parent / ".env"
    if env.exists():
        load_dotenv(env, override=True)
        return
    load_dotenv()


_load_env()

from .tools import JIRA_TOOL_SPECS  # noqa: E402

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
    return "<html><body>Jira widget — build in Task 17</body></html>"


for _spec in JIRA_TOOL_SPECS:
    mcp.tool(
        name=f"jira__{_spec['name']}",
        description=_spec["summary"],
        meta={"ui": {"resourceUri": WIDGET_URI}},
    )(_spec["func"])


def main() -> None:
    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "mcp-session-id"],
        allow_credentials=False,
    )
    port = int(os.environ.get("JIRA_MCP_PORT", "3009"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
