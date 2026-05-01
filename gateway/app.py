"""
GTC ASGI Gateway — single port (8080) for all 10 LOB MCP servers.

Starlette mounts each FastMCP app under a path prefix so M365 Copilot
reaches every runtime through one tunnel port:

  /sf      -> Salesforce CRM          ai-plugin runtime 1
  /sn      -> ServiceNow ITSM         ai-plugin runtime 2
  /sap     -> SAP S/4HANA             ai-plugin runtime 3
  /hs      -> HubSpot Marketing       ai-plugin runtime 4
  /ft      -> Flight Tracker          ai-plugin runtime 5
  /ds      -> DocuSign eSignature     ai-plugin runtime 6
  /saphr   -> SAP SuccessFactors HR   ai-plugin runtime 7
  /workday -> Workday HR              ai-plugin runtime 8
  /coupa   -> Coupa Procurement       ai-plugin runtime 9
  /jira    -> Jira Projects           ai-plugin runtime 10

Widget resourceUris use the ui:// scheme and are runtime-independent,
so mcp-tools.json needs no changes when switching to the gateway.
"""

import json
import os
import time
from contextlib import asynccontextmanager, AsyncExitStack
from pathlib import Path

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

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
    _ROOT / "saphr-mcp-app" / ".env",
    _ROOT / "workday-mcp-app" / ".env",
    _ROOT / "coupa-mcp-app" / ".env",
    _ROOT / "jira-mcp-app" / ".env",
):
    if _env_path.exists():
        load_dotenv(_env_path, override=False)

# Import after env is loaded — each module runs _load_env() + settings at import time
import coupa_mcp.coupa_server as coupa  # noqa: E402
import docusign_mcp.docusign_server as ds  # noqa: E402
import flight_mcp.flight_server as ft  # noqa: E402
import hubspot_mcp.hubspot_server as hs  # noqa: E402
import jira_mcp.jira_server as jira  # noqa: E402
import sap_s4hana_mcp.sap_server as sap  # noqa: E402
import saphr_mcp.saphr_server as saphr  # noqa: E402
import servicenow_mcp.servicenow_server as sn  # noqa: E402
import sf_crm_mcp.salesforce_server as sf  # noqa: E402
import workday_mcp.workday_server as workday  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
from starlette.responses import FileResponse, Response  # noqa: E402
from starlette.routing import Mount, Route  # noqa: E402


class MCPRequestLogger(BaseHTTPMiddleware):
    """Log every MCP request from non-localhost IPs to help diagnose Copilot issues."""

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        is_remote  = client_ip not in ("127.0.0.1", "::1", "localhost")
        path       = request.url.path
        method     = request.method
        t0         = time.monotonic()

        # For remote POSTs capture the JSON body (tool calls, initialize, etc.)
        body_preview = ""
        if is_remote and method == "POST":
            try:
                raw  = await request.body()
                obj  = json.loads(raw)
                rpc  = obj.get("method", "?")
                rid  = obj.get("id", "-")
                params = obj.get("params", {})
                tool = params.get("name", "") if rpc == "tools/call" else ""
                body_preview = f"  rpc={rpc} id={rid}" + (f" tool={tool}" if tool else "")
                # Rebuild body stream for the actual handler
                async def _body():
                    return raw
                request._body = raw
            except Exception:
                pass

        response = await call_next(request)
        elapsed  = int((time.monotonic() - t0) * 1000)

        if is_remote:
            sid = request.headers.get("mcp-session-id", "")[:8]
            print(
                f"\033[96m[COPILOT]\033[0m {method} {path}"
                f"  sid={sid or '-'}"
                f"  → {response.status_code}  ({elapsed}ms)"
                + body_preview,
                flush=True,
            )

        return response

# Build each FastMCP sub-app once so we can reference them in both the
# lifespan and the route table.
_sf_app      = sf.mcp.streamable_http_app()
_sn_app      = sn.mcp.streamable_http_app()
_sap_app     = sap.mcp.streamable_http_app()
_hs_app      = hs.mcp.streamable_http_app()
_ft_app      = ft.mcp.streamable_http_app()
_ds_app      = ds.mcp.streamable_http_app()
_saphr_app   = saphr.mcp.streamable_http_app()
_workday_app = workday.mcp.streamable_http_app()
_coupa_app   = coupa.mcp.streamable_http_app()
_jira_app    = jira.mcp.streamable_http_app()

_SUB_APPS = [
    _sf_app, _sn_app, _sap_app, _hs_app, _ft_app,
    _ds_app, _saphr_app, _workday_app, _coupa_app, _jira_app,
]


@asynccontextmanager
async def lifespan(outer_app: Starlette):
    # Starlette does not propagate lifespan events to mounted sub-apps, so we
    # enter each FastMCP app's lifespan context manually.  This starts the
    # StreamableHTTPSessionManager task-group for each server.
    async with AsyncExitStack() as stack:
        for sub in _SUB_APPS:
            await stack.enter_async_context(sub.router.lifespan_context(outer_app))
        yield


_TOOLS_PATH = _ROOT / "lob-agent" / "appPackage" / "mcp-tools.json"


async def _serve_mcp_tools(request: Request) -> Response:
    """Serve mcp-tools.json so MOS3 validation and Copilot can fetch it via the tunnel URL."""
    if not _TOOLS_PATH.exists():
        return Response("mcp-tools.json not found", status_code=404)
    return FileResponse(str(_TOOLS_PATH), media_type="application/json")


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/mcp-tools.json", _serve_mcp_tools),
        Mount("/sf",      app=_sf_app),
        Mount("/sn",      app=_sn_app),
        Mount("/sap",     app=_sap_app),
        Mount("/hs",      app=_hs_app),
        Mount("/ft",      app=_ft_app),
        Mount("/ds",      app=_ds_app),
        Mount("/saphr",   app=_saphr_app),
        Mount("/workday", app=_workday_app),
        Mount("/coupa",   app=_coupa_app),
        Mount("/jira",    app=_jira_app),
    ],
)

app.add_middleware(MCPRequestLogger)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "mcp-session-id"],
    allow_credentials=False,
)
