"""DocuSign eSignature MCP server for The Great Trading Company.

Provides 9 tools for envelope management, templates, and embedded signing
via the DocuSign REST API v2.1 with JWT Grant authentication.
"""

from __future__ import annotations

import base64
import json
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
import jwt
import structlog
from dotenv import load_dotenv


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
from mcp.server.fastmcp import FastMCP
from pydantic_settings import BaseSettings
from starlette.middleware.cors import CORSMiddleware
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

_load_env()
log = structlog.get_logger()

# ── Settings ────────────────────────────────────────────────────────────────

class DSSettings(BaseSettings):
    docusign_integration_key: str = ""
    docusign_user_id: str = ""
    docusign_account_id: str = ""
    docusign_rsa_private_key: str = ""  # base64-encoded PEM
    docusign_auth_server: str = "account-d.docusign.com"
    docusign_base_url: str = "https://demo.docusign.net/restapi"
    mock_mode: bool = False
    port: int = 3005
    cors_origins: str = "*"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> DSSettings:
    return DSSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


cfg = get_settings()

# ── JWT Auth Client ─────────────────────────────────────────────────────────

_token_cache: dict[str, Any] = {"access_token": None, "expires_at": 0.0}


def clear_token_cache() -> None:
    """Force re-authentication on the next API call."""
    _token_cache["access_token"] = None
    _token_cache["expires_at"] = 0.0


def _get_private_key() -> str:
    """Decode the base64-encoded RSA private key."""
    try:
        return base64.b64decode(cfg.docusign_rsa_private_key).decode("utf-8")
    except Exception:
        return cfg.docusign_rsa_private_key  # already PEM plaintext

def _get_access_token() -> str:
    """Obtain or refresh a DocuSign access token via JWT Grant."""
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 300:
        return _token_cache["access_token"]

    private_key = _get_private_key()
    payload = {
        "iss": cfg.docusign_integration_key,
        "sub": cfg.docusign_user_id,
        "aud": cfg.docusign_auth_server,
        "iat": int(now),
        "exp": int(now) + 3600,
        "scope": "signature impersonation",
    }
    assertion = jwt.encode(payload, private_key, algorithm="RS256")

    with httpx.Client() as client:
        resp = client.post(
            f"https://{cfg.docusign_auth_server}/oauth/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
        )
        resp.raise_for_status()

    data = resp.json()
    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    log.info("docusign_token_refreshed")
    return data["access_token"]


