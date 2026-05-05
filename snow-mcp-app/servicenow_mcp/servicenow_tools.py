"""ServiceNow tool handlers + _TOOL_SPECS_LIST registry."""
import httpx
import structlog
from mcp import types
from mcp.types import PromptMessage, TextContent

from .servicenow_client import (
    CHANGE_FIELDS,
    INCIDENT_FIELDS,
    REQUEST_FIELDS,
    REQUEST_ITEM_FIELDS,
    _val,
    servicenow_request,
)


log = structlog.get_logger("sn")


def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


def _sn_escape(value: str) -> str:
    """Escape a value embedded in a ServiceNow encoded query — removes ^ and = injectors."""
    return value.replace("^", "").replace("=", "")


# ── Internal list helpers (used by write tools to return refreshed views) ─────

async def _fetch_incidents(limit: int = 5) -> list:
    resp = await servicenow_request(
        "GET", "/api/now/table/incident",
        params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                "sysparm_fields": INCIDENT_FIELDS, "sysparm_display_value": "true"},
    )
    return [
        {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
         "short_description": _val(r.get("short_description")),
         "description": _val(r.get("description", "")),
         "state": _val(r.get("state")), "priority": _val(r.get("priority")),
         "assigned_to": _val(r.get("assigned_to")) or None,
         "sys_created_on": _val(r.get("sys_created_on"))}
        for r in resp.json().get("result", [])
    ]


async def _text_search(table: str, query: str, fields: str, limit: int, fallback_query: str) -> list:
    """Try sysparm_text (full-text) first; fall back to explicit LIKE query if empty or error."""
    try:
        resp = await servicenow_request(
            "GET", f"/api/now/table/{table}",
            params={"sysparm_text": query, "sysparm_limit": limit,
                    "sysparm_fields": fields, "sysparm_display_value": "true"},
        )
        records = resp.json().get("result", [])
        if records:
            return records
    except Exception:
        pass
    resp = await servicenow_request(
        "GET", f"/api/now/table/{table}",
        params={"sysparm_query": fallback_query, "sysparm_limit": limit,
                "sysparm_fields": fields, "sysparm_display_value": "true"},
    )
    return resp.json().get("result", [])


async def _fetch_problems(limit: int = 5) -> list:
    PROBLEM_FIELDS = "sys_id,number,short_description,state,priority,assigned_to,sys_created_on"
    resp = await servicenow_request(
        "GET", "/api/now/table/problem",
        params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                "sysparm_fields": PROBLEM_FIELDS, "sysparm_display_value": "true"},
    )
    return [
        {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
         "short_description": _val(r.get("short_description")), "state": _val(r.get("state")),
         "priority": _val(r.get("priority")), "assigned_to": _val(r.get("assigned_to")) or None,
         "sys_created_on": _val(r.get("sys_created_on"))}
        for r in resp.json().get("result", [])
    ]


async def _fetch_hr_cases(limit: int = 10) -> list:
    HR_FIELDS = "sys_id,number,short_description,description,state,priority,opened_by,sys_created_on"
    resp = await servicenow_request(
        "GET", "/api/now/table/sn_hr_core_case",
        params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                "sysparm_fields": HR_FIELDS, "sysparm_display_value": "true"},
    )
    return [
        {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
         "subject": _val(r.get("short_description")), "description": _val(r.get("description")),
         "state": _val(r.get("state")), "priority": _val(r.get("priority")),
         "opened_by": _val(r.get("opened_by")) or None,
         "sys_created_on": _val(r.get("sys_created_on"))}
        for r in resp.json().get("result", [])
    ]


async def _fetch_approvals(limit: int = 10) -> list:
    resp = await servicenow_request(
        "GET", "/api/now/table/sysapproval_approver",
        params={"sysparm_limit": limit,
                "sysparm_query": "state=requested^ORDERBYDESCsys_created_on",
                "sysparm_fields": "sys_id,approver,sysapproval,state,due_date,sys_created_on",
                "sysparm_display_value": "true"},
    )
    return [
        {"sys_id": _val(r.get("sys_id")), "approver": _val(r.get("approver")),
         "document": _val(r.get("sysapproval")), "state": _val(r.get("state")),
         "due_date": _val(r.get("due_date")), "created_on": _val(r.get("sys_created_on"))}
        for r in resp.json().get("result", [])
    ]


async def _fetch_requests(limit: int = 5) -> list:
    resp = await servicenow_request(
        "GET", "/api/now/table/sc_request",
        params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                "sysparm_fields": REQUEST_FIELDS, "sysparm_display_value": "true"},
    )
    return [
        {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
         "short_description": _val(r.get("short_description")),
         "description": _val(r.get("description", "")),
         "request_state": _val(r.get("request_state")), "priority": _val(r.get("priority")),
         "approval": _val(r.get("approval")), "sys_created_on": _val(r.get("sys_created_on"))}
        for r in resp.json().get("result", [])
    ]


# ── Read tools ────────────────────────────────────────────────────────────────

