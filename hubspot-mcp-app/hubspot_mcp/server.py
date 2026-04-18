"""
HubSpot Marketing MCP Server — 14 tools for Email Performance, Contact Lists,
Membership, Contacts & Deals management.

Single entry point: get_emails. The widget handles all drill-down navigation
via callTool — from emails → lists → contacts in list. Tools support:
- Email performance dashboard (read-only, with open/click rates)
- Contact lists: view, rename
- List membership: view contacts, add by email, remove
- Contact editing (inline from list view)
- Contact CRUD (standalone get/create/update)
- Deal CRUD (get/create)
- Interactive form widgets for creating contacts and deals

All tools return structuredContent for the widget, with _meta on the
decorator to ensure M365 Copilot discovers the widget URI from tools/list.
"""

import os
import sys
from pathlib import Path
from typing import Literal

import structlog
import uvicorn
from dotenv import load_dotenv
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
from pydantic_settings import BaseSettings
from starlette.middleware.cors import CORSMiddleware

from .hubspot_client import HubSpotAPIError, HubSpotAuthError, get_client

load_dotenv()

log = structlog.get_logger("hs")


# ── Typed Configuration ───────────────────────────────────────────────────────

class HSSettings(BaseSettings):
    hubspot_access_token: str = ""
    port: int = 3003
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = HSSettings()

WIDGET_URI = "ui://widget/hubspot.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

mcp = FastMCP("gtc-hubspot-trading-post")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def hubspot_widget() -> str:
    """UI widget for displaying HubSpot marketing data."""
    return WIDGET_HTML


