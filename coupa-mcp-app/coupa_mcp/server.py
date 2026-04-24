"""Coupa Procurement MCP Server — invoices, purchase orders, requisitions, suppliers."""
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

from .tools import COUPA_TOOL_SPECS  # noqa: E402

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
    return "<html><body>Coupa Procurement widget — build in Task 17</body></html>"


for _spec in COUPA_TOOL_SPECS:
    mcp.tool(
        name=f"coupa__{_spec['name']}",
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
    port = int(os.environ.get("COUPA_MCP_PORT", "3008"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
