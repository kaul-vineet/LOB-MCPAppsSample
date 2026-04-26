"""SAP SuccessFactors HR API client — mock data, token exchange, and OData helpers."""
from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context

from shared_mcp.auth import get_bearer_token
from shared_mcp.http import create_async_client
from shared_mcp.logger import get_logger
from shared_mcp.settings import load_sap_sf_settings

LOGGER = get_logger(__name__)


# ── Mock data store ─────────────────────────────────────────────────

_MOCK_EMPLOYEES = {
    "EMP-1001": {
        "userId": "EMP-1001",
        "firstName": "Priya",
        "lastName": "Sharma",
        "displayName": "Priya Sharma",
        "email": "priya.sharma@contoso.com",
        "phone": "+44 20 7946 0958",
        "jobTitle": "Senior Software Engineer",
        "department": "Engineering",
        "division": "Product Development",
        "location": "London",
        "manager": "EMP-1010",
        "hireDate": "/Date(1609459200000)/",
        "status": "active",
        "company": "Contoso Ltd",
    },
    "EMP-1002": {
        "userId": "EMP-1002",
        "firstName": "James",
        "lastName": "Okonkwo",
        "displayName": "James Okonkwo",
        "email": "james.okonkwo@contoso.com",
        "phone": "+44 20 7946 1122",
        "jobTitle": "Product Manager",
        "department": "Product",
        "division": "Product Development",
        "location": "London",
        "manager": "EMP-1010",
        "hireDate": "/Date(1585699200000)/",
        "status": "active",
        "company": "Contoso Ltd",
    },
    "EMP-1003": {
        "userId": "EMP-1003",
        "firstName": "Sarah",
        "lastName": "Chen",
        "displayName": "Sarah Chen",
        "email": "sarah.chen@contoso.com",
        "phone": "+1 415 555 0192",
        "jobTitle": "UX Designer",
        "department": "Design",
        "division": "Product Development",
        "location": "San Francisco",
        "manager": "EMP-1010",
        "hireDate": "/Date(1625097600000)/",
        "status": "active",
        "company": "Contoso Inc",
    },
    "EMP-1010": {
        "userId": "EMP-1010",
        "firstName": "Raj",
        "lastName": "Patel",
        "displayName": "Raj Patel",
        "email": "raj.patel@contoso.com",
        "phone": "+44 20 7946 0800",
        "jobTitle": "VP Engineering",
        "department": "Engineering",
        "division": "Product Development",
        "location": "London",
        "manager": "EMP-2001",
        "hireDate": "/Date(1483228800000)/",
        "status": "active",
        "company": "Contoso Ltd",
    },
}

_MOCK_LEAVE_BALANCES = [
    {"planName": "Annual Leave", "balance": 18.0, "unit": "Days", "asOfDate": "2026-04-01"},
    {"planName": "Sick Leave", "balance": 10.0, "unit": "Days", "asOfDate": "2026-04-01"},
    {"planName": "Personal Leave", "balance": 3.0, "unit": "Days", "asOfDate": "2026-04-01"},
    {"planName": "Parental Leave", "balance": 26.0, "unit": "Weeks", "asOfDate": "2026-04-01"},
]

_MOCK_TIME_OFF = [
    {"type": "Annual Leave", "startDate": "2026-03-17", "endDate": "2026-03-21", "quantityInDays": 5.0, "approvalStatus": "approved"},
    {"type": "Sick Leave", "startDate": "2026-02-10", "endDate": "2026-02-10", "quantityInDays": 1.0, "approvalStatus": "approved"},
    {"type": "Annual Leave", "startDate": "2025-12-22", "endDate": "2026-01-02", "quantityInDays": 8.0, "approvalStatus": "approved"},
    {"type": "Personal Leave", "startDate": "2025-11-14", "endDate": "2025-11-14", "quantityInDays": 1.0, "approvalStatus": "approved"},
    {"type": "Annual Leave", "startDate": "2025-08-04", "endDate": "2025-08-15", "quantityInDays": 10.0, "approvalStatus": "approved"},
]

_MOCK_PAY_STUBS = [
    {"id": "PR-2026-04", "payDate": "2026-04-25", "grossPay": 6250.00, "netPay": 4687.50, "currency": "GBP", "payPeriod": "April 2026"},
    {"id": "PR-2026-03", "payDate": "2026-03-25", "grossPay": 6250.00, "netPay": 4687.50, "currency": "GBP", "payPeriod": "March 2026"},
    {"id": "PR-2026-02", "payDate": "2026-02-25", "grossPay": 6250.00, "netPay": 4687.50, "currency": "GBP", "payPeriod": "February 2026"},
    {"id": "PR-2026-01", "payDate": "2026-01-25", "grossPay": 6250.00, "netPay": 4687.50, "currency": "GBP", "payPeriod": "January 2026"},
    {"id": "PR-2025-12", "payDate": "2025-12-20", "grossPay": 6250.00, "netPay": 4687.50, "currency": "GBP", "payPeriod": "December 2025"},
    {"id": "PR-2025-11", "payDate": "2025-11-25", "grossPay": 6250.00, "netPay": 4687.50, "currency": "GBP", "payPeriod": "November 2025"},
]

