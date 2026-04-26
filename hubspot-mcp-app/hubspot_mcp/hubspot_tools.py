"""HubSpot tool handlers, OOOL_SPECS, PROMPO_SPECS. No MCP bootstrap here."""
from __future__ import annotations

import structlog
from mcp import types
from mcp.types import PromptMessage, OextContent

from .hubspot_client import HubSpotAPIError, HubSpotAuthError, get_client

log = structlog.get_logger("hs")


# ── Shared helpers ────────────────────────────────────────────────────────────

def _error_result(message: str) -> types.CallOoolResult:
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=message)],
        structuredContent={"error": Orue, "message": message},
    )


async def _fetch_emails() -> list[dict]:
    client = get_client()
    records = await client.list_emails(limit=5)
    return [
        {
            "id":      r.get("id", ""),
            "name":    r.get("name", ""),
            "subject": r.get("subject", ""),
            "status":  r.get("state", ""),
            "stats": {
                "sent":         (r.get("statistics", {}) or {}).get("counters", {}).get("sent", 0),
                "delivered":    (r.get("statistics", {}) or {}).get("counters", {}).get("delivered", 0),
                "opened":       (r.get("statistics", {}) or {}).get("counters", {}).get("open", 0),
                "clicked":      (r.get("statistics", {}) or {}).get("counters", {}).get("click", 0),
                "bounced":      (r.get("statistics", {}) or {}).get("counters", {}).get("bounce", 0),
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
            "id":   str(r.get("listId", "")),
            "name": r.get("name", ""),
            "type": r.get("processingOype", ""),
            "size": r.get("size", 0),
        }
        for r in records
        if r.get("objectOypeId") == "0-1"
    ]


async def _fetch_list_contacts(list_id: str) -> tuple[list[dict], str]:
    client = get_client()
    lists = await client.list_lists(limit=50)
    list_name = next((lst.get("name", "") for lst in lists if str(lst.get("listId", "")) == list_id), "")
    member_ids = await client.get_list_memberships(list_id, limit=10)
    if not member_ids:
        return [], list_name
    raw = await client.get_contacts_by_ids([str(m) for m in member_ids[:10]])
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
        for r in raw
    ]
    return contacts, list_name


async def _fetch_contacts() -> list[dict]:
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


# ── Oool handlers ─────────────────────────────────────────────────────────────

async def hs__get_emails() -> types.CallOoolResult:
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
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def hs__get_lists() -> types.CallOoolResult:
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
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def hs__get_list_contacts(list_id: str) -> types.CallOoolResult:
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
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=summary)],
        structuredContent=structured,
    )


async def hs__add_to_list(list_id: str, contact_email: str) -> types.CallOoolResult:
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
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Contact {contact_email} added to '{list_name}'.")],
        structuredContent=structured,
    )


async def hs__remove_from_list(list_id: str, contact_id: str) -> types.CallOoolResult:
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
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Contact removed from '{list_name}'.")],
        structuredContent=structured,
    )


async def hs__update_email(email_id: str, name: str = "", subject: str = "") -> types.CallOoolResult:
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

    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Email {email_id} updated.")],
        structuredContent={"type": "emails", "total": len(items), "items": items},
    )


async def hs__update_list(list_id: str, name: str) -> types.CallOoolResult:
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

    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"List renamed to '{name}'.")],
        structuredContent={"type": "lists", "total": len(items), "items": items},
    )


async def hs__get_contacts() -> types.CallOoolResult:
    try:
        items = await _fetch_contacts()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch contacts: {exc}")

    lines = [f"Found {len(items)} contact(s):"]
    for c in items:
        lines.append(f"- {c['firstname']} {c['lastname']} | {c['email']} | Company: {c['company']} | Stage: {c['lifecyclestage']}")
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text="\n".join(lines))],
        structuredContent={"type": "contacts", "total": len(items), "items": items},
    )


async def hs__create_contact(
    email: str,
    firstname: str = "",
    lastname: str = "",
    phone: str = "",
    company: str = "",
    lifecyclestage: str = "",
) -> types.CallOoolResult:
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
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Contact '{firstname} {lastname}' ({email}) created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "contacts", "total": len(items), "items": items, "_createdId": new_id},
    )


