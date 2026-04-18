"""
ServiceNow ITSM MCP Server — 11 tools for Incidents, Requests, Request Items,
Knowledge Articles & operational actions.

Supports both OAuth 2.0 (client credentials) and Basic Auth, controlled by
SERVICENOW_AUTH_MODE env var. All tools return structuredContent for the widget,
with _meta on the decorator to ensure M365 Copilot discovers the widget URI.
"""

import base64
import os
import sys
import time
from pathlib import Path
from typing import Literal

import httpx
import structlog
import uvicorn
from dotenv import load_dotenv
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
from pydantic_settings import BaseSettings
from starlette.middleware.cors import CORSMiddleware
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

log = structlog.get_logger("sn")


# ── Typed Configuration ───────────────────────────────────────────────────────

class SNSettings(BaseSettings):
    servicenow_instance: str = ""
    servicenow_auth_mode: str = "oauth"
    servicenow_client_id: str = ""
    servicenow_client_secret: str = ""
    servicenow_username: str = ""
    servicenow_password: str = ""
    port: int = 3001
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = SNSettings()
BASE_URL = f"https://{settings.servicenow_instance}.service-now.com"

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
                "client_id": settings.servicenow_client_id,
                "client_secret": settings.servicenow_client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 1800)
        return _token_cache["token"]


