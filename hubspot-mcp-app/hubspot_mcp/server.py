"""
HubSpot Marketing MCP Server — 6 tools for Marketing Emails, Lists & Contacts.

All tools return structuredContent for the widget, with _meta on the
decorator to ensure M365 Copilot discovers the widget URI from tools/list.
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

# ── Widget ─────────────────────────────────────────────────────────────────────

WIDGET_URI = "ui://widget/hubspot.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP("hubspot-marketing")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def crm_widget() -> str:
    """UI widget for displaying HubSpot marketing data."""
    return WIDGET_HTML


# ── Helpers ────────────────────────────────────────────────────────────────────

def _error_result(message: str) -> types.CallToolResult:
    """Return a structured error result the widget can display."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


CONTACT_PROPERTIES = ["firstname", "lastname", "email", "phone", "company", "lifecyclestage"]


async def _fetch_emails() -> list[dict]:
    """Fetch the 5 most recently updated marketing emails with stats."""
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
            }
        }
        for r in records
    ]


async def _fetch_lists() -> list[dict]:
    """Fetch contact lists."""
    client = get_client()
    records = await client.list_lists(limit=10)
    return [
        {
            "id": str(r.get("listId", "")),
            "name": r.get("name", ""),
            "type": r.get("processingType", ""),
            "size": r.get("size", 0),
            "object_type": r.get("objectTypeId", ""),
        }
        for r in records
        if r.get("objectTypeId") == "0-1"  # contacts only
    ]