async def sn__get_incidents(limit: int = 5, number: str = "", query: str = "") -> types.CallToolResult:
    PROBLEM_FIELDS_LOCAL = INCIDENT_FIELDS
    if number:
        num = number.strip().upper()
        try:
            resp = await servicenow_request(
                "GET", "/api/now/table/incident",
                params={"sysparm_query": f"number={num}", "sysparm_limit": 1,
                        "sysparm_fields": PROBLEM_FIELDS_LOCAL, "sysparm_display_value": "true"},
            )
            records = resp.json().get("result", [])
        except Exception as e:
            return _error_result(f"Error looking up incident {num}: {e}")
        if not records:
            return _error_result(f"Incident {num} not found.")
        r = records[0]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Opening edit form for {_val(r.get('number'))}.")],
            structuredContent={"type": "form", "entity": "incident", "mode": "edit",
                               "recordId": _val(r.get("sys_id")),
                               "prefill": {"short_description": _val(r.get("short_description", "")),
                                           "description": _val(r.get("description", "")),
                                           "priority": _val(r.get("priority", "3")),
                                           "state": _val(r.get("state", "")),
                                           "category": _val(r.get("category", ""))}},
        )
    if query:
        try:
            records = await _text_search(
                "incident", query, PROBLEM_FIELDS_LOCAL, limit,
                f"short_descriptionLIKE{query}^ORdescriptionLIKE{query}^ORDERBYDESCsys_created_on",
            )
        except Exception as e:
            return _error_result(f"Error searching incidents: {e}")
    else:
        try:
            resp = await servicenow_request(
                "GET", "/api/now/table/incident",
                params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                        "sysparm_fields": PROBLEM_FIELDS_LOCAL, "sysparm_display_value": "true"},
            )
            records = resp.json().get("result", [])
        except httpx.HTTPStatusError as e:
            return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
        except Exception as e:
            return _error_result(f"Error fetching incidents: {e}")
    incidents = [
        {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
         "short_description": _val(r.get("short_description")),
         "description": _val(r.get("description", "")),
         "state": _val(r.get("state")), "priority": _val(r.get("priority")),
         "assigned_to": _val(r.get("assigned_to")) or None,
         "sys_created_on": _val(r.get("sys_created_on"))}
        for r in records
    ]
    structured = {"type": "incidents", "total": len(incidents), "incidents": incidents}
    summary = "No incidents found." if not incidents else f"{len(incidents)} incident(s) retrieved. Widget below ↓"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sn__get_requests(limit: int = 5, number: str = "", query: str = "") -> types.CallToolResult:
    if number:
        num = number.strip().upper()
        try:
            resp = await servicenow_request(
                "GET", "/api/now/table/sc_request",
                params={"sysparm_query": f"number={num}", "sysparm_limit": 1,
                        "sysparm_fields": REQUEST_FIELDS, "sysparm_display_value": "true"},
            )
            records = resp.json().get("result", [])
        except Exception as e:
            return _error_result(f"Error looking up request {num}: {e}")
        if not records:
            return _error_result(f"Request {num} not found.")
        r = records[0]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Opening edit form for {_val(r.get('number'))}.")],
            structuredContent={"type": "form", "entity": "request", "mode": "edit",
                               "recordId": _val(r.get("sys_id")),
                               "prefill": {"short_description": _val(r.get("short_description", "")),
                                           "description": _val(r.get("description", "")),
                                           "priority": _val(r.get("priority", "3")),
                                           "approval": _val(r.get("approval", ""))}},
        )
    if query:
        try:
            records = await _text_search(
                "sc_request", query, REQUEST_FIELDS, limit,
                f"short_descriptionLIKE{query}^ORdescriptionLIKE{query}^ORDERBYDESCsys_created_on",
            )
        except Exception as e:
            return _error_result(f"Error searching requests: {e}")
    else:
        try:
            resp = await servicenow_request(
                "GET", "/api/now/table/sc_request",
                params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                        "sysparm_fields": REQUEST_FIELDS, "sysparm_display_value": "true"},
            )
            records = resp.json().get("result", [])
        except httpx.HTTPStatusError as e:
            return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
        except Exception as e:
            return _error_result(f"Error fetching requests: {e}")
    requests_list = [
        {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
         "short_description": _val(r.get("short_description")),
         "description": _val(r.get("description", "")),
         "request_state": _val(r.get("request_state")), "priority": _val(r.get("priority")),
         "approval": _val(r.get("approval")), "sys_created_on": _val(r.get("sys_created_on"))}
        for r in records
    ]
    structured = {"type": "requests", "total": len(requests_list), "requests": requests_list}
    summary = "No requests found." if not requests_list else f"{len(requests_list)} request(s) retrieved. Widget below ↓"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sn__get_request_items(request_sys_id: str) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "GET", "/api/now/table/sc_req_item",
            params={"sysparm_query": f"request={request_sys_id}",
                    "sysparm_fields": REQUEST_ITEM_FIELDS, "sysparm_display_value": "true"},
        )
        records = resp.json().get("result", [])
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching request items: {e}")

    items = [
        {"sys_id": r.get("sys_id"), "number": r.get("number"),
         "short_description": r.get("short_description"), "state": r.get("state"),
         "stage": r.get("stage"), "quantity": r.get("quantity"), "price": r.get("price")}
        for r in records
    ]
    structured = {"type": "request_items", "request_sys_id": request_sys_id,
                  "total": len(items), "items": items}
    summary = f"No request items found for request {request_sys_id}." if not items else f"{len(items)} request item(s) retrieved. Widget below ↓"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sn__get_change_requests(limit: int = 5, number: str = "", query: str = "") -> types.CallToolResult:
    if number:
        num = number.strip().upper()
        try:
            resp = await servicenow_request(
                "GET", "/api/now/table/change_request",
                params={"sysparm_query": f"number={num}", "sysparm_limit": 1,
                        "sysparm_fields": CHANGE_FIELDS, "sysparm_display_value": "true"},
            )
            records = resp.json().get("result", [])
        except Exception as e:
            return _error_result(f"Error looking up change request {num}: {e}")
        if not records:
            return _error_result(f"Change request {num} not found.")
        r = records[0]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Opening edit form for {_val(r.get('number'))}.")],
            structuredContent={"type": "form", "entity": "change_request", "mode": "edit",
                               "recordId": _val(r.get("sys_id")),
                               "prefill": {"short_description": _val(r.get("short_description", "")),
                                           "category": _val(r.get("category", "")),
                                           "risk": _val(r.get("risk", "medium")),
                                           "priority": _val(r.get("priority", "3")),
                                           "state": _val(r.get("state", ""))}},
        )
    if query:
        try:
            records = await _text_search(
                "change_request", query, CHANGE_FIELDS, limit,
                f"short_descriptionLIKE{query}^ORdescriptionLIKE{query}^ORDERBYDESCsys_created_on",
            )
        except Exception as e:
            return _error_result(f"Error searching change requests: {e}")
    else:
        try:
            resp = await servicenow_request(
                "GET", "/api/now/table/change_request",
                params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                        "sysparm_fields": CHANGE_FIELDS, "sysparm_display_value": "true"},
            )
            records = resp.json().get("result", [])
        except httpx.HTTPStatusError as e:
            return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
        except Exception as e:
            return _error_result(f"Error fetching change requests: {e}")
    items = [
        {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
         "short_description": _val(r.get("short_description")), "state": _val(r.get("state")),
         "priority": _val(r.get("priority")), "risk": _val(r.get("risk")),
         "category": _val(r.get("category")), "assigned_to": _val(r.get("assigned_to")) or None,
         "sys_created_on": _val(r.get("sys_created_on"))}
        for r in records
    ]
    structured = {"type": "change_requests", "total": len(items), "items": items}
    summary = "No change requests found." if not items else f"{len(items)} change request(s) retrieved. Widget below ↓"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sn__get_problems(limit: int = 5, number: str = "", query: str = "") -> types.CallToolResult:
    PROBLEM_FIELDS = "sys_id,number,short_description,description,state,priority,assigned_to,sys_created_on"
    if number:
        num = number.strip().upper()
        try:
            resp = await servicenow_request(
                "GET", "/api/now/table/problem",
                params={"sysparm_query": f"number={num}", "sysparm_limit": 1,
                        "sysparm_fields": PROBLEM_FIELDS, "sysparm_display_value": "true"},
            )
            records = resp.json().get("result", [])
        except Exception as e:
            return _error_result(f"Error looking up problem {num}: {e}")
        if not records:
            return _error_result(f"Problem {num} not found.")
        r = records[0]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Opening edit form for {_val(r.get('number'))}.")],
            structuredContent={"type": "form", "entity": "problem", "mode": "edit",
                               "recordId": _val(r.get("sys_id")),
                               "prefill": {"short_description": _val(r.get("short_description", "")),
                                           "description": _val(r.get("description", "")),
                                           "priority": _val(r.get("priority", "3")),
                                           "state": _val(r.get("state", ""))}},
        )
    if query:
        try:
            records = await _text_search(
                "problem", query, PROBLEM_FIELDS, limit,
                f"short_descriptionLIKE{query}^ORdescriptionLIKE{query}^ORDERBYDESCsys_created_on",
            )
        except Exception as e:
            return _error_result(f"Error searching problems: {e}")
    else:
        try:
            resp = await servicenow_request(
                "GET", "/api/now/table/problem",
                params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                        "sysparm_fields": PROBLEM_FIELDS, "sysparm_display_value": "true"},
            )
            records = resp.json().get("result", [])
        except httpx.HTTPStatusError as e:
            return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
        except Exception as e:
            return _error_result(f"Error fetching problems: {e}")
    items = [
        {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
         "short_description": _val(r.get("short_description")), "state": _val(r.get("state")),
         "priority": _val(r.get("priority")), "assigned_to": _val(r.get("assigned_to")) or None,
         "sys_created_on": _val(r.get("sys_created_on"))}
        for r in records
    ]
    structured = {"type": "problems", "total": len(items), "items": items}
    summary = "No problems found." if not items else f"{len(items)} problem(s) retrieved. Widget below ↓"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sn__get_pending_approvals(limit: int = 10) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "GET", "/api/now/table/sysapproval_approver",
            params={"sysparm_limit": limit,
                    "sysparm_query": "state=requested^ORDERBYDESCsys_created_on",
                    "sysparm_fields": "sys_id,approver,sysapproval,state,due_date,sys_created_on",
                    "sysparm_display_value": "true"},
        )
        records = resp.json().get("result", [])
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching approvals: {e}")

    items = [
        {"sys_id": _val(r.get("sys_id")), "approver": _val(r.get("approver")),
         "document": _val(r.get("sysapproval")), "state": _val(r.get("state")),
         "due_date": _val(r.get("due_date")), "created_on": _val(r.get("sys_created_on"))}
        for r in records
    ]
    structured = {"type": "approvals", "total": len(items), "items": items}
    summary = "No pending approvals." if not items else f"{len(items)} pending approval(s). Widget below ↓"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sn__get_service_catalog_items(limit: int = 10) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "GET", "/api/now/table/sc_cat_item",
            params={"sysparm_limit": limit, "sysparm_query": "active=true^ORDERBYname",
                    "sysparm_fields": "sys_id,name,short_description,category,price,sys_class_name",
                    "sysparm_display_value": "true"},
        )
        records = resp.json().get("result", [])
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching service catalog: {e}")

    items = [
        {"sys_id": _val(r.get("sys_id")), "name": _val(r.get("name")),
         "short_description": _val(r.get("short_description")),
         "category": _val(r.get("category")), "price": _val(r.get("price"))}
        for r in records
    ]
    structured = {"type": "service_catalog", "total": len(items), "items": items}
    summary = "No catalog items found." if not items else f"{len(items)} catalog item(s) retrieved. Widget below ↓"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sn__get_knowledge_articles(query: str = "", limit: int = 5) -> types.CallToolResult:
    params: dict = {
        "sysparm_limit": limit, "sysparm_display_value": "true",
        "sysparm_fields": "sys_id,number,short_description,text,kb_category,author,sys_updated_on,workflow_state",
        "sysparm_query": "workflow_state=published^ORDERBYDESCsys_updated_on",
    }
    if query:
        safe_q = _sn_escape(query)
        params["sysparm_query"] = (
            f"short_descriptionLIKE{safe_q}^ORtextLIKE{safe_q}"
            "^workflow_state=published^ORDERBYDESCsys_updated_on"
        )
    try:
        resp = await servicenow_request("GET", "/api/now/table/kb_knowledge", params=params)
        records = resp.json().get("result", [])
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to fetch knowledge articles: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching knowledge articles: {e}")

    items = [
        {"sys_id": r.get("sys_id", ""), "number": _val(r.get("number", "")),
         "short_description": _val(r.get("short_description", "")),
         "category": _val(r.get("kb_category", "")), "author": _val(r.get("author", "")),
         "updated_on": _val(r.get("sys_updated_on", "")), "state": _val(r.get("workflow_state", ""))}
        for r in records
    ]
    structured = {"type": "knowledge_articles", "total": len(items), "items": items}
    summary = "No knowledge articles found." if not items else f"{len(items)} knowledge article(s) retrieved. Widget below ↓"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ── Write tools ───────────────────────────────────────────────────────────────

