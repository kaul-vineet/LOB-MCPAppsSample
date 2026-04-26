"""DocuSign API client — JWT auth, HTTP, mock data. No MCP imports."""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any

import httpx
import jwt
import structlog
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .settings import get_settings

log = structlog.get_logger("ds")


def _load_env() -> None:
    explicit = os.environ.get("MCP_SERVERS_ENV_FILE")
    if explicit:
        load_dotenv(explicit, override=True)
        return
    project_env = Path.cwd() / "env" / ".env.docusign"
    if project_env.exists():
        load_dotenv(project_env, override=True)
        return
    load_dotenv()


_load_env()
_cfg = get_settings()

# ── Mock data ─────────────────────────────────────────────────────────────────

MOCK_ENVELOPES = [
    {"envelopeId": "env-0001-gtc", "emailSubject": "Spice Trading Agreement — East Indies Route", "status": "completed",  "sentDateTime": "2026-04-20T09:00:00Z", "completedDateTime": "2026-04-21T14:22:00Z"},
    {"envelopeId": "env-0002-gtc", "emailSubject": "Commercial Partnership NDA — CloudBase Corp",  "status": "sent",       "sentDateTime": "2026-04-21T11:30:00Z", "completedDateTime": ""},
    {"envelopeId": "env-0003-gtc", "emailSubject": "Purchase Contract — TechCorp Suppliers Q2",    "status": "delivered",  "sentDateTime": "2026-04-22T08:00:00Z", "completedDateTime": ""},
    {"envelopeId": "env-0004-gtc", "emailSubject": "Cargo Manifest Amendment — Voyage 47",         "status": "declined",   "sentDateTime": "2026-04-18T16:00:00Z", "completedDateTime": ""},
    {"envelopeId": "env-0005-gtc", "emailSubject": "Fleet Insurance Renewal 2026",                  "status": "completed",  "sentDateTime": "2026-04-15T10:00:00Z", "completedDateTime": "2026-04-16T09:10:00Z"},
]

MOCK_TEMPLATES = [
    {"templateId": "tmpl-001", "name": "Standard Trading Contract",    "description": "General goods and services agreement",   "lastModified": "2026-03-01T12:00:00Z", "folderName": "Contracts"},
    {"templateId": "tmpl-002", "name": "NDA — Mutual Confidentiality", "description": "Non-disclosure for partnership talks",    "lastModified": "2026-02-14T09:00:00Z", "folderName": "Legal"},
    {"templateId": "tmpl-003", "name": "Cargo Insurance Certificate",  "description": "Marine cargo insurance declaration",     "lastModified": "2026-01-20T15:30:00Z", "folderName": "Insurance"},
    {"templateId": "tmpl-004", "name": "Supplier Onboarding Pack",     "description": "KYC and terms for new suppliers",        "lastModified": "2026-03-15T11:00:00Z", "folderName": "Procurement"},
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def status_emoji(status: str) -> str:
    return {
        "created": "📝", "sent": "📤", "delivered": "📬", "signed": "✍️",
        "completed": "✅", "declined": "❌", "voided": "🚫",
    }.get(status.lower(), "📄")


def validate_env() -> str | None:
    missing = []
    if not _cfg.docusign_integration_key: missing.append("DOCUSIGN_INTEGRATION_KEY")
    if not _cfg.docusign_user_id:         missing.append("DOCUSIGN_USER_ID")
    if not _cfg.docusign_account_id:      missing.append("DOCUSIGN_ACCOUNT_ID")
    if not _cfg.docusign_rsa_private_key: missing.append("DOCUSIGN_RSA_PRIVATE_KEY")
    return f"Missing environment variables: {', '.join(missing)}" if missing else None


def is_mock() -> bool:
    return _cfg.mock_mode or bool(validate_env())


# ── JWT auth ──────────────────────────────────────────────────────────────────

_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def clear_token_cache() -> None:
    _token_cache["access_token"] = None
    _token_cache["expires_at"] = 0.0


def _get_private_key() -> str:
    try:
        return base64.b64decode(_cfg.docusign_rsa_private_key).decode("utf-8")
    except Exception:
        return _cfg.docusign_rsa_private_key


def get_access_token() -> str:
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 300:
        return _token_cache["access_token"]

    private_key = _get_private_key()
    payload = {
        "iss": _cfg.docusign_integration_key,
        "sub": _cfg.docusign_user_id,
        "aud": _cfg.docusign_auth_server,
        "iat": int(now),
        "exp": int(now) + 3600,
        "scope": "signature impersonation",
    }
    assertion = jwt.encode(payload, private_key, algorithm="RS256")
    with httpx.Client() as client:
        resp = client.post(
            f"https://{_cfg.docusign_auth_server}/oauth/token",
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion},
        )
        resp.raise_for_status()
    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    log.info("docusign_token_refreshed")
    return data["access_token"]


# ── HTTP client ───────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.RequestError),
)
async def ds_request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict | list | bytes:
    token = get_access_token()
    url = f"{_cfg.docusign_base_url}/v2.1/accounts/{_cfg.docusign_account_id}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, url, headers=headers, params=params, json=json_body)
        resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return resp.json()
    return resp.content


async def fetch_envelopes(
    from_date: str | None = None, status: str | None = None, count: int = 10
) -> list[dict]:
    params: dict[str, Any] = {"count": str(count), "order_by": "last_modified desc"}
    if from_date: params["from_date"] = from_date
    if status:    params["status"] = status
    data = await ds_request("GET", "/envelopes", params=params)
    return data.get("envelopes", []) if isinstance(data, dict) else []
