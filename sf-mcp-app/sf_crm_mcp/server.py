"""
Salesforce CRM MCP Server — 15 tools for Leads, Opportunities, Accounts & Contacts CRUD.

All tools return structuredContent for the widget, with _meta on the
decorator to ensure M365 Copilot discovers the widget URI from tools/list.
"""

import os
import sys
from datetime import datetime, timezone
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

from .salesforce import SalesforceAPIError, SalesforceAuthError, get_client

load_dotenv()

log = structlog.get_logger("sf")


# ── Typed Configuration ───────────────────────────────────────────────────────

class SFSettings(BaseSettings):
    sf_instance_url: str = ""
    sf_client_id: str = ""
    sf_client_secret: str = ""
    port: int = 3000
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = SFSettings()


# ── Widget ─────────────────────────────────────────────────────────────────────

WIDGET_URI = "ui://widget/crm.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP("gtc-sf-trading-post")


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


async def _fetch_accounts() -> list[dict]:
    """Fetch the 5 most recently created Accounts."""
    sf = get_client()
    records = await sf.query(
        "SELECT Id, Name, Industry, Phone, Website, BillingCity, Type, NumberOfEmployees "
        "FROM Account ORDER BY CreatedDate DESC LIMIT 5"
    )
    return [
        {
            "id":           r.get("Id"),
            "name":         r.get("Name") or "",
            "industry":     r.get("Industry") or "",
            "phone":        r.get("Phone") or "",
            "website":      r.get("Website") or "",
            "billing_city": r.get("BillingCity") or "",
            "type":         r.get("Type") or "",
            "employees":    r.get("NumberOfEmployees"),
        }
        for r in records
    ]


