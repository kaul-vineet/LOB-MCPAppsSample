"""DocuSign tool handlers, TOOL_SPECS, PROMPT_SPECS. No MCP bootstrap here."""
from __future__ import annotations

import structlog
from mcp import types

from .docusign_client import (
    MOCK_ENVELOPES,
    MOCK_TEMPLATES,
    ds_request,
    fetch_envelopes,
    is_mock,
    status_emoji,
)

log = structlog.get_logger("ds")


# ── Shared helpers ────────────────────────────────────────────────────────────

def _error_result(msg: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Error: {msg}")],
        structuredContent={"error": True, "message": msg},
    )


def _mock_envelope_rows(envelopes: list[dict]) -> list[dict]:
    return [
        {
            "envelopeId":        e["envelopeId"],
            "emailSubject":      e["emailSubject"],
            "status":            e["status"],
            "statusEmoji":       status_emoji(e["status"]),
            "sentDateTime":      e["sentDateTime"],
            "completedDateTime": e["completedDateTime"],
            "recipientCount":    2,
        }
        for e in envelopes
    ]


def _mock_list_response(rows: list[dict], label: str, data_type: str = "envelopes") -> types.CallToolResult:
    summary_lines = [f"[demo] Found {len(rows)} {label}."]
    for r in rows[:3]:
        summary_lines.append(
            f"  {r.get('statusEmoji', '')} {r.get('emailSubject', r.get('name', ''))} — {r.get('status', '')}"
        )
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(summary_lines))],
        structuredContent={"type": data_type, "total": len(rows), "items": rows},
    )


# ── Tool handlers ─────────────────────────────────────────────────────────────

async def ds__get_envelopes(
    from_date: str | None = None,
    status: str | None = None,
    count: int = 10,
) -> types.CallToolResult:
    if is_mock():
        filtered = [e for e in MOCK_ENVELOPES if not status or e["status"] == status]
        return _mock_list_response(_mock_envelope_rows(filtered[:count]), "envelope(s)", "envelopes")
    try:
        envelopes = await fetch_envelopes(from_date, status, count)
        rows = [
            {
                "envelopeId":        e.get("envelopeId", ""),
                "emailSubject":      e.get("emailSubject", ""),
                "status":            e.get("status", ""),
                "statusEmoji":       status_emoji(e.get("status", "")),
                "sentDateTime":      e.get("sentDateTime", ""),
                "completedDateTime": e.get("completedDateTime", ""),
                "recipientCount":    len(e.get("recipients", {}).get("signers", [])),
            }
            for e in envelopes
        ]
        summary = [f"Found {len(rows)} envelope(s)."] + [
            f"  {r['statusEmoji']} {r['emailSubject'][:50]} — {r['status']} ({r['envelopeId'][:8]}…)"
            for r in rows[:5]
        ]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="\n".join(summary))],
            structuredContent={"type": "envelopes", "total": len(rows), "items": rows},
        )
    except Exception as exc:
        log.error("ds__get_envelopes_failed", error=str(exc))
        return _error_result(str(exc))


async def ds__get_envelope_details(envelope_id: str) -> types.CallToolResult:
    if is_mock():
        env = next((e for e in MOCK_ENVELOPES if e["envelopeId"] == envelope_id), MOCK_ENVELOPES[0])
        detail = {
            **env,
            "statusEmoji": status_emoji(env["status"]),
            "signers": [
                {"name": "Alexandra Harrington", "email": "a.harrington@cloudbase.corp", "status": "completed", "signedDateTime": "2026-04-21T10:00:00Z", "deliveredDateTime": "2026-04-20T09:05:00Z"},
                {"name": "James Pemberton",       "email": "j.pemberton@gtc.internal",   "status": "completed", "signedDateTime": "2026-04-21T14:22:00Z", "deliveredDateTime": "2026-04-20T09:05:00Z"},
            ],
        }
        summary = (
            f"[demo] Envelope: {detail['emailSubject']}\n"
            f"Status: {detail['statusEmoji']} {detail['status']}\n"
            "Signers: 2\n  • Alexandra Harrington — completed\n  • James Pemberton — completed"
        )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=summary)],
            structuredContent={"type": "envelope_detail", "items": [detail]},
        )
    try:
        envelope = await ds_request("GET", f"/envelopes/{envelope_id}")
        recipients = await ds_request("GET", f"/envelopes/{envelope_id}/recipients")
        signers = [
            {
                "name":              s.get("name", ""),
                "email":             s.get("email", ""),
                "status":            s.get("status", ""),
                "signedDateTime":    s.get("signedDateTime", ""),
                "deliveredDateTime": s.get("deliveredDateTime", ""),
            }
            for s in recipients.get("signers", [])
        ]
        detail = {
            "envelopeId":        envelope.get("envelopeId", ""),
            "emailSubject":      envelope.get("emailSubject", ""),
            "status":            envelope.get("status", ""),
            "statusEmoji":       status_emoji(envelope.get("status", "")),
            "sentDateTime":      envelope.get("sentDateTime", ""),
            "completedDateTime": envelope.get("completedDateTime", ""),
            "signers":           signers,
        }
        summary = (
            f"Envelope: {detail['emailSubject']}\n"
            f"Status: {detail['statusEmoji']} {detail['status']}\n"
            f"Signers: {len(signers)}"
        ) + "".join(f"\n  • {s['name']} ({s['email']}) — {s['status']}" for s in signers)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=summary)],
            structuredContent={"type": "envelope_detail", "items": [detail]},
        )
    except Exception as exc:
        log.error("ds__get_envelope_details_failed", error=str(exc))
        return _error_result(str(exc))