async def sn__create_incident(
    short_description: str, description: str = "", priority: str = "3", category: str = ""
) -> types.CallToolResult:
    body: dict = {"short_description": short_description, "priority": priority}
    if description: body["description"] = description
    if category: body["category"] = category
    try:
        resp = await servicenow_request("POST", "/api/now/table/incident", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to create incident: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error creating incident: {e}")
    number = _val(record.get("number", ""))
    try:
        incidents = await _fetch_incidents()
    except Exception as exc:
        log.warning("sn__create_incident_refresh_failed", error=str(exc))
        incidents = []
    structured = {"type": "incidents", "total": len(incidents), "incidents": incidents,
                  "_createdId": record.get("sys_id")}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Incident {number} created. Refreshed list returned.")],
        structuredContent=structured,
    )


async def sn__create_request(
    short_description: str, description: str = "", priority: str = "3"
) -> types.CallToolResult:
    body: dict = {"short_description": short_description, "priority": priority}
    if description: body["description"] = description
    try:
        resp = await servicenow_request("POST", "/api/now/table/sc_request", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to create request: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error creating request: {e}")
    number = _val(record.get("number", ""))
    try:
        requests_list = await _fetch_requests()
    except Exception as exc:
        log.warning("sn__create_request_refresh_failed", error=str(exc))
        requests_list = []
    structured = {"type": "requests", "total": len(requests_list), "requests": requests_list,
                  "_createdId": record.get("sys_id")}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Request {number} created. Refreshed list returned.")],
        structuredContent=structured,
    )