def _error_result(message: str) -> types.CallToolResult:
    """Return a structured error result the widget can display."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


# ── Helpers ────────────────────────────────────────────────────────────────

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
                # Safely extract nested properties, defaulting if None
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
    """Fetch contact lists, filtered to contact-type lists only (objectTypeId 0-1)."""
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
        if r.get("objectTypeId") == "0-1"  # Filter to contact lists only (0-1 = contacts object type)
    ]


async def _fetch_list_contacts(list_id: str) -> tuple[list[dict], str]:
    """Fetch contacts in a specific list. Returns (contacts_list, list_name) tuple."""
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
            # Safely extract nested properties, defaulting if None
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
# EMAIL TOOLS (entry point)
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the latest marketing emails from HubSpot with performance stats. "
        "This is the entry point — the widget handles drill-down to lists and contacts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__get_emails() -> types.CallToolResult:
    """Fetch latest marketing emails from HubSpot with performance stats."""
    try:
        items = await _fetch_emails()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching emails: {exc}")

    structured = {"type": "emails", "total": len(items), "items": items}
    if not items:
        summary = "No marketing emails found."
    else:
        lines = [f"Retrieved {len(items)} marketing email(s):"]
        for em in items:
            s = em.get("stats", {})
            lines.append(f"- {em['name']} | {em['status']} | Sent: {s.get('sent',0)} | Opened: {s.get('opened',0)} | Clicked: {s.get('clicked',0)}")
        summary = "\n".join(lines)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# LIST TOOLS (widget-driven navigation)
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description="Get contact lists from HubSpot. Called by the widget for drill-down navigation.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__get_lists() -> types.CallToolResult:
    """Fetch contact lists (segments) from HubSpot."""
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
async def hs__get_list_contacts(list_id: str) -> types.CallToolResult:
    """Fetch contacts belonging to a specific list.

    Args:
        list_id: HubSpot list ID to fetch contacts from
    """
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


# ══════════════════════════════════════════════════════════════════════════════
# LIST MEMBERSHIP TOOLS (widget-driven CRUD)
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description="Add a contact to a static list by email. Called by the widget.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__add_to_list(list_id: str, contact_email: str) -> types.CallToolResult:
    """Add a contact to a list by email address.

    Args:
        list_id:       HubSpot list ID
        contact_email: Email of the contact to add
    """
    try:
        client = get_client()
        contact_id = await client.search_contact_by_email(contact_email)
        if not contact_id:
            return _error_result(f"No contact found with email: {contact_email}")
        await client.add_to_list(list_id, [int(contact_id)])  # HubSpot membership API expects integer record IDs
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
async def hs__remove_from_list(list_id: str, contact_id: str) -> types.CallToolResult:
    """Remove a contact from a list.

    Args:
        list_id:    HubSpot list ID
        contact_id: Contact ID to remove
    """
    try:
        client = get_client()
        await client.remove_from_list(list_id, [int(contact_id)])  # HubSpot membership API expects integer record IDs
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


# ══════════════════════════════════════════════════════════════════════════════
# EMAIL & LIST EDITING TOOLS (widget-driven)
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description="Update a marketing email's name or subject. Called by the widget.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__update_email(email_id: str, name: str = "", subject: str = "") -> types.CallToolResult:
    """Update a marketing email's name or subject.

    Args:
        email_id: HubSpot email ID
        name:     Updated email name (empty = no change)
        subject:  Updated subject line (empty = no change)
    """
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
async def hs__update_list(list_id: str, name: str) -> types.CallToolResult:
    """Rename a contact list.

    Args:
        list_id: HubSpot list ID
        name:    New list name
    """
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
# CONTACT & DEAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════


async def _fetch_contacts() -> list[dict]:
    """Fetch the 5 most recently created contacts via Search API."""
    client = get_client()
    records = await client.list_objects(
        "contacts",
        properties=["firstname", "lastname", "email", "phone", "company", "lifecyclestage"],
        limit=5,
    )
    return [
        {
            "id":             r.get("id", ""),
            "firstname":      r.get("firstname", ""),
            "lastname":       r.get("lastname", ""),
            "email":          r.get("email", ""),
            "phone":          r.get("phone", ""),
            "company":        r.get("company", ""),
            "lifecyclestage": r.get("lifecyclestage", ""),
        }
        for r in records
    ]


async def _fetch_deals() -> list[dict]:
    """Fetch the 5 most recently created deals via Search API."""
    client = get_client()
    records = await client.list_objects(
        "deals",
        properties=["dealname", "dealstage", "amount", "closedate", "pipeline", "hubspot_owner_id"],
        limit=5,
    )
    return [
        {
            "id":        r.get("id", ""),
            "dealname":  r.get("dealname", ""),
            "dealstage": r.get("dealstage", ""),
            "amount":    r.get("amount", ""),
            "closedate": r.get("closedate", ""),
            "pipeline":  r.get("pipeline", ""),
        }
        for r in records
    ]


# ══════════════════════════════════════════════════════════════════════════════
# CONTACT TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the latest 5 Contacts from HubSpot CRM. "
        "Returns name, email, phone, company, and lifecycle stage."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__get_contacts() -> types.CallToolResult:
    try:
        items = await _fetch_contacts()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch contacts: {exc}")

    structured = {"type": "contacts", "total": len(items), "items": items}

    lines = [f"Found {len(items)} contact(s):"]
    for c in items:
        lines.append(f"- {c['firstname']} {c['lastname']} | {c['email']} | Company: {c['company']} | Stage: {c['lifecyclestage']}")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(lines))],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new Contact in HubSpot CRM. "
        "Requires email at minimum. "
        "Returns the updated list of latest 5 contacts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__create_contact(
    email: str,
    firstname: str = "",
    lastname: str = "",
    phone: str = "",
    company: str = "",
    lifecyclestage: str = "",
) -> types.CallToolResult:
    """
    Args:
        email:          Contact email address (required)
        firstname:      First name
        lastname:       Last name
        phone:          Phone number
        company:        Company name
        lifecyclestage: Lifecycle stage (e.g. 'subscriber', 'lead', 'customer')
    """
    try:
        client = get_client()
        props: dict = {"email": email}
        if firstname:      props["firstname"] = firstname
        if lastname:       props["lastname"] = lastname
        if phone:          props["phone"] = phone
        if company:        props["company"] = company
        if lifecyclestage: props["lifecyclestage"] = lifecyclestage

        new_id = await client.create_object("contacts", props)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to create contact: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating contact: {exc}")

    try:
        items = await _fetch_contacts()
    except Exception:
        items = []

    structured = {"type": "contacts", "total": len(items), "items": items, "_createdId": new_id}

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact '{firstname} {lastname}' ({email}) created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing Contact in HubSpot CRM by its record Id. "
        "Only fields provided will be updated. "
        "Returns the updated list of latest 5 contacts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__update_contact(
    contact_id: str,
    email: str = "",
    firstname: str = "",
    lastname: str = "",
    phone: str = "",
    company: str = "",
    lifecyclestage: str = "",
) -> types.CallToolResult:
    """
    Args:
        contact_id:     HubSpot Contact record Id (required)
        email:          Updated email address
        firstname:      Updated first name
        lastname:       Updated last name
        phone:          Updated phone number
        company:        Updated company name
        lifecyclestage: Updated lifecycle stage
    """
    try:
        client = get_client()
        props: dict = {}
        if email:          props["email"] = email
        if firstname:      props["firstname"] = firstname
        if lastname:       props["lastname"] = lastname
        if phone:          props["phone"] = phone
        if company:        props["company"] = company
        if lifecyclestage: props["lifecyclestage"] = lifecyclestage

        if not props:
            return _error_result("No fields provided to update.")

        await client.update_object("contacts", contact_id, props)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to update contact: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating contact: {exc}")

    try:
        items = await _fetch_contacts()
    except Exception:
        items = []

    structured = {"type": "contacts", "total": len(items), "items": items}

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact {contact_id} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# DEAL TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the latest 5 Deals from HubSpot CRM. "
        "Returns deal name, stage, amount, close date, and pipeline."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__get_deals() -> types.CallToolResult:
    try:
        items = await _fetch_deals()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch deals: {exc}")

    structured = {"type": "deals", "total": len(items), "items": items}

    lines = [f"Found {len(items)} deal(s):"]
    for d in items:
        lines.append(f"- {d['dealname']} | Stage: {d['dealstage']} | Amount: {d['amount']} | Close: {d['closedate']}")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(lines))],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new Deal in HubSpot CRM. "
        "Requires deal_name at minimum. "
        "Returns the updated list of latest 5 deals."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__create_deal(
    deal_name: str,
    deal_stage: str = "",
    amount: str = "",
    close_date: str = "",
    pipeline: str = "",
) -> types.CallToolResult:
    """
    Args:
        deal_name:   Deal name (required)
        deal_stage:  Deal stage (e.g. 'appointmentscheduled', 'qualifiedtobuy', 'closedwon')
        amount:      Deal amount (string, e.g. '50000')
        close_date:  Expected close date YYYY-MM-DD
        pipeline:    Pipeline name or ID (default pipeline used if omitted)
    """
    try:
        client = get_client()
        props: dict = {"dealname": deal_name}
        if deal_stage: props["dealstage"] = deal_stage
        if amount:     props["amount"] = amount
        if close_date: props["closedate"] = close_date
        if pipeline:   props["pipeline"] = pipeline

        new_id = await client.create_object("deals", props)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to create deal: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating deal: {exc}")

    try:
        items = await _fetch_deals()
    except Exception:
        items = []

    structured = {"type": "deals", "total": len(items), "items": items, "_createdId": new_id}

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Deal '{deal_name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description="Opens a form to create a new HubSpot Contact. The user fills in details and submits.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__create_contact_form() -> types.CallToolResult:
    """Opens an interactive form widget for creating a new HubSpot Contact."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Opening Contact creation form. Fill in the details and click Submit.")],
        structuredContent={"type": "form", "entity": "contact"},
    )


@mcp.tool(
    description="Opens a form to create a new HubSpot Deal. The user fills in details and submits.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def hs__create_deal_form() -> types.CallToolResult:
    """Opens an interactive form widget for creating a new HubSpot Deal."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Opening Deal creation form. Fill in the details and click Submit.")],
        structuredContent={"type": "form", "entity": "deal"},
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


def _validate_env() -> None:
    """Check required environment variables and print startup checklist."""
    log.info("validating_env")
    token = settings.hubspot_access_token

    print("  ┌─ Environment ─────────────────────────────────")
    print(f"  │ HUBSPOT_ACCESS_TOKEN  {'✓ ' + token[:12] + '...' if token else '✗ MISSING'}")
    print("  └────────────────────────────────────────────────")

    if not token:
        log.error("missing_env_vars", vars=["HUBSPOT_ACCESS_TOKEN"])
        print("\n  ❌ Missing required env var: HUBSPOT_ACCESS_TOKEN")
        print("  Copy .env.example to .env and fill in your HubSpot Private App token.")
        sys.exit(1)


def main():
    _validate_env()
    log.info("starting", port=settings.port)
    print(f"⚓ GTC — HubSpot Trading Post starting on port {settings.port}")

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
