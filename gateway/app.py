"""
GTC ASGI Gateway — single port (8080) for all 6 LOB MCP servers.

Starlette mounts each FastMCP app under a path prefix so M365 Copilot
reaches every runtime through one tunnel port:

  /sf   -> Salesforce CRM       (9 tools)   ai-plugin runtime 1
  /sn   -> ServiceNow ITSM      (5 tools)   ai-plugin runtime 2
  /sap  -> SAP S/4HANA           (6 tools)   ai-plugin runtime 3
  /hs   -> HubSpot Marketing     (7 tools)   ai-plugin runtime 4
  /ft   -> Flight Tracker        (5 tools)   ai-plugin runtime 5
  /ds   -> DocuSign eSignature   (9 tools)   ai-plugin runtime 6

Widget resourceUris use the ui:// scheme and are runtime-independent,
so mcp-tools.json needs no changes when switching to the gateway.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Pre-load all LOB .env files before importing server modules.
# Server modules call _load_env() at import time; because override=False,
# env vars set here survive their fallback load_dotenv() calls.
_ROOT = Path(__file__).parent.parent
for _env_path in (
    _ROOT / "sf-mcp-app" / ".env",
    _ROOT / "snow-mcp-app" / ".env",
    _ROOT / "sap-mcp-app" / ".env",
    _ROOT / "hubspot-mcp-app" / ".env",
    _ROOT / "flight-mcp-app" / ".env",
    _ROOT / "docusign-mcp-app" / ".env",
):
    if _env_path.exists():
        load_dotenv(_env_path, override=False)

# Import after env is loaded — each module runs _load_env() + settings at import time
import docusign_mcp.server as ds  # noqa: E402
import flight_mcp.server as ft  # noqa: E402
import hubspot_mcp.server as hs  # noqa: E402
import sap_s4hana_mcp.server as sap  # noqa: E402
import servicenow_mcp.server as sn  # noqa: E402
import sf_crm_mcp.server as sf  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
from starlette.routing import Mount  # noqa: E402

app = Starlette(
    routes=[
        Mount("/sf",  app=sf.mcp.streamable_http_app()),
        Mount("/sn",  app=sn.mcp.streamable_http_app()),
        Mount("/sap", app=sap.mcp.streamable_http_app()),
        Mount("/hs",  app=hs.mcp.streamable_http_app()),
        Mount("/ft",  app=ft.mcp.streamable_http_app()),
        Mount("/ds",  app=ds.mcp.streamable_http_app()),
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "mcp-session-id"],
    allow_credentials=False,
)
