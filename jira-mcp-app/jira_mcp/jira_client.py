"""Jira REST API v3 HTTP client, data helpers, and provider functions."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from mcp.server.fastmcp import Context

from shared_mcp.auth import get_bearer_token
from shared_mcp.http import create_async_client
from shared_mcp.logger import get_logger
from shared_mcp.settings import load_jira_settings

LOGGER = get_logger(__name__)

# ── HTTP helpers ─────────────────────────────────────────────────────

async def _jira_get(
    path: str, ctx: Optional[Context] = None, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    settings = load_jira_settings()
    url = f"{settings.base_url.rstrip('/')}/rest/api/3{path}"
    headers = {
        "Authorization": f"Bearer {get_bearer_token(ctx)}",
        "Accept": "application/json",
    }
    async with create_async_client() as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def _jira_post(path: str, body: Dict[str, Any], ctx: Optional[Context] = None) -> Dict[str, Any]:
    settings = load_jira_settings()
    url = f"{settings.base_url.rstrip('/')}/rest/api/3{path}"
    headers = {
        "Authorization": f"Bearer {get_bearer_token(ctx)}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    async with create_async_client() as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type and resp.content:
            return resp.json()
        return {"status": "ok"}


async def _jira_put(path: str, body: Dict[str, Any], ctx: Optional[Context] = None) -> Dict[str, Any]:
    settings = load_jira_settings()
    url = f"{settings.base_url.rstrip('/')}/rest/api/3{path}"
    headers = {
        "Authorization": f"Bearer {get_bearer_token(ctx)}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    async with create_async_client() as client:
        resp = await client.put(url, json=body, headers=headers)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type and resp.content:
            return resp.json()
        return {"status": "ok"}


async def _jira_search(
    jql: str, max_results: int = 50, fields: Optional[str] = None, ctx: Optional[Context] = None
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"jql": jql, "maxResults": max_results}
    if fields:
        body["fields"] = [f.strip() for f in fields.split(",")]
    return await _jira_post("/search/jql", body, ctx)


async def _jira_agile_get(
    path: str, ctx: Optional[Context] = None, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    settings = load_jira_settings()
    url = f"{settings.base_url.rstrip('/')}/rest/agile/1.0{path}"
    headers = {
        "Authorization": f"Bearer {get_bearer_token(ctx)}",
        "Accept": "application/json",
    }
    async with create_async_client() as client:
        resp = await client.get(url, params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


# ── Data helpers ─────────────────────────────────────────────────────

_SEARCH_FIELDS = (
    "summary,status,priority,assignee,reporter,issuetype,"
    "project,created,updated,duedate,labels,description"
)


def _simplify_issue(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten a Jira issue into a concise dict."""
    fields = raw.get("fields", {})
    status = fields.get("status", {})
    priority = fields.get("priority", {})
    assignee = fields.get("assignee") or {}
    reporter = fields.get("reporter") or {}
    issue_type = fields.get("issuetype", {})
    project = fields.get("project", {})

    return {
        "key": raw.get("key"),
        "id": raw.get("id"),
        "summary": fields.get("summary"),
        "description": fields.get("description"),
        "status": status.get("name") if isinstance(status, dict) else status,
        "priority": priority.get("name") if isinstance(priority, dict) else priority,
        "assignee": assignee.get("displayName") if isinstance(assignee, dict) else None,
        "reporter": reporter.get("displayName") if isinstance(reporter, dict) else None,
        "issueType": issue_type.get("name") if isinstance(issue_type, dict) else issue_type,
        "project": project.get("name") if isinstance(project, dict) else project,
        "projectKey": project.get("key") if isinstance(project, dict) else None,
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "duedate": fields.get("duedate"),
        "labels": fields.get("labels", []),
    }


def _extract_adf_text(body: Any) -> str:
    """Extract plain text from Jira ADF (Atlassian Document Format)."""
    if isinstance(body, str):
        return body
    if not isinstance(body, dict):
        return ""
    parts: List[str] = []
    for content_block in body.get("content", []):
        for inline in content_block.get("content", []):
            if inline.get("type") == "text":
                parts.append(inline.get("text", ""))
    return "".join(parts)


def _build_adf(text: str) -> Dict[str, Any]:
    """Build a simple ADF document from plain text."""
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


# ── Provider function for TaskServer integration ─────────────────────

async def provider_list_tasks(ctx: Optional[Context] = None) -> List[Dict[str, Any]]:
    """List Jira issues assigned to the configured user."""
    try:
        load_jira_settings()
    except Exception:  # noqa: BLE001
        LOGGER.debug("jira_settings_not_configured")
        return []

    data = await _jira_search(
        jql="assignee = currentUser() ORDER BY updated DESC",
        max_results=50,
        fields=_SEARCH_FIELDS,
        ctx=ctx,
    )
    return data.get("issues", [])
