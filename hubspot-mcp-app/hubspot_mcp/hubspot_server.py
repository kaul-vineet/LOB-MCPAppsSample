"""HubSpot MCP server — bootstrap only. Tools in tools.py, client in hubspot_client.py."""
import sys
from pathlib import Path

import structlog
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from .hubspot_settings import get_settings
from .hubspot_tools import PROMPT_SPECS, TOOL_SPECS
from shared_mcp.telemetry import wrap_specs
TOOL_SPECS = wrap_specs(TOOL_SPECS)

log = structlog.get_logger("hs")
settings = get_settings()

WIDGET_URI = "ui://widget/hubspot.html"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

mcp = FastMCP("gtc-hubspot-trading-post")


@mcp.resource(WIDGET_URI, mime_type="text/html;profile=mcp-app")
async def hubspot_widget() -> str:
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
    token = settings.hubspot_access_token
    print("  ┌─ Environment ─────────────────────────────────")
    print(f"  │ HUBSPOT_ACCESS_TOKEN  {'✓ ' + token[:12] + '...' if token else '✗ MISSING'}")
    print("  └────────────────────────────────────────────────")
    if not token:
        log.error("missing_env_vars", vars=["HUBSPOT_ACCESS_TOKEN"])
        print("\n  ❌ Missing required env var: HUBSPOT_ACCESS_TOKEN")
        sys.exit(1)


def main() -> None:
    _validate_env()
    log.info("starting", port=settings.port)
    print(f"⚓ GTC — HubSpot Trading Post starting on port {settings.port}")
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
