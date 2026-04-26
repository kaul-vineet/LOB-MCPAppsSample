"""ServiceNow tool handlers + TOOL_SPECS registry."""
import httpx
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


def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


# ── Read tools ────────────────────────────────────────────────────────────────

async def sn__get_incidents(limit: int = 5) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "GET", "/api/now/table/incident",
            params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                    "sysparm_fields": INCIDENT_FIELDS, "sysparm_display_value": "true"},
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


async def sn__get_requests(limit: int = 5) -> types.CallToolResult:
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
    if not requests_list:
        summary = "No requests found."
    else:
        lines = [f"Found {len(requests_list)} request(s):"]
        for req in requests_list:
            lines.append(f"- {req['number']} | {req['request_state']} | {req['priority']} | {req['short_description']}")
        summary = "\n".join(lines)
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


async def sn__get_change_requests(limit: int = 5) -> types.CallToolResult:
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
    if not items:
        summary = "No change requests found."
    else:
        lines = [f"Found {len(items)} change request(s):"]
        for cr in items:
            lines.append(f"- {cr['number']} | {cr['priority']} | {cr['state']} | {cr['short_description']}")
        summary = "\n".join(lines)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def sn__get_problems(limit: int = 5) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "GET", "/api/now/table/problem",
            params={"sysparm_limit": limit, "sysparm_query": "ORDERBYDESCsys_created_on",
                    "sysparm_fields": "sys_id,number,short_description,state,priority,assigned_to,sys_created_on",
                    "sysparm_display_value": "true"},
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
    if not items:
        summary = "No problems found."
    else:
        lines = [f"Found {len(items)} problem(s):"]
        for p in items:
            lines.append(f"- {p['number']} | P{p['priority']} | {p['state']} | {p['short_description']}")
        summary = "\n".join(lines)
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
    if not items:
        summary = "No pending approvals."
    else:
        lines = [f"Found {len(items)} pending approval(s):"]
        for a in items:
            lines.append(f"- {a['document']} | approver: {a['approver']} | due: {a['due_date'] or 'N/A'}")
        summary = "\n".join(lines)
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
    if not items:
        summary = "No catalog items found."
    else:
        lines = [f"Found {len(items)} catalog item(s):"]
        for item in items:
            lines.append(f"- {item['name']} | {item['category']} | {item['price'] or 'free'}")
        summary = "\n".join(lines)
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
        params["sysparm_query"] = (
            f"short_descriptionLIKE{query}^ORtextLIKE{query}"
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
    lines = [f"Found {len(items)} knowledge article(s){' matching: ' + query if query else ''}:"]
    for a in items:
        lines.append(f"- {a['number']}: {a['short_description']} (Category: {a['category']})")
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(lines))],
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
    structured = {"type": "created", "record_type": "incident",
                  "sys_id": record.get("sys_id"), "number": record.get("number"),
                  "message": f"Incident {record.get('number', '')} created successfully"}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
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
    structured = {"type": "created", "record_type": "request",
                  "sys_id": record.get("sys_id"), "number": record.get("number"),
                  "message": f"Request {record.get('number', '')} created successfully"}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
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
    except Exception:
        items = []

    structured = {"type": "change_requests", "total": len(items), "items": items, "_createdId": new_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Change request {new_id} created. Refreshed list returned.")],
        structuredContent=structured,
    )


async def sn__update_incident(
    sys_id: str, description: str | None = None, priority: str | None = None
) -> types.CallToolResult:
    body: dict = {}
    if description is not None: body["description"] = description
    if priority is not None: body["priority"] = priority
    if not body:
        return _error_result("No fields to update. Provide description or priority.")
    try:
        resp = await servicenow_request("PATCH", f"/api/now/table/incident/{sys_id}", json_body=body)
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to update incident: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating incident: {e}")
    structured = {"type": "updated", "record_type": "incident", "sys_id": sys_id,
                  "number": record.get("number"),
                  "message": f"Incident {record.get('number', '')} updated successfully"}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
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
    structured = {"type": "updated", "record_type": "request", "sys_id": sys_id,
                  "number": record.get("number"),
                  "message": f"Request {record.get('number', '')} approval updated successfully"}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=structured["message"])],
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


async def sn__add_work_note(sys_id: str, work_note: str) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "PATCH", f"/api/now/table/incident/{sys_id}", json_body={"work_notes": work_note}
        )
        record = resp.json().get("result", {})
    except httpx.HTTPStatusError as e:
        return _error_result(f"Failed to add work note: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error adding work note: {e}")
    number = _val(record.get("number", ""))
    structured = {"type": "work_note_added", "record_type": "incident", "sys_id": sys_id,
                  "number": number,
                  "message": f"Work note added to incident {number}: {work_note[:80]}{'...' if len(work_note) > 80 else ''}"}
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


async def sn__create_hr_case(
    subject: str, description: str = "", priority: str = "3"
) -> types.CallToolResult:
    try:
        resp = await servicenow_request(
            "POST", "/api/now/table/sn_hr_core_case",
            json={"short_description": subject, "description": description, "priority": priority},
        )
        new_id = resp.json().get("result", {}).get("sys_id", "")
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error creating HR case: {e}")

    structured = {"type": "hr_case_created", "sys_id": new_id, "subject": subject}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"HR case created: {subject}")],
        structuredContent=structured,
    )


async def sn__update_hr_case(
    sys_id: str, subject: str | None = None, priority: str | None = None, state: str | None = None
) -> types.CallToolResult:
    body: dict = {}
    if subject is not None:
        body["short_description"] = subject
    if priority is not None:
        body["priority"] = priority
    if state is not None:
        body["state"] = state
    try:
        await servicenow_request("PATCH", f"/api/now/table/sn_hr_core_case/{sys_id}", json=body)
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error updating HR case: {e}")

    structured = {"type": "hr_case_updated", "sys_id": sys_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="HR case updated.")],
        structuredContent=structured,
    )