async def _fetch_list_contacts(list_id: str) -> tuple[list[dict], str]:
    """Fetch contacts in a specific list. Returns (contacts, list_name)."""
    client = get_client()
    # Get list info
    lists = await client.list_lists(limit=50)
    list_name = ""
    for lst in lists:
        if str(lst.get("listId", "")) == list_id:
            list_name = lst.get("name", "")
            break

    # Get member IDs
    member_ids = await client.get_list_memberships(list_id, limit=10)
    if not member_ids:
        return [], list_name

    # Batch fetch contact details
    raw_contacts = await client.get_contacts_by_ids([str(m) for m in member_ids[:10]])
    contacts = [
        {
            "id":             r.get("id", ""),
            "firstname":      (r.get("properties", {}) or {}).get("firstname", ""),
            "lastname":       (r.get("properties", {}) or {}).get("lastname", ""),
            "email":          (r.get("properties", {}) or {}).get("email", ""),
            "phone":          (r.get("properties", {}) or {}).get("phone", ""),
            "company":        (r.get("properties", {}) or {}).get("company", ""),
            "lifecyclestage": (r.get("properties", {}) or {}).get("lifecyclestage", ""),
        }
        for r in raw_contacts
    ]
    return contacts, list_name


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the 5 most recent marketing emails from HubSpot. "
        "Returns email name, subject, status, and performance stats "
        "(sent, delivered, opened, clicked, bounced, unsubscribed)."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_emails() -> types.CallToolResult:
    """Fetch latest 5 marketing emails from HubSpot."""
    try:
        items = await _fetch_emails()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching emails: {exc}")

    structured = {
        "type": "emails",
        "total": len(items),
        "items": items,
    }

    summary = (
        "No marketing emails found."
        if not items
        else f"Retrieved {len(items)} marketing email(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# LIST TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get contact lists (segments) from HubSpot. "
        "Returns list name, type (MANUAL/DYNAMIC), and size."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_lists() -> types.CallToolResult:
    """Fetch contact lists from HubSpot."""
    try:
        items = await _fetch_lists()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching lists: {exc}")

    structured = {
        "type": "lists",
        "total": len(items),
        "items": items,
    }

    summary = (
        "No lists found."
        if not items
        else f"Retrieved {len(items)} list(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Get contacts belonging to a specific list. "
        "Returns contact name, email, phone, company, and lifecycle stage."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_list_contacts(list_id: str) -> types.CallToolResult:
    """
    Args:
        list_id: HubSpot list ID to fetch contacts from (required)
    """
    try:
        items, list_name = await _fetch_list_contacts(list_id)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching list contacts: {exc}")

    structured = {
        "type": "list_contacts",
        "list_id": list_id,
        "list_name": list_name,
        "total": len(items),
        "items": items,
    }

    summary = (
        f"No contacts found in list '{list_name}'."
        if not items
        else f"Retrieved {len(items)} contact(s) from list '{list_name}'."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Add a contact to a static list by email address. "
        "Looks up the contact by email and adds them to the list."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def add_to_list(list_id: str, contact_email: str) -> types.CallToolResult:
    """
    Args:
        list_id:       HubSpot list ID (required)
        contact_email: Email of the contact to add (required)
    """
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

    structured = {
        "type": "list_contacts",
        "list_id": list_id,
        "list_name": list_name,
        "total": len(items),
        "items": items,
        "_addedEmail": contact_email,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact {contact_email} added to list '{list_name}'.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Remove a contact from a static list by contact ID. "
        "Returns the updated list of contacts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def remove_from_list(list_id: str, contact_id: str) -> types.CallToolResult:
    """
    Args:
        list_id:    HubSpot list ID (required)
        contact_id: Contact ID to remove (required)
    """
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

    structured = {
        "type": "list_contacts",
        "list_id": list_id,
        "list_name": list_name,
        "total": len(items),
        "items": items,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact {contact_id} removed from list '{list_name}'.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CONTACT TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Update an existing Contact in HubSpot by its record Id. "
        "Only fields provided will be updated. "
        "Returns the updated contact data."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_contact(
    contact_id: str,
    firstname: str = "",
    lastname: str = "",
    email: str = "",
    phone: str = "",
    company: str = "",
    lifecyclestage: str = "",
) -> types.CallToolResult:
    """
    Args:
        contact_id:     HubSpot Contact record Id (required)
        firstname:      Updated first name (empty string = no change)
        lastname:       Updated last name
        email:          Updated email
        phone:          Updated phone
        company:        Updated company
        lifecyclestage: Updated lifecycle stage
    """
    try:
        hs = get_client()
        data: dict = {}
        if firstname:      data["firstname"] = firstname
        if lastname:       data["lastname"] = lastname
        if email:          data["email"] = email
        if phone:          data["phone"] = phone
        if company:        data["company"] = company
        if lifecyclestage: data["lifecyclestage"] = lifecyclestage

        if not data:
            return _error_result("No fields provided to update.")

        await hs.update_object("contacts", contact_id, data)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to update contact: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating contact: {exc}")

    # Return a contacts-type response with the updated fields
    updated = {
        "id": contact_id,
        "firstname": firstname,
        "lastname": lastname,
        "email": email,
        "phone": phone,
        "company": company,
        "lifecyclestage": lifecyclestage,
    }

    structured = {
        "type": "contacts",
        "total": 1,
        "items": [updated],
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact {contact_id} updated.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.prompt()
def show_emails() -> list[PromptMessage]:
    """Show the latest 5 marketing emails from HubSpot."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the latest 5 marketing emails from HubSpot. "
                    "Call get_emails and display the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def show_lists() -> list[PromptMessage]:
    """Show contact lists from HubSpot."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the contact lists from HubSpot. "
                    "Call get_lists and display the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def manage_marketing() -> list[PromptMessage]:
    """Help manage HubSpot marketing — emails, lists, and contacts."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "I want to manage my HubSpot marketing data. "
                    "Start by showing me the latest marketing emails with get_emails. "
                    "I may want to view contact lists, drill into list members, "
                    "or add/remove contacts from lists."
                ),
            ),
        )
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SERVER ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def main():
    port = int(os.environ.get("PORT", 3003))
    app = mcp.app

    # Add CORS middleware (required for M365 widget renderer origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
