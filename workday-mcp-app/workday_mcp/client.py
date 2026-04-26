"""Workday HR API client — endpoints, worker context, and HTTP helpers."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from mcp.server.fastmcp import Context
from pydantic import BaseModel

from shared_mcp.auth import get_bearer_token
from shared_mcp.http import create_async_client
from shared_mcp.logger import get_logger
from shared_mcp.settings import load_workday_settings

LOGGER = get_logger(__name__)


# ── API Endpoints ────────────────────────────────────────────────────

class WorkdayApiEndpoints(BaseModel):
    tenant: str
    base_url: str
    skills_report: str
    learning_report: str

    def full_url(self, path_template: str, **kwargs: str) -> str:
        path = path_template.format(tenant=self.tenant, **kwargs)
        return f"{self.base_url}{path}"

    def skills_report_url(self) -> str:
        return (
            f"{self.base_url}/ccx/service/customreport2/{self.tenant}"
            f"/{self.skills_report}?format=json"
        )

    def learning_report_url(self, workday_id: str) -> str:
        return (
            f"{self.base_url}/ccx/service/customreport2/{self.tenant}"
            f"/{self.learning_report}"
            f"?Worker_s__for_Learning_Assignment%21WID={workday_id}&format=json"
        )


@lru_cache(maxsize=1)
def get_endpoints() -> WorkdayApiEndpoints:
    settings = load_workday_settings()
    return WorkdayApiEndpoints(
        tenant=settings.tenant,
        base_url=settings.base_url,
        skills_report=settings.skills_report,
        learning_report=settings.learning_report,
    )


# ── Worker context ───────────────────────────────────────────────────

@dataclass
class WorkerContext:
    payload: Dict[str, Any]
    worker_id: str
    workday_id: str
    workday_access_token: str
    worker_data: Dict[str, Any]


async def build_worker_context_from_bearer(token: str) -> WorkerContext:
    """Build worker context using /workers/me then enriching via the staffing API."""
    endpoints = get_endpoints()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    me_url = endpoints.full_url("/ccx/api/common/v1/{tenant}/workers/me")
    LOGGER.info("resolving_worker_via_me", url=me_url)
    async with create_async_client() as client:
        response = await client.get(me_url, headers=headers)
        response.raise_for_status()
        me_data = response.json()

    workday_id = me_data.get("id", "")
    LOGGER.info("resolved_worker_via_me", workday_id=workday_id)

    staffing_url = endpoints.full_url(
        "/ccx/api/staffing/v4/{tenant}/workers/{workday_id}",
        workday_id=workday_id,
    )
    LOGGER.info("enriching_worker_from_staffing", url=staffing_url)
    async with create_async_client() as client:
        staffing_resp = await client.get(staffing_url, headers=headers)
        if staffing_resp.is_success:
            worker_data = staffing_resp.json()
            for key in (
                "isManager", "yearsOfService", "primaryWorkAddressText",
                "primaryWorkEmail", "primarySupervisoryOrganization",
                "supervisoryOrganizationsManaged",
            ):
                if key in me_data and key not in worker_data:
                    worker_data[key] = me_data[key]
            LOGGER.info("enriched_worker_from_staffing", keys=list(worker_data.keys()))
        else:
            LOGGER.warning(
                "staffing_enrichment_failed",
                status=staffing_resp.status_code,
                fallback="using /workers/me data",
            )
            worker_data = me_data

    worker_id = worker_data.get("workerId", workday_id)
    return WorkerContext(
        payload={},
        worker_id=worker_id,
        workday_id=workday_id,
        workday_access_token=token,
        worker_data=worker_data,
    )


# ── HTTP infrastructure ──────────────────────────────────────────────

class WorkdayApiNotAvailable(Exception):
    """Raised when a Workday REST API returns 404 (not enabled for this tenant)."""

    def __init__(self, api_name: str, status_code: int, detail: str = ""):
        self.api_name = api_name
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{api_name} API is not available for this Workday tenant: {detail}")


def _get_auth_token(ctx: Optional[Context] = None) -> str:
    return get_bearer_token(ctx)


def _transform_worker(worker_data: Dict[str, Any]) -> Dict[str, Any]:
    primary_job = worker_data.get("primaryJob", {})
    location = primary_job.get("location", {})
    country = location.get("country", {})

    return {
        "workdayId": worker_data.get("id"),
        "workerId": worker_data.get("workerId"),
        "name": worker_data.get("descriptor"),
        "email": worker_data.get("person", {}).get("email")
            or worker_data.get("primaryWorkEmail"),
        "workerType": worker_data.get("workerType", {}).get("descriptor"),
        "businessTitle": primary_job.get("businessTitle")
            or worker_data.get("businessTitle"),
        "location": location.get("descriptor")
            or worker_data.get("location", {}).get("descriptor"),
        "locationId": location.get("Location_ID"),
        "country": country.get("descriptor"),
        "countryCode": country.get("ISO_3166-1_Alpha-3_Code"),
        "supervisoryOrganization": primary_job.get("supervisoryOrganization", {}).get("descriptor")
            or worker_data.get("primarySupervisoryOrganization", {}).get("descriptor"),
        "jobType": primary_job.get("jobType", {}).get("descriptor"),
        "jobProfile": primary_job.get("jobProfile", {}).get("descriptor"),
        "primaryJobId": primary_job.get("id"),
        "primaryJobDescriptor": primary_job.get("descriptor"),
        "isManager": worker_data.get("isManager"),
        "yearsOfService": worker_data.get("yearsOfService"),
        "primaryWorkAddress": worker_data.get("primaryWorkAddressText"),
    }


async def _fetch_json(url: str, access_token: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    async with create_async_client() as client:
        response = await client.get(url, headers=headers)
        if response.status_code in (404, 400):
            try:
                body = response.json()
                detail = body.get("error", response.text[:200])
            except Exception:
                detail = response.text[:200]
            api_name = url.split("/ccx/api/")[-1].split("/")[0] if "/ccx/api/" in url else url
            raise WorkdayApiNotAvailable(api_name, response.status_code, detail)
        response.raise_for_status()
        return response.json()


def _tool_response(summary: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return payload dict directly; fastmcp serialises it as structuredContent."""
    return payload


async def _fetch_json_with_params(
    url: str, access_token: str, params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if params:
        url = f"{url}?{urlencode(params)}"
    return await _fetch_json(url, access_token)
