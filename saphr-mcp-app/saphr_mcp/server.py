"""SAP SuccessFactors HR MCP Server — employee profiles, leave, payslips, org charts."""
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

from .tools import SAP_SF_TOOL_SPECS  # noqa: E402

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
    return "<html><body>SAP SuccessFactors HR widget — build in Task 17</body></html>"


for _spec in SAP_SF_TOOL_SPECS:
    mcp.tool(
        name=f"saphr__{_spec['name']}",
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
    port = int(os.environ.get("SAPHR_MCP_PORT", "3006"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