# ── Unified HTTP helper ──────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=True,
)
async def servicenow_request(
    method: str, path: str, params: dict | None = None, json_body: dict | None = None
) -> httpx.Response:
    """Make an authenticated request to the ServiceNow Table API.

    Handles both OAuth and Basic auth based on SERVICENOW_AUTH_MODE.
    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    if settings.servicenow_auth_mode.lower() == "oauth":
        token = await get_servicenow_token()
        headers["Authorization"] = f"Bearer {token}"
    else:
        creds = base64.b64encode(f"{settings.servicenow_username}:{settings.servicenow_password}".encode()).decode()
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
async def sn__get_incidents(limit: int = 5) -> types.CallToolResult:
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

    if not incidents:
        summary = "No incidents found."
    else:
        lines = [f"Found {len(incidents)} incident(s):"]
        for inc in incidents:
            lines.append(f"- {inc['number']} | P{inc['priority']} | {inc['state']} | {inc['short_description']}")
        summary = "\n".join(lines)

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
async def sn__get_requests(limit: int = 5) -> types.CallToolResult:
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

    if not requests_list:
        summary = "No requests found."
    else:
        lines = [f"Found {len(requests_list)} request(s):"]
        for req in requests_list:
            lines.append(f"- {req['number']} (sys_id={req['sys_id']}) | {req['request_state']} | {req['priority']} | {req['short_description']}")
        summary = "\n".join(lines)

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
async def sn__get_request_items(request_sys_id: str) -> types.CallToolResult:
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

    if not items:
        summary = f"No request items found for request {request_sys_id}."
    else:
        lines = [f"Found {len(items)} request item(s):"]
        for it in items:
            lines.append(f"- {it.get('number','')} | {it.get('short_description','')} | qty={it.get('quantity','')} | {it.get('stage','')}")
        summary = "\n".join(lines)

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
async def sn__create_incident(
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
async def sn__create_request(
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
async def sn__update_incident(
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
async def sn__update_request(
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
async def sn__update_request_item(
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
# RESOLVE / WORK-NOTE / KNOWLEDGE TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Resolve an incident in ServiceNow by setting state to Resolved. "
        "Requires close_code and close_notes."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sn__resolve_incident(
    sys_id: str,
    close_code: str,
    close_notes: str,
) -> types.CallToolResult:
    """
    Args:
        sys_id:       The sys_id of the incident to resolve
        close_code:   Resolution code (e.g. 'Solved (Permanently)', 'Solved (Workaround/Temporarily)', 'Not Solved')
        close_notes:  Description of how the incident was resolved
    """
    body = {
        "state": "6",
        "close_code": close_code,
        "close_notes": close_notes,
    }
    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/incident/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to resolve incident: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error resolving incident: {e}")

    number = _val(record.get("number", ""))
    structured = {
        "type": "resolved",
        "record_type": "incident",
        "sys_id": sys_id,
        "number": number,
        "close_code": close_code,
        "message": f"Incident {number} resolved ({close_code}): {close_notes}",
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Add a work note to an existing incident in ServiceNow. "
        "Work notes are internal comments visible only to IT staff."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sn__add_work_note(
    sys_id: str,
    work_note: str,
) -> types.CallToolResult:
    """
    Args:
        sys_id:    The sys_id of the incident to add a work note to
        work_note: The work note text to append
    """
    body = {"work_notes": work_note}
    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/incident/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to add work note: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error adding work note: {e}")

    number = _val(record.get("number", ""))
    structured = {
        "type": "work_note_added",
        "record_type": "incident",
        "sys_id": sys_id,
        "number": number,
        "message": f"Work note added to incident {number}: {work_note[:80]}{'...' if len(work_note) > 80 else ''}",
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Search knowledge articles in ServiceNow. "
        "Returns articles from the kb_knowledge table matching the query. "
        "Useful for finding solutions before creating incidents."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sn__get_knowledge_articles(
    query: str = "",
    limit: int = 5,
) -> types.CallToolResult:
    """
    Args:
        query:  Free-text search string to find relevant knowledge articles
        limit:  Maximum number of articles to return (default 5)
    """
    params: dict = {
        "sysparm_limit": limit,
        "sysparm_display_value": "true",
        "sysparm_fields": "sys_id,number,short_description,text,kb_category,author,sys_updated_on,workflow_state",
        "sysparm_query": f"workflow_state=published^ORDERBYDESCsys_updated_on",
    }
    if query:
        params["sysparm_query"] = f"short_descriptionLIKE{query}^ORtextLIKE{query}^workflow_state=published^ORDERBYDESCsys_updated_on"

    try:
        resp = await servicenow_request("GET", "/api/now/table/kb_knowledge", params=params)
        records = resp.json().get("result", [])
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to fetch knowledge articles: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching knowledge articles: {e}")

    items = [
        {
            "sys_id":            r.get("sys_id", ""),
            "number":            _val(r.get("number", "")),
            "short_description": _val(r.get("short_description", "")),
            "category":          _val(r.get("kb_category", "")),
            "author":            _val(r.get("author", "")),
            "updated_on":        _val(r.get("sys_updated_on", "")),
            "state":             _val(r.get("workflow_state", "")),
        }
        for r in records
    ]

    structured = {"type": "knowledge_articles", "total": len(items), "items": items}

    lines = [f"Found {len(items)} knowledge article(s){' matching: ' + query if query else ''}:"]
    for a in items:
        lines.append(f"- {a['number']}: {a['short_description']} (Category: {a['category']})")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(lines))],
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
    log.info("validating_env")
    inst = settings.servicenow_instance
    mode = settings.servicenow_auth_mode.lower()
    print("  ┌─ Environment ─────────────────────────────────")
    print(f"  │ SERVICENOW_INSTANCE  {'✓ ' + inst if inst else '✗ MISSING'}")
    print(f"  │ AUTH_MODE            ✓ {mode}")
    if mode == "oauth":
        print(f"  │ CLIENT_ID           {'✓ ' + settings.servicenow_client_id[:8] + '...' if settings.servicenow_client_id else '✗ MISSING'}")
        print(f"  │ CLIENT_SECRET       {'✓ (set)' if settings.servicenow_client_secret else '✗ MISSING'}")
    else:
        print(f"  │ USERNAME            {'✓ ' + settings.servicenow_username if settings.servicenow_username else '✗ MISSING'}")
        print(f"  │ PASSWORD            {'✓ (set)' if settings.servicenow_password else '✗ MISSING'}")
    print("  └────────────────────────────────────────────────")

    missing = []
    if not inst: missing.append("SERVICENOW_INSTANCE")
    if mode == "oauth":
        if not settings.servicenow_client_id: missing.append("SERVICENOW_CLIENT_ID")
        if not settings.servicenow_client_secret: missing.append("SERVICENOW_CLIENT_SECRET")
    else:
        if not settings.servicenow_username: missing.append("SERVICENOW_USERNAME")
        if not settings.servicenow_password: missing.append("SERVICENOW_PASSWORD")
    if missing:
        log.error("missing_env_vars", vars=missing)
        print(f"\n  ❌ Missing required env vars: {', '.join(missing)}")
        print("  Copy .env.example to .env and fill in your ServiceNow credentials.")
        sys.exit(1)


def main() -> None:
    _validate_env()
    log.info("starting", port=settings.port)
    print(f"⚓ GTC — ServiceNow Trading Post starting on port {settings.port}")

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
