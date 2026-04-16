"""
ServiceNow ITSM MCP Server — 8 tools for Incidents, Requests & Request Items.

Supports both OAuth 2.0 (client credentials) and Basic Auth, controlled by
SERVICENOW_AUTH_MODE env var. All tools return structuredContent for the widget,
with _meta on the decorator to ensure M365 Copilot discovers the widget URI.
"""

import base64
import os
import sys
import time
from pathlib import Path

import httpx
import uvicorn
from dotenv import load_dotenv
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
from starlette.middleware.cors import CORSMiddleware

load_dotenv()

# ── Configuration (all from .env) ─────────────────────────────────────────────

INSTANCE = os.environ.get("SERVICENOW_INSTANCE", "")
AUTH_MODE = os.environ.get("SERVICENOW_AUTH_MODE", "oauth").lower()
CLIENT_ID = os.environ.get("SERVICENOW_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("SERVICENOW_CLIENT_SECRET", "")
USERNAME = os.environ.get("SERVICENOW_USERNAME", "")
PASSWORD = os.environ.get("SERVICENOW_PASSWORD", "")
BASE_URL = f"https://{INSTANCE}.service-now.com"

# ── Widget ────────────────────────────────────────────────────────────────────

WIDGET_URI = "ui://widget/servicenow.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")


def _error_result(message: str) -> types.CallToolResult:
    """Return a structured error result the widget can display."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


# ── MCP Server ────────────────────────────────────────────────────────────────

mcp = FastMCP("gtc-servicenow-post")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def servicenow_widget() -> str:
    """UI widget for displaying ServiceNow data."""
    return WIDGET_HTML


# ── OAuth Token Cache ─────────────────────────────────────────────────────────

_token_cache: dict = {"token": None, "expires_at": 0.0}


async def get_servicenow_token() -> str:
    """Get OAuth token, refreshing if expired or about to expire."""
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/oauth_token.do",
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 1800)
        return _token_cache["token"]


# ── Unified HTTP helper ──────────────────────────────────────────────────────

async def servicenow_request(
    method: str, path: str, params: dict | None = None, json_body: dict | None = None
) -> httpx.Response:
    """Make an authenticated request to the ServiceNow Table API.

    Handles both OAuth and Basic auth based on SERVICENOW_AUTH_MODE.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    if AUTH_MODE == "oauth":
        token = await get_servicenow_token()
        headers["Authorization"] = f"Bearer {token}"
    else:
        creds = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
        headers["Authorization"] = f"Basic {creds}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.request(
            method,
            f"{BASE_URL}{path}",
            headers=headers,
            params=params,
            json=json_body,
        )
        resp.raise_for_status()
        return resp


# ── Field lists ──────────────────────────────────────────────────────────────

def _val(v):
    """Extract display_value from ServiceNow reference objects."""
    if isinstance(v, dict) and "display_value" in v:
        return v["display_value"]
    return v


INCIDENT_FIELDS = (
    "sys_id,number,short_description,description,state,priority,"
    "urgency,category,assigned_to,sys_created_on,sys_updated_on"
)

REQUEST_FIELDS = (
    "sys_id,number,short_description,description,request_state,"
    "priority,approval,sys_created_on,sys_updated_on"
)

REQUEST_ITEM_FIELDS = (
    "sys_id,number,short_description,description,state,stage,"
    "quantity,price,request,sys_created_on"
)


