"""
HubSpot CRM REST API client using Private App Token authentication.

All HubSpot interactions are encapsulated here — the MCP server
delegates to this module for authentication, queries, and mutations.
"""

import os
from typing import Any

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

log = structlog.get_logger("hs.client")

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

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
        reraise=True,
    )
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

    # ── Update Marketing Email ────────────────────────────────────────────────

    async def update_email(self, email_id: str, data: dict) -> None:
        """Update a marketing email's properties."""
        resp = await self._request(
            "PATCH",
            f"/marketing/v3/emails/{email_id}",
            json_body=data,
        )
        self._raise_for_error(resp, f"update email {email_id}")

    # ── Update List Name ──────────────────────────────────────────────────────

    async def update_list(self, list_id: str, name: str) -> None:
        """Update a list's name."""
        resp = await self._request(
            "PUT",
            f"/crm/v3/lists/{list_id}/update-list-name",
            json_body={"name": name},
        )
        self._raise_for_error(resp, f"update list {list_id}")

    # ── Lists ─────────────────────────────────────────────────────────────────

    async def list_lists(self, limit: int = 10) -> list[dict]:
        """Fetch contact lists."""
        resp = await self._request("GET", "/crm/v3/lists", params={
            "includeFilters": "false",
        })
        self._raise_for_error(resp, "list lists")
        data = resp.json()
        results = data.get("lists", [])[:limit]
        return results

    async def get_list_memberships(self, list_id: str, limit: int = 10) -> list[str]:
        """Fetch record IDs in a list."""
        resp = await self._request(
            "GET",
            f"/crm/v3/lists/{list_id}/memberships",
        )
        self._raise_for_error(resp, f"list memberships {list_id}")
        data = resp.json()
        return data.get("results", [])[:limit]

    async def get_contacts_by_ids(self, contact_ids: list[str]) -> list[dict]:
        """Batch fetch contacts by their IDs."""
        if not contact_ids:
            return []
        resp = await self._request(
            "POST",
            "/crm/v3/objects/contacts/batch/read",
            json_body={
                "inputs": [{"id": cid} for cid in contact_ids],
                "properties": ["firstname", "lastname", "email", "phone", "company", "lifecyclestage"],
            },
        )
        self._raise_for_error(resp, "batch read contacts")
        data = resp.json()
        return data.get("results", [])

    async def add_to_list(self, list_id: str, record_ids: list[str]) -> None:
        """Add records to a static list."""
        resp = await self._request(
            "PUT",
            f"/crm/v3/lists/{list_id}/memberships/add",
            json_body=record_ids,
        )
        self._raise_for_error(resp, f"add to list {list_id}")

    async def remove_from_list(self, list_id: str, record_ids: list[str]) -> None:
        """Remove records from a static list."""
        resp = await self._request(
            "PUT",
            f"/crm/v3/lists/{list_id}/memberships/remove",
            json_body=record_ids,
        )
        self._raise_for_error(resp, f"remove from list {list_id}")

    async def get_associated_ids(
        self,
        from_type: str,
        from_id: str,
        to_type: str,
        limit: int = 10,
    ) -> list[str]:
        """Fetch associated record IDs via the HubSpot v4 Associations API."""
        resp = await self._request(
            "GET",
            f"/crm/v4/objects/{from_type}/{from_id}/associations/{to_type}",
        )
        self._raise_for_error(resp, f"associations {from_type}/{from_id}/{to_type}")
        results = resp.json().get("results", [])[:limit]
        return [str(r["toObjectId"]) for r in results]

    async def search_contact_by_email(self, email: str) -> str | None:
        """Search for a contact by email and return their ID."""
        resp = await self._request(
            "POST",
            "/crm/v3/objects/contacts/search",
            json_body={
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email,
                    }]
                }],
                "properties": ["email"],
                "limit": 1,
            },
        )
        self._raise_for_error(resp, "search contact by email")
        data = resp.json()
        results = data.get("results", [])
        return results[0]["id"] if results else None


# ── Module-level singleton ────────────────────────────────────────────────────
# Lazily initialised so the module can be imported before env vars are loaded.

_client: HubSpotClient | None = None


def get_client() -> HubSpotClient:
    """Return the shared HubSpotClient instance, creating it on first call."""
    global _client
    if _client is None:
        _client = HubSpotClient()
    return _client
