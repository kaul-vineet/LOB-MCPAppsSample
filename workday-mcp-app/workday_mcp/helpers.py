"""Shared Workday helper functions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from shared_mcp.http import create_async_client
from shared_mcp.logger import get_logger

from .config import get_endpoints

LOGGER = get_logger(__name__)


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
