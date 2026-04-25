"""
Salesforce CRM MCP Server — 15 tools for Leads, Opportunities, Accounts & Contacts CRUD.

All tools return structuredContent for the widget, with _meta on the
decorator to ensure M365 Copilot discovers the widget URI from tools/list.
"""

import copy
import json
import os
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import structlog
import uvicorn
from dotenv import load_dotenv


def _load_env() -> None:
    explicit = os.environ.get("MCP_SERVERS_ENV_FILE")
    if explicit:
        load_dotenv(explicit, override=True)
        return
    project_env = Path.cwd() / "env" / ".env.sf"
    if project_env.exists():
        load_dotenv(project_env, override=True)
        return
    load_dotenv()
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
from pydantic_settings import BaseSettings
from starlette.middleware.cors import CORSMiddleware

from .salesforce import SalesforceAPIError, SalesforceAuthError, get_client

_load_env()

log = structlog.get_logger("sf")


# ── Typed Configuration ───────────────────────────────────────────────────────

class SFSettings(BaseSettings):
    sf_instance_url: str = ""
    sf_client_id: str = ""
    sf_client_secret: str = ""
    port: int = 3000
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


@lru_cache(maxsize=1)
def get_settings() -> SFSettings:
    return SFSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


settings = get_settings()


# ── Widget ─────────────────────────────────────────────────────────────────────

WIDGET_URI = "ui://widget/crm.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")

# ── Entity Config ─────────────────────────────────────────────────────────────

_CONFIG_PATH = Path(__file__).parent / "config" / "entities.json"
_DEFAULT_PATH = Path(__file__).parent / "config" / "entities.default.json"
_config_store: dict = {}


def _load_config() -> None:
    global _config_store
    try:
        _config_store = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        log.warning("entity_config_not_found", falling_back="defaults")
        _config_store = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log.error("entity_config_load_error", error=str(exc))
        _config_store = {}


def _get_schema(entity_type: str) -> dict:
    return _config_store.get(entity_type, {})


_load_config()


# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP("gtc-sf-trading-post")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def crm_widget() -> str:
    """UI widget for displaying Salesforce CRM data."""
    return WIDGET_HTML


# ── Helpers ────────────────────────────────────────────────────────────────────

def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"error": True, "message": message},
    )


def _flatten_record(r: dict, columns: list[dict]) -> dict:
    """Map a raw Salesforce record to a response dict using column apiNames."""
    result: dict[str, Any] = {"id": r.get("Id", "")}
    for col in columns:
        api = col["apiName"]
        if api == "Id":
            continue
        if "." in api:
            parts = api.split(".", 1)
            result[api] = ((r.get(parts[0]) or {}).get(parts[1])) or ""
        else:
            val = r.get(api)
            result[api] = val if val is not None else ""
    return result


async def _fetch_entity(entity_type: str) -> list[dict]:
    """Fetch records for any entity using its current config."""
    cfg = _get_schema(entity_type)
    columns = cfg.get("columns", [])
    limit = cfg.get("limit", 5)
    order_by = cfg.get("orderBy", "CreatedDate DESC")
    soql_object = cfg.get("soqlObject", entity_type)
    api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
    soql = f"SELECT {', '.join(api_names)} FROM {soql_object} ORDER BY {order_by} LIMIT {limit}"
    sf = get_client()
    records = await sf.query(soql)
    return [_flatten_record(r, columns) for r in records]


def _list_summary(entity_label: str, items: list[dict], entity_type: str) -> str:
    if not items:
        return f"No {entity_label} found."
    cols = _get_schema(entity_type).get("columns", [])
    lines = [f"Retrieved {len(items)} {entity_label}:"]
    for item in items:
        parts = [str(item.get(c["apiName"], "")) for c in cols[:4] if c["apiName"] != "Id"]
        lines.append(f"- {' | '.join(p for p in parts if p)}")
    return "\n".join(lines)


async def _fetch_leads() -> list[dict]:
    return await _fetch_entity("Lead")


async def _fetch_opportunities() -> list[dict]:
    return await _fetch_entity("Opportunity")


async def _fetch_accounts() -> list[dict]:
    return await _fetch_entity("Account")


async def _fetch_contacts() -> list[dict]:
    return await _fetch_entity("Contact")