async def _fetch_contacts() -> list[dict]:
    """Fetch the 5 most recently created Contacts."""
    sf = get_client()
    records = await sf.query(
        "SELECT Id, FirstName, LastName, Email, Phone, Title, Account.Name "
        "FROM Contact ORDER BY CreatedDate DESC LIMIT 5"
    )
    return [
        {
            "id":           r.get("Id"),
            "first_name":   r.get("FirstName") or "",
            "last_name":    r.get("LastName") or "",
            "email":        r.get("Email") or "",
            "phone":        r.get("Phone") or "",
            "title":        r.get("Title") or "",
            "account_name": (r.get("Account") or {}).get("Name") or "",
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
async def sf__get_leads() -> types.CallToolResult:
    """Fetch latest 5 Leads from Salesforce."""
    log.info("sf__get_leads")
    try:
        items = await _fetch_leads()
    except SalesforceAuthError as exc:
        log.error("auth_failed", error=str(exc))
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        log.error("api_error", error=str(exc))
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        log.error("unexpected_error", error=str(exc))
        return _error_result(f"Unexpected error fetching leads: {exc}")

    structured = {
        "type": "leads",
        "total": len(items),
        "items": items,
    }

    if not items:
        summary = "No leads found."
    else:
        lines = [f"Retrieved {len(items)} lead(s):"]
        for ld in items:
            lines.append(f"- {ld['first_name']} {ld['last_name']} | {ld['company']} | {ld['status']} | {ld['lead_source']}")
        summary = "\n".join(lines)

    log.info("sf__get_leads_done", count=len(items))
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
async def sf__create_lead(
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
async def sf__update_lead(
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
async def sf__get_opportunities() -> types.CallToolResult:
    """Fetch latest 5 Opportunities from Salesforce."""
    log.info("sf__get_opportunities")
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

    if not items:
        summary = "No opportunities found."
    else:
        lines = [f"Retrieved {len(items)} opportunity(ies):"]
        for opp in items:
            lines.append(f"- {opp['name']} | {opp['stage']} | ${opp.get('amount') or 0:,.0f} | Close: {opp['close_date']}")
        summary = "\n".join(lines)

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
async def sf__create_opportunity(
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
async def sf__update_opportunity(
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
# ACCOUNT TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the latest 5 Accounts from Salesforce. "
        "Returns company name, industry, phone, website, and employee count."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_accounts() -> types.CallToolResult:
    try:
        items = await _fetch_accounts()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch accounts: {exc}")

    structured = {"type": "accounts", "total": len(items), "items": items}

    lines = [f"Found {len(items)} account(s):"]
    for a in items:
        lines.append(f"- {a['name']} | Industry: {a['industry']} | City: {a['billing_city']} | Employees: {a.get('employees', 'N/A')}")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(lines))],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new Account in Salesforce. "
        "Requires name at minimum. "
        "Returns the updated list of latest 5 accounts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__create_account(
    name: str,
    industry: str = "",
    phone: str = "",
    website: str = "",
    billing_city: str = "",
    account_type: str = "",
) -> types.CallToolResult:
    """
    Args:
        name:          Account / company name (required)
        industry:      Industry (e.g. 'Technology', 'Finance')
        phone:         Phone number
        website:       Company website URL
        billing_city:  Billing city
        account_type:  Account type (e.g. 'Customer', 'Partner', 'Prospect')
    """
    try:
        sf = get_client()
        data: dict = {"Name": name}
        if industry:     data["Industry"] = industry
        if phone:        data["Phone"] = phone
        if website:      data["Website"] = website
        if billing_city: data["BillingCity"] = billing_city
        if account_type: data["Type"] = account_type

        new_id = await sf.create("Account", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create account: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating account: {exc}")

    try:
        items = await _fetch_accounts()
    except Exception:
        items = []

    structured = {"type": "accounts", "total": len(items), "items": items, "_createdId": new_id}

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Account '{name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing Account in Salesforce by its record Id. "
        "Only fields provided will be updated. "
        "Returns the updated list of latest 5 accounts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__update_account(
    account_id: str,
    name: str = "",
    industry: str = "",
    phone: str = "",
    website: str = "",
    billing_city: str = "",
    account_type: str = "",
) -> types.CallToolResult:
    """
    Args:
        account_id:    Salesforce Account record Id (required)
        name:          Updated company name
        industry:      Updated industry
        phone:         Updated phone number
        website:       Updated website URL
        billing_city:  Updated billing city
        account_type:  Updated account type
    """
    try:
        sf = get_client()
        data: dict = {}
        if name:         data["Name"] = name
        if industry:     data["Industry"] = industry
        if phone:        data["Phone"] = phone
        if website:      data["Website"] = website
        if billing_city: data["BillingCity"] = billing_city
        if account_type: data["Type"] = account_type

        if not data:
            return _error_result("No fields provided to update.")

        await sf.update("Account", account_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update account: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating account: {exc}")

    try:
        items = await _fetch_accounts()
    except Exception:
        items = []

    structured = {"type": "accounts", "total": len(items), "items": items}

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Account {account_id} updated. Refreshed list returned.")],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# CONTACT TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the latest 5 Contacts from Salesforce. "
        "Returns first name, last name, email, phone, title, and associated account."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_contacts() -> types.CallToolResult:
    try:
        items = await _fetch_contacts()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch contacts: {exc}")

    structured = {"type": "contacts", "total": len(items), "items": items}

    lines = [f"Found {len(items)} contact(s):"]
    for c in items:
        lines.append(f"- {c['first_name']} {c['last_name']} | {c['email']} | Title: {c['title']} | Account: {c['account_name']}")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(lines))],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Create a new Contact in Salesforce. "
        "Requires last_name at minimum. "
        "Returns the updated list of latest 5 contacts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__create_contact(
    last_name: str,
    first_name: str = "",
    email: str = "",
    phone: str = "",
    title: str = "",
    account_id: str = "",
) -> types.CallToolResult:
    """
    Args:
        last_name:   Contact last name (required)
        first_name:  Contact first name
        email:       Email address
        phone:       Phone number
        title:       Job title
        account_id:  Salesforce Account Id to link this contact to
    """
    try:
        sf = get_client()
        data: dict = {"LastName": last_name}
        if first_name: data["FirstName"] = first_name
        if email:      data["Email"] = email
        if phone:      data["Phone"] = phone
        if title:      data["Title"] = title
        if account_id: data["AccountId"] = account_id

        new_id = await sf.create("Contact", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create contact: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating contact: {exc}")

    try:
        items = await _fetch_contacts()
    except Exception:
        items = []

    structured = {"type": "contacts", "total": len(items), "items": items, "_createdId": new_id}

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact '{first_name} {last_name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Update an existing Contact in Salesforce by its record Id. "
        "Only fields provided will be updated. "
        "Returns the updated list of latest 5 contacts."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__update_contact(
    contact_id: str,
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    phone: str = "",
    title: str = "",
    account_id: str = "",
) -> types.CallToolResult:
    """
    Args:
        contact_id:  Salesforce Contact record Id (required)
        first_name:  Updated first name
        last_name:   Updated last name
        email:       Updated email address
        phone:       Updated phone number
        title:       Updated job title
        account_id:  Updated Account Id link
    """
    try:
        sf = get_client()
        data: dict = {}
        if first_name: data["FirstName"] = first_name
        if last_name:  data["LastName"] = last_name
        if email:      data["Email"] = email
        if phone:      data["Phone"] = phone
        if title:      data["Title"] = title
        if account_id: data["AccountId"] = account_id

        if not data:
            return _error_result("No fields provided to update.")

        await sf.update("Contact", contact_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
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
# FORM TOOLS — open interactive create-forms in the widget
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description="Opens a form to create a new Salesforce Lead. The user fills in details and submits.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__create_lead_form() -> types.CallToolResult:
    """Opens an interactive form widget for creating a new Salesforce Lead."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Opening Lead creation form. Fill in the details and click Submit.")],
        structuredContent={"type": "form", "entity": "lead"},
    )


@mcp.tool(
    description="Opens a form to create a new Salesforce Account. The user fills in details and submits.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__create_account_form() -> types.CallToolResult:
    """Opens an interactive form widget for creating a new Salesforce Account."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Opening Account creation form. Fill in the details and click Submit.")],
        structuredContent={"type": "form", "entity": "account"},
    )


