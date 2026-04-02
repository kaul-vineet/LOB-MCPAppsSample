"""
Salesforce CRM MCP Server — 6 tools for Leads & Opportunities CRUD.

All tools return structuredContent for the widget, with _meta on the
decorator to ensure M365 Copilot discovers the widget URI from tools/list.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
from starlette.middleware.cors import CORSMiddleware

from .salesforce import SalesforceAPIError, SalesforceAuthError, get_client

load_dotenv()

# ── Widget ─────────────────────────────────────────────────────────────────────

WIDGET_URI = "ui://widget/crm.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP("sf-crm")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def crm_widget() -> str:
    """UI widget for displaying Salesforce CRM data."""
    return WIDGET_HTML


# ── Helpers ────────────────────────────────────────────────────────────────────

def _error_result(message: str) -> types.CallToolResult:
    """Return a structured error result the widget can display."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


async def _fetch_leads() -> list[dict]:
    """Fetch the 5 most recently created Leads."""
    sf = get_client()
    records = await sf.query(
        "SELECT Id, FirstName, LastName, Company, Email, Phone, Status, LeadSource "
        "FROM Lead ORDER BY CreatedDate DESC LIMIT 5"
    )
    return [
        {
            "id":          r.get("Id"),
            "first_name":  r.get("FirstName") or "",
            "last_name":   r.get("LastName") or "",
            "company":     r.get("Company") or "",
            "email":       r.get("Email") or "",
            "phone":       r.get("Phone") or "",
            "status":      r.get("Status") or "",
            "lead_source": r.get("LeadSource") or "",
        }
        for r in records
    ]


async def _fetch_opportunities() -> list[dict]:
    """Fetch the 5 most recently created Opportunities."""
    sf = get_client()
    records = await sf.query(
        "SELECT Id, Name, Account.Name, StageName, Amount, CloseDate, Probability "
        "FROM Opportunity ORDER BY CreatedDate DESC LIMIT 5"
    )
    return [
        {
            "id":           r.get("Id"),
            "name":         r.get("Name") or "",
            "account_name": (r.get("Account") or {}).get("Name") or "",
            "stage":        r.get("StageName") or "",
            "amount":       r.get("Amount"),
            "close_date":   r.get("CloseDate") or "",
            "probability":  r.get("Probability"),
        }
        for r in records
    ]


