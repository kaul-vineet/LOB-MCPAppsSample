"""DocuSign MCP server — bootstrap only. Tools in tools.py, client in client.py."""
import sys
from pathlib import Path

import structlog
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from .docusign_settings import get_settings
from .docusign_tools import PROMPT_SPECS, TOOL_SPECS
from shared_mcp.telemetry import wrap_specs
TOOL_SPECS = wrap_specs(TOOL_SPECS)

log = structlog.get_logger("ds")
settings = get_settings()

WIDGET_URI = "ui://widget/docusign.html"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

mcp = FastMCP("gtc-docusign-post")


@mcp.resource(WIDGET_URI, mime_type="text/html;profile=mcp-app")
async def docusign_widget() -> str:
    return WIDGET_HTML


for _spec in TOOL_SPECS:
    mcp.tool(
        name=_spec["name"],
        description=_spec["description"],
        meta={"ui": {"resourceUri": WIDGET_URI}},
    )(_spec["handler"])

for _spec in PROMPT_SPECS:
    mcp.prompt(name=_spec["name"], description=_spec["description"])(_spec["handler"])


def _validate_env() -> None:
    from .docusign_client import validate_env
    key = settings.docusign_integration_key
    uid = settings.docusign_user_id
    acct = settings.docusign_account_id
    mock = settings.mock_mode
    print("  ┌─ Environment ─────────────────────────────────")
    print(f"  │ INTEGRATION_KEY  {'✓ set' if key  else '✗ MISSING'}")
    print(f"  │ USER_ID          {'✓ set' if uid  else '✗ MISSING'}")
    print(f"  │ ACCOUNT_ID       {'✓ set' if acct else '✗ MISSING'}")
    print(f"  │ RSA_PRIVATE_KEY  {'✓ set' if settings.docusign_rsa_private_key else '✗ MISSING'}")
    print(f"  │ MOCK_MODE        {'✓ enabled' if mock else '✗ disabled'}")
    print("  └────────────────────────────────────────────────")
    err = validate_env()
    if err and not mock:
        log.error("missing_env_vars", detail=err)
        print(f"\n  ❌ {err}")
        sys.exit(1)


def main() -> None:
    _validate_env()
    log.info("starting", port=settings.port)
    print(f"⚓ GTC — DocuSign Trading Post starting on port {settings.port}")
    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "mcp-session-id"],
    )
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
