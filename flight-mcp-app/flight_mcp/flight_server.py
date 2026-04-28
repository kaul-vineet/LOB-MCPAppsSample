"""Flight Tracker MCP server — bootstrap only. Tools in tools.py, client in client.py."""
import sys
from pathlib import Path

import structlog
import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware

from .flight_settings import get_settings
from .flight_tools import PROMPT_SPECS, TOOL_SPECS
from shared_mcp.telemetry import wrap_specs
TOOL_SPECS = wrap_specs(TOOL_SPECS)

log = structlog.get_logger("ft")
settings = get_settings()

WIDGET_URI = "ui://widget/flights.html"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

mcp = FastMCP("gtc-flight-tracker")


@mcp.resource(WIDGET_URI, mime_type="text/html;profile=mcp-app")
async def flight_widget() -> str:
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
    from .flight_client import is_mock
    cid = settings.opensky_client_id
    cs = settings.opensky_client_secret
    print("  ┌─ Environment ─────────────────────────────────")
    print(f"  │ OPENSKY_CLIENT_ID     {'✓ ' + cid[:8] + '...' if cid else '✗ MISSING'}")
    print(f"  │ OPENSKY_CLIENT_SECRET {'✓ set' if cs else '✗ MISSING'}")
    print("  └────────────────────────────────────────────────")
    if not cid or not cs:
        if is_mock():
            print("  [demo mode] No credentials — running with mock data")
        else:
            missing = [v for v, s in [("OPENSKY_CLIENT_ID", cid), ("OPENSKY_CLIENT_SECRET", cs)] if not s]
            log.error("missing_env_vars", vars=missing)
            print(f"\n  ❌ Missing required env vars: {', '.join(missing)}")
            print("  Set MOCK_MODE=true to run with demo data.")
            sys.exit(1)


def main() -> None:
    _validate_env()
    log.info("starting", port=settings.port)
    print(f"✈️  GTC — Flight Tracker starting on port {settings.port}")
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
