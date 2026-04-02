"""
HubSpot CRM MCP Server — 6 tools for Contacts & Deals CRUD.

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

mcp = FastMCP("hubspot-crm")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def crm_widget() -> str:
    """UI widget for displaying HubSpot CRM data."""
    return WIDGET_HTML


# ── Helpers ────────────────────────────────────────────────────────────────────

def _error_result(message: str) -> types.CallToolResult:
    """Return a structured error result the widget can display."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


CONTACT_PROPERTIES = ["firstname", "lastname", "email", "phone", "company", "lifecyclestage"]
DEAL_PROPERTIES = ["dealname", "dealstage", "amount", "closedate", "pipeline"]


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


async def _fetch_deals() -> list[dict]:
    """Fetch the 5 most recently created Deals."""
    hs = get_client()
    records = await hs.list_objects("deals", DEAL_PROPERTIES, limit=5)
    return [
        {
            "id":        r.get("id", ""),
            "dealname":  r.get("dealname") or "",
            "dealstage": r.get("dealstage") or "",
            "amount":    r.get("amount"),
            "closedate": r.get("closedate") or "",
            "pipeline":  r.get("pipeline") or "",
        }
        for r in records
    ]


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
# DEAL TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the 5 most recent Deals from HubSpot. "
        "Returns deal name, stage, amount, close date, and pipeline."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_deals() -> types.CallToolResult:
    """Fetch latest 5 Deals from HubSpot."""
    try:
        items = await _fetch_deals()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"HubSpot API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching deals: {exc}")

    structured = {
        "type": "deals",
        "total": len(items),
        "items": items,
    }

    summary = (
        "No deals found."
        if not items
        else f"Retrieved {len(items)} deal(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new Deal in HubSpot. "
        "Requires dealname, pipeline, and dealstage at minimum. "
        "Returns the updated list of latest 5 deals."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def create_deal(
    dealname: str,
    pipeline: str,
    dealstage: str,
    amount: float = 0.0,
    closedate: str = "",
) -> types.CallToolResult:
    """
    Args:
        dealname:   Deal name (required)
        pipeline:   Pipeline identifier (required, e.g. 'default')
        dealstage:  Deal stage (required, e.g. 'appointmentscheduled')
        amount:     Deal amount in currency
        closedate:  Expected close date YYYY-MM-DD
    """
    try:
        hs = get_client()
        data: dict = {
            "dealname": dealname,
            "pipeline": pipeline,
            "dealstage": dealstage,
        }
        if amount:    data["amount"] = str(amount)
        if closedate: data["closedate"] = closedate

        new_id = await hs.create_object("deals", data)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to create deal: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating deal: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_deals()
    except Exception:
        items = []

    structured = {
        "type": "deals",
        "total": len(items),
        "items": items,
        "_createdId": new_id,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Deal created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing Deal in HubSpot by its record Id. "
        "Only fields provided will be updated. "
        "Returns the updated list of latest 5 deals."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_deal(
    deal_id: str,
    dealname: str = "",
    dealstage: str = "",
    amount: float = 0.0,
    closedate: str = "",
    pipeline: str = "",
) -> types.CallToolResult:
    """
    Args:
        deal_id:    HubSpot Deal record Id (required)
        dealname:   Updated deal name
        dealstage:  Updated deal stage
        amount:     Updated deal amount
        closedate:  Updated close date YYYY-MM-DD
        pipeline:   Updated pipeline
    """
    try:
        hs = get_client()
        data: dict = {}
        if dealname:  data["dealname"] = dealname
        if dealstage: data["dealstage"] = dealstage
        if amount:    data["amount"] = str(amount)
        if closedate: data["closedate"] = closedate
        if pipeline:  data["pipeline"] = pipeline

        if not data:
            return _error_result("No fields provided to update.")

        await hs.update_object("deals", deal_id, data)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to update deal: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating deal: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_deals()
    except Exception:
        items = []

    structured = {
        "type": "deals",
        "total": len(items),
        "items": items,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Deal {deal_id} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════


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
def show_deals() -> list[PromptMessage]:
    """Show the latest 5 deals from HubSpot."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the latest 5 deals from HubSpot. "
                    "Call get_deals and display the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def manage_hubspot() -> list[PromptMessage]:
    """Help manage HubSpot CRM data — contacts and deals."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "I want to manage my HubSpot CRM data. "
                    "Start by showing me the latest 5 contacts with get_contacts. "
                    "I may want to create new contacts, edit existing ones, "
                    "or switch to viewing deals."
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