async def sn__create_change_request(
    short_description: str, category: str = "Normal", risk: str = "medium", priority: str = "3"
) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "POST", "/api/now/table/change_request",
            json_body={"short_description": short_description, "category": category,
                       "risk": risk, "priority": priority},
        )
        resp.raise_for_status()
        created = resp.json().get("result", {})
        new_id = _val(created.get("number")) or created.get("sys_id", "")
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error creating change request: {e}")

    try:
        refresh_resp = await servicenow_request(
            "GET", "/api/now/table/change_request",
            params={"sysparm_limit": 5, "sysparm_query": "ORDERBYDESCsys_created_on",
                    "sysparm_fields": CHANGE_FIELDS, "sysparm_display_value": "true"},
        )
        items = [
            {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
             "short_description": _val(r.get("short_description")), "state": _val(r.get("state")),
             "priority": _val(r.get("priority")), "risk": _val(r.get("risk"))}
            for r in refresh_resp.json().get("result", [])
        ]
    except Exception as exc:
        log.warning("sn__create_change_request_list_refresh_failed", error=str(exc))
        items = []

    structured = {"type": "change_requests", "total": len(items), "items": items, "_createdId": new_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Change request {new_id} created. Refreshed list returned.")],
        structuredContent=structured,
    )


async def sn__update_change_request(
    sys_id: str, short_description: str | None = None, category: str | None = None,
    risk: str | None = None, priority: str | None = None
) -> types.CallToolResult:
    body: dict = {}
    if short_description is not None: body["short_description"] = short_description
    if category is not None: body["category"] = category
    if risk is not None: body["risk"] = risk
    if priority is not None: body["priority"] = priority
    if not body:
        return _error_result("No fields to update. Provide short_description, category, risk, or priority.")
    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/change_request/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to update change request: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating change request: {e}")
    number = _val(record.get("number", ""))
    try:
        refresh_resp = await servicenow_request(
            "GET", "/api/now/table/change_request",
            params={"sysparm_limit": 5, "sysparm_query": "ORDERBYDESCsys_created_on",
                    "sysparm_fields": CHANGE_FIELDS, "sysparm_display_value": "true"},
        )
        items = [
            {"sys_id": _val(r.get("sys_id")), "number": _val(r.get("number")),
             "short_description": _val(r.get("short_description")), "state": _val(r.get("state")),
             "priority": _val(r.get("priority")), "risk": _val(r.get("risk"))}
            for r in refresh_resp.json().get("result", [])
        ]
    except Exception as exc:
        log.warning("sn__update_change_request_refresh_failed", error=str(exc))
        items = []
    structured = {"type": "change_requests", "total": len(items), "items": items, "_updatedId": sys_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Change request {number} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


async def sn__update_incident(
    sys_id: str, description: str | None = None, priority: str | None = None,
    work_note: str | None = None
) -> types.CallToolResult:
    body: dict = {}
    if description is not None: body["description"] = description
    if priority is not None: body["priority"] = priority
    if work_note is not None: body["work_notes"] = work_note
    if not body:
        return _error_result("No fields to update. Provide description, priority, or work_note.")
    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/incident/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to update incident: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating incident: {e}")
    number = _val(record.get("number", ""))
    try:
        incidents = await _fetch_incidents()
    except Exception as exc:
        log.warning("sn__update_incident_refresh_failed", error=str(exc))
        incidents = []
    structured = {"type": "incidents", "total": len(incidents), "incidents": incidents,
                  "_updatedId": sys_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Incident {number} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


async def sn__update_request(sys_id: str, approval: str | None = None) -> types.CallToolResult:
    body: dict = {}
    if approval is not None: body["approval"] = approval
    if not body:
        return _error_result("No fields to update. Provide approval.")
    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/sc_request/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to update request: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating request: {e}")
    number = _val(record.get("number", ""))
    try:
        requests_list = await _fetch_requests()
    except Exception as exc:
        log.warning("sn__update_request_refresh_failed", error=str(exc))
        requests_list = []
    structured = {"type": "requests", "total": len(requests_list), "requests": requests_list,
                  "_updatedId": sys_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Request {number} approval updated. Refreshed list returned.")],
        structuredContent=structured,
    )


async def sn__update_request_item(sys_id: str, quantity: str | None = None) -> types.CallToolResult:
    body: dict = {}
    if quantity is not None: body["quantity"] = quantity
    if not body:
        return _error_result("No fields to update. Provide quantity.")
    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/sc_req_item/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to update request item: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating request item: {e}")
    structured = {"type": "updated", "record_type": "request_item", "sys_id": sys_id,
                  "number": record.get("number"),
                  "message": f"Request item {record.get('number', '')} quantity updated successfully"}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
        structuredContent=structured,
    )


async def sn__update_problem(
    sys_id: str, short_description: str | None = None, priority: str | None = None,
    state: str | None = None, work_note: str | None = None
) -> types.CallToolResult:
    body: dict = {}
    if short_description is not None: body["short_description"] = short_description
    if priority is not None: body["priority"] = priority
    if state is not None: body["state"] = state
    if work_note is not None: body["work_notes"] = work_note
    if not body:
        return _error_result("No fields to update. Provide short_description, priority, state, or work_note.")
    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/problem/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to update problem: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating problem: {e}")
    number = _val(record.get("number", ""))
    try:
        items = await _fetch_problems()
    except Exception as exc:
        log.warning("sn__update_problem_refresh_failed", error=str(exc))
        items = []
    structured = {"type": "problems", "total": len(items), "items": items, "_updatedId": sys_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Problem {number} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


async def sn__create_problem(
    short_description: str, description: str = "", priority: str = "3",
) -> types.CallToolResult:
    body: dict = {"short_description": short_description}
    if description: body["description"] = description
    if priority:    body["priority"] = priority
    try:
        resp = await servicenow_request("POST", "/api/now/table/problem", json_body=body)
        new_id = resp.json().get("result", {}).get("sys_id", "")
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error creating problem: {e}")
    try:
        items = await _fetch_problems()
    except Exception as exc:
        log.warning("sn__create_problem_refresh_failed", error=str(exc))
        items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Problem created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "problems", "total": len(items), "items": items, "_createdId": new_id},
    )


