"""
Salesforce REST API client using OAuth2 client_credentials flow.

All Salesforce interactions are encapsulated here — the MCP server
delegates to this module for authentication, queries, and mutations.
"""

import os
import time
from typing import Any

import httpx

# Salesforce REST API version
SF_API_VERSION = "v62.0"


class SalesforceAuthError(Exception):
    """Raised when Salesforce authentication fails."""


class SalesforceAPIError(Exception):
    """Raised when a Salesforce API call fails."""

    def __init__(self, message: str, status_code: int | None = None, sf_errors: list | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.sf_errors = sf_errors or []


class SalesforceClient:
    """Async Salesforce REST API client with token caching."""

    def __init__(self) -> None:
        self.instance_url = os.environ.get("SF_INSTANCE_URL", "").rstrip("/")
        self.client_id = os.environ.get("SF_CLIENT_ID", "")
        self.client_secret = os.environ.get("SF_CLIENT_SECRET", "")

        if not all([self.instance_url, self.client_id, self.client_secret]):
            raise SalesforceAuthError(
                "Missing Salesforce credentials. Set SF_INSTANCE_URL, SF_CLIENT_ID, "
                "and SF_CLIENT_SECRET in your .env file."
            )

        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def _base_url(self) -> str:
        return f"{self.instance_url}/services/data/{SF_API_VERSION}"

    async def _authenticate(self) -> str:
        """
        Obtain an access token via OAuth2 client_credentials grant.
        Caches the token until 5 minutes before expiry.
        """
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        token_url = f"{self.instance_url}/services/oauth2/token"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
        except httpx.RequestError as exc:
            raise SalesforceAuthError(
                f"Network error connecting to Salesforce token endpoint: {exc}"
            ) from exc

        if resp.status_code != 200:
            detail = resp.text[:500]
            raise SalesforceAuthError(
                f"Salesforce auth failed (HTTP {resp.status_code}): {detail}"
            )

        data = resp.json()
        self._access_token = data["access_token"]
        # Default session timeout is 2 hours; refresh 5 minutes early
        self._token_expires_at = time.time() + 7200 - 300
        return self._access_token

    async def _headers(self) -> dict[str, str]:
        token = await self._authenticate()
        return {
            "Authorization": f"Bearer {token}",
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
        """Execute an authenticated request to Salesforce REST API."""
        headers = await self._headers()
        url = f"{self._base_url}{path}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                )
        except httpx.RequestError as exc:
            raise SalesforceAPIError(
                f"Network error calling Salesforce API ({method} {path}): {exc}"
            ) from exc

        # Handle 401 (expired token) — retry once with fresh token
        if resp.status_code == 401:
            self._access_token = None
            headers = await self._headers()
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        json=json_body,
                    )
            except httpx.RequestError as exc:
                raise SalesforceAPIError(
                    f"Network error on retry ({method} {path}): {exc}"
                ) from exc

        return resp

    def _raise_for_error(self, resp: httpx.Response, context: str) -> None:
        """Raise SalesforceAPIError if the response indicates failure."""
        if resp.is_success:
            return

        try:
            errors = resp.json()
            if isinstance(errors, list):
                messages = [e.get("message", str(e)) for e in errors]
            else:
                messages = [errors.get("message", str(errors))]
        except Exception:
            messages = [resp.text[:500]]

        raise SalesforceAPIError(
            f"Salesforce API error ({context}, HTTP {resp.status_code}): "
            + "; ".join(messages),
            status_code=resp.status_code,
            sf_errors=messages,
        )

    # ── SOQL Query ────────────────────────────────────────────────────────────

    async def query(self, soql: str) -> list[dict[str, Any]]:
        """Execute a SOQL query and return the records."""
        resp = await self._request("GET", "/query", params={"q": soql})
        self._raise_for_error(resp, f"query: {soql[:80]}")

        data = resp.json()
        records = data.get("records", [])

        # Strip Salesforce metadata from each record
        for record in records:
            record.pop("attributes", None)
            # Flatten nested relationship objects (e.g., Account.Name)
            for key, value in list(record.items()):
                if isinstance(value, dict) and "attributes" in value:
                    value.pop("attributes", None)

        return records

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(self, sobject: str, data: dict[str, Any]) -> str:
        """
        Create a new Salesforce record.
        Returns the new record's Id.
        """
        resp = await self._request("POST", f"/sobjects/{sobject}", json_body=data)
        self._raise_for_error(resp, f"create {sobject}")

        result = resp.json()
        if not result.get("success"):
            errors = result.get("errors", [])
            raise SalesforceAPIError(
                f"Create {sobject} failed: {errors}",
                sf_errors=[str(e) for e in errors],
            )

        return result["id"]

    # ── Update ────────────────────────────────────────────────────────────────

    async def update(self, sobject: str, record_id: str, data: dict[str, Any]) -> None:
        """Update an existing Salesforce record by Id."""
        resp = await self._request(
            "PATCH",
            f"/sobjects/{sobject}/{record_id}",
            json_body=data,
        )
        self._raise_for_error(resp, f"update {sobject}/{record_id}")


# ── Module-level singleton ────────────────────────────────────────────────────
# Lazily initialised so the module can be imported before env vars are loaded.

_client: SalesforceClient | None = None


def get_client() -> SalesforceClient:
    """Return the shared SalesforceClient instance, creating it on first call."""
    global _client
    if _client is None:
        _client = SalesforceClient()
    return _client