# ══════════════════════════════════════════════════════════════════════════════
# READ TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    description=(
        "Retrieve the latest incidents from ServiceNow. "
        "Returns up to 'limit' incidents (default 5), ordered by creation date descending. "
        "Use sysparm_display_value=true to get human-readable field values."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_incidents(limit: int = 5) -> types.CallToolResult:
    """
    Args:
        limit: Maximum number of incidents to return (default 5)
    """
    try:
        resp = await servicenow_request(
            "GET",
            "/api/now/table/incident",
            params={
                "sysparm_limit": limit,
                "sysparm_query": "ORDERBYDESCsys_created_on",
                "sysparm_fields": INCIDENT_FIELDS,
                "sysparm_display_value": "true",
            },
        )
        records = resp.json().get("result", [])
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching incidents: {e}")

    incidents = [
        {
            "sys_id": _val(r.get("sys_id")),
            "number": _val(r.get("number")),
            "short_description": _val(r.get("short_description")),
            "description": _val(r.get("description", "")),
            "state": _val(r.get("state")),
            "priority": _val(r.get("priority")),
            "assigned_to": _val(r.get("assigned_to")) or None,
            "sys_created_on": _val(r.get("sys_created_on")),
        }
        for r in records
    ]

    structured = {"type": "incidents", "total": len(incidents), "incidents": incidents}

    summary = (
        f"No incidents found."
        if not incidents
        else f"Found {len(incidents)} incident(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Retrieve the latest service requests from ServiceNow. "
        "Returns up to 'limit' requests (default 5), ordered by creation date descending."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_requests(limit: int = 5) -> types.CallToolResult:
    """
    Args:
        limit: Maximum number of requests to return (default 5)
    """
    try:
        resp = await servicenow_request(
            "GET",
            "/api/now/table/sc_request",
            params={
                "sysparm_limit": limit,
                "sysparm_query": "ORDERBYDESCsys_created_on",
                "sysparm_fields": REQUEST_FIELDS,
                "sysparm_display_value": "true",
            },
        )
        records = resp.json().get("result", [])
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching requests: {e}")

    requests_list = [
        {
            "sys_id": _val(r.get("sys_id")),
            "number": _val(r.get("number")),
            "short_description": _val(r.get("short_description")),
            "description": _val(r.get("description", "")),
            "request_state": _val(r.get("request_state")),
            "priority": _val(r.get("priority")),
            "approval": _val(r.get("approval")),
            "sys_created_on": _val(r.get("sys_created_on")),
        }
        for r in records
    ]

    structured = {"type": "requests", "total": len(requests_list), "requests": requests_list}

    summary = (
        f"No requests found."
        if not requests_list
        else f"Found {len(requests_list)} request(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Retrieve request items for a specific service request. "
        "request_sys_id is the sys_id of the parent sc_request record. "
        "This tool is called from the widget when expanding a request row."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_request_items(request_sys_id: str) -> types.CallToolResult:
    """
    Args:
        request_sys_id: The sys_id of the parent request
    """
    try:
        resp = await servicenow_request(
            "GET",
            "/api/now/table/sc_req_item",
            params={
                "sysparm_query": f"request={request_sys_id}",
                "sysparm_fields": REQUEST_ITEM_FIELDS,
                "sysparm_display_value": "true",
            },
        )
        records = resp.json().get("result", [])
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching request items: {e}")

    items = [
        {
            "sys_id": r.get("sys_id"),
            "number": r.get("number"),
            "short_description": r.get("short_description"),
            "state": r.get("state"),
            "stage": r.get("stage"),
            "quantity": r.get("quantity"),
            "price": r.get("price"),
        }
        for r in records
    ]

    structured = {
        "type": "request_items",
        "request_sys_id": request_sys_id,
        "total": len(items),
        "items": items,
    }

    summary = (
        f"No request items found for request {request_sys_id}."
        if not items
        else f"Found {len(items)} request item(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CREATE TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    description=(
        "Create a new incident in ServiceNow. "
        "Requires short_description. Optional: description, priority (1-4), category."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def create_incident(
    short_description: str,
    description: str = "",
    priority: str = "3",
    category: str = "",
) -> types.CallToolResult:
    """
    Args:
        short_description: Brief summary of the incident
        description:       Detailed description
        priority:          Priority level 1-4 (1=Critical, 4=Low)
        category:          Category (e.g. 'software', 'hardware', 'network')
    """
    body: dict = {"short_description": short_description, "priority": priority}
    if description:
        body["description"] = description
    if category:
        body["category"] = category

    try:
        resp = await servicenow_request("POST", "/api/now/table/incident", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to create incident: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error creating incident: {e}")

    structured = {
        "type": "created",
        "record_type": "incident",
        "sys_id": record.get("sys_id"),
        "number": record.get("number"),
        "message": f"Incident {record.get('number', '')} created successfully",
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new service request in ServiceNow. "
        "Requires short_description. Optional: description, priority (1-4). "
        "Does not create request items."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def create_request(
    short_description: str,
    description: str = "",
    priority: str = "3",
) -> types.CallToolResult:
    """
    Args:
        short_description: Brief summary of the request
        description:       Detailed description
        priority:          Priority level 1-4 (1=Critical, 4=Low)
    """
    body: dict = {"short_description": short_description, "priority": priority}
    if description:
        body["description"] = description

    try:
        resp = await servicenow_request("POST", "/api/now/table/sc_request", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to create request: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error creating request: {e}")

    structured = {
        "type": "created",
        "record_type": "request",
        "sys_id": record.get("sys_id"),
        "number": record.get("number"),
        "message": f"Request {record.get('number', '')} created successfully",
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE TOOLS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.tool(
    description=(
        "Update an existing incident in ServiceNow. "
        "Requires sys_id. Editable fields: description, priority."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_incident(
    sys_id: str,
    description: str | None = None,
    priority: str | None = None,
) -> types.CallToolResult:
    """
    Args:
        sys_id:      The sys_id of the incident to update
        description: New description text (optional)
        priority:    New priority 1-4 (optional)
    """
    body: dict = {}
    if description is not None:
        body["description"] = description
    if priority is not None:
        body["priority"] = priority

    if not body:
        return _error_result("No fields to update. Provide description or priority.")

    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/incident/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to update incident: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating incident: {e}")

    structured = {
        "type": "updated",
        "record_type": "incident",
        "sys_id": sys_id,
        "number": record.get("number"),
        "message": f"Incident {record.get('number', '')} updated successfully",
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing service request in ServiceNow. "
        "Requires sys_id. Editable field: approval."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_request(
    sys_id: str,
    approval: str | None = None,
) -> types.CallToolResult:
    """
    Args:
        sys_id:   The sys_id of the request to update
        approval: New approval status (not requested, requested, approved, rejected)
    """
    body: dict = {}
    if approval is not None:
        body["approval"] = approval

    if not body:
        return _error_result("No fields to update. Provide approval.")

    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/sc_request/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to update request: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating request: {e}")

    structured = {
        "type": "updated",
        "record_type": "request",
        "sys_id": sys_id,
        "number": record.get("number"),
        "message": f"Request {record.get('number', '')} approval updated successfully",
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing request item in ServiceNow. "
        "Requires sys_id. Editable field: quantity."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_request_item(
    sys_id: str,
    quantity: str | None = None,
) -> types.CallToolResult:
    """
    Args:
        sys_id:   The sys_id of the request item to update
        quantity: New quantity value
    """
    body: dict = {}
    if quantity is not None:
        body["quantity"] = quantity

    if not body:
        return _error_result("No fields to update. Provide quantity.")

    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/sc_req_item/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to update request item: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating request item: {e}")

    structured = {
        "type": "updated",
        "record_type": "request_item",
        "sys_id": sys_id,
        "number": record.get("number"),
        "message": f"Request item {record.get('number', '')} quantity updated successfully",
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
def show_incidents() -> list[PromptMessage]:
    """Show the latest incidents from ServiceNow."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the latest incidents from ServiceNow. "
                    "Call get_incidents with limit=5. "
                    "Present the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def show_requests() -> list[PromptMessage]:
    """Show the latest service requests from ServiceNow."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the latest service requests from ServiceNow. "
                    "Call get_requests with limit=5. "
                    "Present the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def incident_summary() -> list[PromptMessage]:
    """Get a summary analysis of recent incidents."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Give me a summary of the latest incidents from ServiceNow. "
                    "Call get_incidents with limit=5. "
                    "Show the widget, then provide a brief written summary: "
                    "how many are critical/high priority, how many are unassigned, "
                    "and any patterns in categories."
                ),
            ),
        )
    ]


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def _validate_env() -> None:
    """Check required environment variables and print startup checklist."""
    print("  ┌─ Environment ─────────────────────────────────")
    print(f"  │ SERVICENOW_INSTANCE  {'✓ ' + INSTANCE if INSTANCE else '✗ MISSING'}")
    print(f"  │ AUTH_MODE            ✓ {AUTH_MODE}")
    if AUTH_MODE == "oauth":
        print(f"  │ CLIENT_ID           {'✓ ' + CLIENT_ID[:8] + '...' if CLIENT_ID else '✗ MISSING'}")
        print(f"  │ CLIENT_SECRET       {'✓ (set)' if CLIENT_SECRET else '✗ MISSING'}")
    else:
        print(f"  │ USERNAME            {'✓ ' + USERNAME if USERNAME else '✗ MISSING'}")
        print(f"  │ PASSWORD            {'✓ (set)' if PASSWORD else '✗ MISSING'}")
    print("  └────────────────────────────────────────────────")

    missing = []
    if not INSTANCE: missing.append("SERVICENOW_INSTANCE")
    if AUTH_MODE == "oauth":
        if not CLIENT_ID: missing.append("SERVICENOW_CLIENT_ID")
        if not CLIENT_SECRET: missing.append("SERVICENOW_CLIENT_SECRET")
    else:
        if not USERNAME: missing.append("SERVICENOW_USERNAME")
        if not PASSWORD: missing.append("SERVICENOW_PASSWORD")
    if missing:
        print(f"\n  ❌ Missing required env vars: {', '.join(missing)}")
        print("  Copy .env.example to .env and fill in your ServiceNow credentials.")
        sys.exit(1)


def main() -> None:
    port = int(os.environ.get("PORT", 3001))
    cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    _validate_env()
    print(f"⚓ GTC — ServiceNow Trading Post starting on port {port}")

    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "mcp-session-id"],
    )
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