# ── HTTP Client ─────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(httpx.RequestError),
)
async def _ds_request(
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict | list | bytes:
    """Make an authenticated request to DocuSign REST API v2.1."""
    token = _get_access_token()
    url = f"{cfg.docusign_base_url}/v2.1/accounts/{cfg.docusign_account_id}{path}"
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(
            method, url, headers=headers, params=params, json=json_body
        )
        resp.raise_for_status()

    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        return resp.json()
    return resp.content  # binary (PDF docs)


# ── MCP Server ──────────────────────────────────────────────────────────────

WIDGET_URI = "docusign://widget"
mcp = FastMCP("DocuSign eSignature")

@mcp.resource(WIDGET_URI)
def get_widget() -> str:
    """Serve the DocuSign widget HTML."""
    html_path = Path(__file__).parent / "web" / "widget.html"
    return html_path.read_text(encoding="utf-8")


def _is_mock() -> bool:
    return cfg.mock_mode or bool(_validate_env())


def _error_result(msg: str) -> list[dict]:
    return [{"type": "text", "text": f"Error: {msg}"}]


# ── Mock Data ─────────────────────────────────────────────────────────────────

_MOCK_ENVELOPES = [
    {"envelopeId": "env-0001-gtc", "emailSubject": "Spice Trading Agreement — East Indies Route", "status": "completed",  "sentDateTime": "2026-04-20T09:00:00Z", "completedDateTime": "2026-04-21T14:22:00Z"},
    {"envelopeId": "env-0002-gtc", "emailSubject": "Commercial Partnership NDA — CloudBase Corp",  "status": "sent",       "sentDateTime": "2026-04-21T11:30:00Z", "completedDateTime": ""},
    {"envelopeId": "env-0003-gtc", "emailSubject": "Purchase Contract — TechCorp Suppliers Q2",    "status": "delivered",  "sentDateTime": "2026-04-22T08:00:00Z", "completedDateTime": ""},
    {"envelopeId": "env-0004-gtc", "emailSubject": "Cargo Manifest Amendment — Voyage 47",         "status": "declined",   "sentDateTime": "2026-04-18T16:00:00Z", "completedDateTime": ""},
    {"envelopeId": "env-0005-gtc", "emailSubject": "Fleet Insurance Renewal 2026",                  "status": "completed",  "sentDateTime": "2026-04-15T10:00:00Z", "completedDateTime": "2026-04-16T09:10:00Z"},
]

_MOCK_TEMPLATES = [
    {"templateId": "tmpl-001", "name": "Standard Trading Contract",    "description": "General goods and services agreement",   "lastModified": "2026-03-01T12:00:00Z", "folderName": "Contracts"},
    {"templateId": "tmpl-002", "name": "NDA — Mutual Confidentiality", "description": "Non-disclosure for partnership talks",    "lastModified": "2026-02-14T09:00:00Z", "folderName": "Legal"},
    {"templateId": "tmpl-003", "name": "Cargo Insurance Certificate",  "description": "Marine cargo insurance declaration",     "lastModified": "2026-01-20T15:30:00Z", "folderName": "Insurance"},
    {"templateId": "tmpl-004", "name": "Supplier Onboarding Pack",     "description": "KYC and terms for new suppliers",        "lastModified": "2026-03-15T11:00:00Z", "folderName": "Procurement"},
]


def _mock_envelope_rows(envelopes: list[dict]) -> list[dict]:
    return [
        {
            "envelopeId":        e["envelopeId"],
            "emailSubject":      e["emailSubject"],
            "status":            e["status"],
            "statusEmoji":       _status_emoji(e["status"]),
            "sentDateTime":      e["sentDateTime"],
            "completedDateTime": e["completedDateTime"],
            "recipientCount":    2,
        }
        for e in envelopes
    ]


def _mock_list_response(rows: list[dict], label: str) -> list[dict]:
    summary_lines = [f"[demo] Found {len(rows)} {label}."]
    for r in rows[:3]:
        summary_lines.append(f"  {r.get('statusEmoji', '')} {r.get('emailSubject', r.get('name', ''))} — {r.get('status', '')}")
    return [
        {"type": "text", "text": "\n".join(summary_lines)},
        {
            "type": "resource",
            "resource": {"uri": WIDGET_URI, "mimeType": "text/html", "text": get_widget()},
            "annotations": {"audience": ["user"]},
            "metadata": {"structured_content": {"type": "envelopes", "data": rows}},
        },
    ]


def _validate_env() -> str | None:
    """Return an error message if required env vars are missing."""
    missing = []
    if not cfg.docusign_integration_key:
        missing.append("DOCUSIGN_INTEGRATION_KEY")
    if not cfg.docusign_user_id:
        missing.append("DOCUSIGN_USER_ID")
    if not cfg.docusign_account_id:
        missing.append("DOCUSIGN_ACCOUNT_ID")
    if not cfg.docusign_rsa_private_key:
        missing.append("DOCUSIGN_RSA_PRIVATE_KEY")
    if missing:
        return f"Missing environment variables: {', '.join(missing)}"
    return None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _status_emoji(status: str) -> str:
    return {
        "created": "📝",
        "sent": "📤",
        "delivered": "📬",
        "signed": "✍️",
        "completed": "✅",
        "declined": "❌",
        "voided": "🚫",
    }.get(status.lower(), "📄")


async def _fetch_envelopes(
    from_date: str | None = None,
    status: str | None = None,
    count: int = 10,
) -> list[dict]:
    """Fetch envelopes from DocuSign."""
    params: dict[str, Any] = {"count": str(count), "order_by": "last_modified desc"}
    if from_date:
        params["from_date"] = from_date
    if status:
        params["status"] = status

    data = await _ds_request("GET", "/envelopes", params=params)
    return data.get("envelopes", []) if isinstance(data, dict) else []


# ── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool(
    name="ds__get_envelopes",
    description=(
        "Get the latest envelopes from DocuSign. "
        "Optional filters: from_date (ISO 8601), status (sent|delivered|completed|declined|voided), count (default 10)."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_envelopes(
    from_date: str | None = None,
    status: str | None = None,
    count: int = 10,
) -> list[dict]:
    if _is_mock():
        filtered = [e for e in _MOCK_ENVELOPES if not status or e["status"] == status]
        return _mock_list_response(_mock_envelope_rows(filtered[:count]), "envelope(s)")
    try:
        envelopes = await _fetch_envelopes(from_date, status, count)
        rows = []
        for e in envelopes:
            rows.append({
                "envelopeId": e.get("envelopeId", ""),
                "emailSubject": e.get("emailSubject", ""),
                "status": e.get("status", ""),
                "statusEmoji": _status_emoji(e.get("status", "")),
                "sentDateTime": e.get("sentDateTime", ""),
                "completedDateTime": e.get("completedDateTime", ""),
                "recipientCount": len(e.get("recipients", {}).get("signers", [])),
            })

        summary_lines = [f"Found {len(rows)} envelope(s)."]
        for r in rows[:5]:
            summary_lines.append(
                f"  {r['statusEmoji']} {r['emailSubject'][:50]} — {r['status']} ({r['envelopeId'][:8]}…)"
            )

        return [
            {"type": "text", "text": "\n".join(summary_lines)},
            {
                "type": "resource",
                "resource": {
                    "uri": WIDGET_URI,
                    "mimeType": "text/html",
                    "text": get_widget(),
                },
                "annotations": {"audience": ["user"]},
                "metadata": {
                    "structured_content": {
                        "type": "envelopes",
                        "data": rows,
                    }
                },
            },
        ]
    except Exception as exc:
        log.error("ds__get_envelopes_failed", error=str(exc))
        return _error_result(str(exc))


@mcp.tool(
    name="ds__get_envelope_details",
    description="Get detailed information about a specific envelope including recipients and their signing status.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_envelope_details(envelope_id: str) -> list[dict]:
    if _is_mock():
        env = next((e for e in _MOCK_ENVELOPES if e["envelopeId"] == envelope_id), _MOCK_ENVELOPES[0])
        detail = {**env, "statusEmoji": _status_emoji(env["status"]), "signers": [
            {"name": "Alexandra Harrington", "email": "a.harrington@cloudbase.corp", "status": "completed", "signedDateTime": "2026-04-21T10:00:00Z", "deliveredDateTime": "2026-04-20T09:05:00Z"},
            {"name": "James Pemberton",       "email": "j.pemberton@gtc.internal",   "status": "completed", "signedDateTime": "2026-04-21T14:22:00Z", "deliveredDateTime": "2026-04-20T09:05:00Z"},
        ]}
        summary = f"[demo] Envelope: {detail['emailSubject']}\nStatus: {detail['statusEmoji']} {detail['status']}\nSigners: 2\n  • Alexandra Harrington — completed\n  • James Pemberton — completed"
        return [
            {"type": "text", "text": summary},
            {"type": "resource", "resource": {"uri": WIDGET_URI, "mimeType": "text/html", "text": get_widget()},
             "annotations": {"audience": ["user"]}, "metadata": {"structured_content": {"type": "envelope_detail", "data": detail}}},
        ]
    try:
        envelope = await _ds_request("GET", f"/envelopes/{envelope_id}")
        recipients = await _ds_request("GET", f"/envelopes/{envelope_id}/recipients")

        signers = []
        for s in recipients.get("signers", []):
            signers.append({
                "name": s.get("name", ""),
                "email": s.get("email", ""),
                "status": s.get("status", ""),
                "signedDateTime": s.get("signedDateTime", ""),
                "deliveredDateTime": s.get("deliveredDateTime", ""),
            })

        detail = {
            "envelopeId": envelope.get("envelopeId", ""),
            "emailSubject": envelope.get("emailSubject", ""),
            "status": envelope.get("status", ""),
            "statusEmoji": _status_emoji(envelope.get("status", "")),
            "sentDateTime": envelope.get("sentDateTime", ""),
            "completedDateTime": envelope.get("completedDateTime", ""),
            "signers": signers,
        }

        summary = (
            f"Envelope: {detail['emailSubject']}\n"
            f"Status: {detail['statusEmoji']} {detail['status']}\n"
            f"Signers: {len(signers)}"
        )
        for s in signers:
            summary += f"\n  • {s['name']} ({s['email']}) — {s['status']}"

        return [
            {"type": "text", "text": summary},
            {
                "type": "resource",
                "resource": {"uri": WIDGET_URI, "mimeType": "text/html", "text": get_widget()},
                "annotations": {"audience": ["user"]},
                "metadata": {"structured_content": {"type": "envelope_detail", "data": detail}},
            },
        ]
    except Exception as exc:
        log.error("ds__get_envelope_details_failed", error=str(exc))
        return _error_result(str(exc))


@mcp.tool(
    name="ds__get_templates",
    description="List available DocuSign templates. Returns template name, description, and ID.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def get_templates(count: int = 10) -> list[dict]:
    if _is_mock():
        rows = _MOCK_TEMPLATES[:count]
        lines = [f"[demo] Found {len(rows)} template(s)."] + [f"  {r['name']} ({r['templateId']})" for r in rows]
        return [
            {"type": "text", "text": "\n".join(lines)},
            {"type": "resource", "resource": {"uri": WIDGET_URI, "mimeType": "text/html", "text": get_widget()},
             "annotations": {"audience": ["user"]}, "metadata": {"structured_content": {"type": "templates", "data": rows}}},
        ]
    try:
        data = await _ds_request("GET", "/templates", params={"count": str(count)})
        templates = data.get("envelopeTemplates", []) if isinstance(data, dict) else []

        rows = []
        for t in templates:
            rows.append({
                "templateId": t.get("templateId", ""),
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "lastModified": t.get("lastModified", ""),
                "folderName": t.get("folderName", ""),
            })

        summary_lines = [f"Found {len(rows)} template(s)."]
        for r in rows[:5]:
            summary_lines.append(f"  📋 {r['name']} ({r['templateId'][:8]}…)")

        return [
            {"type": "text", "text": "\n".join(summary_lines)},
            {
                "type": "resource",
                "resource": {"uri": WIDGET_URI, "mimeType": "text/html", "text": get_widget()},
                "annotations": {"audience": ["user"]},
                "metadata": {"structured_content": {"type": "templates", "data": rows}},
            },
        ]
    except Exception as exc:
        log.error("ds__get_templates_failed", error=str(exc))
        return _error_result(str(exc))


@mcp.tool(
    name="ds__send_envelope",
    description=(
        "Send a new envelope for signing. Requires template_id, subject, and signers "
        "(list of {name, email, role_name}). Returns envelope ID and status."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def send_envelope(
    template_id: str,
    subject: str,
    signers: list[dict],
    email_body: str = "Please sign this document.",
) -> list[dict]:
    if _is_mock():
        mock_id = "env-demo-new"
        rows = _mock_envelope_rows([{"envelopeId": mock_id, "emailSubject": subject, "status": "sent", "sentDateTime": "2026-04-22T14:00:00Z", "completedDateTime": ""}] + _MOCK_ENVELOPES[:4])
        return [
            {"type": "text", "text": f"[demo] Envelope sent. ID: {mock_id}, Status: sent"},
            {"type": "resource", "resource": {"uri": WIDGET_URI, "mimeType": "text/html", "text": get_widget()},
             "annotations": {"audience": ["user"]}, "metadata": {"structured_content": {"type": "envelopes", "data": rows}}},
        ]
    try:
        template_roles = []
        for s in signers:
            template_roles.append({
                "name": s.get("name", ""),
                "email": s.get("email", ""),
                "roleName": s.get("role_name", "Signer"),
            })

        body = {
            "templateId": template_id,
            "templateRoles": template_roles,
            "emailSubject": subject,
            "emailBlurb": email_body,
            "status": "sent",
        }
        result = await _ds_request("POST", "/envelopes", json_body=body)

        env_id = result.get("envelopeId", "unknown")
        env_status = result.get("status", "unknown")

        # Fetch updated list
        envelopes = await _fetch_envelopes(count=5)
        rows = []
        for e in envelopes:
            rows.append({
                "envelopeId": e.get("envelopeId", ""),
                "emailSubject": e.get("emailSubject", ""),
                "status": e.get("status", ""),
                "statusEmoji": _status_emoji(e.get("status", "")),
                "sentDateTime": e.get("sentDateTime", ""),
            })

        return [
            {"type": "text", "text": f"Envelope sent. ID: {env_id}, Status: {env_status}"},
            {
                "type": "resource",
                "resource": {"uri": WIDGET_URI, "mimeType": "text/html", "text": get_widget()},
                "annotations": {"audience": ["user"]},
                "metadata": {"structured_content": {"type": "envelopes", "data": rows}},
            },
        ]
    except Exception as exc:
        log.error("ds__send_envelope_failed", error=str(exc))
        return _error_result(str(exc))


@mcp.tool(
    name="ds__void_envelope",
    description="Void (cancel) an envelope. Requires envelope_id and void_reason.",
)
async def void_envelope(envelope_id: str, void_reason: str) -> list[dict]:
    if _is_mock():
        return [{"type": "text", "text": f"[demo] Envelope {envelope_id} voided. Reason: {void_reason}"}]
    try:
        await _ds_request(
            "PUT",
            f"/envelopes/{envelope_id}",
            json_body={"status": "voided", "voidedReason": void_reason},
        )
        return [{"type": "text", "text": f"Envelope {envelope_id} voided. Reason: {void_reason}"}]
    except Exception as exc:
        log.error("ds__void_envelope_failed", error=str(exc))
        return _error_result(str(exc))


@mcp.tool(
    name="ds__resend_envelope",
    description="Resend notifications for an envelope to recipients who haven't signed yet.",
)
async def resend_envelope(envelope_id: str) -> list[dict]:
    if _is_mock():
        return [{"type": "text", "text": f"[demo] Envelope {envelope_id} resent to pending recipients."}]
    try:
        await _ds_request(
            "PUT",
            f"/envelopes/{envelope_id}",
            json_body={"resend_envelope": "true"},
        )
        return [{"type": "text", "text": f"Envelope {envelope_id} resent to pending recipients."}]
    except Exception as exc:
        log.error("ds__resend_envelope_failed", error=str(exc))
        return _error_result(str(exc))


@mcp.tool(
    name="ds__get_signing_url",
    description=(
        "Generate an embedded signing URL for a recipient. "
        "Requires envelope_id, signer_name, signer_email, and a return_url."
    ),
)
async def get_signing_url(
    envelope_id: str,
    signer_name: str,
    signer_email: str,
    return_url: str = "https://example.com/signing-complete",
) -> list[dict]:
    if _is_mock():
        return [{"type": "text", "text": f"[demo] Signing URL for {signer_name}: https://demo.docusign.net/signing/mock?env={envelope_id}"}]
    try:
        body = {
            "returnUrl": return_url,
            "authenticationMethod": "none",
            "email": signer_email,
            "userName": signer_name,
        }
        result = await _ds_request(
            "POST", f"/envelopes/{envelope_id}/views/recipient", json_body=body
        )
        signing_url = result.get("url", "")
        return [
            {"type": "text", "text": f"Signing URL for {signer_name}: {signing_url}"}
        ]
    except Exception as exc:
        log.error("ds__get_signing_url_failed", error=str(exc))
        return _error_result(str(exc))


@mcp.tool(
    name="ds__download_document",
    description=(
        "Download a document from an envelope. "
        "Pass document_id='combined' for all documents as one PDF."
    ),
)
async def download_document(
    envelope_id: str, document_id: str = "combined"
) -> list[dict]:
    if _is_mock():
        return [{"type": "text", "text": f"[demo] Downloaded document '{document_id}' from envelope {envelope_id} (42.3 KB). Binary content available."}]
    try:
        content = await _ds_request(
            "GET", f"/envelopes/{envelope_id}/documents/{document_id}"
        )
        if isinstance(content, bytes):
            size_kb = len(content) / 1024
            return [
                {
                    "type": "text",
                    "text": (
                        f"Downloaded document '{document_id}' from envelope {envelope_id} "
                        f"({size_kb:.1f} KB). Binary content available."
                    ),
                }
            ]
        return [{"type": "text", "text": "Document downloaded (unexpected format)."}]
    except Exception as exc:
        log.error("ds__download_document_failed", error=str(exc))
        return _error_result(str(exc))


@mcp.tool(
    name="ds__send_envelope_form",
    description="Opens a form to send a new DocuSign envelope. The user fills in recipient details and submits.",
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def send_envelope_form() -> list[dict]:
    """Opens an interactive form widget for sending a new DocuSign envelope."""
    return [
        {"type": "text", "text": "Opening envelope sending form. Fill in the recipient details and click Send."},
        {
            "type": "resource",
            "resource": {"uri": WIDGET_URI, "mimeType": "text/html", "text": get_widget()},
            "annotations": {"audience": ["user"]},
            "metadata": {"structured_content": {"type": "form", "entity": "send_envelope"}},
        },
    ]


# ── Prompts ──────────────────────────────────────────────────────────────────

@mcp.prompt(
    name="docusign-overview",
    description="Explain what the DocuSign eSignature tools can do",
)
def overview_prompt() -> str:
    return (
        "You have access to DocuSign eSignature tools:\n"
        "• ds__get_envelopes — list envelopes with status filters\n"
        "• ds__get_envelope_details — view recipients and signing progress\n"
        "• ds__get_templates — list available signing templates\n"
        "• ds__send_envelope — send a new envelope using a template\n"
        "• ds__void_envelope — cancel an envelope\n"
        "• ds__resend_envelope — resend to pending signers\n"
        "• ds__get_signing_url — generate embedded signing URL\n"
        "• ds__download_document — download signed documents\n"
        "• ds__send_envelope_form — open interactive form to send envelope\n\n"
        "Typical workflows:\n"
        "1. Browse templates → send envelope → track status\n"
        "2. Check envelope details → resend to unsigned recipients\n"
        "3. Void an expired envelope → send replacement"
    )


# ── Server Startup ──────────────────────────────────────────────────────────

def main():
    import uvicorn

    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins.split(","),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "mcp-session-id"],
        allow_credentials=False,
    )
    log.info("starting_docusign_mcp", port=cfg.port, tools=9)
    uvicorn.run(app, host="0.0.0.0", port=cfg.port)


if __name__ == "__main__":
    main()
