"""Salesforce CRM tool handlers, _TOOL_SPECS_LIST, PROMPT_SPECS. No MCP bootstrap here."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import structlog
from mcp import types
from mcp.types import PromptMessage, TextContent

from .salesforce_client import SalesforceAPIError, SalesforceAuthError, get_client

log = structlog.get_logger("sf")

# ── Entity config ─────────────────────────────────────────────────────────────

_CONFIG_PATH  = Path(__file__).parent / "config" / "entities.json"
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


# ── Shared helpers ────────────────────────────────────────────────────────────

def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        isError=True,
    )


def _flatten_record(r: dict, columns: list[dict]) -> dict:
    result: dict[str, Any] = {"id": r.get("Id", "")}
    for col in columns:
        api = col["apiName"]
        key = col.get("key", api)
        if api == "Id":
            continue
        if "." in api:
            parts = api.split(".", 1)
            val = ((r.get(parts[0]) or {}).get(parts[1])) or ""
        else:
            val = r.get(api)
            if val is None:
                val = ""
        result[key] = val
    return result


async def _fetch_entity(entity_type: str) -> list[dict]:
    cfg = _get_schema(entity_type)
    columns = cfg.get("columns", [])
    hidden = cfg.get("hiddenColumns", [])
    all_cols = columns + hidden
    limit = cfg.get("limit", 5)
    order_by = cfg.get("orderBy", "CreatedDate DESC")
    soql_object = cfg.get("soqlObject", entity_type)
    api_names = ["Id"] + [c["apiName"] for c in all_cols if c["apiName"] != "Id"]
    soql = f"SELECT {', '.join(api_names)} FROM {soql_object} ORDER BY {order_by} LIMIT {limit}"
    sf = get_client()
    records = await sf.query(soql)
    return [_flatten_record(r, all_cols) for r in records]


def _list_summary(entity_label: str, items: list[dict], entity_type: str) -> str:
    if not items:
        return f"No {entity_label} found."
    cols = _get_schema(entity_type).get("columns", [])
    lines = [f"Retrieved {len(items)} {entity_label}:"]
    for item in items:
        parts = [str(item.get(c.get("key", c["apiName"]), "")) for c in cols[:4] if c["apiName"] != "Id"]
        lines.append(f"- {' | '.join(p for p in parts if p)}")
    return "\n".join(lines)


async def _fetch_leads()         -> list[dict]: return await _fetch_entity("Lead")
async def _fetch_opportunities() -> list[dict]: return await _fetch_entity("Opportunity")
async def _fetch_accounts()      -> list[dict]: return await _fetch_entity("Account")
async def _fetch_contacts()      -> list[dict]: return await _fetch_entity("Contact")
async def _fetch_cases()         -> list[dict]: return await _fetch_entity("Case")
async def _fetch_tasks()         -> list[dict]: return await _fetch_entity("Task")


# ── Tool handlers ─────────────────────────────────────────────────────────────

async def sf__get_leads(campaign_id: str = "", name: str = "") -> types.CallToolResult:
    log.info("sf__get_leads", campaign_id=campaign_id, name=name)
    try:
        cfg = _get_schema("Lead")
        columns = cfg.get("columns", []) + cfg.get("hiddenColumns", [])
        api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
        if campaign_id:
            soql = (f"SELECT {', '.join(api_names)} FROM Lead "
                    f"WHERE Id IN (SELECT LeadId FROM CampaignMember WHERE CampaignId = '{campaign_id}') "
                    f"ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        elif name:
            soql = (f"SELECT {', '.join(api_names)} FROM Lead "
                    f"WHERE FirstName LIKE '%{name}%' OR LastName LIKE '%{name}%' OR Company LIKE '%{name}%' "
                    f"ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        else:
            items = await _fetch_leads()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching leads: {exc}")
    log.info("sf__get_leads_done", count=len(items))
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("lead(s)", items, "Lead"))],
        structuredContent={"type": "leads", "total": len(items), "items": items, "_schema": _get_schema("Lead")},
    )


async def sf__create_lead(
    last_name: str, company: str, first_name: str = "", email: str = "",
    phone: str = "", status: str = "Open - Not Contacted", lead_source: str = "",
) -> types.CallToolResult:
    try:
        sf = get_client()
        data: dict = {"LastName": last_name, "Company": company}
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
    try: items = await _fetch_leads()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "leads", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Lead")},
    )


async def sf__update_lead(
    lead_id: str, first_name: str = "", last_name: str = "", company: str = "",
    email: str = "", phone: str = "", status: str = "", lead_source: str = "",
) -> types.CallToolResult:
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
        if not data: return _error_result("No fields provided to update.")
        await sf.update("Lead", lead_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update lead: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating lead: {exc}")
    try: items = await _fetch_leads()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead {lead_id} updated. Refreshed list returned.")],
        structuredContent={"type": "leads", "total": len(items), "items": items, "_schema": _get_schema("Lead")},
    )


async def sf__get_lead(lead_id: str) -> types.CallToolResult:
    log.info("sf__get_lead", lead_id=lead_id)
    try:
        sf = get_client()
        soql = (f"SELECT Id, FirstName, LastName, Company, Email, Phone, Status, LeadSource, "
                f"Title, Website, Description, AnnualRevenue, NumberOfEmployees, CreatedDate "
                f"FROM Lead WHERE Id = '{lead_id}' LIMIT 1")
        records = await sf.query(soql)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching lead: {exc}")
    if not records: return _error_result(f"Lead {lead_id} not found.")
    r = records[0]
    record = {
        "id": r.get("Id", ""), "first_name": r.get("FirstName") or "", "last_name": r.get("LastName") or "",
        "company": r.get("Company") or "", "email": r.get("Email") or "", "phone": r.get("Phone") or "",
        "status": r.get("Status") or "", "lead_source": r.get("LeadSource") or "",
        "title": r.get("Title") or "", "website": r.get("Website") or "",
        "description": r.get("Description") or "", "annual_revenue": r.get("AnnualRevenue"),
        "number_of_employees": r.get("NumberOfEmployees"), "created_date": (r.get("CreatedDate") or "")[:10],
    }
    name = f"{record['first_name']} {record['last_name']}".strip()
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead: {name} at {record['company']}. Status: {record['status']}.")],
        structuredContent={"type": "lead_detail", "record": record},
    )


async def sf__get_opportunities(account_id: str = "", name: str = "", stage: str = "") -> types.CallToolResult:
    log.info("sf__get_opportunities", account_id=account_id, name=name, stage=stage)
    try:
        cfg = _get_schema("Opportunity")
        columns = cfg.get("columns", []) + cfg.get("hiddenColumns", [])
        api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
        if account_id:
            soql = (f"SELECT {', '.join(api_names)} FROM Opportunity "
                    f"WHERE AccountId = '{account_id}' ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        elif name or stage:
            clauses = []
            if name:  clauses.append(f"Name LIKE '%{name}%'")
            if stage: clauses.append(f"StageName = '{stage}'")
            soql = (f"SELECT {', '.join(api_names)} FROM Opportunity "
                    f"WHERE {' AND '.join(clauses)} ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
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


async def sf__create_opportunity(
    name: str, stage: str, close_date: str, amount: float = 0.0, probability: int = 0,
) -> types.CallToolResult:
    try:
        sf = get_client()
        data: dict = {"Name": name, "StageName": stage, "CloseDate": close_date}
        if amount:      data["Amount"] = amount
        if probability: data["Probability"] = probability
        new_id = await sf.create("Opportunity", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create opportunity: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating opportunity: {exc}")
    try: items = await _fetch_opportunities()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Opportunity created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "opportunities", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Opportunity")},
    )


async def sf__update_opportunity(
    opportunity_id: str, name: str = "", stage: str = "",
    amount: float = 0.0, close_date: str = "", probability: int = 0,
) -> types.CallToolResult:
    try:
        sf = get_client()
        data: dict = {}
        if name:        data["Name"] = name
        if stage:       data["StageName"] = stage
        if amount:      data["Amount"] = amount
        if close_date:  data["CloseDate"] = close_date
        if probability: data["Probability"] = probability
        if not data: return _error_result("No fields provided to update.")
        await sf.update("Opportunity", opportunity_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update opportunity: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating opportunity: {exc}")
    try: items = await _fetch_opportunities()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Opportunity {opportunity_id} updated. Refreshed list returned.")],
        structuredContent={"type": "opportunities", "total": len(items), "items": items, "_schema": _get_schema("Opportunity")},
    )


async def sf__get_accounts(name: str = "", industry: str = "") -> types.CallToolResult:
    log.info("sf__get_accounts", name=name, industry=industry)
    try:
        if name or industry:
            cfg = _get_schema("Account")
            columns = cfg.get("columns", []) + cfg.get("hiddenColumns", [])
            api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
            clauses = []
            if name:     clauses.append(f"Name LIKE '%{name}%'")
            if industry: clauses.append(f"Industry = '{industry}'")
            soql = f"SELECT {', '.join(api_names)} FROM Account WHERE {' AND '.join(clauses)} ORDER BY CreatedDate DESC LIMIT 20"
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        else:
            items = await _fetch_accounts()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch accounts: {exc}")
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("account(s)", items, "Account"))],
        structuredContent={"type": "accounts", "total": len(items), "items": items, "_schema": _get_schema("Account")},
    )


async def sf__create_account(
    name: str, industry: str = "", phone: str = "",
    website: str = "", billing_city: str = "", account_type: str = "",
) -> types.CallToolResult:
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
    try: items = await _fetch_accounts()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Account '{name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "accounts", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Account")},
    )


async def sf__update_account(
    account_id: str, name: str = "", industry: str = "", phone: str = "",
    website: str = "", billing_city: str = "", account_type: str = "",
) -> types.CallToolResult:
    try:
        sf = get_client()
        data: dict = {}
        if name:         data["Name"] = name
        if industry:     data["Industry"] = industry
        if phone:        data["Phone"] = phone
        if website:      data["Website"] = website
        if billing_city: data["BillingCity"] = billing_city
        if account_type: data["Type"] = account_type
        if not data: return _error_result("No fields provided to update.")
        await sf.update("Account", account_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update account: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating account: {exc}")
    try: items = await _fetch_accounts()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Account {account_id} updated. Refreshed list returned.")],
        structuredContent={"type": "accounts", "total": len(items), "items": items, "_schema": _get_schema("Account")},
    )


async def sf__get_contacts(account_id: str = "", name: str = "") -> types.CallToolResult:
    log.info("sf__get_contacts", account_id=account_id, name=name)
    try:
        cfg = _get_schema("Contact")
        columns = cfg.get("columns", []) + cfg.get("hiddenColumns", [])
        api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
        if account_id:
            soql = (f"SELECT {', '.join(api_names)} FROM Contact "
                    f"WHERE AccountId = '{account_id}' ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        elif name:
            soql = (f"SELECT {', '.join(api_names)} FROM Contact "
                    f"WHERE FirstName LIKE '%{name}%' OR LastName LIKE '%{name}%' "
                    f"ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
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


async def sf__create_contact(
    last_name: str, first_name: str = "", email: str = "",
    phone: str = "", title: str = "", account_id: str = "",
) -> types.CallToolResult:
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
    try: items = await _fetch_contacts()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact '{first_name} {last_name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "contacts", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Contact")},
    )


async def sf__update_contact(
    contact_id: str, first_name: str = "", last_name: str = "", email: str = "",
    phone: str = "", title: str = "", account_id: str = "",
) -> types.CallToolResult:
    try:
        sf = get_client()
        data: dict = {}
        if first_name: data["FirstName"] = first_name
        if last_name:  data["LastName"] = last_name
        if email:      data["Email"] = email
        if phone:      data["Phone"] = phone
        if title:      data["Title"] = title
        if account_id: data["AccountId"] = account_id
        if not data: return _error_result("No fields provided to update.")
        await sf.update("Contact", contact_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update contact: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating contact: {exc}")
    try: items = await _fetch_contacts()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact {contact_id} updated. Refreshed list returned.")],
        structuredContent={"type": "contacts", "total": len(items), "items": items, "_schema": _get_schema("Contact")},
    )


async def sf__get_cases(account_id: str = "", subject: str = "") -> types.CallToolResult:
    log.info("sf__get_cases", account_id=account_id, subject=subject)
    try:
        cfg = _get_schema("Case")
        columns = cfg.get("columns", []) + cfg.get("hiddenColumns", [])
        api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
        if account_id:
            soql = (f"SELECT {', '.join(api_names)} FROM Case "
                    f"WHERE AccountId = '{account_id}' ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        elif subject:
            soql = (f"SELECT {', '.join(api_names)} FROM Case "
                    f"WHERE Subject LIKE '%{subject}%' ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
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


async def sf__create_case(
    subject: str, priority: str = "Medium", account_id: str = "", description: str = "",
) -> types.CallToolResult:
    log.info("sf__create_case", subject=subject)
    try:
        sf = get_client()
        data: dict = {"Subject": subject, "Priority": priority}
        if account_id:  data["AccountId"] = account_id
        if description: data["Description"] = description
        new_id = await sf.create("Case", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create case: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating case: {exc}")
    try: items = await _fetch_cases()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Case created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "cases", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Case")},
    )


async def sf__update_case(case_id: str, status: str = "", resolution: str = "") -> types.CallToolResult:
    log.info("sf__update_case", case_id=case_id)
    try:
        sf = get_client()
        data: dict = {}
        if status:     data["Status"] = status
        if resolution: data["Comments"] = resolution
        if not data: return _error_result("No fields provided to update.")
        await sf.update("Case", case_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update case: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating case: {exc}")
    try: items = await _fetch_cases()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Case {case_id} updated. Refreshed list returned.")],
        structuredContent={"type": "cases", "total": len(items), "items": items, "_schema": _get_schema("Case")},
    )


async def sf__get_case(case_id: str) -> types.CallToolResult:
    log.info("sf__get_case", case_id=case_id)
    try:
        sf = get_client()
        soql = (f"SELECT Id, CaseNumber, Subject, Status, Priority, Origin, Type, "
                f"Account.Name, Description, Comments, CreatedDate, ClosedDate "
                f"FROM Case WHERE Id = '{case_id}' LIMIT 1")
        records = await sf.query(soql)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching case: {exc}")
    if not records: return _error_result(f"Case {case_id} not found.")
    r = records[0]; account = r.get("Account") or {}
    record = {
        "id": r.get("Id", ""), "case_number": r.get("CaseNumber") or "",
        "subject": r.get("Subject") or "", "status": r.get("Status") or "",
        "priority": r.get("Priority") or "", "origin": r.get("Origin") or "",
        "type": r.get("Type") or "", "account_name": account.get("Name") or "",
        "description": r.get("Description") or "", "comments": r.get("Comments") or "",
        "created_date": (r.get("CreatedDate") or "")[:10], "closed_date": (r.get("ClosedDate") or "")[:10],
    }
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Case {record['case_number']}: {record['subject']}. Status: {record['status']}.")],
        structuredContent={"type": "case_detail", "record": record},
    )


async def sf__get_case_comments(case_id: str) -> types.CallToolResult:
    log.info("sf__get_case_comments", case_id=case_id)
    try:
        sf = get_client()
        soql = (f"SELECT Id, CommentBody, CreatedDate, CreatedBy.Name "
                f"FROM CaseComment WHERE ParentId = '{case_id}' ORDER BY CreatedDate ASC LIMIT 50")
        records = await sf.query(soql)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch case comments: {exc}")
    items = [
        {"id": r.get("Id", ""), "body": r.get("CommentBody") or "",
         "created_by_name": (r.get("CreatedBy") or {}).get("Name") or "",
         "created_date": (r.get("CreatedDate") or "")[:10]}
        for r in records
    ]
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"{len(items)} comment(s) for case {case_id}.")],
        structuredContent={"type": "case_comments", "case_id": case_id, "items": items},
    )


async def sf__get_tasks(subject: str = "") -> types.CallToolResult:
    log.info("sf__get_tasks", subject=subject)
    try:
        if subject:
            cfg = _get_schema("Task")
            columns = cfg.get("columns", []) + cfg.get("hiddenColumns", [])
            api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
            soql = (f"SELECT {', '.join(api_names)} FROM Task "
                    f"WHERE Subject LIKE '%{subject}%' ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        else:
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


async def sf__create_task(
    subject: str, priority: str = "Normal", status: str = "Not Started",
    activity_date: str = "", description: str = "",
) -> types.CallToolResult:
    log.info("sf__create_task", subject=subject)
    try:
        sf = get_client()
        data: dict = {"Subject": subject, "Priority": priority, "Status": status}
        if activity_date: data["ActivityDate"] = activity_date
        if description:   data["Description"] = description
        new_id = await sf.create("Task", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create task: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating task: {exc}")
    try: items = await _fetch_tasks()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Task created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "tasks", "total": len(items), "items": items, "_createdId": new_id, "_schema": _get_schema("Task")},
    )


async def sf__update_task(
    task_id: str, subject: str = "", priority: str = "", status: str = "",
    activity_date: str = "", description: str = "",
) -> types.CallToolResult:
    log.info("sf__update_task", task_id=task_id)
    try:
        sf = get_client()
        data: dict = {}
        if subject:       data["Subject"] = subject
        if priority:      data["Priority"] = priority
        if status:        data["Status"] = status
        if activity_date: data["ActivityDate"] = activity_date
        if description:   data["Description"] = description
        if not data: return _error_result("No fields provided to update.")
        await sf.update("Task", task_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update task: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating task: {exc}")
    try: items = await _fetch_tasks()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Task {task_id} updated. Refreshed list returned.")],
        structuredContent={"type": "tasks", "total": len(items), "items": items, "_schema": _get_schema("Task")},
    )


async def sf__get_task(task_id: str) -> types.CallToolResult:
    log.info("sf__get_task", task_id=task_id)
    try:
        sf = get_client()
        soql = (f"SELECT Id, Subject, Status, Priority, ActivityDate, "
                f"Description, WhoId, WhatId, CreatedDate "
                f"FROM Task WHERE Id = '{task_id}' LIMIT 1")
        records = await sf.query(soql)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching task: {exc}")
    if not records: return _error_result(f"Task {task_id} not found.")
    r = records[0]
    record = {
        "id": r.get("Id", ""), "subject": r.get("Subject") or "", "status": r.get("Status") or "",
        "priority": r.get("Priority") or "", "activity_date": r.get("ActivityDate") or "",
        "description": r.get("Description") or "", "who_id": r.get("WhoId") or "",
        "what_id": r.get("WhatId") or "", "created_date": (r.get("CreatedDate") or "")[:10],
    }
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Task: {record['subject']}. Status: {record['status']}. Due: {record['activity_date'] or 'not set'}.")],
        structuredContent={"type": "task_detail", "record": record},
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
    try: items = await _fetch_leads()
    except Exception: items = []
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead {lead_id} deleted. Refreshed list returned.")],
        structuredContent={"type": "leads", "total": len(items), "items": items, "_schema": _get_schema("Lead")},
    )


async def sf__convert_lead(
    lead_id: str, converted_status: str = "Closed - Converted", create_opportunity: bool = True,
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
    summary = (f"Lead {lead_id} converted.\n  Account:     {account_id or 'existing'}\n"
               f"  Contact:     {contact_id or 'existing'}\n  Opportunity: {opp_id or 'not created'}")
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent={"type": "lead_convert", "leadId": lead_id, "accountId": account_id, "contactId": contact_id, "opportunityId": opp_id},
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
    stages = [{"stage": r.get("StageName") or "", "count": r.get("cnt") or 0, "amount": r.get("amount") or 0.0} for r in records]
    total_amount = sum(s["amount"] for s in stages)
    lines = [f"Pipeline dashboard — {len(stages)} stage(s), total ${total_amount:,.0f}:"]
    for s in stages:
        lines.append(f"  {s['stage']}: {s['count']} deal(s), ${s['amount']:,.0f}")
    summary = "\n".join(lines) if stages else "No open opportunities."
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent={"type": "pipeline_dashboard", "total_amount": total_amount, "stages": stages},
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
        {"id": r.get("Id"), "name": r.get("Name") or "", "status": r.get("Status") or "",
         "type": r.get("Type") or "", "start_date": r.get("StartDate") or "",
         "end_date": r.get("EndDate") or "", "num_leads": r.get("NumberOfLeads") or 0}
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


async def sf__get_pending_approvals() -> types.CallToolResult:
    log.info("sf__get_pending_approvals")
    try:
        sf = get_client()
        records = await sf.query(
            "SELECT Id, ProcessInstance.TargetObjectId, "
            "ProcessInstance.Status, ProcessInstance.TargetObject.Name, CreatedDate "
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
        {"id": r.get("Id"),
         "target_id": (r.get("ProcessInstance") or {}).get("TargetObjectId") or "",
         "target_name": ((r.get("ProcessInstance") or {}).get("TargetObject") or {}).get("Name") or "",
         "status": (r.get("ProcessInstance") or {}).get("Status") or "",
         "created_date": r.get("CreatedDate") or ""}
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


async def sf__get_entity_config(entity_type: str) -> types.CallToolResult:
    schema = _get_schema(entity_type)
    if not schema:
        return _error_result(f"No configuration found for entity type '{entity_type}'.")
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Configuration for {entity_type} retrieved.")],
        structuredContent={"type": "entity_config", "entity": entity_type, "config": schema},
    )


async def sf__update_entity_config(entity_type: str, patch: str) -> types.CallToolResult:
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


async def sf__reset_entity_config(entity_type: str) -> types.CallToolResult:
    global _config_store
    try:
        defaults = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return _error_result(f"Failed to read default config: {exc}")
    if entity_type == "all":
        _config_store = copy.deepcopy(defaults); msg = "All entity configurations reset to factory defaults."
    elif entity_type in defaults:
        _config_store[entity_type] = copy.deepcopy(defaults[entity_type]); msg = f"{entity_type} configuration reset to factory defaults."
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


async def sf__show_create_form(entity: str, fk_options: dict = None) -> types.CallToolResult:
    structured: dict = {"type": "form", "entity": entity}
    if fk_options:
        structured["fkSelections"] = fk_options
    label = entity.replace("_", " ").title()
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Opening {label} creation form. Fill in the details and click Submit.")],
        structuredContent=structured,
    )


# ── Prompt handlers ───────────────────────────────────────────────────────────

def show_leads_prompt() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text", text=(
        "Show me the latest 5 leads from Salesforce. Call get_leads and display the results in the widget."
    )))]


def show_opportunities_prompt() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text", text=(
        "Show me the latest 5 opportunities from Salesforce. Call get_opportunities and display the results in the widget."
    )))]


def manage_crm_prompt() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text", text=(
        "I want to manage my Salesforce CRM data. "
        "Start by showing me the latest 5 leads with get_leads. "
        "I may want to create new leads, edit existing ones, "
        "or switch to viewing opportunities, accounts, or contacts."
    )))]


# ── Registries ────────────────────────────────────────────────────────────────

_TOOL_SPECS_LIST = [
    {"name": "sf__get_leads",             "description": "Get the 5 most recent Leads from Salesforce. Pass campaign_id to get leads for a specific campaign. Returns lead name, company, email, phone, status, and lead source.", "handler": sf__get_leads},
    {"name": "sf__create_lead",           "description": "Create a new Lead in Salesforce. Requires last_name and company at minimum. Returns the updated list of latest 5 leads.", "handler": sf__create_lead},
    {"name": "sf__update_lead",           "description": "Update an existing Lead in Salesforce by its record Id. Only fields provided will be updated. Returns the updated list of latest 5 leads.", "handler": sf__update_lead},
    {"name": "sf__get_lead",              "description": "Get full details for a single Salesforce Lead by Id. Returns all fields including description, title, website, revenue, and created date.", "handler": sf__get_lead},
    {"name": "sf__get_opportunities",     "description": "Get the 5 most recent Opportunities from Salesforce. Returns opportunity name, account, stage, amount, close date, and probability.", "handler": sf__get_opportunities},
    {"name": "sf__create_opportunity",    "description": "Create a new Opportunity in Salesforce. Requires name, stage, and close_date at minimum. Returns the updated list of latest 5 opportunities.", "handler": sf__create_opportunity},
    {"name": "sf__update_opportunity",    "description": "Update an existing Opportunity in Salesforce by its record Id. Only fields provided will be updated. Returns the updated list of latest 5 opportunities.", "handler": sf__update_opportunity},
    {"name": "sf__get_accounts",          "description": "Get the latest 5 Accounts from Salesforce. Returns company name, industry, phone, website, and employee count.", "handler": sf__get_accounts},
    {"name": "sf__create_account",        "description": "Create a new Account in Salesforce. Requires name at minimum. Returns the updated list of latest 5 accounts.", "handler": sf__create_account},
    {"name": "sf__update_account",        "description": "Update an existing Account in Salesforce by its record Id. Only fields provided will be updated. Returns the updated list of latest 5 accounts.", "handler": sf__update_account},
    {"name": "sf__get_contacts",          "description": "Get the latest 5 Contacts from Salesforce. Returns first name, last name, email, phone, title, and associated account.", "handler": sf__get_contacts},
    {"name": "sf__create_contact",        "description": "Create a new Contact in Salesforce. Requires last_name at minimum. Returns the updated list of latest 5 contacts.", "handler": sf__create_contact},
    {"name": "sf__update_contact",        "description": "Update an existing Contact in Salesforce by its record Id. Only fields provided will be updated. Returns the updated list of latest 5 contacts.", "handler": sf__update_contact},
    {"name": "sf__get_cases",             "description": "Get the 5 most recent Cases from Salesforce. Returns case number, subject, status, priority, and account name.", "handler": sf__get_cases},
    {"name": "sf__create_case",           "description": "Create a new Salesforce Case. Required: subject. Optional: priority (High/Medium/Low), account_id, description.", "handler": sf__create_case},
    {"name": "sf__update_case",           "description": "Update a Salesforce Case. Required: case_id. Optional: status, resolution (Internal Comments).", "handler": sf__update_case},
    {"name": "sf__get_case",              "description": "Get full details for a single Salesforce Case by Id. Returns all fields including description, comments, origin, type, account, and dates.", "handler": sf__get_case},
    {"name": "sf__get_case_comments",     "description": "Get notes/comments for a Salesforce Case by case Id.", "handler": sf__get_case_comments},
    {"name": "sf__get_tasks",             "description": "Get the 5 most recent Tasks from Salesforce. Returns subject, status, priority, and due date.", "handler": sf__get_tasks},
    {"name": "sf__create_task",           "description": "Create a new Salesforce Task (activity). Required: subject. Optional: priority, due_date (YYYY-MM-DD), what_id (related record Id).", "handler": sf__create_task},
    {"name": "sf__update_task",           "description": "Update a Salesforce Task. Pass task_id plus any fields to change.", "handler": sf__update_task},
    {"name": "sf__get_task",              "description": "Get full details for a single Salesforce Task by Id. Returns subject, status, priority, due date, description, and related record.", "handler": sf__get_task},
    {"name": "sf__delete_lead",           "description": "Delete a Salesforce Lead by Id. Returns the refreshed lead list.", "handler": sf__delete_lead},
    {"name": "sf__convert_lead",          "description": "Convert a Salesforce Lead into an Account, Contact, and optionally an Opportunity. Required: lead_id. Optional: converted_status, create_opportunity.", "handler": sf__convert_lead},
    {"name": "sf__get_pipeline_dashboard","description": "Get the Salesforce opportunity pipeline grouped by stage. Returns deal count and total amount per stage.", "handler": sf__get_pipeline_dashboard},
    {"name": "sf__get_campaigns",         "description": "Get the 5 most recent Campaigns from Salesforce. Returns campaign name, status, type, start/end date, and lead count.", "handler": sf__get_campaigns},
    {"name": "sf__get_pending_approvals", "description": "Get pending Salesforce approval requests assigned to the current user. Returns pending ProcessInstance workitems requiring action.", "handler": sf__get_pending_approvals},
    {"name": "sf__get_entity_config",     "description": "Get the current display configuration for a Salesforce entity. entity_type: Lead, Opportunity, Account, Contact, Case, or Task.", "handler": sf__get_entity_config},
    {"name": "sf__update_entity_config",  "description": "Update the display configuration for a Salesforce entity. Pass entity_type and a JSON patch string. Changes take effect immediately and are saved to disk.", "handler": sf__update_entity_config},
    {"name": "sf__reset_entity_config",   "description": "Reset a Salesforce entity configuration to factory defaults. Pass entity_type='all' to reset every entity at once.", "handler": sf__reset_entity_config},
    {"name": "sf__show_create_form",      "description": "Opens a create form in the widget for the specified Salesforce entity. Supported entities: lead, account, contact, opportunity, case, task. FK pre-resolution required for contact, opportunity, case.", "handler": sf__show_create_form},
]

PROMPT_SPECS = [
    {"name": "show_leads",        "description": "Show the latest 5 leads from Salesforce.",                                              "handler": show_leads_prompt},
    {"name": "show_opportunities","description": "Show the latest 5 opportunities from Salesforce.",                                      "handler": show_opportunities_prompt},
    {"name": "manage_crm",        "description": "Help manage Salesforce CRM data — leads, opportunities, accounts, and contacts.",       "handler": manage_crm_prompt},
]


# ── Aliases for server.py imports ────────────────────────────────────────────
from mcp.types import PromptMessage as _PM, TextContent as _TC  # noqa: E402

TOOL_SPECS = _TOOL_SPECS_LIST

PROMPT_SPECS = [
    {
        "name": "my-leads",
        "description": "Show the latest leads in your Salesforce CRM.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me the latest leads from Salesforce. "
            "Call sf__get_leads and display the results in the widget."
        )))],
    },
    {
        "name": "my-cases",
        "description": "Show the latest open cases from Salesforce.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me the latest cases from Salesforce. "
            "Call sf__get_cases and display the results in the widget."
        )))],
    },
    {
        "name": "pipeline",
        "description": "See your opportunity pipeline broken down by stage.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me the opportunity pipeline. "
            "Call sf__get_pipeline_dashboard and sf__get_opportunities — these are independent. "
            "Once both return, show the stage breakdown and list deals at Proposal or Negotiation stage."
        )))],
    },
    {
        "name": "morning-briefing",
        "description": "Start your day with a summary of open cases, overdue tasks, and pending approvals.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Give me my daily CRM briefing. "
            "Call sf__get_cases, sf__get_tasks, and sf__get_pending_approvals — these are independent. "
            "Once all three return, summarise: open cases by priority, overdue tasks, and approval count."
        )))],
    },
    {
        "name": "convert-lead",
        "description": "Convert a lead into an account, contact, and opportunity.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to convert a lead. Call sf__get_leads to show me the latest leads. "
            "Ask me which lead to convert and whether to create an opportunity. "
            "Then call sf__convert_lead with that lead_id and create_opportunity choice."
        )))],
    },
    {
        "name": "account-view",
        "description": "See all cases, contacts, and open deals for a single account.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want a full view of an account. Call sf__get_accounts to show available accounts. "
            "Ask me which account to inspect. "
            "Then call sf__get_cases, sf__get_contacts, and sf__get_opportunities each with that "
            "account_id — these are independent. "
            "Once all three return, show cases, contacts, and open deals for that account."
        )))],
    },
]