# ══════════════════════════════════════════════════════════════════════════════
# LEAD TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the 5 most recent Leads from Salesforce. "
        "Returns lead name, company, email, phone, status, and lead source."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_leads() -> types.CallToolResult:
    """Fetch latest 5 Leads from Salesforce."""
    try:
        items = await _fetch_leads()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching leads: {exc}")

    structured = {
        "type": "leads",
        "total": len(items),
        "items": items,
    }

    summary = (
        "No leads found."
        if not items
        else f"Retrieved {len(items)} lead(s). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new Lead in Salesforce. "
        "Requires last_name and company at minimum. "
        "Returns the updated list of latest 5 leads."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def create_lead(
    last_name: str,
    company: str,
    first_name: str = "",
    email: str = "",
    phone: str = "",
    status: str = "Open - Not Contacted",
    lead_source: str = "",
) -> types.CallToolResult:
    """
    Args:
        last_name:   Lead's last name (required)
        company:     Lead's company (required)
        first_name:  Lead's first name
        email:       Lead's email address
        phone:       Lead's phone number
        status:      Lead status (e.g. 'Open - Not Contacted')
        lead_source: Lead source (e.g. 'Web', 'Phone Inquiry')
    """
    try:
        sf = get_client()
        data = {"LastName": last_name, "Company": company}
        if first_name:  data["FirstName"] = first_name
        if email:       data["Email"] = email
        if phone:       data["Phone"] = phone
        if status:      data["Status"] = status
        if lead_source: data["LeadSource"] = lead_source

        new_id = await sf.create("Lead", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create lead: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating lead: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_leads()
    except Exception:
        items = []

    structured = {
        "type": "leads",
        "total": len(items),
        "items": items,
        "_createdId": new_id,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing Lead in Salesforce by its record Id. "
        "Only fields provided will be updated. "
        "Returns the updated list of latest 5 leads."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_lead(
    lead_id: str,
    first_name: str = "",
    last_name: str = "",
    company: str = "",
    email: str = "",
    phone: str = "",
    status: str = "",
    lead_source: str = "",
) -> types.CallToolResult:
    """
    Args:
        lead_id:     Salesforce Lead record Id (required)
        first_name:  Updated first name (empty string = no change)
        last_name:   Updated last name
        company:     Updated company
        email:       Updated email
        phone:       Updated phone
        status:      Updated status
        lead_source: Updated lead source
    """
    try:
        sf = get_client()
        data: dict = {}
        if first_name:  data["FirstName"] = first_name
        if last_name:   data["LastName"] = last_name
        if company:     data["Company"] = company
        if email:       data["Email"] = email
        if phone:       data["Phone"] = phone
        if status:      data["Status"] = status
        if lead_source: data["LeadSource"] = lead_source

        if not data:
            return _error_result("No fields provided to update.")

        await sf.update("Lead", lead_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update lead: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating lead: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_leads()
    except Exception:
        items = []

    structured = {
        "type": "leads",
        "total": len(items),
        "items": items,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead {lead_id} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# OPPORTUNITY TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the 5 most recent Opportunities from Salesforce. "
        "Returns opportunity name, account, stage, amount, close date, and probability."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_opportunities() -> types.CallToolResult:
    """Fetch latest 5 Opportunities from Salesforce."""
    try:
        items = await _fetch_opportunities()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching opportunities: {exc}")

    structured = {
        "type": "opportunities",
        "total": len(items),
        "items": items,
    }

    summary = (
        "No opportunities found."
        if not items
        else f"Retrieved {len(items)} opportunity(ies). See the widget for details."
    )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new Opportunity in Salesforce. "
        "Requires name, stage, and close_date at minimum. "
        "Returns the updated list of latest 5 opportunities."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def create_opportunity(
    name: str,
    stage: str,
    close_date: str,
    amount: float = 0.0,
    probability: int = 0,
) -> types.CallToolResult:
    """
    Args:
        name:        Opportunity name (required)
        stage:       Sales stage (e.g. 'Prospecting', 'Closed Won')
        close_date:  Expected close date YYYY-MM-DD (required)
        amount:      Deal amount in currency
        probability: Win probability percentage (0-100)
    """
    try:
        sf = get_client()
        data: dict = {
            "Name": name,
            "StageName": stage,
            "CloseDate": close_date,
        }
        if amount:      data["Amount"] = amount
        if probability: data["Probability"] = probability

        new_id = await sf.create("Opportunity", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create opportunity: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating opportunity: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_opportunities()
    except Exception:
        items = []

    structured = {
        "type": "opportunities",
        "total": len(items),
        "items": items,
        "_createdId": new_id,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Opportunity created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing Opportunity in Salesforce by its record Id. "
        "Only fields provided will be updated. "
        "Returns the updated list of latest 5 opportunities."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def update_opportunity(
    opportunity_id: str,
    name: str = "",
    stage: str = "",
    amount: float = 0.0,
    close_date: str = "",
    probability: int = 0,
) -> types.CallToolResult:
    """
    Args:
        opportunity_id: Salesforce Opportunity record Id (required)
        name:           Updated opportunity name
        stage:          Updated sales stage
        amount:         Updated deal amount
        close_date:     Updated close date YYYY-MM-DD
        probability:    Updated win probability (0-100)
    """
    try:
        sf = get_client()
        data: dict = {}
        if name:       data["Name"] = name
        if stage:      data["StageName"] = stage
        if amount:     data["Amount"] = amount
        if close_date: data["CloseDate"] = close_date
        if probability: data["Probability"] = probability

        if not data:
            return _error_result("No fields provided to update.")

        await sf.update("Opportunity", opportunity_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update opportunity: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating opportunity: {exc}")

    # Re-fetch the refreshed list
    try:
        items = await _fetch_opportunities()
    except Exception:
        items = []

    structured = {
        "type": "opportunities",
        "total": len(items),
        "items": items,
    }

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Opportunity {opportunity_id} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.prompt()
def show_leads() -> list[PromptMessage]:
    """Show the latest 5 leads from Salesforce."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the latest 5 leads from Salesforce. "
                    "Call get_leads and display the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def show_opportunities() -> list[PromptMessage]:
    """Show the latest 5 opportunities from Salesforce."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "Show me the latest 5 opportunities from Salesforce. "
                    "Call get_opportunities and display the results in the widget."
                ),
            ),
        )
    ]


@mcp.prompt()
def manage_crm() -> list[PromptMessage]:
    """Help manage Salesforce CRM data — leads and opportunities."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "I want to manage my Salesforce CRM data. "
                    "Start by showing me the latest 5 leads with get_leads. "
                    "I may want to create new leads, edit existing ones, "
                    "or switch to viewing opportunities."
                ),
            ),
        )
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SERVER ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def main():
    port = int(os.environ.get("PORT", 3000))
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