_MOCK_PAY_DETAIL = {
    "id": "PR-2026-04",
    "payDate": "2026-04-25",
    "grossPay": 6250.00,
    "netPay": 4687.50,
    "currency": "GBP",
    "earnings": [
        {"type": "Earning", "name": "Base Salary", "amount": 6250.00},
    ],
    "deductions": [
        {"type": "Deduction", "name": "Income Tax (PAYE)", "amount": 1041.67},
        {"type": "Deduction", "name": "National Insurance", "amount": 416.67},
        {"type": "Deduction", "name": "Pension (5%)", "amount": 312.50},
    ],
}

_MOCK_DOCUMENTS = [
    {"id": "DOC-0001", "fileName": "Employment_Contract_2021.pdf", "mimeType": "application/pdf", "documentType": "Contract", "createdDate": "2021-01-04"},
    {"id": "DOC-0002", "fileName": "Salary_Review_2025.pdf", "mimeType": "application/pdf", "documentType": "Letter", "createdDate": "2025-04-01"},
    {"id": "DOC-0003", "fileName": "P60_2024-25.pdf", "mimeType": "application/pdf", "documentType": "Tax Document", "createdDate": "2025-05-15"},
    {"id": "DOC-0004", "fileName": "Benefits_Enrolment_2026.pdf", "mimeType": "application/pdf", "documentType": "Benefits", "createdDate": "2026-01-10"},
]

_MOCK_BACKGROUND_CHECKS = [
    {"type": "standard", "status": "completed", "startDate": "2020-12-15", "endDate": "2021-01-02"},
    {"type": "dbs_enhanced", "status": "completed", "startDate": "2020-12-15", "endDate": "2021-01-10"},
]


def _default_uid(user_id: str | None) -> str:
    return user_id or "EMP-1001"


def _mock_profile(uid: str) -> dict:
    return copy.deepcopy(_MOCK_EMPLOYEES.get(uid, _MOCK_EMPLOYEES["EMP-1001"]))


# ── Token exchange ───────────────────────────────────────────────────

async def _exchange_token_for_sap(entra_token: str) -> str:
    """Exchange an Entra ID bearer token for a SAP SuccessFactors OAuth token."""
    settings = load_sap_sf_settings()
    async with create_async_client() as client:
        resp = await client.post(
            settings.token_url,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:saml2-bearer",
                "client_id": settings.client_id,
                "company_id": settings.company_id,
                "assertion": entra_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


def _get_auth_token(ctx: Optional[Context] = None) -> str:
    return get_bearer_token(ctx)


# ── OData helpers ────────────────────────────────────────────────────

async def _sf_get(path: str, sap_token: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    settings = load_sap_sf_settings()
    url = f"{settings.odata_url}{path}"
    all_params: Dict[str, str] = {"$format": "json"}
    if params:
        all_params.update(params)
    async with create_async_client() as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {sap_token}"},
            params=all_params,
        )
        resp.raise_for_status()
        return resp.json()


async def _sf_post(path: str, sap_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = load_sap_sf_settings()
    url = f"{settings.odata_url}{path}"
    async with create_async_client() as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {sap_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


async def _sf_patch(path: str, sap_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    settings = load_sap_sf_settings()
    url = f"{settings.odata_url}{path}"
    async with create_async_client() as client:
        resp = await client.patch(
            url,
            headers={
                "Authorization": f"Bearer {sap_token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {"status": "ok"}


# ── Data transformation ──────────────────────────────────────────────

def _transform_employee(data: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten OData User entity into a clean employee profile dict."""
    d = data.get("d", data)
    person = d.get("personNav", {}).get("results", [{}])[0] if d.get("personNav") else {}
    job = d.get("jobInfoNav", {}).get("results", [{}])[0] if d.get("jobInfoNav") else {}
    emails = d.get("emailNav", {}).get("results", []) if d.get("emailNav") else []
    phones = d.get("phoneNav", {}).get("results", []) if d.get("phoneNav") else []
    primary_email = next((e.get("emailAddress") for e in emails if e.get("isPrimary")), None)
    primary_phone = next((p.get("phoneNumber") for p in phones if p.get("isPrimary")), None)

    return {
        "userId": d.get("userId"),
        "firstName": d.get("firstName"),
        "lastName": d.get("lastName"),
        "displayName": d.get("displayName") or f"{d.get('firstName', '')} {d.get('lastName', '')}".strip(),
        "email": primary_email or d.get("email"),
        "phone": primary_phone,
        "jobTitle": job.get("jobTitle") or d.get("title"),
        "department": job.get("department") or d.get("department"),
        "division": job.get("division") or d.get("division"),
        "location": job.get("location") or d.get("location"),
        "manager": job.get("managerId"),
        "hireDate": d.get("hireDate"),
        "status": d.get("status"),
        "company": job.get("company") or d.get("company"),
    }
