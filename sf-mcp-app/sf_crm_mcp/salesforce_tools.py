"""Salesforce CRM tool handlers, _TOOL_SPECS_LIST, PROMPT_SPECS. No MCP bootstrap here."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog
from cachetools import TTLCache
from mcp import types
from mcp.types import PromptMessage, TextContent

from .salesforce_client import SalesforceAPIError, SalesforceAuthError, get_client

log = structlog.get_logger("sf")


def _sq(value: str) -> str:
    """Escape a string literal for SOQL — single quotes and backslashes only."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


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


# ── TTL cache (90 s, invalidated on write) ────────────────────────────────────

_ENTITY_CACHE: dict[str, TTLCache] = {
    "leads":         TTLCache(maxsize=2, ttl=90),
    "opportunities": TTLCache(maxsize=2, ttl=90),
    "accounts":      TTLCache(maxsize=2, ttl=90),
    "contacts":      TTLCache(maxsize=2, ttl=90),
    "cases":         TTLCache(maxsize=2, ttl=90),
    "tasks":         TTLCache(maxsize=2, ttl=90),
    "campaigns":     TTLCache(maxsize=2, ttl=90),
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _time_ago(iso: str) -> str:
    try:
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        secs = int((datetime.now(timezone.utc) - dt).total_seconds())
        if secs < 5:    return "just now"
        if secs < 60:   return f"{secs}s ago"
        if secs < 3600: return f"{secs // 60}m ago"
        return f"{secs // 3600}h ago"
    except Exception:
        return iso


def _cache_get(entity: str) -> tuple[list | None, str | None]:
    entry = _ENTITY_CACHE[entity].get("v")
    if entry:
        return entry["items"], entry["at"]
    return None, None


def _cache_set(entity: str, items: list) -> str:
    at = _now_iso()
    _ENTITY_CACHE[entity]["v"] = {"items": items, "at": at}
    return at


def _cache_invalidate(entity: str) -> None:
    _ENTITY_CACHE[entity].pop("v", None)


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


def _list_summary(entity_label: str, items: list[dict], entity_type: str,
                  cache_hit: bool = False, cached_at: str = "") -> str:
    if not items:
        return f"No {entity_label} found."
    cols = _get_schema(entity_type).get("columns", [])
    names = []
    for item in items[:3]:
        parts = [str(item.get(c.get("key", c["apiName"]), "")) for c in cols[:2] if c["apiName"] != "Id"]
        names.append(" / ".join(p for p in parts if p))
    more = f" (+{len(items) - 3} more)" if len(items) > 3 else ""
    source = f"from cache ({_time_ago(cached_at)}) — use ↻ in widget to refresh" if cache_hit else "retrieved"
    return f"{len(items)} {entity_label} {source} — {', '.join(names)}{more}. Widget below ↓"


async def _fetch_leads()         -> list[dict]: return await _fetch_entity("Lead")
async def _fetch_opportunities() -> list[dict]: return await _fetch_entity("Opportunity")
async def _fetch_accounts()      -> list[dict]: return await _fetch_entity("Account")
async def _fetch_contacts()      -> list[dict]: return await _fetch_entity("Contact")
async def _fetch_cases()         -> list[dict]: return await _fetch_entity("Case")
async def _fetch_tasks()         -> list[dict]: return await _fetch_entity("Task")

async def _fetch_campaigns() -> list[dict]:
    sf = get_client()
    records = await sf.query(
        "SELECT Id, Name, Status, Type, StartDate, EndDate, NumberOfLeads "
        "FROM Campaign ORDER BY CreatedDate DESC LIMIT 5"
    )
    return [
        {"id": r.get("Id"), "name": r.get("Name") or "", "status": r.get("Status") or "",
         "type": r.get("Type") or "", "start_date": r.get("StartDate") or "",
         "end_date": r.get("EndDate") or "", "num_leads": r.get("NumberOfLeads") or 0}
        for r in records
    ]


# ── Tool handlers ─────────────────────────────────────────────────────────────

async def sf__get_leads(campaign_id: str = "", name: str = "", lead_id: str = "", refresh: bool = False) -> types.CallToolResult:
    log.info("sf__get_leads", campaign_id=campaign_id, name=name, lead_id=lead_id, refresh=refresh)
    if lead_id:
        try:
            sf = get_client()
            soql = (f"SELECT Id, FirstName, LastName, Company, Email, Phone, Status, LeadSource, "
                    f"Title, Website, Description, AnnualRevenue, NumberOfEmployees, CreatedDate "
                    f"FROM Lead WHERE Id = '{_sq(lead_id)}' LIMIT 1")
            records = await sf.query(soql)
        except Exception as exc:
            return _error_result(f"Error looking up lead: {exc}")
        if not records:
            return _error_result(f"Lead {lead_id} not found.")
        r = records[0]
        name_str = f"{r.get('FirstName') or ''} {r.get('LastName') or ''}".strip()
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Opening edit form for lead: {name_str}.")],
            structuredContent={"type": "form", "entity": "lead", "mode": "edit", "recordId": r.get("Id", ""),
                               "prefill": {"first_name": r.get("FirstName") or "", "last_name": r.get("LastName") or "",
                                           "company": r.get("Company") or "", "email": r.get("Email") or "",
                                           "phone": r.get("Phone") or "", "status": r.get("Status") or "",
                                           "lead_source": r.get("LeadSource") or ""}},
        )
    use_cache = not campaign_id and not name and not refresh
    cache_hit, cached_at = False, _now_iso()
    if use_cache:
        cached_items, stored_at = _cache_get("leads")
        if cached_items is not None:
            log.info("sf__get_leads_cache_hit")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=_list_summary("lead(s)", cached_items, "Lead", cache_hit=True, cached_at=stored_at))],
                structuredContent={"type": "leads", "total": len(cached_items), "items": cached_items,
                                   "_schema": _get_schema("Lead"), "_cache": {"hit": True, "cached_at": stored_at}},
            )
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
                    f"WHERE FirstName LIKE '%{_sq(name)}%' OR LastName LIKE '%{_sq(name)}%' OR Company LIKE '%{_sq(name)}%' "
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
    if use_cache:
        cached_at = _cache_set("leads", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("lead(s)", items, "Lead"))],
        structuredContent={"type": "leads", "total": len(items), "items": items,
                           "_schema": _get_schema("Lead"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("leads")
    try: items = await _fetch_leads()
    except Exception: items = []
    cached_at = _cache_set("leads", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "leads", "total": len(items), "items": items, "_createdId": new_id,
                           "_schema": _get_schema("Lead"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("leads")
    try: items = await _fetch_leads()
    except Exception: items = []
    cached_at = _cache_set("leads", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Lead {lead_id} updated. Refreshed list returned.")],
        structuredContent={"type": "leads", "total": len(items), "items": items,
                           "_schema": _get_schema("Lead"), "_cache": {"hit": False, "cached_at": cached_at}},
    )


async def sf__get_opportunities(account_id: str = "", name: str = "", stage: str = "", refresh: bool = False) -> types.CallToolResult:
    log.info("sf__get_opportunities", account_id=account_id, name=name, stage=stage, refresh=refresh)
    use_cache = not account_id and not name and not stage and not refresh
    if use_cache:
        cached_items, stored_at = _cache_get("opportunities")
        if cached_items is not None:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=_list_summary("opportunity(ies)", cached_items, "Opportunity", cache_hit=True, cached_at=stored_at))],
                structuredContent={"type": "opportunities", "total": len(cached_items), "items": cached_items,
                                   "_schema": _get_schema("Opportunity"), "_cache": {"hit": True, "cached_at": stored_at}},
            )
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
            if name:  clauses.append(f"Name LIKE '%{_sq(name)}%'")
            if stage: clauses.append(f"StageName = '{_sq(stage)}'")
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
    cached_at = _cache_set("opportunities", items) if use_cache else _now_iso()
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("opportunity(ies)", items, "Opportunity"))],
        structuredContent={"type": "opportunities", "total": len(items), "items": items,
                           "_schema": _get_schema("Opportunity"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("opportunities")
    try: items = await _fetch_opportunities()
    except Exception: items = []
    cached_at = _cache_set("opportunities", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Opportunity created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "opportunities", "total": len(items), "items": items, "_createdId": new_id,
                           "_schema": _get_schema("Opportunity"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("opportunities")
    try: items = await _fetch_opportunities()
    except Exception: items = []
    cached_at = _cache_set("opportunities", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Opportunity {opportunity_id} updated. Refreshed list returned.")],
        structuredContent={"type": "opportunities", "total": len(items), "items": items,
                           "_schema": _get_schema("Opportunity"), "_cache": {"hit": False, "cached_at": cached_at}},
    )


async def sf__get_accounts(name: str = "", industry: str = "", refresh: bool = False) -> types.CallToolResult:
    log.info("sf__get_accounts", name=name, industry=industry, refresh=refresh)
    use_cache = not name and not industry and not refresh
    if use_cache:
        cached_items, stored_at = _cache_get("accounts")
        if cached_items is not None:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=_list_summary("account(s)", cached_items, "Account", cache_hit=True, cached_at=stored_at))],
                structuredContent={"type": "accounts", "total": len(cached_items), "items": cached_items,
                                   "_schema": _get_schema("Account"), "_cache": {"hit": True, "cached_at": stored_at}},
            )
    try:
        if name or industry:
            cfg = _get_schema("Account")
            columns = cfg.get("columns", []) + cfg.get("hiddenColumns", [])
            api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
            clauses = []
            if name:     clauses.append(f"Name LIKE '%{_sq(name)}%'")
            if industry: clauses.append(f"Industry = '{_sq(industry)}'")
            soql = f"SELECT {', '.join(api_names)} FROM Account WHERE {' AND '.join(clauses)} ORDER BY CreatedDate DESC LIMIT 20"
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        else:
            items = await _fetch_accounts()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch accounts: {exc}")
    cached_at = _cache_set("accounts", items) if use_cache else _now_iso()
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("account(s)", items, "Account"))],
        structuredContent={"type": "accounts", "total": len(items), "items": items,
                           "_schema": _get_schema("Account"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("accounts")
    try: items = await _fetch_accounts()
    except Exception: items = []
    cached_at = _cache_set("accounts", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Account '{name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "accounts", "total": len(items), "items": items, "_createdId": new_id,
                           "_schema": _get_schema("Account"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("accounts")
    try: items = await _fetch_accounts()
    except Exception: items = []
    cached_at = _cache_set("accounts", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Account {account_id} updated. Refreshed list returned.")],
        structuredContent={"type": "accounts", "total": len(items), "items": items,
                           "_schema": _get_schema("Account"), "_cache": {"hit": False, "cached_at": cached_at}},
    )


async def sf__get_contacts(account_id: str = "", name: str = "", refresh: bool = False) -> types.CallToolResult:
    log.info("sf__get_contacts", account_id=account_id, name=name, refresh=refresh)
    use_cache = not account_id and not name and not refresh
    if use_cache:
        cached_items, stored_at = _cache_get("contacts")
        if cached_items is not None:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=_list_summary("contact(s)", cached_items, "Contact", cache_hit=True, cached_at=stored_at))],
                structuredContent={"type": "contacts", "total": len(cached_items), "items": cached_items,
                                   "_schema": _get_schema("Contact"), "_cache": {"hit": True, "cached_at": stored_at}},
            )
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
                    f"WHERE FirstName LIKE '%{_sq(name)}%' OR LastName LIKE '%{_sq(name)}%' "
                    f"ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        else:
            items = await _fetch_contacts()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch contacts: {exc}")
    cached_at = _cache_set("contacts", items) if use_cache else _now_iso()
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("contact(s)", items, "Contact"))],
        structuredContent={"type": "contacts", "total": len(items), "items": items,
                           "_schema": _get_schema("Contact"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("contacts")
    try: items = await _fetch_contacts()
    except Exception: items = []
    cached_at = _cache_set("contacts", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact '{first_name} {last_name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "contacts", "total": len(items), "items": items, "_createdId": new_id,
                           "_schema": _get_schema("Contact"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("contacts")
    try: items = await _fetch_contacts()
    except Exception: items = []
    cached_at = _cache_set("contacts", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Contact {contact_id} updated. Refreshed list returned.")],
        structuredContent={"type": "contacts", "total": len(items), "items": items,
                           "_schema": _get_schema("Contact"), "_cache": {"hit": False, "cached_at": cached_at}},
    )


async def sf__get_cases(account_id: str = "", subject: str = "", case_id: str = "", refresh: bool = False) -> types.CallToolResult:
    log.info("sf__get_cases", account_id=account_id, subject=subject, case_id=case_id, refresh=refresh)
    if case_id:
        try:
            sf = get_client()
            soql = (f"SELECT Id, CaseNumber, Subject, Status, Priority, Origin, Type, "
                    f"Account.Name, Description, CreatedDate "
                    f"FROM Case WHERE Id = '{_sq(case_id)}' LIMIT 1")
            records = await sf.query(soql)
        except Exception as exc:
            return _error_result(f"Error looking up case: {exc}")
        if not records:
            return _error_result(f"Case {case_id} not found.")
        r = records[0]
        account = r.get("Account") or {}
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Opening edit form for case: {r.get('CaseNumber', '')}.")],
            structuredContent={"type": "form", "entity": "case", "mode": "edit", "recordId": r.get("Id", ""),
                               "prefill": {"subject": r.get("Subject") or "", "status": r.get("Status") or "",
                                           "priority": r.get("Priority") or "", "account_name": account.get("Name") or "",
                                           "description": r.get("Description") or ""}},
        )
    use_cache = not account_id and not subject and not refresh
    if use_cache:
        cached_items, stored_at = _cache_get("cases")
        if cached_items is not None:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=_list_summary("case(s)", cached_items, "Case", cache_hit=True, cached_at=stored_at))],
                structuredContent={"type": "cases", "total": len(cached_items), "items": cached_items,
                                   "_schema": _get_schema("Case"), "_cache": {"hit": True, "cached_at": stored_at}},
            )
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
                    f"WHERE Subject LIKE '%{_sq(subject)}%' ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        else:
            items = await _fetch_cases()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching cases: {exc}")
    cached_at = _cache_set("cases", items) if use_cache else _now_iso()
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("case(s)", items, "Case"))],
        structuredContent={"type": "cases", "total": len(items), "items": items,
                           "_schema": _get_schema("Case"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("cases")
    try: items = await _fetch_cases()
    except Exception: items = []
    cached_at = _cache_set("cases", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Case created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "cases", "total": len(items), "items": items, "_createdId": new_id,
                           "_schema": _get_schema("Case"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("cases")
    try: items = await _fetch_cases()
    except Exception: items = []
    cached_at = _cache_set("cases", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Case {case_id} updated. Refreshed list returned.")],
        structuredContent={"type": "cases", "total": len(items), "items": items,
                           "_schema": _get_schema("Case"), "_cache": {"hit": False, "cached_at": cached_at}},
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


async def sf__get_tasks(subject: str = "", task_id: str = "", refresh: bool = False) -> types.CallToolResult:
    log.info("sf__get_tasks", subject=subject, task_id=task_id, refresh=refresh)
    if task_id:
        try:
            sf = get_client()
            soql = (f"SELECT Id, Subject, Status, Priority, ActivityDate, Description, CreatedDate "
                    f"FROM Task WHERE Id = '{_sq(task_id)}' LIMIT 1")
            records = await sf.query(soql)
        except Exception as exc:
            return _error_result(f"Error looking up task: {exc}")
        if not records:
            return _error_result(f"Task {task_id} not found.")
        r = records[0]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Opening edit form for task: {r.get('Subject', '')}.")],
            structuredContent={"type": "form", "entity": "task", "mode": "edit", "recordId": r.get("Id", ""),
                               "prefill": {"subject": r.get("Subject") or "", "status": r.get("Status") or "",
                                           "priority": r.get("Priority") or "",
                                           "activity_date": (r.get("ActivityDate") or "")[:10],
                                           "description": r.get("Description") or ""}},
        )
    use_cache = not subject and not refresh
    if use_cache:
        cached_items, stored_at = _cache_get("tasks")
        if cached_items is not None:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=_list_summary("task(s)", cached_items, "Task", cache_hit=True, cached_at=stored_at))],
                structuredContent={"type": "tasks", "total": len(cached_items), "items": cached_items,
                                   "_schema": _get_schema("Task"), "_cache": {"hit": True, "cached_at": stored_at}},
            )
    try:
        if subject:
            cfg = _get_schema("Task")
            columns = cfg.get("columns", []) + cfg.get("hiddenColumns", [])
            api_names = ["Id"] + [c["apiName"] for c in columns if c["apiName"] != "Id"]
            soql = (f"SELECT {', '.join(api_names)} FROM Task "
                    f"WHERE Subject LIKE '%{_sq(subject)}%' ORDER BY CreatedDate DESC LIMIT 20")
            sf = get_client(); records = await sf.query(soql); items = [_flatten_record(r, columns) for r in records]
        else:
            items = await _fetch_tasks()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching tasks: {exc}")
    cached_at = _cache_set("tasks", items) if use_cache else _now_iso()
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=_list_summary("task(s)", items, "Task"))],
        structuredContent={"type": "tasks", "total": len(items), "items": items,
                           "_schema": _get_schema("Task"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("tasks")
    try: items = await _fetch_tasks()
    except Exception: items = []
    cached_at = _cache_set("tasks", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Task created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "tasks", "total": len(items), "items": items, "_createdId": new_id,
                           "_schema": _get_schema("Task"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("tasks")
    try: items = await _fetch_tasks()
    except Exception: items = []
    cached_at = _cache_set("tasks", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Task {task_id} updated. Refreshed list returned.")],
        structuredContent={"type": "tasks", "total": len(items), "items": items,
                           "_schema": _get_schema("Task"), "_cache": {"hit": False, "cached_at": cached_at}},
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
    _cache_invalidate("leads")
    try: items = await _fetch_leads()
    except Exception: items = []
    cached_at = _cache_set("leads", items)
    summary = f"Lead converted. Account: {account_id or 'existing'}, Contact: {contact_id or 'existing'}, Opportunity: {opp_id or 'not created'}. Widget below ↓"
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent={"type": "leads", "total": len(items), "items": items,
                           "_schema": _get_schema("Lead"), "_cache": {"hit": False, "cached_at": cached_at},
                           "_convertedId": lead_id, "_convert": {"accountId": account_id, "contactId": contact_id, "opportunityId": opp_id}},
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
        structuredContent={"type": "sales_dashboard", "total_amount": total_amount, "stages": stages},
    )


async def sf__get_campaigns(campaign_id: str = "", refresh: bool = False) -> types.CallToolResult:
    log.info("sf__get_campaigns", campaign_id=campaign_id, refresh=refresh)
    if campaign_id:
        try:
            sf = get_client()
            records = await sf.query(
                f"SELECT Id, Name, Status, Type, StartDate, EndDate "
                f"FROM Campaign WHERE Id = '{_sq(campaign_id)}' LIMIT 1"
            )
        except SalesforceAuthError as exc:
            return _error_result(f"Salesforce authentication failed: {exc}")
        except Exception as exc:
            return _error_result(f"Error fetching campaign: {exc}")
        if not records:
            return _error_result(f"Campaign {campaign_id} not found.")
        r = records[0]
        prefill = {"name": r.get("Name") or "", "status": r.get("Status") or "",
                   "type": r.get("Type") or "", "start_date": r.get("StartDate") or "",
                   "end_date": r.get("EndDate") or ""}
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Campaign {campaign_id} ready to edit.")],
            structuredContent={"type": "form", "entity": "campaign", "mode": "edit",
                               "recordId": campaign_id, "prefill": prefill},
        )
    if not refresh:
        cached_items, stored_at = _cache_get("campaigns")
        if cached_items is not None:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=_list_summary("campaign(s)", cached_items, "Campaign", cache_hit=True, cached_at=stored_at))],
                structuredContent={"type": "campaigns", "total": len(cached_items), "items": cached_items,
                                   "_cache": {"hit": True, "cached_at": stored_at}},
            )
    try:
        items = await _fetch_campaigns()
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Salesforce API error: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error fetching campaigns: {exc}")
    cached_at = _cache_set("campaigns", items)
    if not items:
        summary = "No campaigns found."
    else:
        lines = [f"Retrieved {len(items)} campaign(s):"]
        for c in items:
            lines.append(f"- {c['name']} | {c['status']} | {c['type']} | leads: {c['num_leads']}")
        summary = "\n".join(lines)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent={"type": "campaigns", "total": len(items), "items": items,
                           "_cache": {"hit": False, "cached_at": cached_at}},
    )


