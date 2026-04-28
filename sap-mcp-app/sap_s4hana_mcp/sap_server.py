"""SAP S/4HANA MCP server — bootstrap only. Tools in tools.py, client in sap_client.py."""
import sys
from pathlib import Path

import structlog
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from .sap_settings import get_settings
from .sap_tools import PROMPT_SPECS, TOOL_SPECS
from shared_mcp.telemetry import wrap_specs
TOOL_SPECS = wrap_specs(TOOL_SPECS)

log = structlog.get_logger("sap")
settings = get_settings()

WIDGET_URI = "ui://widget/sap.html"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

mcp = FastMCP("gtc-sap-trading-post")


@mcp.resource(WIDGET_URI, mime_type="text/html;profile=mcp-app")
async def sap_widget() -> str:
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
    mode = settings.sap_mode.lower()
    print("  ┌─ Environment ─────────────────────────────────")
    print(f"  │ SAP_MODE           ✓ {mode}")
    if mode == "sandbox":
        print(f"  │ SAP_API_KEY        {'✓ ' + settings.sap_api_key[:8] + '...' if settings.sap_api_key else '✗ MISSING'}")
    else:
        print(f"  │ SAP_TENANT_URL     {'✓ ' + settings.sap_tenant_url[:40] if settings.sap_tenant_url else '✗ MISSING'}")
        print(f"  │ SAP_USERNAME       {'✓ ' + settings.sap_username if settings.sap_username else '✗ MISSING'}")
        print(f"  │ SAP_PASSWORD       {'✓ (set)' if settings.sap_password else '✗ MISSING'}")
    print("  └────────────────────────────────────────────────")
    missing = []
    if mode == "sandbox":
        if not settings.sap_api_key: missing.append("SAP_API_KEY")
    else:
        if not settings.sap_tenant_url: missing.append("SAP_TENANT_URL")
        if not settings.sap_username:   missing.append("SAP_USERNAME")
        if not settings.sap_password:   missing.append("SAP_PASSWORD")
    if missing:
        log.error("missing_env_vars", vars=missing)
        print(f"\n  ❌ Missing required env vars: {', '.join(missing)}")
        sys.exit(1)


def main() -> None:
    _validate_env()
    log.info("starting", port=settings.port, mode=settings.sap_mode)
    print(f"⚓ GTC — SAP S/4HANA Trading Post starting on port {settings.port} (mode: {settings.sap_mode})")
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