@mcp.tool(
    description="Opens a form to create a new Salesforce Contact. The user fills in details and submits.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__create_contact_form() -> types.CallToolResult:
    """Opens an interactive form widget for creating a new Salesforce Contact."""
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Opening Contact creation form. Fill in the details and click Submit.")],
        structuredContent={"type": "form", "entity": "contact"},
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
    """Help manage Salesforce CRM data — leads, opportunities, accounts, and contacts."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    "I want to manage my Salesforce CRM data. "
                    "Start by showing me the latest 5 leads with get_leads. "
                    "I may want to create new leads, edit existing ones, "
                    "or switch to viewing opportunities, accounts, or contacts."
                ),
            ),
        )
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SERVER ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def _validate_env() -> None:
    """Check required environment variables and print startup checklist."""
    log.info("validating_env")
    print("  ┌─ Environment ─────────────────────────────────")
    print(f"  │ SF_INSTANCE_URL   {'✓ ' + settings.sf_instance_url[:40] if settings.sf_instance_url else '✗ MISSING'}")
    print(f"  │ SF_CLIENT_ID      {'✓ ' + settings.sf_client_id[:8] + '...' if settings.sf_client_id else '✗ MISSING'}")
    print(f"  │ SF_CLIENT_SECRET  {'✓ (set)' if settings.sf_client_secret else '✗ MISSING'}")
    print("  └────────────────────────────────────────────────")

    missing = []
    if not settings.sf_instance_url: missing.append("SF_INSTANCE_URL")
    if not settings.sf_client_id: missing.append("SF_CLIENT_ID")
    if not settings.sf_client_secret: missing.append("SF_CLIENT_SECRET")
    if missing:
        log.error("missing_env_vars", vars=missing)
        print(f"\n  ❌ Missing required env vars: {', '.join(missing)}")
        print("  Copy .env.example to .env and fill in your Salesforce credentials.")
        sys.exit(1)


def main():
    _validate_env()
    log.info("starting", port=settings.port)
    print(f"⚓ GTC — Salesforce Trading Post starting on port {settings.port}")

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