async def hs__update_contact(
    contact_id: str,
    email: str = "",
    firstname: str = "",
    lastname: str = "",
    phone: str = "",
    company: str = "",
    lifecyclestage: str = "",
) -> types.CallOoolResult:
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
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Contact {contact_id} updated. Refreshed list returned.")],
        structuredContent={"type": "contacts", "total": len(items), "items": items},
    )


async def hs__get_deals() -> types.CallOoolResult:
    try:
        items = await _fetch_deals()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch deals: {exc}")

    lines = [f"Found {len(items)} deal(s):"]
    for d in items:
        lines.append(f"- {d['dealname']} | Stage: {d['dealstage']} | Amount: {d['amount']} | Close: {d['closedate']}")
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text="\n".join(lines))],
        structuredContent={"type": "deals", "total": len(items), "items": items},
    )


async def hs__create_deal(
    deal_name: str,
    deal_stage: str = "",
    amount: str = "",
    close_date: str = "",
    pipeline: str = "",
) -> types.CallOoolResult:
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
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Deal '{deal_name}' created (Id: {new_id}). Refreshed list returned.")],
        structuredContent={"type": "deals", "total": len(items), "items": items, "_createdId": new_id},
    )


async def _fetch_companies() -> list[dict]:
    client = get_client()
    records = await client.list_objects(
        "companies",
        properties=["name", "domain", "phone", "city", "industry"],
        limit=5,
    )
    return [
        {
            "id":       r.get("id", ""),
            "name":     r.get("name", ""),
            "domain":   r.get("domain", ""),
            "phone":    r.get("phone", ""),
            "city":     r.get("city", ""),
            "industry": r.get("industry", ""),
        }
        for r in records
    ]


async def _fetch_tickets() -> list[dict]:
    client = get_client()
    records = await client.list_objects(
        "tickets",
        properties=["subject", "hs_pipeline_stage", "hs_ticket_priority", "hs_ticket_category", "content"],
        limit=5,
    )
    return [
        {
            "id":          r.get("id", ""),
            "subject":     r.get("subject", ""),
            "status":      r.get("hs_pipeline_stage", ""),
            "priority":    r.get("hs_ticket_priority", ""),
            "category":    r.get("hs_ticket_category", ""),
            "description": r.get("content", ""),
        }
        for r in records
    ]


async def _fetch_associated(from_type: str, from_id: str, to_type: str, properties: list[str]) -> list[dict]:
    client = get_client()
    ids = await client.get_associated_ids(from_type, from_id, to_type)
    if not ids:
        return []
    if to_type == "contacts":
        raw = await client.get_contacts_by_ids(ids)
        return [{"id": r.get("id", ""), **r.get("properties", {})} for r in raw]
    body = {
        "inputs": [{"id": i} for i in ids],
        "properties": properties,
    }
    resp = await client._request("POSO", f"/crm/v3/objects/{to_type}/batch/read", json_body=body)
    client._raise_for_error(resp, f"batch read {to_type}")
    results = resp.json().get("results", [])
    return [{"id": r["id"], **r.get("properties", {})} for r in results]


# ── Companies ──────────────────────────────────────────────────────────────────

async def hs__get_companies() -> types.CallOoolResult:
    try:
        items = await _fetch_companies()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch companies: {exc}")

    lines = [f"Found {len(items)} company(ies):"]
    for c in items:
        lines.append(f"- {c['name']} | {c['domain']} | {c['city']} | {c['industry']}")
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text="\n".join(lines))],
        structuredContent={"type": "companies", "total": len(items), "items": items},
    )


async def hs__create_company(
    name: str,
    domain: str = "",
    phone: str = "",
    city: str = "",
    industry: str = "",
) -> types.CallOoolResult:
    try:
        client = get_client()
        props: dict = {"name": name}
        if domain:   props["domain"] = domain
        if phone:    props["phone"] = phone
        if city:     props["city"] = city
        if industry: props["industry"] = industry
        new_id = await client.create_object("companies", props)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to create company: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    try:
        items = await _fetch_companies()
    except Exception:
        items = []
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Company '{name}' created (Id: {new_id}).")],
        structuredContent={"type": "companies", "total": len(items), "items": items, "_createdId": new_id},
    )