async def sn__add_hr_work_note(sys_id: str, work_note: str) -> types.CallToolResult:
    try:
        await servicenow_request(
            "PATCH", f"/api/now/table/sn_hr_core_case/{sys_id}",
            json={"work_notes": work_note},
        )
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error adding HR work note: {e}")

    structured = {"type": "hr_work_note_added", "sys_id": sys_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Work note added to HR case.")],
        structuredContent=structured,
    )


async def sn__hr_approve_record(sys_id: str) -> types.CallToolResult:
    try:
        await servicenow_request(
            "PATCH", f"/api/now/table/sysapproval_approver/{sys_id}",
            json={"state": "approved", "comments": "Approved via M365 Copilot"},
        )
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error approving HR record: {e}")

    structured = {"type": "hr_record_approved", "sys_id": sys_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="HR record approved.")],
        structuredContent=structured,
    )


async def sn__hr_reject_record(sys_id: str, comments: str = "") -> types.CallToolResult:
    try:
        await servicenow_request(
            "PATCH", f"/api/now/table/sysapproval_approver/{sys_id}",
            json={"state": "rejected", "comments": comments or "Rejected via M365 Copilot"},
        )
    except httpx.HTTPStatusError as e:
        return _error_result(f"ServiceNow API error: {e.response.status_code} {e.response.text}")
    except Exception as e:
        return _error_result(f"Error rejecting HR record: {e}")

    structured = {"type": "hr_record_rejected", "sys_id": sys_id}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="HR record rejected.")],
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


# ── TOOL_SPECS registry ───────────────────────────────────────────────────────

TOOL_SPECS = [
    {"name": "sn__get_incidents",
     "description": "Retrieve the latest incidents from ServiceNow. Returns up to 'limit' incidents (default 5), ordered by creation date descending.",
     "handler": sn__get_incidents},
    {"name": "sn__get_requests",
     "description": "Retrieve the latest service requests from ServiceNow. Returns up to 'limit' requests (default 5), ordered by creation date descending.",
     "handler": sn__get_requests},
    {"name": "sn__get_request_items",
     "description": "Retrieve request items for a specific service request. request_sys_id is the sys_id of the parent sc_request record. Called from the widget when expanding a request row.",
     "handler": sn__get_request_items},
    {"name": "sn__get_change_requests",
     "description": "Get the latest Change Requests from ServiceNow. Returns up to 'limit' records (default 5) ordered by creation date descending.",
     "handler": sn__get_change_requests},
    {"name": "sn__get_problems",
     "description": "Get the latest Problem records from ServiceNow. Returns up to 'limit' problems (default 5) ordered by creation date descending.",
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
    {"name": "sn__update_incident",
     "description": "Update an existing incident in ServiceNow. Requires sys_id. Editable fields: description, priority.",
     "handler": sn__update_incident},
    {"name": "sn__update_request",
     "description": "Update an existing service request in ServiceNow. Requires sys_id. Editable field: approval.",
     "handler": sn__update_request},
    {"name": "sn__update_request_item",
     "description": "Update an existing request item in ServiceNow. Requires sys_id. Editable field: quantity.",
     "handler": sn__update_request_item},
    {"name": "sn__resolve_incident",
     "description": "Resolve an incident in ServiceNow by setting state to Resolved. Requires close_code and close_notes.",
     "handler": sn__resolve_incident},
    {"name": "sn__add_work_note",
     "description": "Add a work note to an existing incident in ServiceNow. Work notes are internal comments visible only to IT staff.",
     "handler": sn__add_work_note},
    {"name": "sn__create_incident_form",
     "description": "Opens a form to create a new ServiceNow Incident. The user fills in details and submits.",
     "handler": sn__create_incident_form},
    {"name": "sn__create_request_form",
     "description": "Opens a form to create a new ServiceNow Request. The user fills in details and submits.",
     "handler": sn__create_request_form},
    {"name": "sn__get_change_tasks",
     "description": "Get change tasks for a specific change request. Requires change_sys_id (the sys_id of the parent change_request). Called from the widget when expanding a change request row.",
     "handler": sn__get_change_tasks},
    {"name": "sn__create_hr_case",
     "description": "Create a new HR case in ServiceNow. Requires subject. Optional: description, priority (1=Critical, 2=High, 3=Moderate, 4=Low).",
     "handler": sn__create_hr_case},
    {"name": "sn__update_hr_case",
     "description": "Update an existing HR case in ServiceNow. Requires sys_id. Optional editable fields: subject, priority, state.",
     "handler": sn__update_hr_case},
    {"name": "sn__add_hr_work_note",
     "description": "Add a work note to an existing HR case in ServiceNow. Requires sys_id and work_note text.",
     "handler": sn__add_hr_work_note},
    {"name": "sn__hr_approve_record",
     "description": "Approve an HR approval record in ServiceNow. Requires sys_id of the sysapproval_approver record.",
     "handler": sn__hr_approve_record},
    {"name": "sn__hr_reject_record",
     "description": "Reject an HR approval record in ServiceNow. Requires sys_id. Optional: comments explaining the rejection.",
     "handler": sn__hr_reject_record},
]

PROMPT_SPECS = [
    {"name": "show_incidents", "description": "Show the latest incidents from ServiceNow.", "handler": prompt_show_incidents},
    {"name": "show_requests", "description": "Show the latest service requests from ServiceNow.", "handler": prompt_show_requests},
    {"name": "incident_summary", "description": "Get a summary analysis of recent incidents.", "handler": prompt_incident_summary},
]
