"""
HubSpot Marketing MCP Server — 7 tools for Marketing Emails, Contacts & Companies.

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
COMPANY_PROPERTIES = ["name", "domain", "industry", "city", "phone", "numberofemployees"]


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


async def _fetch_contacts() -> list[dict]:
    """Fetch the 5 most recently created Contacts."""
    hs = get_client()
    records = await hs.list_objects("contacts", CONTACT_PROPERTIES, limit=5)
    return [
        {
            "id":             r.get("id", ""),
            "firstname":      r.get("firstname") or "",
            "lastname":       r.get("lastname") or "",
            "email":          r.get("email") or "",
            "phone":          r.get("phone") or "",
            "company":        r.get("company") or "",
            "lifecyclestage": r.get("lifecyclestage") or "",
        }
        for r in records
    ]


async def _fetch_companies() -> list[dict]:
    """Fetch the 5 most recently created Companies."""
    client = get_client()
    records = await client.list_objects(
        "companies",
        properties=COMPANY_PROPERTIES,
        limit=5,
    )
    return [
        {
            "id": r.get("id", ""),
            "name": r.get("name") or "",
            "domain": r.get("domain") or "",
            "industry": r.get("industry") or "",
            "city": r.get("city") or "",
            "phone": r.get("phone") or "",
            "employees": r.get("numberofemployees") or "",
        }
        for r in records
    ]


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
# CONTACT TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the 5 most recent Contacts from HubSpot. "
        "Returns contact name, email, phone, company, and lifecycle stage."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_contacts() -> types.CallToolResult:
    """Fetch latest 5 Contacts from HubSpot."""
    try:
        items = await _fetch_contacts()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching contacts: {exc}")

    structured = {
        "type": "contacts",
        "total": len(items),
        "items": items,
    }

    summary = (
        "No contacts found."
        if not items
        else f"Retrieved {len(items)} contact(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new Contact in HubSpot. "
        "Requires email at minimum. "
        "Returns the updated list of latest 5 contacts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def create_contact(
    email: str,
    firstname: str,
    lastname: str,
    phone: str = "",
    company: str = "",
    lifecyclestage: str = "lead",
) -> types.CallToolResult:
    """
    Args:
        email:          Contact's email address (required)
        firstname:      Contact's first name (required)
        lastname:       Contact's last name (required)
        phone:          Contact's phone number
        company:        Contact's company
        lifecyclestage: Lifecycle stage (e.g. 'lead', 'subscriber')
    """
    try:
        hs = get_client()
        data = {"email": email, "firstname": firstname, "lastname": lastname}
        if phone:          data["phone"] = phone
        if company:        data["company"] = company
        if lifecyclestage: data["lifecyclestage"] = lifecyclestage

        new_id = await hs.create_object("contacts", data)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to create contact: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating contact: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_contacts()
    except Exception:
        items = []

    structured = {
        "type": "contacts",
        "total": len(items),
        "items": items,
        "_createdId": new_id,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing Contact in HubSpot by its record Id. "
        "Only fields provided will be updated. "
        "Returns the updated list of latest 5 contacts."
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

    # Re-fetch the refreshed list
    try:
        items = await _fetch_contacts()
    except Exception:
        items = []

    structured = {
        "type": "contacts",
        "total": len(items),
        "items": items,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact {contact_id} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPANY TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the 5 most recent Companies from HubSpot. "
        "Returns company name, domain, industry, city, phone, and employee count."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_companies() -> types.CallToolResult:
    """Fetch latest 5 Companies from HubSpot."""
    try:
        items = await _fetch_companies()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching companies: {exc}")

    structured = {
        "type": "companies",
        "total": len(items),
        "items": items,
    }

    summary = (
        "No companies found."
        if not items
        else f"Retrieved {len(items)} company/companies. See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new Company in HubSpot. "
        "Requires name at minimum. "
        "Returns the updated list of latest 5 companies."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def create_company(
    name: str,
    domain: str = "",
    industry: str = "",
    city: str = "",
    phone: str = "",
) -> types.CallToolResult:
    """
    Args:
        name:     Company name (required)
        domain:   Company website domain
        industry: Industry vertical
        city:     Company city
        phone:    Company phone number
    """
    try:
        hs = get_client()
        data: dict = {"name": name}
        if domain:   data["domain"] = domain
        if industry: data["industry"] = industry
        if city:     data["city"] = city
        if phone:    data["phone"] = phone

        new_id = await hs.create_object("companies", data)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to create company: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating company: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_companies()
    except Exception:
        items = []

    structured = {
        "type": "companies",
        "total": len(items),
        "items": items,
        "_createdId": new_id,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Company created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing Company in HubSpot by its record Id. "
        "Only fields provided will be updated. "
        "Returns the updated list of latest 5 companies."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_company(
    company_id: str,
    name: str = "",
    domain: str = "",
    industry: str = "",
    city: str = "",
    phone: str = "",
) -> types.CallToolResult:
    """
    Args:
        company_id: HubSpot Company record Id (required)
        name:       Updated company name (empty string = no change)
        domain:     Updated domain
        industry:   Updated industry
        city:       Updated city
        phone:      Updated phone
    """
    try:
        hs = get_client()
        data: dict = {}
        if name:     data["name"] = name
        if domain:   data["domain"] = domain
        if industry: data["industry"] = industry
        if city:     data["city"] = city
        if phone:    data["phone"] = phone

        if not data:
            return _error_result("No fields provided to update.")

        await hs.update_object("companies", company_id, data)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to update company: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating company: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_companies()
    except Exception:
        items = []

    structured = {
        "type": "companies",
        "total": len(items),
        "items": items,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Company {company_id} updated. Refreshed list returned.")],
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
def show_contacts() -> list[PromptMessage]:
    """Show the latest 5 contacts from HubSpot."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the latest 5 contacts from HubSpot. "
                    "Call get_contacts and display the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def show_companies() -> list[PromptMessage]:
    """Show the latest 5 companies from HubSpot."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the latest 5 companies from HubSpot. "
                    "Call get_companies and display the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def manage_marketing() -> list[PromptMessage]:
    """Help manage HubSpot marketing data — emails, contacts, and companies."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "I want to manage my HubSpot marketing data. "
                    "Start by showing me the latest 5 marketing emails with get_emails. "
                    "I may want to view contacts, manage companies, "
                    "or review email performance stats."
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