async def ds__get_templates(count: int = 10) -> types.CallToolResult:
    if is_mock():
        rows = MOCK_TEMPLATES[:count]
        lines = [f"[demo] Found {len(rows)} template(s)."] + [f"  {r['name']} ({r['templateId']})" for r in rows]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="\n".join(lines))],
            structuredContent={"type": "templates", "total": len(rows), "items": rows},
        )
    try:
        data = await ds_request("GET", "/templates", params={"count": str(count)})
        templates = data.get("envelopeTemplates", []) if isinstance(data, dict) else []
        rows = [
            {
                "templateId":   t.get("templateId", ""),
                "name":         t.get("name", ""),
                "description":  t.get("description", ""),
                "lastModified": t.get("lastModified", ""),
                "folderName":   t.get("folderName", ""),
            }
            for t in templates
        ]
        summary = [f"Found {len(rows)} template(s)."] + [f"  📋 {r['name']} ({r['templateId'][:8]}…)" for r in rows[:5]]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="\n".join(summary))],
            structuredContent={"type": "templates", "total": len(rows), "items": rows},
        )
    except Exception as exc:
        log.error("ds__get_templates_failed", error=str(exc))
        return _error_result(str(exc))


async def ds__send_envelope(
    template_id: str,
    subject: str,
    signers: list[dict],
    email_body: str = "Please sign this document.",
) -> types.CallToolResult:
    if is_mock():
        mock_id = "env-demo-new"
        rows = _mock_envelope_rows(
            [{"envelopeId": mock_id, "emailSubject": subject, "status": "sent", "sentDateTime": "2026-04-22T14:00:00Z", "completedDateTime": ""}]
            + MOCK_ENVELOPES[:4]
        )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"[demo] Envelope sent. ID: {mock_id}, Status: sent")],
            structuredContent={"type": "envelopes", "total": len(rows), "items": rows, "_createdId": mock_id},
        )
    try:
        body = {
            "templateId":     template_id,
            "templateRoles":  [{"name": s.get("name", ""), "email": s.get("email", ""), "roleName": s.get("role_name", "Signer")} for s in signers],
            "emailSubject":   subject,
            "emailBlurb":     email_body,
            "status":         "sent",
        }
        result = await ds_request("POST", "/envelopes", json_body=body)
        env_id = result.get("envelopeId", "unknown")
        envelopes = await fetch_envelopes(count=5)
        rows = [
            {
                "envelopeId":   e.get("envelopeId", ""),
                "emailSubject": e.get("emailSubject", ""),
                "status":       e.get("status", ""),
                "statusEmoji":  status_emoji(e.get("status", "")),
                "sentDateTime": e.get("sentDateTime", ""),
            }
            for e in envelopes
        ]
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Envelope sent. ID: {env_id}, Status: {result.get('status', '')}")],
            structuredContent={"type": "envelopes", "total": len(rows), "items": rows, "_createdId": env_id},
        )
    except Exception as exc:
        log.error("ds__send_envelope_failed", error=str(exc))
        return _error_result(str(exc))


async def ds__void_envelope(envelope_id: str, void_reason: str) -> types.CallToolResult:
    if is_mock():
        msg = f"[demo] Envelope {envelope_id} voided. Reason: {void_reason}"
    else:
        try:
            await ds_request("PUT", f"/envelopes/{envelope_id}", json_body={"status": "voided", "voidedReason": void_reason})
            msg = f"Envelope {envelope_id} voided. Reason: {void_reason}"
        except Exception as exc:
            log.error("ds__void_envelope_failed", error=str(exc))
            return _error_result(str(exc))
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=msg)],
        structuredContent={"type": "action_result", "action": "void", "envelopeId": envelope_id, "message": msg},
    )


async def ds__resend_envelope(envelope_id: str) -> types.CallToolResult:
    if is_mock():
        msg = f"[demo] Envelope {envelope_id} resent to pending recipients."
    else:
        try:
            await ds_request("PUT", f"/envelopes/{envelope_id}", json_body={"resend_envelope": "true"})
            msg = f"Envelope {envelope_id} resent to pending recipients."
        except Exception as exc:
            log.error("ds__resend_envelope_failed", error=str(exc))
            return _error_result(str(exc))
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=msg)],
        structuredContent={"type": "action_result", "action": "resend", "envelopeId": envelope_id, "message": msg},
    )