# ══════════════════════════════════════════════════════════════════════════════
# LEAD TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the 5 most recent Leads from Salesforce. "
        "Pass campaign_id to get leads for a specific campaign. "
        "Returns lead name, company, email, phone, status, and lead source."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_leads(campaign_id: str = "") -> types.CallToolResult:
    """Fetch latest 5 Leads from Salesforce, optionally filtered by campaign."""
    log.info("sf__get_leads", campaign_id=campaign_id)
    try:
        if campaign_id:
            cfg = _get_schema("Lead")
            columns = cfg.get("columns", [])
            api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
            soql = (
                f"SELECT {', '.join(api_names)} FROM Lead "
                f"WHERE Id IN (SELECT LeadId FROM CampaignMember WHERE CampaignId = '{campaign_id}') "
                f"ORDER BY CreatedDate DESC LIMIT 20"
            )
            sf = get_client()
            records = await sf.query(soql)
            items = [_flatten_record(r, columns) for r in records]
        else:
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

    log.info("sf__get_leads_done", count=len(items))
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("lead(s)", items, "Lead"))],
        structuredContent={"type": "leads", "total": len(items), "items": items, "_schema": _get_schema("Lead")},
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

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "leads", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Lead")},
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

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead {lead_id} updated. Refreshed list returned.")],
        structuredContent={"type": "leads", "total": len(items), "items": items, "_schema": _get_schema("Lead")},
    )


@mcp.tool(
    description=(
        "Get full details for a single Salesforce Lead by Id. "
        "Returns all fields including description, title, website, revenue, and created date."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_lead(lead_id: str) -> types.CallToolResult:
    log.info("sf__get_lead", lead_id=lead_id)
    try:
        sf = get_client()
        soql = (
            f"SELECT Id, FirstName, LastName, Company, Email, Phone, Status, LeadSource, "
            f"Title, Website, Description, AnnualRevenue, NumberOfEmployees, CreatedDate "
            f"FROM Lead WHERE Id = '{lead_id}' LIMIT 1"
        )
        records = await sf.query(soql)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching lead: {exc}")

    if not records:
        return _error_result(f"Lead {lead_id} not found.")

    r = records[0]
    record = {
        "id": r.get("Id", ""),
        "first_name": r.get("FirstName") or "",
        "last_name": r.get("LastName") or "",
        "company": r.get("Company") or "",
        "email": r.get("Email") or "",
        "phone": r.get("Phone") or "",
        "status": r.get("Status") or "",
        "lead_source": r.get("LeadSource") or "",
        "title": r.get("Title") or "",
        "website": r.get("Website") or "",
        "description": r.get("Description") or "",
        "annual_revenue": r.get("AnnualRevenue"),
        "number_of_employees": r.get("NumberOfEmployees"),
        "created_date": (r.get("CreatedDate") or "")[:10],
    }
    name = f"{record['first_name']} {record['last_name']}".strip()
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead: {name} at {record['company']}. Status: {record['status']}.")],
        structuredContent={"type": "lead_detail", "record": record},
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
async def sf__get_opportunities(account_id: str = "") -> types.CallToolResult:
    """Fetch latest 5 Opportunities, optionally filtered by account."""
    log.info("sf__get_opportunities", account_id=account_id)
    try:
        if account_id:
            cfg = _get_schema("Opportunity")
            columns = cfg.get("columns", [])
            api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
            soql = (
                f"SELECT {', '.join(api_names)} FROM Opportunity "
                f"WHERE AccountId = '{account_id}' ORDER BY CreatedDate DESC LIMIT 20"
            )
            sf = get_client()
            records = await sf.query(soql)
            items = [_flatten_record(r, columns) for r in records]
        else:
            items = await _fetch_opportunities()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching opportunities: {exc}")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("opportunity(ies)", items, "Opportunity"))],
        structuredContent={"type": "opportunities", "total": len(items), "items": items, "_schema": _get_schema("Opportunity")},
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

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Opportunity created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "opportunities", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Opportunity")},
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

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Opportunity {opportunity_id} updated. Refreshed list returned.")],
        structuredContent={"type": "opportunities", "total": len(items), "items": items, "_schema": _get_schema("Opportunity")},
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

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("account(s)", items, "Account"))],
        structuredContent={"type": "accounts", "total": len(items), "items": items, "_schema": _get_schema("Account")},
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

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Account '{name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "accounts", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Account")},
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

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Account {account_id} updated. Refreshed list returned.")],
        structuredContent={"type": "accounts", "total": len(items), "items": items, "_schema": _get_schema("Account")},
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
async def sf__get_contacts(account_id: str = "") -> types.CallToolResult:
    try:
        if account_id:
            cfg = _get_schema("Contact")
            columns = cfg.get("columns", [])
            api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
            soql = (
                f"SELECT {', '.join(api_names)} FROM Contact "
                f"WHERE AccountId = '{account_id}' ORDER BY CreatedDate DESC LIMIT 20"
            )
            sf = get_client()
            records = await sf.query(soql)
            items = [_flatten_record(r, columns) for r in records]
        else:
            items = await _fetch_contacts()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch contacts: {exc}")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("contact(s)", items, "Contact"))],
        structuredContent={"type": "contacts", "total": len(items), "items": items, "_schema": _get_schema("Contact")},
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

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact '{first_name} {last_name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "contacts", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Contact")},
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

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact {contact_id} updated. Refreshed list returned.")],
        structuredContent={"type": "contacts", "total": len(items), "items": items, "_schema": _get_schema("Contact")},
    )