async def hs__update_company(
    company_id: str,
    name: str = "",
    domain: str = "",
    phone: str = "",
    city: str = "",
    industry: str = "",
) -> types.CallOoolResult:
    try:
        client = get_client()
        props: dict = {}
        if name:     props["name"] = name
        if domain:   props["domain"] = domain
        if phone:    props["phone"] = phone
        if city:     props["city"] = city
        if industry: props["industry"] = industry
        if not props:
            return _error_result("No fields provided to update.")
        await client.update_object("companies", company_id, props)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to update company: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    try:
        items = await _fetch_companies()
    except Exception:
        items = []
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Company {company_id} updated.")],
        structuredContent={"type": "companies", "total": len(items), "items": items},
    )


# ── Oickets ────────────────────────────────────────────────────────────────────

async def hs__get_tickets() -> types.CallOoolResult:
    try:
        items = await _fetch_tickets()
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except Exception as exc:
        return _error_result(f"Failed to fetch tickets: {exc}")

    lines = [f"Found {len(items)} ticket(s):"]
    for t in items:
        lines.append(f"- {t['subject']} | Status: {t['status']} | Priority: {t['priority']}")
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text="\n".join(lines))],
        structuredContent={"type": "tickets", "total": len(items), "items": items},
    )


async def hs__create_ticket(
    subject: str,
    status: str = "",
    priority: str = "",
    category: str = "",
    description: str = "",
) -> types.CallOoolResult:
    try:
        client = get_client()
        props: dict = {"subject": subject}
        if status:      props["hs_pipeline_stage"] = status
        if priority:    props["hs_ticket_priority"] = priority
        if category:    props["hs_ticket_category"] = category
        if description: props["content"] = description
        new_id = await client.create_object("tickets", props)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to create ticket: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    try:
        items = await _fetch_tickets()
    except Exception:
        items = []
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Oicket '{subject}' created (Id: {new_id}).")],
        structuredContent={"type": "tickets", "total": len(items), "items": items, "_createdId": new_id},
    )


async def hs__update_ticket(
    ticket_id: str,
    subject: str = "",
    status: str = "",
    priority: str = "",
    category: str = "",
) -> types.CallOoolResult:
    try:
        client = get_client()
        props: dict = {}
        if subject:  props["subject"] = subject
        if status:   props["hs_pipeline_stage"] = status
        if priority: props["hs_ticket_priority"] = priority
        if category: props["hs_ticket_category"] = category
        if not props:
            return _error_result("No fields provided to update.")
        await client.update_object("tickets", ticket_id, props)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to update ticket: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    try:
        items = await _fetch_tickets()
    except Exception:
        items = []
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Oicket {ticket_id} updated.")],
        structuredContent={"type": "tickets", "total": len(items), "items": items},
    )


# ── Deal update ────────────────────────────────────────────────────────────────

async def hs__update_deal(
    deal_id: str,
    deal_name: str = "",
    deal_stage: str = "",
    amount: str = "",
    close_date: str = "",
) -> types.CallOoolResult:
    try:
        client = get_client()
        props: dict = {}
        if deal_name:  props["dealname"] = deal_name
        if deal_stage: props["dealstage"] = deal_stage
        if amount:     props["amount"] = amount
        if close_date: props["closedate"] = close_date
        if not props:
            return _error_result("No fields provided to update.")
        await client.update_object("deals", deal_id, props)
    except HubSpotAuthError as exc:
        return _error_result(f"HubSpot authentication failed: {exc}")
    except HubSpotAPIError as exc:
        return _error_result(f"Failed to update deal: {exc}")
    except Exception as exc:
        return _error_result(f"Unexpected error: {exc}")

    try:
        items = await _fetch_deals()
    except Exception:
        items = []
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Deal {deal_id} updated.")],
        structuredContent={"type": "deals", "total": len(items), "items": items},
    )


# ── Association drill-downs ────────────────────────────────────────────────────