async def ds__get_signing_url(
    envelope_id: str,
    signer_name: str,
    signer_email: str,
    return_url: str = "https://example.com/signing-complete",
) -> types.CallToolResult:
    if is_mock():
        url = f"https://demo.docusign.net/signing/mock?env={envelope_id}"
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"[demo] Signing URL for {signer_name}: {url}")],
            structuredContent={"type": "signing_url", "signerName": signer_name, "url": url},
        )
    try:
        result = await ds_request(
            "POST",
            f"/envelopes/{envelope_id}/views/recipient",
            json_body={"returnUrl": return_url, "authenticationMethod": "none", "email": signer_email, "userName": signer_name},
        )
        signing_url = result.get("url", "")
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Signing URL for {signer_name}: {signing_url}")],
            structuredContent={"type": "signing_url", "signerName": signer_name, "url": signing_url},
        )
    except Exception as exc:
        log.error("ds__get_signing_url_failed", error=str(exc))
        return _error_result(str(exc))


async def ds__download_document(envelope_id: str, document_id: str = "combined") -> types.CallToolResult:
    if is_mock():
        msg = f"[demo] Downloaded document '{document_id}' from envelope {envelope_id} (42.3 KB). Binary content available."
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=msg)],
            structuredContent={"type": "document_download", "envelopeId": envelope_id, "documentId": document_id, "sizeKb": 42.3},
        )
    try:
        content = await ds_request("GET", f"/envelopes/{envelope_id}/documents/{document_id}")
        if isinstance(content, bytes):
            size_kb = len(content) / 1024
            msg = f"Downloaded document '{document_id}' from envelope {envelope_id} ({size_kb:.1f} KB). Binary content available."
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=msg)],
                structuredContent={"type": "document_download", "envelopeId": envelope_id, "documentId": document_id, "sizeKb": round(size_kb, 1)},
            )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="Document downloaded (unexpected format).")],
            structuredContent={"type": "document_download", "envelopeId": envelope_id, "documentId": document_id},
        )
    except Exception as exc:
        log.error("ds__download_document_failed", error=str(exc))
        return _error_result(str(exc))


async def ds__send_envelope_form() -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Opening envelope sending form. Fill in the recipient details and click Send.")],
        structuredContent={"type": "form", "entity": "send_envelope"},
    )


# ── Prompt handlers ───────────────────────────────────────────────────────────

def docusign_overview_prompt() -> str:
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


# ── Registries ────────────────────────────────────────────────────────────────

TOOL_SPECS = [
    {
        "name": "ds__get_envelopes",
        "description": (
            "Get the latest envelopes from DocuSign. "
            "Optional filters: from_date (ISO 8601), status (sent|delivered|completed|declined|voided), count (default 10)."
        ),
        "handler": ds__get_envelopes,
    },
    {
        "name": "ds__get_envelope_details",
        "description": "Get detailed information about a specific envelope including recipients and their signing status.",
        "handler": ds__get_envelope_details,
    },
    {
        "name": "ds__get_templates",
        "description": "List available DocuSign templates. Returns template name, description, and ID.",
        "handler": ds__get_templates,
    },
    {
        "name": "ds__send_envelope",
        "description": (
            "Send a new envelope for signing. Requires template_id, subject, and signers "
            "(list of {name, email, role_name}). Returns envelope ID and status."
        ),
        "handler": ds__send_envelope,
    },
    {
        "name": "ds__void_envelope",
        "description": "Void (cancel) an envelope. Requires envelope_id and void_reason.",
        "handler": ds__void_envelope,
    },
    {
        "name": "ds__resend_envelope",
        "description": "Resend notifications for an envelope to recipients who haven't signed yet.",
        "handler": ds__resend_envelope,
    },
    {
        "name": "ds__get_signing_url",
        "description": (
            "Generate an embedded signing URL for a recipient. "
            "Requires envelope_id, signer_name, signer_email, and a return_url."
        ),
        "handler": ds__get_signing_url,
    },
    {
        "name": "ds__download_document",
        "description": (
            "Download a document from an envelope. "
            "Pass document_id='combined' for all documents as one PDF."
        ),
        "handler": ds__download_document,
    },
    {
        "name": "ds__send_envelope_form",
        "description": "Opens a form to send a new DocuSign envelope. The user fills in recipient details and submits.",
        "handler": ds__send_envelope_form,
    },
]

PROMPT_SPECS = [
    {
        "name": "docusign-overview",
        "description": "Explain what the DocuSign eSignature tools can do",
        "handler": docusign_overview_prompt,
    },
]
