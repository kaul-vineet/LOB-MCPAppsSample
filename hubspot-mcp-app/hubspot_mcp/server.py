"""
HubSpot Marketing MCP Server — 7 tools for Marketing Emails, Lists & Contacts.

Single entry point: get_emails. All drill-down is widget-driven via callTool.
"""

import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
from starlette.middleware.cors import CORSMiddleware

from .hubspot_client import HubSpotAPIError, HubSpotAuthError, get_client

load_dotenv()

WIDGET_URI = "ui://widget/hubspot.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

mcp = FastMCP("hubspot-marketing")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def hubspot_widget() -> str:
    """UI widget for displaying HubSpot marketing data."""
    return WIDGET_HTML


def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


# ── Helpers ────────────────────────────────────────────────────────────────

async def _fetch_emails() -> list[dict]:
    client = get_client()
    records = await client.list_emails(limit=5)
    return [
        {
            "id": r.get("id", ""),
            "name": r.get("name", ""),
            "subject": r.get("subject", ""),
            "status": r.get("state", ""),
            "stats": {
                "sent": (r.get("statistics", {}) or {}).get("counters", {}).get("sent", 0),
                "delivered": (r.get("statistics", {}) or {}).get("counters", {}).get("delivered", 0),
                "opened": (r.get("statistics", {}) or {}).get("counters", {}).get("open", 0),
                "clicked": (r.get("statistics", {}) or {}).get("counters", {}).get("click", 0),
                "bounced": (r.get("statistics", {}) or {}).get("counters", {}).get("bounce", 0),
                "unsubscribed": (r.get("statistics", {}) or {}).get("counters", {}).get("unsubscribed", 0),
            },
        }
        for r in records
    ]


async def _fetch_lists() -> list[dict]:
    client = get_client()
    records = await client.list_lists(limit=10)
    return [
        {
            "id": str(r.get("listId", "")),
            "name": r.get("name", ""),
            "type": r.get("processingType", ""),
            "size": r.get("size", 0),
        }
        for r in records
        if r.get("objectTypeId") == "0-1"
    ]


async def _fetch_list_contacts(list_id: str) -> tuple[list[dict], str]:
    client = get_client()
    lists = await client.list_lists(limit=50)
    list_name = ""
    for lst in lists:
        if str(lst.get("listId", "")) == list_id:
            list_name = lst.get("name", "")
            break
    member_ids = await client.get_list_memberships(list_id, limit=10)
    if not member_ids:
        return [], list_name
    raw = await client.get_contacts_by_ids([str(m) for m in member_ids[:10]])
    contacts = [
        {
            "id": r.get("id", ""),
            "firstname": (r.get("properties", {}) or {}).get("firstname", ""),
            "lastname": (r.get("properties", {}) or {}).get("lastname", ""),
            "email": (r.get("properties", {}) or {}).get("email", ""),
            "phone": (r.get("properties", {}) or {}).get("phone", ""),
            "company": (r.get("properties", {}) or {}).get("company", ""),
            "lifecyclestage": (r.get("properties", {}) or {}).get("lifecyclestage", ""),
        }
        for r in raw
    ]
    return contacts, list_name


# ══════════════════════════════════════════════════════════════════════════════
# TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the latest marketing emails from HubSpot with performance stats. "
        "This is the entry point — the widget handles drill-down to lists and contacts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_emails() -> types.CallToolResult:
    try:
        items = await _fetch_emails()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching emails: {exc}")

    structured = {"type": "emails", "total": len(items), "items": items}
    summary = "No marketing emails found." if not items else f"Retrieved {len(items)} marketing email(s). See the widget for details."
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description="Get contact lists from HubSpot. Called by the widget for drill-down navigation.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_lists() -> types.CallToolResult:
    try:
        items = await _fetch_lists()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching lists: {exc}")

    structured = {"type": "lists", "total": len(items), "items": items}
    summary = "No lists found." if not items else f"Retrieved {len(items)} list(s)."
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description="Get contacts in a specific list. Called by the widget when drilling into a list.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_list_contacts(list_id: str) -> types.CallToolResult:
    try:
        items, list_name = await _fetch_list_contacts(list_id)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    structured = {"type": "list_contacts", "list_id": list_id, "list_name": list_name, "total": len(items), "items": items}
    summary = f"No contacts in '{list_name}'." if not items else f"Retrieved {len(items)} contact(s) from '{list_name}'."
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description="Add a contact to a static list by email. Called by the widget.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def add_to_list(list_id: str, contact_email: str) -> types.CallToolResult:
    try:
        client = get_client()
        contact_id = await client.search_contact_by_email(contact_email)
        if not contact_id:
            return _error_result(f"No contact found with email: {contact_email}")
        await client.add_to_list(list_id, [int(contact_id)])
        items, list_name = await _fetch_list_contacts(list_id)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to add to list: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    structured = {"type": "list_contacts", "list_id": list_id, "list_name": list_name, "total": len(items), "items": items, "_addedEmail": contact_email}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact {contact_email} added to '{list_name}'.")],
        structuredContent=structured,
    )


@mcp.tool(
    description="Remove a contact from a static list. Called by the widget.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def remove_from_list(list_id: str, contact_id: str) -> types.CallToolResult:
    try:
        client = get_client()
        await client.remove_from_list(list_id, [int(contact_id)])
        items, list_name = await _fetch_list_contacts(list_id)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to remove from list: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    structured = {"type": "list_contacts", "list_id": list_id, "list_name": list_name, "total": len(items), "items": items}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact removed from '{list_name}'.")],
        structuredContent=structured,
    )


@mcp.tool(
    description="Update a marketing email's name or subject. Called by the widget.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_email(email_id: str, name: str = "", subject: str = "") -> types.CallToolResult:
    try:
        client = get_client()
        data: dict = {}
        if name:    data["name"] = name
        if subject: data["subject"] = subject
        if not data:
            return _error_result("No fields provided to update.")
        await client.update_email(email_id, data)
        items = await _fetch_emails()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to update email: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    structured = {"type": "emails", "total": len(items), "items": items}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Email {email_id} updated.")],
        structuredContent=structured,
    )


@mcp.tool(
    description="Update a list's name. Called by the widget.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_list(list_id: str, name: str) -> types.CallToolResult:
    try:
        client = get_client()
        await client.update_list(list_id, name)
        items = await _fetch_lists()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to update list: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    structured = {"type": "lists", "total": len(items), "items": items}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"List renamed to '{name}'.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.prompt()
def show_marketing() -> list[PromptMessage]:
    """Show marketing email performance from HubSpot."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text="Show me the marketing email performance from HubSpot. Call get_emails.",
            ),
        )
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SERVER ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def main():
    port = int(os.environ.get("PORT", 3003))
    cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")

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