async def sf__create_campaign(
    name: str, status: str = "Planned", type: str = "",
    start_date: str = "", end_date: str = "",
) -> types.CallToolResult:
    try:
        sf = get_client()
        data: dict = {"Name": name}
        if status:     data["Status"] = status
        if type:       data["Type"] = type
        if start_date: data["StartDate"] = start_date
        if end_date:   data["EndDate"] = end_date
        new_id = await sf.create("Campaign", data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to create campaign: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error creating campaign: {exc}")
    _cache_invalidate("campaigns")
    try: items = await _fetch_campaigns()
    except Exception: items = []
    cached_at = _cache_set("campaigns", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Campaign created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "campaigns", "total": len(items), "items": items, "_createdId": new_id,
                           "_cache": {"hit": False, "cached_at": cached_at}},
    )


async def sf__update_campaign(
    campaign_id: str, name: str = "", status: str = "", type: str = "",
    start_date: str = "", end_date: str = "",
) -> types.CallToolResult:
    try:
        sf = get_client()
        data: dict = {}
        if name:       data["Name"] = name
        if status:     data["Status"] = status
        if type:       data["Type"] = type
        if start_date: data["StartDate"] = start_date
        if end_date:   data["EndDate"] = end_date
        if not data: return _error_result("No fields provided to update.")
        await sf.update("Campaign", campaign_id, data)
    except SalesforceAuthError as exc:
        return _error_result(f"Salesforce authentication failed: {exc}")
    except SalesforceAPIError as exc:
        return _error_result(f"Failed to update campaign: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error updating campaign: {exc}")
    _cache_invalidate("campaigns")
    try: items = await _fetch_campaigns()
    except Exception: items = []
    cached_at = _cache_set("campaigns", items)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Campaign {campaign_id} updated. Refreshed list returned.")],
        structuredContent={"type": "campaigns", "total": len(items), "items": items,
                           "_cache": {"hit": False, "cached_at": cached_at}},
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
    {"name": "sf__get_leads",             "description": "Get Leads from Salesforce. Pass lead_id for exact record lookup → opens edit form. Pass name to search by name/company. No params returns the 5 most recent leads.", "handler": sf__get_leads},
    {"name": "sf__create_lead",           "description": "Create a new Lead in Salesforce. Requires last_name and company at minimum. Returns the updated list of latest 5 leads.", "handler": sf__create_lead},
    {"name": "sf__update_lead",           "description": "Update an existing Lead in Salesforce by its record Id. Only fields provided will be updated. Returns the updated list of latest 5 leads.", "handler": sf__update_lead},
    {"name": "sf__get_opportunities",     "description": "Get the 5 most recent Opportunities from Salesforce. Returns opportunity name, account, stage, amount, close date, and probability.", "handler": sf__get_opportunities},
    {"name": "sf__create_opportunity",    "description": "Create a new Opportunity in Salesforce. Requires name, stage, and close_date at minimum. Returns the updated list of latest 5 opportunities.", "handler": sf__create_opportunity},
    {"name": "sf__update_opportunity",    "description": "Update an existing Opportunity in Salesforce by its record Id. Only fields provided will be updated. Returns the updated list of latest 5 opportunities.", "handler": sf__update_opportunity},
    {"name": "sf__get_accounts",          "description": "Get the latest 5 Accounts from Salesforce. Returns company name, industry, phone, website, and employee count.", "handler": sf__get_accounts},
    {"name": "sf__create_account",        "description": "Create a new Account in Salesforce. Requires name at minimum. Returns the updated list of latest 5 accounts.", "handler": sf__create_account},
    {"name": "sf__update_account",        "description": "Update an existing Account in Salesforce by its record Id. Only fields provided will be updated. Returns the updated list of latest 5 accounts.", "handler": sf__update_account},
    {"name": "sf__get_contacts",          "description": "Get the latest 5 Contacts from Salesforce. Returns first name, last name, email, phone, title, and associated account.", "handler": sf__get_contacts},
    {"name": "sf__create_contact",        "description": "Create a new Contact in Salesforce. Requires last_name at minimum. Returns the updated list of latest 5 contacts.", "handler": sf__create_contact},
    {"name": "sf__update_contact",        "description": "Update an existing Contact in Salesforce by its record Id. Only fields provided will be updated. Returns the updated list of latest 5 contacts.", "handler": sf__update_contact},
    {"name": "sf__get_cases",             "description": "Get Cases from Salesforce. Pass case_id for exact record lookup → opens edit form. Pass subject to search by subject. No params returns the 5 most recent cases.", "handler": sf__get_cases},
    {"name": "sf__create_case",           "description": "Create a new Salesforce Case. Required: subject. Optional: priority (High/Medium/Low), account_id, description.", "handler": sf__create_case},
    {"name": "sf__update_case",           "description": "Update a Salesforce Case. Required: case_id. Optional: status, resolution (Internal Comments).", "handler": sf__update_case},
    {"name": "sf__get_case_comments",     "description": "Get notes/comments for a Salesforce Case by case Id.", "handler": sf__get_case_comments},
    {"name": "sf__get_tasks",             "description": "Get Tasks from Salesforce. Pass task_id for exact record lookup → opens edit form. Pass subject to search by subject. No params returns the 5 most recent tasks.", "handler": sf__get_tasks},
    {"name": "sf__create_task",           "description": "Create a new Salesforce Task (activity). Required: subject. Optional: priority, due_date (YYYY-MM-DD), what_id (related record Id).", "handler": sf__create_task},
    {"name": "sf__update_task",           "description": "Update a Salesforce Task. Pass task_id plus any fields to change.", "handler": sf__update_task},
    {"name": "sf__convert_lead",          "description": "Convert a Salesforce Lead into an Account, Contact, and optionally an Opportunity. Required: lead_id. Optional: converted_status, create_opportunity.", "handler": sf__convert_lead},
    {"name": "sf__get_pipeline_dashboard","description": "Get the Salesforce opportunity pipeline grouped by stage. Returns deal count and total amount per stage.", "handler": sf__get_pipeline_dashboard},
    {"name": "sf__get_campaigns",         "description": "Get Salesforce Campaigns. Pass campaign_id for exact record lookup → opens edit form. No params returns the 5 most recent campaigns.", "handler": sf__get_campaigns},
    {"name": "sf__create_campaign",       "description": "Create a new Salesforce Campaign. Required: name. Optional: status (Planned/Active/Completed/Aborted), type, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD).", "handler": sf__create_campaign},
    {"name": "sf__update_campaign",       "description": "Update a Salesforce Campaign. Required: campaign_id. Optional: name, status, type, start_date, end_date.", "handler": sf__update_campaign},
    {"name": "sf__get_pending_approvals", "description": "Get pending Salesforce approval requests assigned to the current user. Returns pending ProcessInstance workitems requiring action.", "handler": sf__get_pending_approvals},
    {"name": "sf__get_entity_config",     "description": "Get the current display configuration for a Salesforce entity. entity_type: Lead, Opportunity, Account, Contact, Case, or Task.", "handler": sf__get_entity_config},
    {"name": "sf__update_entity_config",  "description": "Update the display configuration for a Salesforce entity. Pass entity_type and a JSON patch string. Changes take effect immediately and are saved to disk.", "handler": sf__update_entity_config},
    {"name": "sf__reset_entity_config",   "description": "Reset a Salesforce entity configuration to factory defaults. Pass entity_type='all' to reset every entity at once.", "handler": sf__reset_entity_config},
    {"name": "sf__show_create_form",      "description": "Use this when the user asks to create a new Salesforce lead, account, contact, opportunity, case, task, or campaign. Opens the interactive creation form — do NOT call sf__create_lead or other direct create tools. Pass the entity name (lead/account/contact/opportunity/case/task/campaign).", "handler": sf__show_create_form},
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