async def sn__resolve_incident(sys_id: str, close_code: str, close_notes: str) -> types.CallToolResult:
    body = {"state": "6", "close_code": close_code, "close_notes": close_notes}
    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/incident/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to resolve incident: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error resolving incident: {e}")
    number = _val(record.get("number", ""))
    structured = {"type": "resolved", "record_type": "incident", "sys_id": sys_id,
                  "number": number, "close_code": close_code,
                  "message": f"Incident {number} resolved ({close_code}): {close_notes}"}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
        structuredContent=structured,
    )


# ── Form tools ────────────────────────────────────────────────────────────────

async def sn__create_incident_form() -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Opening Incident creation form.")],
        structuredContent={"type": "form", "entity": "incident"},
    )


async def sn__create_request_form() -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Opening Request creation form.")],
        structuredContent={"type": "form", "entity": "request"},
    )


async def sn__get_change_tasks(change_sys_id: str) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "GET", "/api/now/table/change_task",
            params={"sysparm_query": f"change_request={change_sys_id}^ORDERBYDESCsys_created_on",
                    "sysparm_fields": "sys_id,short_description,state,priority,assigned_to,sys_created_on",
                    "sysparm_display_value": "true"},
        )
        records = resp.json().get("result", [])
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching change tasks: {e}")

    items = [
        {"sys_id": _val(r.get("sys_id")), "short_description": _val(r.get("short_description")),
         "state": _val(r.get("state")), "priority": _val(r.get("priority")),
         "assigned_to": _val(r.get("assigned_to")) or None,
         "sys_created_on": _val(r.get("sys_created_on"))}
        for r in records
    ]
    structured = {"type": "change_tasks", "change_sys_id": change_sys_id, "total": len(items), "items": items}
    summary = f"Found {len(items)} change task(s)." if items else "No change tasks found."
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sn__get_hr_cases(sys_id: str = "", limit: int = 10) -> types.CallToolResult:
    if sys_id:
        HR_FIELDS = "sys_id,number,short_description,description,state,priority"
        try:
            resp = await servicenow_request(
                "GET", f"/api/now/table/sn_hr_core_case/{sys_id}",
                params={"sysparm_fields": HR_FIELDS, "sysparm_display_value": "true"},
            )
            r = resp.json().get("result", {})
        except Exception as e:
            return _error_result(f"Error fetching HR case: {e}")
        prefill = {"subject": _val(r.get("short_description")), "description": _val(r.get("description")),
                   "priority": _val(r.get("priority")), "state": _val(r.get("state"))}
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"HR case {sys_id} ready to edit.")],
            structuredContent={"type": "form", "entity": "hr_case", "mode": "edit",
                               "recordId": sys_id, "prefill": prefill},
        )
    try:
        items = await _fetch_hr_cases(limit)
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error fetching HR cases: {e}")
    summary = f"Found {len(items)} HR case(s)." if items else "No HR cases found."
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent={"type": "hr_cases", "total": len(items), "items": items},
    )


