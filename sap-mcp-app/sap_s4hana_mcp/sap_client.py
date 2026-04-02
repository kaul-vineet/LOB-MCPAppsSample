"""
SAP S/4HANA OData API client with sandbox / tenant dual-mode support.

All SAP interactions are encapsulated here — the MCP server
delegates to this module for queries and mutations.
"""

import base64
import os
import time
from typing import Any

import httpx

# SAP API Hub sandbox base
_SANDBOX_BASE = "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap"


class SAPAuthError(Exception):
    """Raised when SAP authentication fails."""


class SAPAPIError(Exception):
    """Raised when an SAP OData API call fails."""

    def __init__(self, message: str, status_code: int | None = None, details: list | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or []


class SAPClient:
    """Async SAP S/4HANA OData client with sandbox and tenant modes."""

    def __init__(self) -> None:
        self._mode = os.environ.get("SAP_MODE", "sandbox").lower()

        if self._mode == "sandbox":
            self._api_key = os.environ.get("SAP_API_KEY", "")
            if not self._api_key:
                raise SAPAuthError(
                    "Missing SAP_API_KEY. Set it in your .env file for sandbox mode."
                )
            self._base_url = _SANDBOX_BASE
        else:
            tenant_url = os.environ.get("SAP_TENANT_URL", "").rstrip("/")
            self._username = os.environ.get("SAP_USERNAME", "")
            self._password = os.environ.get("SAP_PASSWORD", "")
            if not all([tenant_url, self._username, self._password]):
                raise SAPAuthError(
                    "Missing SAP tenant credentials. Set SAP_TENANT_URL, "
                    "SAP_USERNAME, and SAP_PASSWORD in your .env file."
                )
            self._base_url = f"{tenant_url}/sap/opu/odata/sap"

    @property
    def is_sandbox(self) -> bool:
        return self._mode == "sandbox"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.is_sandbox:
            headers["apikey"] = self._api_key
        else:
            creds = base64.b64encode(
                f"{self._username}:{self._password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {creds}"
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> httpx.Response:
        """Execute an authenticated request to the SAP OData API."""
        headers = self._headers()
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
            raise SAPAPIError(
                f"Network error calling SAP API ({method} {path}): {exc}"
            ) from exc

        return resp

    def _raise_for_error(self, resp: httpx.Response, context: str) -> None:
        """Raise SAPAPIError if the response indicates failure."""
        if resp.is_success:
            return

        try:
            body = resp.json()
            error = body.get("error", {})
            message = error.get("message", {}).get("value", resp.text[:500])
        except Exception:
            message = resp.text[:500]

        raise SAPAPIError(
            f"SAP API error ({context}, HTTP {resp.status_code}): {message}",
            status_code=resp.status_code,
            details=[message],
        )

    # ── Query (collection) ────────────────────────────────────────────────────

    async def query(
        self,
        service: str,
        entity: str,
        params: dict | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Execute an OData query and return the result records."""
        query_params: dict[str, str] = {
            "$top": str(limit),
            "$orderby": "CreationDate desc",
            "$format": "json",
        }
        if params:
            query_params.update(params)

        resp = await self._request(
            "GET",
            f"/{service}/{entity}",
            params=query_params,
        )
        self._raise_for_error(resp, f"query {service}/{entity}")

        data = resp.json()
        return data.get("d", {}).get("results", [])

    # ── Get single entity ─────────────────────────────────────────────────────

    async def get_entity(
        self,
        service: str,
        entity: str,
        key: str,
    ) -> dict[str, Any]:
        """Fetch a single entity by its key."""
        resp = await self._request(
            "GET",
            f"/{service}/{entity}('{key}')",
            params={"$format": "json"},
        )
        self._raise_for_error(resp, f"get {service}/{entity}('{key}')")

        data = resp.json()
        return data.get("d", {})

    # ── Create entity ─────────────────────────────────────────────────────────

    async def create_entity(
        self,
        service: str,
        entity: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create a new entity.
        In sandbox mode returns mock data; in tenant mode POSTs to the API.
        """
        if self.is_sandbox:
            mock_id = f"MOCK-PO-{int(time.time())}"
            print(f"[sandbox] Mock create {service}/{entity} → {mock_id}")
            return {"id": mock_id, **data}

        resp = await self._request(
            "POST",
            f"/{service}/{entity}",
            json_body=data,
        )
        self._raise_for_error(resp, f"create {service}/{entity}")
        return resp.json().get("d", {})

    # ── Update entity ─────────────────────────────────────────────────────────

    async def update_entity(
        self,
        service: str,
        entity: str,
        key: str,
        data: dict[str, Any],
    ) -> None:
        """
        Update an entity by key.
        In sandbox mode this is a no-op; in tenant mode PATCHes the API.
        """
        if self.is_sandbox:
            print(f"[sandbox] Mock update {service}/{entity}('{key}'): {data}")
            return

        resp = await self._request(
            "PATCH",
            f"/{service}/{entity}('{key}')",
            json_body=data,
        )
        self._raise_for_error(resp, f"update {service}/{entity}('{key}')")


# ── Module-level singleton ────────────────────────────────────────────────────
# Lazily initialised so the module can be imported before env vars are loaded.

_client: SAPClient | None = None


def get_client() -> SAPClient:
    """Return the shared SAPClient instance, creating it on first call."""
    global _client
    if _client is None:
        _client = SAPClient()
    return _client