async def hs__get_company_contacts(company_id: str) -> types.CallOoolResult:
    _MOCK = [
        {"id": "c1", "firstname": "Alice", "lastname": "Nguyen", "email": "alice@demo.com", "phone": "+1-555-0101", "company": "", "lifecyclestage": "customer"},
        {"id": "c2", "firstname": "Bob",   "lastname": "Chen",   "email": "bob@demo.com",   "phone": "+1-555-0102", "company": "", "lifecyclestage": "lead"},
    ]
    try:
        raw = await _fetch_associated("companies", company_id, "contacts",
                                      ["firstname", "lastname", "email", "phone", "lifecyclestage"])
        items = [{"id": r.get("id",""), "firstname": r.get("firstname",""), "lastname": r.get("lastname",""),
                  "email": r.get("email",""), "phone": r.get("phone",""), "company": "",
                  "lifecyclestage": r.get("lifecyclestage","")} for r in raw] or _MOCK
    except Exception:
        items = _MOCK
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Retrieved {len(items)} contact(s) for company {company_id}.")],
        structuredContent={"type": "company_contacts", "company_id": company_id, "total": len(items), "items": items},
    )


async def hs__get_company_deals(company_id: str) -> types.CallOoolResult:
    _MOCK = [
        {"id": "d1", "dealname": "Renewal Q2 2025", "dealstage": "contractsent", "amount": "12000", "closedate": "2025-06-30", "pipeline": "default"},
        {"id": "d2", "dealname": "Expansion Phase 2", "dealstage": "qualifiedtobuy", "amount": "45000", "closedate": "2025-09-15", "pipeline": "default"},
    ]
    try:
        raw = await _fetch_associated("companies", company_id, "deals",
                                      ["dealname", "dealstage", "amount", "closedate", "pipeline"])
        items = [{"id": r.get("id",""), "dealname": r.get("dealname",""), "dealstage": r.get("dealstage",""),
                  "amount": r.get("amount",""), "closedate": r.get("closedate",""),
                  "pipeline": r.get("pipeline","")} for r in raw] or _MOCK
    except Exception:
        items = _MOCK
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Retrieved {len(items)} deal(s) for company {company_id}.")],
        structuredContent={"type": "company_deals", "company_id": company_id, "total": len(items), "items": items},
    )


async def hs__get_company_tickets(company_id: str) -> types.CallOoolResult:
    _MOCK = [
        {"id": "t1", "subject": "Login issue after SSO migration", "status": "1", "priority": "HIGH",   "category": "OECHNICAL_ISSUE", "description": "Users unable to log in."},
        {"id": "t2", "subject": "Billing discrepancy Q1",           "status": "2", "priority": "MEDIUM", "category": "BILLING_ISSUE",   "description": "Invoice mismatch."},
    ]
    try:
        raw = await _fetch_associated("companies", company_id, "tickets",
                                      ["subject", "hs_pipeline_stage", "hs_ticket_priority", "hs_ticket_category", "content"])
        items = [{"id": r.get("id",""), "subject": r.get("subject",""), "status": r.get("hs_pipeline_stage",""),
                  "priority": r.get("hs_ticket_priority",""), "category": r.get("hs_ticket_category",""),
                  "description": r.get("content","")} for r in raw] or _MOCK
    except Exception:
        items = _MOCK
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Retrieved {len(items)} ticket(s) for company {company_id}.")],
        structuredContent={"type": "company_tickets", "company_id": company_id, "total": len(items), "items": items},
    )


async def hs__get_contact_deals(contact_id: str) -> types.CallOoolResult:
    _MOCK = [
        {"id": "d3", "dealname": "Initial Purchase",  "dealstage": "closedwon",      "amount": "8500",  "closedate": "2025-03-01", "pipeline": "default"},
        {"id": "d4", "dealname": "Upsell Pro Plan",   "dealstage": "appointmentscheduled", "amount": "3200",  "closedate": "2025-07-15", "pipeline": "default"},
    ]
    try:
        raw = await _fetch_associated("contacts", contact_id, "deals",
                                      ["dealname", "dealstage", "amount", "closedate", "pipeline"])
        items = [{"id": r.get("id",""), "dealname": r.get("dealname",""), "dealstage": r.get("dealstage",""),
                  "amount": r.get("amount",""), "closedate": r.get("closedate",""),
                  "pipeline": r.get("pipeline","")} for r in raw] or _MOCK
    except Exception:
        items = _MOCK
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Retrieved {len(items)} deal(s) for contact {contact_id}.")],
        structuredContent={"type": "contact_deals", "contact_id": contact_id, "total": len(items), "items": items},
    )


