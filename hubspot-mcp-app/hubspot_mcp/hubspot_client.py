"""
HubSpot CRM REST API client using Private App Token authentication.

All HubSpot interactions are encapsulated here — the MCP server
delegates to this module for authentication, queries, and mutations.
"""

import os
from typing import Any

import httpx

# HubSpot CRM API base URL
HUBSPOT_BASE_URL = "https://api.hubapi.com"


class HubSpotAuthError(Exception):
    """Raised when HubSpot authentication fails."""


class HubSpotAPIError(Exception):
    """Raised when a HubSpot API call fails."""

    def __init__(self, message: str, status_code: int | None = None, hs_errors: list | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.hs_errors = hs_errors or []


class HubSpotClient:
    """Async HubSpot CRM API client with Bearer token auth."""

    def __init__(self) -> None:
        self.access_token = os.environ.get("HUBSPOT_ACCESS_TOKEN", "")

        if not self.access_token:
            raise HubSpotAuthError(
                "Missing HubSpot credentials. Set HUBSPOT_ACCESS_TOKEN in your .env file."
            )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> httpx.Response:
        """Execute an authenticated request to HubSpot CRM API."""
        url = f"{HUBSPOT_BASE_URL}{path}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(
                    method,
                    url,
                    headers=self._headers,
                    params=params,
                    json=json_body,
                )
        except httpx.RequestError as exc:
            raise HubSpotAPIError(
                f"Network error calling HubSpot API ({method} {path}): {exc}"
            ) from exc

        # Handle 401 (invalid or expired token)
        if resp.status_code == 401:
            raise HubSpotAuthError(
                "HubSpot authentication failed: invalid or expired access token."
            )

        return resp

    def _raise_for_error(self, resp: httpx.Response, context: str) -> None:
        """Raise HubSpotAPIError if the response indicates failure."""
        if resp.is_success:
            return

        try:
            body = resp.json()
            message = body.get("message", str(body))
            messages = [message]
        except Exception:
            messages = [resp.text[:500]]

        raise HubSpotAPIError(
            f"HubSpot API error ({context}, HTTP {resp.status_code}): "
            + "; ".join(messages),
            status_code=resp.status_code,
            hs_errors=messages,
        )

    # ── List Objects (via Search endpoint for sorting) ─────────────────────────

    async def list_objects(
        self,
        object_type: str,
        properties: list[str],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Fetch recent records of the given object type using the Search API.
        Sorted by createdate descending.
        """
        body = {
            "sorts": [{"propertyName": "createdate", "direction": "DESCENDING"}],
            "properties": properties,
            "limit": limit,
        }
        resp = await self._request(
            "POST",
            f"/crm/v3/objects/{object_type}/search",
            json_body=body,
        )
        self._raise_for_error(resp, f"list {object_type}")

        data = resp.json()
        results = data.get("results", [])

        # Return flattened properties with id
        return [
            {"id": r["id"], **r.get("properties", {})}
            for r in results
        ]

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_object(
        self,
        object_type: str,
        properties: dict[str, Any],
    ) -> str:
        """
        Create a new HubSpot CRM record.
        Returns the new record's id.
        """
        resp = await self._request(
            "POST",
            f"/crm/v3/objects/{object_type}",
            json_body={"properties": properties},
        )
        self._raise_for_error(resp, f"create {object_type}")

        result = resp.json()
        return result["id"]

    # ── Marketing Emails ─────────────────────────────────────────────────────

    async def list_emails(self, limit: int = 5) -> list[dict]:
        """Fetch marketing emails with stats."""
        resp = await self._request("GET", "/marketing/v3/emails", params={
            "limit": limit,
            "orderBy": "-updated",
        })
        self._raise_for_error(resp, "list emails")
        data = resp.json()
        return data.get("results", [])

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_object(
        self,
        object_type: str,
        object_id: str,
        properties: dict[str, Any],
    ) -> None:
        """Update an existing HubSpot CRM record by id."""
        resp = await self._request(
            "PATCH",
            f"/crm/v3/objects/{object_type}/{object_id}",
            json_body={"properties": properties},
        )
        self._raise_for_error(resp, f"update {object_type}/{object_id}")


# ── Module-level singleton ────────────────────────────────────────────────────
# Lazily initialised so the module can be imported before env vars are loaded.

_client: HubSpotClient | None = None


def get_client() -> HubSpotClient:
    """Return the shared HubSpotClient instance, creating it on first call."""
    global _client
    if _client is None:
        _client = HubSpotClient()
    return _client
