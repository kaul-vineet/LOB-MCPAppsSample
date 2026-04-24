"""Settings loaders for all new GTC LOBs (SAP HR, Workday, Coupa, Jira)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class SapSfSettings:
    odata_url: str
    token_url: str
    company_id: str
    client_id: str
    resource_uri: str = ""


@dataclass
class WorkdaySettings:
    base_url: str
    tenant: str
    skills_report: str = "svasireddy/ESSMCPSkills"
    learning_report: str = "svasireddy/Required_Learning"


@dataclass
class JiraSettings:
    base_url: str
    project_key: str = ""


@dataclass
class CoupaSettings:
    instance_url: str = "https://mock.coupahost.com"
    mock: bool = True


@lru_cache(maxsize=1)
def load_sap_sf_settings() -> SapSfSettings:
    odata_url = os.getenv("SAP_SF_ODATA_URL", "")
    if not odata_url:
        raise ValueError("SAP_SF_ODATA_URL not configured — mock mode active")
    return SapSfSettings(
        odata_url=odata_url,
        token_url=os.getenv("SAP_SF_TOKEN_URL", ""),
        company_id=os.getenv("SAP_SF_COMPANY_ID", ""),
        client_id=os.getenv("SAP_SF_CLIENT_ID", ""),
        resource_uri=os.getenv("SAP_SF_RESOURCE_URI", ""),
    )


@lru_cache(maxsize=1)
def load_workday_settings() -> WorkdaySettings:
    base_url = os.getenv("WORKDAY_BASE_URL", "")
    if not base_url:
        raise ValueError("WORKDAY_BASE_URL not configured — mock mode active")
    return WorkdaySettings(
        base_url=base_url,
        tenant=os.getenv("WORKDAY_TENANT", ""),
        skills_report=os.getenv("WORKDAY_SKILLS_REPORT", "svasireddy/ESSMCPSkills"),
        learning_report=os.getenv("WORKDAY_LEARNING_REPORT", "svasireddy/Required_Learning"),
    )


@lru_cache(maxsize=1)
def load_jira_settings() -> JiraSettings:
    base_url = os.getenv("JIRA_BASE_URL", "")
    if not base_url:
        raise ValueError("JIRA_BASE_URL not configured — mock mode active")
    return JiraSettings(
        base_url=base_url,
        project_key=os.getenv("JIRA_PROJECT_KEY", ""),
    )


@lru_cache(maxsize=1)
def load_coupa_settings() -> CoupaSettings:
    return CoupaSettings(
        instance_url=os.getenv("COUPA_INSTANCE_URL", "https://mock.coupahost.com"),
        mock=os.getenv("COUPA_MOCK", "true").lower() != "false",
    )


def reset_settings_cache() -> None:
    load_sap_sf_settings.cache_clear()
    load_workday_settings.cache_clear()
    load_jira_settings.cache_clear()
    load_coupa_settings.cache_clear()