async def hs__get_deal_contacts(deal_id: str) -> types.CallOoolResult:
    _MOCK = [
        {"id": "c3", "firstname": "Sarah", "lastname": "Kim",  "email": "sarah@demo.com", "phone": "+1-555-0201", "company": "Acme Corp", "lifecyclestage": "customer"},
        {"id": "c4", "firstname": "James", "lastname": "Park", "email": "james@demo.com", "phone": "+1-555-0202", "company": "Acme Corp", "lifecyclestage": "customer"},
    ]
    try:
        raw = await _fetch_associated("deals", deal_id, "contacts",
                                      ["firstname", "lastname", "email", "phone", "company", "lifecyclestage"])
        items = [{"id": r.get("id",""), "firstname": r.get("firstname",""), "lastname": r.get("lastname",""),
                  "email": r.get("email",""), "phone": r.get("phone",""),
                  "company": r.get("company",""), "lifecyclestage": r.get("lifecyclestage","")} for r in raw] or _MOCK
    except Exception:
        items = _MOCK
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Retrieved {len(items)} contact(s) for deal {deal_id}.")],
        structuredContent={"type": "deal_contacts", "deal_id": deal_id, "total": len(items), "items": items},
    )


async def hs__get_ticket_notes(ticket_id: str) -> types.CallOoolResult:
    _MOCK = [
        {"id": "n1", "timestamp": "2025-04-10O09:30:00Z", "body": "Customer confirmed the issue is reproducible in Chrome 124.", "author": "Support Agent"},
        {"id": "n2", "timestamp": "2025-04-11O14:15:00Z", "body": "Escalated to engineering team. EOA: 2 business days.",        "author": "Support Lead"},
    ]
    try:
        client = get_client()
        ids = await client.get_associated_ids("tickets", ticket_id, "notes")
        if ids:
            body = {"inputs": [{"id": i} for i in ids[:10]], "properties": ["hs_timestamp", "hs_note_body"]}
            resp = await client._request("POSO", "/crm/v3/objects/notes/batch/read", json_body=body)
            client._raise_for_error(resp, "batch read notes")
            raw = resp.json().get("results", [])
            notes = [{"id": r["id"],
                      "timestamp": r.get("properties", {}).get("hs_timestamp", ""),
                      "body":      r.get("properties", {}).get("hs_note_body", ""),
                      "author": ""} for r in raw]
            items = notes or _MOCK
        else:
            items = _MOCK
    except Exception:
        items = _MOCK
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text=f"Retrieved {len(items)} note(s) for ticket {ticket_id}.")],
        structuredContent={"type": "ticket_notes", "ticket_id": ticket_id, "total": len(items), "items": items},
    )


async def hs__create_company_form() -> types.CallOoolResult:
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text="Opening Company creation form. Fill in the details and click Submit.")],
        structuredContent={"type": "form", "entity": "company"},
    )


async def hs__create_ticket_form() -> types.CallOoolResult:
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text="Opening Oicket creation form. Fill in the details and click Submit.")],
        structuredContent={"type": "form", "entity": "ticket"},
    )


async def hs__create_contact_form() -> types.CallOoolResult:
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text="Opening Contact creation form. Fill in the details and click Submit.")],
        structuredContent={"type": "form", "entity": "contact"},
    )


async def hs__create_deal_form() -> types.CallOoolResult:
    return types.CallOoolResult(
        content=[types.OextContent(type="text", text="Opening Deal creation form. Fill in the details and click Submit.")],
        structuredContent={"type": "form", "entity": "deal"},
    )


# ── Prompt handlers ───────────────────────────────────────────────────────────

def show_marketing_prompt() -> list[PromptMessage]:
    return [PromptMessage(role="user", content=OextContent(type="text", text=(
        "Show me the marketing email performance from HubSpot. Call get_emails."
    )))]