async def sn__create_hr_case(
    subject: str, description: str = "", priority: str = "3"
) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "POST", "/api/now/table/sn_hr_core_case",
            json_body={"short_description": subject, "description": description, "priority": priority},
        )
        new_id = resp.json().get("result", {}).get("sys_id", "")
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error creating HR case: {e}")
    try:
        items = await _fetch_hr_cases()
    except Exception as exc:
        log.warning("sn__create_hr_case_refresh_failed", error=str(exc))
        items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"HR case created: {subject}")],
        structuredContent={"type": "hr_cases", "total": len(items), "items": items, "_createdId": new_id},
    )


async def sn__update_hr_case(
    sys_id: str, subject: str | None = None, priority: str | None = None,
    state: str | None = None, work_note: str | None = None
) -> types.CallToolResult:
    body: dict = {}
    if subject is not None: body["short_description"] = subject
    if priority is not None: body["priority"] = priority
    if state is not None: body["state"] = state
    if work_note is not None: body["work_notes"] = work_note
    if not body:
        return _error_result("No fields to update. Provide subject, priority, state, or work_note.")
    try:
        await servicenow_request("PATCH", f"/api/now/table/sn_hr_core_case/{sys_id}", json_body=body)
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating HR case: {e}")
    try:
        items = await _fetch_hr_cases()
    except Exception as exc:
        log.warning("sn__update_hr_case_refresh_failed", error=str(exc))
        items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="HR case updated. Refreshed list returned.")],
        structuredContent={"type": "hr_cases", "total": len(items), "items": items, "_updatedId": sys_id},
    )