# ══════════════════════════════════════════════════════════════════════════════
# CASE TOOLS
# ══════════════════════════════════════════════════════════════════════════════


async def _fetch_cases() -> list[dict]:
    return await _fetch_entity("Case")


@mcp.tool(
    description=(
        "Get the 5 most recent Cases from Salesforce. "
        "Returns case number, subject, status, priority, and account name."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_cases(account_id: str = "") -> types.CallToolResult:
    log.info("sf__get_cases", account_id=account_id)
    try:
        if account_id:
            cfg = _get_schema("Case")
            columns = cfg.get("columns", [])
            api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
            soql = (
                f"SELECT {', '.join(api_names)} FROM Case "
                f"WHERE AccountId = '{account_id}' ORDER BY CreatedDate DESC LIMIT 20"
            )
            sf = get_client()
            records = await sf.query(soql)
            items = [_flatten_record(r, columns) for r in records]
        else:
            items = await _fetch_cases()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching cases: {exc}")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("case(s)", items, "Case"))],
        structuredContent={"type": "cases", "total": len(items), "items": items, "_schema": _get_schema("Case")},
    )


@mcp.tool(
    description=(
        "Create a new Salesforce Case. "
        "Required: subject. Optional: priority (High/Medium/Low), account_id, description."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__create_case(
    subject: str,
    priority: str = "Medium",
    account_id: str = "",
    description: str = "",
) -> types.CallToolResult:
    log.info("sf__create_case", subject=subject)
    try:
        sf = get_client()
        data: dict = {"Subject": subject, "Priority": priority}
        if account_id:   data["AccountId"] = account_id
        if description:  data["Description"] = description
        new_id = await sf.create("Case", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create case: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating case: {exc}")

    try:
        items = await _fetch_cases()
    except Exception:
        items = []

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Case created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "cases", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Case")},
    )


@mcp.tool(
    description=(
        "Update a Salesforce Case. "
        "Required: case_id. Optional: status, resolution (Internal Comments)."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__update_case(
    case_id: str,
    status: str = "",
    resolution: str = "",
) -> types.CallToolResult:
    log.info("sf__update_case", case_id=case_id)
    try:
        sf = get_client()
        data: dict = {}
        if status:      data["Status"] = status
        if resolution:  data["Comments"] = resolution
        if not data:
            return _error_result("No fields provided to update.")
        await sf.update("Case", case_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update case: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating case: {exc}")

    try:
        items = await _fetch_cases()
    except Exception:
        items = []

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Case {case_id} updated. Refreshed list returned.")],
        structuredContent={"type": "cases", "total": len(items), "items": items, "_schema": _get_schema("Case")},
    )


@mcp.tool(
    description=(
        "Get full details for a single Salesforce Case by Id. "
        "Returns all fields including description, comments, origin, type, account, and dates."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_case(case_id: str) -> types.CallToolResult:
    log.info("sf__get_case", case_id=case_id)
    try:
        sf = get_client()
        soql = (
            f"SELECT Id, CaseNumber, Subject, Status, Priority, Origin, Type, "
            f"Account.Name, Description, Comments, CreatedDate, ClosedDate "
            f"FROM Case WHERE Id = '{case_id}' LIMIT 1"
        )
        records = await sf.query(soql)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching case: {exc}")

    if not records:
        return _error_result(f"Case {case_id} not found.")

    r = records[0]
    account = r.get("Account") or {}
    record = {
        "id": r.get("Id", ""),
        "case_number": r.get("CaseNumber") or "",
        "subject": r.get("Subject") or "",
        "status": r.get("Status") or "",
        "priority": r.get("Priority") or "",
        "origin": r.get("Origin") or "",
        "type": r.get("Type") or "",
        "account_name": account.get("Name") or "",
        "description": r.get("Description") or "",
        "comments": r.get("Comments") or "",
        "created_date": (r.get("CreatedDate") or "")[:10],
        "closed_date": (r.get("ClosedDate") or "")[:10],
    }
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Case {record['case_number']}: {record['subject']}. Status: {record['status']}.")],
        structuredContent={"type": "case_detail", "record": record},
    )


@mcp.tool(
    description="Get notes/comments for a Salesforce Case by case Id.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_case_comments(case_id: str) -> types.CallToolResult:
    log.info("sf__get_case_comments", case_id=case_id)
    try:
        sf = get_client()
        soql = (
            f"SELECT Id, CommentBody, CreatedDate, CreatedBy.Name "
            f"FROM CaseComment WHERE ParentId = '{case_id}' ORDER BY CreatedDate ASC LIMIT 50"
        )
        records = await sf.query(soql)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch case comments: {exc}")

    items = [
        {
            "id": r.get("Id", ""),
            "body": r.get("CommentBody") or "",
            "created_by": (r.get("CreatedBy") or {}).get("Name") or "",
            "created_date": (r.get("CreatedDate") or "")[:10],
        }
        for r in records
    ]
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"{len(items)} comment(s) for case {case_id}.")],
        structuredContent={"type": "case_comments", "case_id": case_id, "items": items},
    )


# ══════════════════════════════════════════════════════════════════════════════
# TASK TOOLS
# ══════════════════════════════════════════════════════════════════════════════


async def _fetch_tasks() -> list[dict]:
    return await _fetch_entity("Task")


@mcp.tool(
    description=(
        "Get the 5 most recent Tasks from Salesforce. "
        "Returns subject, status, priority, and due date."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_tasks() -> types.CallToolResult:
    log.info("sf__get_tasks")
    try:
        items = await _fetch_tasks()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching tasks: {exc}")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("task(s)", items, "Task"))],
        structuredContent={"type": "tasks", "total": len(items), "items": items, "_schema": _get_schema("Task")},
    )


@mcp.tool(
    description=(
        "Create a new Salesforce Task (activity). "
        "Required: subject. Optional: priority, due_date (YYYY-MM-DD), what_id (related record Id)."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__create_task(
    subject: str,
    priority: str = "Normal",
    due_date: str = "",
    what_id: str = "",
) -> types.CallToolResult:
    log.info("sf__create_task", subject=subject)
    try:
        sf = get_client()
        data: dict = {"Subject": subject, "Priority": priority, "Status": "Not Started"}
        if due_date: data["ActivityDate"] = due_date
        if what_id:  data["WhatId"] = what_id
        new_id = await sf.create("Task", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create task: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating task: {exc}")

    try:
        items = await _fetch_tasks()
    except Exception:
        items = []

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Task created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "tasks", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Task")},
    )


@mcp.tool(
    description=(
        "Get full details for a single Salesforce Task by Id. "
        "Returns subject, status, priority, due date, description, and related record."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_task(task_id: str) -> types.CallToolResult:
    log.info("sf__get_task", task_id=task_id)
    try:
        sf = get_client()
        soql = (
            f"SELECT Id, Subject, Status, Priority, ActivityDate, "
            f"Description, WhoId, WhatId, CreatedDate "
            f"FROM Task WHERE Id = '{task_id}' LIMIT 1"
        )
        records = await sf.query(soql)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching task: {exc}")

    if not records:
        return _error_result(f"Task {task_id} not found.")

    r = records[0]
    record = {
        "id": r.get("Id", ""),
        "subject": r.get("Subject") or "",
        "status": r.get("Status") or "",
        "priority": r.get("Priority") or "",
        "activity_date": r.get("ActivityDate") or "",
        "description": r.get("Description") or "",
        "who_id": r.get("WhoId") or "",
        "what_id": r.get("WhatId") or "",
        "created_date": (r.get("CreatedDate") or "")[:10],
    }
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Task: {record['subject']}. Status: {record['status']}. Due: {record['activity_date'] or 'not set'}.")],
        structuredContent={"type": "task_detail", "record": record},
    )


# ══════════════════════════════════════════════════════════════════════════════
# LEAD — DELETE & CONVERT
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description="Delete a Salesforce Lead by Id. Returns the refreshed lead list.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__delete_lead(lead_id: str) -> types.CallToolResult:
    log.info("sf__delete_lead", lead_id=lead_id)
    try:
        sf = get_client()
        await sf.delete("Lead", lead_id)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to delete lead: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error deleting lead: {exc}")

    try:
        items = await _fetch_leads()
    except Exception:
        items = []

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead {lead_id} deleted. Refreshed list returned.")],
        structuredContent={"type": "leads", "total": len(items), "items": items, "_schema": _get_schema("Lead")},
    )


@mcp.tool(
    description=(
        "Convert a Salesforce Lead into an Account, Contact, and optionally an Opportunity. "
        "Required: lead_id. Optional: converted_status (defaults to 'Closed - Converted'), "
        "create_opportunity (true/false)."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__convert_lead(
    lead_id: str,
    converted_status: str = "Closed - Converted",
    create_opportunity: bool = True,
) -> types.CallToolResult:
    log.info("sf__convert_lead", lead_id=lead_id)
    try:
        sf = get_client()
        results = await sf.invoke_action(
            "convertLead",
            [{"leadId": lead_id, "convertedStatus": converted_status, "doNotCreateOpportunity": not create_opportunity}],
        )
        result = results[0] if results else {}
        account_id = result.get("accountId", "")
        contact_id = result.get("contactId", "")
        opp_id     = result.get("opportunityId", "")
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to convert lead: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error converting lead: {exc}")

    summary = (
        f"Lead {lead_id} converted.\n"
        f"  Account:     {account_id or 'existing'}\n"
        f"  Contact:     {contact_id or 'existing'}\n"
        f"  Opportunity: {opp_id or 'not created'}"
    )
    structured = {
        "type": "lead_convert",
        "leadId": lead_id,
        "accountId": account_id,
        "contactId": contact_id,
        "opportunityId": opp_id,
    }
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE DASHBOARD, CAMPAIGNS, APPROVALS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the Salesforce opportunity pipeline grouped by stage. "
        "Returns deal count and total amount per stage."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_pipeline_dashboard() -> types.CallToolResult:
    log.info("sf__get_pipeline_dashboard")
    try:
        sf = get_client()
        records = await sf.query(
            "SELECT StageName, COUNT(Id) cnt, SUM(Amount) amount "
            "FROM Opportunity WHERE IsClosed = false "
            "GROUP BY StageName ORDER BY StageName"
        )
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching pipeline: {exc}")

    stages = [
        {
            "stage":  r.get("StageName") or "",
            "count":  r.get("cnt") or 0,
            "amount": r.get("amount") or 0.0,
        }
        for r in records
    ]
    total_amount = sum(s["amount"] for s in stages)
    lines = [f"Pipeline dashboard — {len(stages)} stage(s), total ${total_amount:,.0f}:"]
    for s in stages:
        lines.append(f"  {s['stage']}: {s['count']} deal(s), ${s['amount']:,.0f}")
    summary = "\n".join(lines) if stages else "No open opportunities."

    structured = {"type": "pipeline_dashboard", "total_amount": total_amount, "stages": stages}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Get the 5 most recent Campaigns from Salesforce. "
        "Returns campaign name, status, type, start/end date, and lead count."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_campaigns() -> types.CallToolResult:
    log.info("sf__get_campaigns")
    try:
        sf = get_client()
        records = await sf.query(
            "SELECT Id, Name, Status, Type, StartDate, EndDate, NumberOfLeads "
            "FROM Campaign ORDER BY CreatedDate DESC LIMIT 5"
        )
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching campaigns: {exc}")

    items = [
        {
            "id":          r.get("Id"),
            "name":        r.get("Name") or "",
            "status":      r.get("Status") or "",
            "type":        r.get("Type") or "",
            "start_date":  r.get("StartDate") or "",
            "end_date":    r.get("EndDate") or "",
            "num_leads":   r.get("NumberOfLeads") or 0,
        }
        for r in records
    ]
    structured = {"type": "campaigns", "total": len(items), "items": items}
    if not items:
        summary = "No campaigns found."
    else:
        lines = [f"Retrieved {len(items)} campaign(s):"]
        for c in items:
            lines.append(f"- {c['name']} | {c['status']} | {c['type']} | leads: {c['num_leads']}")
        summary = "\n".join(lines)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Get pending Salesforce approval requests assigned to the current user. "
        "Returns pending ProcessInstance workitems requiring action."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_pending_approvals() -> types.CallToolResult:
    log.info("sf__get_pending_approvals")
    try:
        sf = get_client()
        records = await sf.query(
            "SELECT Id, ProcessInstance.TargetObjectId, "
            "ProcessInstance.Status, ProcessInstance.TargetObject.Name, "
            "CreatedDate "
            "FROM ProcessInstanceWorkitem "
            "WHERE ProcessInstance.Status = 'Pending' "
            "ORDER BY CreatedDate DESC LIMIT 10"
        )
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching approvals: {exc}")

    items = [
        {
            "id":            r.get("Id"),
            "target_id":     (r.get("ProcessInstance") or {}).get("TargetObjectId") or "",
            "target_name":   ((r.get("ProcessInstance") or {}).get("TargetObject") or {}).get("Name") or "",
            "status":        (r.get("ProcessInstance") or {}).get("Status") or "",
            "created_date":  r.get("CreatedDate") or "",
        }
        for r in records
    ]
    structured = {"type": "approvals", "total": len(items), "items": items}
    if not items:
        summary = "No pending approvals."
    else:
        lines = [f"Retrieved {len(items)} pending approval(s):"]
        for a in items:
            lines.append(f"- {a['target_name'] or a['target_id']} | {a['status']}")
        summary = "\n".join(lines)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ENTITY CONFIG TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Get the current display configuration for a Salesforce entity. "
        "entity_type: Lead, Opportunity, Account, Contact, Case, or Task."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__get_entity_config(entity_type: str) -> types.CallToolResult:
    schema = _get_schema(entity_type)
    if not schema:
        return _error_result(f"No configuration found for entity type '{entity_type}'.")
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Configuration for {entity_type} retrieved.")],
        structuredContent={"type": "entity_config", "entity": entity_type, "config": schema},
    )


@mcp.tool(
    description=(
        "Update the display configuration for a Salesforce entity. "
        "Pass entity_type (Lead, Opportunity, etc.) and a JSON patch string. "
        "Example patch: '{\"limit\": 10}' or '{\"columns\": [{\"apiName\": \"Name\", \"label\": \"Full Name\", \"width\": \"200px\"}]}'. "
        "Changes take effect immediately and are saved to disk."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__update_entity_config(entity_type: str, patch: str) -> types.CallToolResult:
    """
    Args:
        entity_type: e.g. 'Lead', 'Opportunity', 'Account', 'Contact', 'Case', 'Task'
        patch:       JSON string with top-level keys to update
    """
    global _config_store
    if entity_type not in _config_store:
        return _error_result(f"Unknown entity type '{entity_type}'. Valid types: {', '.join(_config_store.keys())}")
    try:
        patch_dict = json.loads(patch)
    except json.JSONDecodeError as exc:
        return _error_result(f"Invalid JSON patch: {exc}")

    _config_store[entity_type].update(patch_dict)
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(json.dumps(_config_store, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        log.error("entity_config_write_error", error=str(exc))
        return _error_result(f"Config updated in memory but failed to write to disk: {exc}")

    log.info("entity_config_updated", entity=entity_type)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Configuration for {entity_type} updated and saved.")],
        structuredContent={"type": "entity_config", "entity": entity_type, "config": _config_store[entity_type]},
    )


@mcp.tool(
    description=(
        "Reset a Salesforce entity configuration to factory defaults. "
        "Pass entity_type='all' to reset every entity at once."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def sf__reset_entity_config(entity_type: str) -> types.CallToolResult:
    """
    Args:
        entity_type: e.g. 'Lead', 'Opportunity', or 'all'
    """
    global _config_store
    try:
        defaults = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return _error_result(f"Failed to read default config: {exc}")

    if entity_type == "all":
        _config_store = copy.deepcopy(defaults)
        msg = "All entity configurations reset to factory defaults."
    elif entity_type in defaults:
        _config_store[entity_type] = copy.deepcopy(defaults[entity_type])
        msg = f"{entity_type} configuration reset to factory defaults."
    else:
        return _error_result(f"Unknown entity type '{entity_type}'. Valid types: all, {', '.join(defaults.keys())}")

    try:
        _CONFIG_PATH.write_text(json.dumps(_config_store, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        log.error("entity_config_write_error", error=str(exc))
        return _error_result(f"Config reset in memory but failed to write to disk: {exc}")

    log.info("entity_config_reset", entity=entity_type)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=msg)],
        structuredContent={"type": "entity_config_reset", "entity": entity_type},
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