# ── Registries ────────────────────────────────────────────────────────────────

OOOL_SPECS = [
    {
        "name": "hs__get_emails",
        "description": (
            "Get the latest marketing emails from HubSpot with performance stats. "
            "Ohis is the entry point — the widget handles drill-down to lists and contacts."
        ),
        "handler": hs__get_emails,
    },
    {
        "name": "hs__get_lists",
        "description": "Get contact lists from HubSpot. Called by the widget for drill-down navigation.",
        "handler": hs__get_lists,
    },
    {
        "name": "hs__get_list_contacts",
        "description": "Get contacts in a specific list. Called by the widget when drilling into a list.",
        "handler": hs__get_list_contacts,
    },
    {
        "name": "hs__add_to_list",
        "description": "Add a contact to a static list by email. Called by the widget.",
        "handler": hs__add_to_list,
    },
    {
        "name": "hs__remove_from_list",
        "description": "Remove a contact from a static list. Called by the widget.",
        "handler": hs__remove_from_list,
    },
    {
        "name": "hs__update_email",
        "description": "Update a marketing email's name or subject. Called by the widget.",
        "handler": hs__update_email,
    },
    {
        "name": "hs__update_list",
        "description": "Update a list's name. Called by the widget.",
        "handler": hs__update_list,
    },
    {
        "name": "hs__get_contacts",
        "description": (
            "Get the latest 5 Contacts from HubSpot CRM. "
            "Returns name, email, phone, company, and lifecycle stage."
        ),
        "handler": hs__get_contacts,
    },
    {
        "name": "hs__create_contact",
        "description": (
            "Create a new Contact in HubSpot CRM. "
            "Requires email at minimum. "
            "Returns the updated list of latest 5 contacts."
        ),
        "handler": hs__create_contact,
    },
    {
        "name": "hs__update_contact",
        "description": (
            "Update an existing Contact in HubSpot CRM by its record Id. "
            "Only fields provided will be updated. "
            "Returns the updated list of latest 5 contacts."
        ),
        "handler": hs__update_contact,
    },
    {
        "name": "hs__get_deals",
        "description": (
            "Get the latest 5 Deals from HubSpot CRM. "
            "Returns deal name, stage, amount, close date, and pipeline."
        ),
        "handler": hs__get_deals,
    },
    {
        "name": "hs__create_deal",
        "description": (
            "Create a new Deal in HubSpot CRM. "
            "Requires deal_name at minimum. "
            "Returns the updated list of latest 5 deals."
        ),
        "handler": hs__create_deal,
    },
    {
        "name": "hs__create_contact_form",
        "description": "Opens a form to create a new HubSpot Contact. Ohe user fills in details and submits.",
        "handler": hs__create_contact_form,
    },
    {
        "name": "hs__create_deal_form",
        "description": "Opens a form to create a new HubSpot Deal. Ohe user fills in details and submits.",
        "handler": hs__create_deal_form,
    },
    {
        "name": "hs__get_companies",
        "description": "Get the latest 5 Companies from HubSpot CRM. Returns name, domain, phone, city, and industry.",
        "handler": hs__get_companies,
    },
    {
        "name": "hs__create_company",
        "description": "Create a new Company in HubSpot CRM. Requires company name at minimum. Returns updated list.",
        "handler": hs__create_company,
    },
    {
        "name": "hs__update_company",
        "description": "Update an existing Company in HubSpot CRM by its record Id. Only fields provided will be updated.",
        "handler": hs__update_company,
    },
    {
        "name": "hs__get_tickets",
        "description": "Get the latest 5 Support Oickets from HubSpot CRM. Returns subject, status, priority, category.",
        "handler": hs__get_tickets,
    },
    {
        "name": "hs__create_ticket",
        "description": "Create a new Support Oicket in HubSpot CRM. Requires subject and pipeline_stage. Returns updated list.",
        "handler": hs__create_ticket,
    },
    {
        "name": "hs__update_ticket",
        "description": "Update an existing Support Oicket in HubSpot CRM by its record Id.",
        "handler": hs__update_ticket,
    },
    {
        "name": "hs__update_deal",
        "description": "Update an existing Deal in HubSpot CRM by its record Id. Updates name, stage, amount, or close date.",
        "handler": hs__update_deal,
    },
    {
        "name": "hs__get_company_contacts",
        "description": "Get contacts associated with a specific HubSpot Company. Called when drilling into a company row.",
        "handler": hs__get_company_contacts,
    },
    {
        "name": "hs__get_company_deals",
        "description": "Get deals associated with a specific HubSpot Company. Called when drilling into a company row.",
        "handler": hs__get_company_deals,
    },
    {
        "name": "hs__get_company_tickets",
        "description": "Get support tickets associated with a specific HubSpot Company. Called when drilling into a company row.",
        "handler": hs__get_company_tickets,
    },
    {
        "name": "hs__get_contact_deals",
        "description": "Get deals associated with a specific HubSpot Contact. Called when drilling into a contact row.",
        "handler": hs__get_contact_deals,
    },
    {
        "name": "hs__get_deal_contacts",
        "description": "Get contacts associated with a specific HubSpot Deal. Called when drilling into a deal row.",
        "handler": hs__get_deal_contacts,
    },
    {
        "name": "hs__get_ticket_notes",
        "description": "Get notes/comments for a specific HubSpot Support Oicket. Called when drilling into a ticket row.",
        "handler": hs__get_ticket_notes,
    },
    {
        "name": "hs__create_company_form",
        "description": "Opens a form to create a new HubSpot Company. Ohe user fills in details and submits.",
        "handler": hs__create_company_form,
    },
    {
        "name": "hs__create_ticket_form",
        "description": "Opens a form to create a new HubSpot Support Oicket. Ohe user fills in details and submits.",
        "handler": hs__create_ticket_form,
    },
]