async def sn__approve_record(sys_id: str) -> types.CallToolResult:
    try:
        await servicenow_request(
            "PATCH", f"/api/now/table/sysapproval_approver/{sys_id}",
            json_body={"state": "approved", "comments": "Approved via M365 Copilot"},
        )
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error approving record: {e}")
    try:
        approvals = await _fetch_approvals()
    except Exception as exc:
        log.warning("sn__approve_record_refresh_failed", error=str(exc))
        approvals = []
    structured = {"type": "approvals", "total": len(approvals), "items": approvals}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Approval granted. Refreshed list returned.")],
        structuredContent=structured,
    )


async def sn__reject_record(sys_id: str, comments: str = "") -> types.CallToolResult:
    try:
        await servicenow_request(
            "PATCH", f"/api/now/table/sysapproval_approver/{sys_id}",
            json_body={"state": "rejected", "comments": comments or "Rejected via M365 Copilot"},
        )
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error rejecting record: {e}")
    try:
        approvals = await _fetch_approvals()
    except Exception as exc:
        log.warning("sn__reject_record_refresh_failed", error=str(exc))
        approvals = []
    structured = {"type": "approvals", "total": len(approvals), "items": approvals}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Approval rejected. Refreshed list returned.")],
        structuredContent=structured,
    )


# ── Prompts ───────────────────────────────────────────────────────────────────

def prompt_show_incidents() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text",
        text="Show me the latest incidents from ServiceNow. Call get_incidents with limit=5. Present the results in the widget."))]


def prompt_show_requests() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text",
        text="Show me the latest service requests from ServiceNow. Call get_requests with limit=5. Present the results in the widget."))]


def prompt_incident_summary() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text",
        text="Give me a summary of the latest incidents from ServiceNow. Call get_incidents with limit=5. Show the widget, then provide a brief written summary: how many are critical/high priority, how many are unassigned, and any patterns in categories."))]


# ── _TOOL_SPECS_LIST registry ───────────────────────────────────────────────────────

_TOOL_SPECS_LIST = [
    {"name": "sn__get_incidents",
     "description": "Retrieve incidents from ServiceNow. Pass 'number' (e.g. INC0010001) to open the edit form for that incident. Pass 'query' to search by text. No params returns the latest 'limit' incidents (default 5).",
     "handler": sn__get_incidents},
    {"name": "sn__get_requests",
     "description": "Retrieve service requests from ServiceNow. Pass 'number' (e.g. REQ0010001) to open the edit form for that request. Pass 'query' to search by text. No params returns the latest 'limit' requests (default 5).",
     "handler": sn__get_requests},
    {"name": "sn__get_request_items",
     "description": "Retrieve request items for a specific service request. request_sys_id is the sys_id of the parent sc_request record. Called from the widget when expanding a request row.",
     "handler": sn__get_request_items},
    {"name": "sn__get_change_requests",
     "description": "Get Change Requests from ServiceNow. Pass 'number' (e.g. CHG0010001) to open the edit form for that change request. Pass 'query' to search by text. No params returns the latest 'limit' records (default 5).",
     "handler": sn__get_change_requests},
    {"name": "sn__get_problems",
     "description": "Get Problem records from ServiceNow. Pass 'number' (e.g. PRB0010001) to open the edit form for that problem. Pass 'query' to search by text. No params returns the latest 'limit' problems (default 5).",
     "handler": sn__get_problems},
    {"name": "sn__get_pending_approvals",
     "description": "Get pending approval requests in ServiceNow. Returns up to 'limit' approvals (default 10) with approver, document, and state.",
     "handler": sn__get_pending_approvals},
    {"name": "sn__get_service_catalog_items",
     "description": "Get available items from the ServiceNow Service Catalog. Returns up to 'limit' catalog items (default 10).",
     "handler": sn__get_service_catalog_items},
    {"name": "sn__get_knowledge_articles",
     "description": "Search knowledge articles in ServiceNow. Returns articles from the kb_knowledge table matching the query.",
     "handler": sn__get_knowledge_articles},
    {"name": "sn__create_incident",
     "description": "Create a new incident in ServiceNow. Requires short_description. Optional: description, priority (1-4), category.",
     "handler": sn__create_incident},
    {"name": "sn__create_request",
     "description": "Create a new service request in ServiceNow. Requires short_description. Optional: description, priority (1-4).",
     "handler": sn__create_request},
    {"name": "sn__create_change_request",
     "description": "Create a new Change Request in ServiceNow. Required: short_description. Optional: category, risk, priority.",
     "handler": sn__create_change_request},
    {"name": "sn__update_change_request",
     "description": "Update an existing Change Request in ServiceNow. Requires sys_id. Optional editable fields: short_description, category, risk, priority.",
     "handler": sn__update_change_request},
    {"name": "sn__update_incident",
     "description": "Update an existing incident in ServiceNow. Requires sys_id. Editable fields: description, priority, work_note (appended as internal journal entry).",
     "handler": sn__update_incident},
    {"name": "sn__update_request",
     "description": "Update an existing service request in ServiceNow. Requires sys_id. Editable field: approval.",
     "handler": sn__update_request},
    {"name": "sn__update_request_item",
     "description": "Update an existing request item in ServiceNow. Requires sys_id. Editable field: quantity.",
     "handler": sn__update_request_item},
    {"name": "sn__update_problem",
     "description": "Update an existing Problem record in ServiceNow. Requires sys_id. Editable fields: short_description, priority, state, work_note (appended as internal journal entry).",
     "handler": sn__update_problem},
    {"name": "sn__resolve_incident",
     "description": "Resolve an incident in ServiceNow by setting state to Resolved. Requires close_code and close_notes.",
     "handler": sn__resolve_incident},
    {"name": "sn__create_incident_form",
     "description": "Use this when the user asks to create or log a new ServiceNow incident. Opens the interactive incident creation form.",
     "handler": sn__create_incident_form},
    {"name": "sn__create_request_form",
     "description": "Use this when the user asks to raise or create a new ServiceNow service request. Opens the interactive request creation form.",
     "handler": sn__create_request_form},
    {"name": "sn__get_change_tasks",
     "description": "Get change tasks for a specific change request. Requires change_sys_id (the sys_id of the parent change_request). Called from the widget when expanding a change request row.",
     "handler": sn__get_change_tasks},
    {"name": "sn__create_problem",
     "description": "Create a new Problem record in ServiceNow. Requires short_description. Optional: description, priority (1=Critical, 2=High, 3=Moderate, 4=Low).",
     "handler": sn__create_problem},
    {"name": "sn__get_hr_cases",
     "description": "Get HR cases from ServiceNow. Pass sys_id for exact record lookup → opens edit form. No params returns the latest HR cases.",
     "handler": sn__get_hr_cases},
    {"name": "sn__create_hr_case",
     "description": "Create a new HR case in ServiceNow. Requires subject. Optional: description, priority (1=Critical, 2=High, 3=Moderate, 4=Low).",
     "handler": sn__create_hr_case},
    {"name": "sn__update_hr_case",
     "description": "Update an existing HR case in ServiceNow. Requires sys_id. Editable fields: subject, priority, state, work_note.",
     "handler": sn__update_hr_case},
    {"name": "sn__approve_record",
     "description": "Approve a pending approval in ServiceNow. Requires sys_id of the sysapproval_approver record.",
     "handler": sn__approve_record},
    {"name": "sn__reject_record",
     "description": "Reject a pending approval in ServiceNow. Requires sys_id. Optional: comments explaining the rejection.",
     "handler": sn__reject_record},
]

PROMPT_SPECS = [
    {"name": "show_incidents", "description": "Show the latest incidents from ServiceNow.", "handler": prompt_show_incidents},
    {"name": "show_requests", "description": "Show the latest service requests from ServiceNow.", "handler": prompt_show_requests},
    {"name": "incident_summary", "description": "Get a summary analysis of recent incidents.", "handler": prompt_incident_summary},
]


# ── Aliases for server.py imports ────────────────────────────────────────────
from mcp.types import PromptMessage as _PM, TextContent as _TC  # noqa: E402

TOOL_SPECS = _TOOL_SPECS_LIST

PROMPT_SPECS = [
    {
        "name": "my-incidents",
        "description": "Show the latest open incidents from ServiceNow.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me the latest incidents from ServiceNow. "
            "Call sn__get_incidents and display the results in the widget."
        )))],
    },
    {
        "name": "my-approvals",
        "description": "Show pending approval requests assigned to you in ServiceNow.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me my pending approvals from ServiceNow. "
            "Call sn__get_pending_approvals and display the results in the widget."
        )))],
    },
    {
        "name": "it-snapshot",
        "description": "Get a live summary of incidents, requests, change requests, and problems.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Give me an IT snapshot. "
            "Call sn__get_incidents, sn__get_requests, sn__get_change_requests, and sn__get_problems "
            "— these are independent. "
            "Once all four return, summarise: open incident count by priority, pending requests, "
            "in-flight change requests, and open problems."
        )))],
    },
    {
        "name": "resolve-incident",
        "description": "Pick an open incident and mark it resolved with close code and notes.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to resolve an incident. Call sn__get_incidents to show the latest open incidents. "
            "Ask me which incident to resolve, then ask for the close code and resolution notes. "
            "Then call sn__resolve_incident with sys_id, close_code, and close_notes."
        )))],
    },
    {
        "name": "search-and-log",
        "description": "Search the knowledge base for a topic and add a work note to a related incident.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to find a knowledge article and log it on an incident. "
            "Ask me for the search topic, then call sn__get_knowledge_articles with that query. "
            "Also call sn__get_incidents to show open incidents — these are independent. "
            "Ask me which article and which incident to link, then call sn__update_incident "
            "with the incident sys_id and a work_note referencing the article."
        )))],
    },
    {
        "name": "raise-change",
        "description": "Browse the service catalog and raise a new change request.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to raise a change request. Call sn__get_service_catalog_items to show available items. "
            "Ask me what change I need to make. "
            "Then call sn__create_change_request with the short_description, category, and risk level."
        )))],
    },
]