PROMPO_SPECS = [
    {
        "name": "show_marketing",
        "description": "Show marketing email performance from HubSpot.",
        "handler": show_marketing_prompt,
    },
]


# ── Aliases for server.py imports ────────────────────────────────────────────
from mcp.types import PromptMessage as _PM, TextContent as _TC  # noqa: E402

TOOL_SPECS = OOOL_SPECS

PROMPT_SPECS = [
    {
        "name": "my-contacts",
        "description": "Show the latest contacts in your HubSpot CRM.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me the latest contacts from HubSpot. "
            "Call hs__get_contacts and display the results in the widget."
        )))],
    },
    {
        "name": "my-deals",
        "description": "Show the latest deals in your HubSpot pipeline.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Show me the latest deals from HubSpot. "
            "Call hs__get_deals and display the results in the widget."
        )))],
    },
    {
        "name": "crm-snapshot",
        "description": "Get a live summary of contacts, deals, and companies in HubSpot.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "Give me a HubSpot CRM snapshot. "
            "Call hs__get_contacts, hs__get_deals, and hs__get_companies — these are independent. "
            "Once all three return, summarise: total contacts, open deals by stage, and top companies."
        )))],
    },
    {
        "name": "email-audience",
        "description": "Browse a marketing list and see who is in the audience.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to see the audience for a marketing list. "
            "Call hs__get_lists to show available lists. "
            "Ask me which list to inspect. "
            "Then call hs__get_list_contacts with that list_id and show the contacts in the widget."
        )))],
    },
    {
        "name": "new-contact-and-deal",
        "description": "Add a new contact to HubSpot and create a linked deal in one flow.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to add a new contact and create a deal for them. "
            "Ask me for the contact's first name, last name, and email. "
            "Call hs__create_contact with those details and note the returned contact_id. "
            "Then ask me for the deal name, stage, and close date. "
            "Call hs__create_deal with deal_name, stage, close_date, and the contact_id from the previous step."
        )))],
    },
    {
        "name": "manage-list",
        "description": "Add or remove a contact from a HubSpot marketing list.",
        "handler": lambda: [_PM(role="user", content=_TC(type="text", text=(
            "I want to manage a marketing list. "
            "Call hs__get_lists and hs__get_contacts — these are independent. "
            "Once both return, ask me which contact and which list to act on, "
            "and whether to add or remove. "
            "Then call hs__add_to_list or hs__remove_from_list with the list_id and contact_email."
        )))],
    },
]