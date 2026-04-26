"""Settings loaders for all GTC LOB MCP servers."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from pydantic_settings import BaseSettings


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


# ── Pydantic BaseSettings for LOB servers (auto-load from env) ───────────────

class HSSettings(BaseSettings):
    """HubSpot MCP server settings."""
    hubspot_access_token: str = ""
    port: int = 3003
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


class SNSettings(BaseSettings):
    """ServiceNow ITSM MCP server settings."""
    servicenow_instance: str = ""
    servicenow_auth_mode: str = "oauth"
    servicenow_client_id: str = ""
    servicenow_client_secret: str = ""
    servicenow_username: str = ""
    servicenow_password: str = ""
    port: int = 3001
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


class DSSettings(BaseSettings):
    """DocuSign MCP server settings."""
    docusign_integration_key: str = ""
    docusign_user_id: str = ""
    docusign_account_id: str = ""
    docusign_rsa_private_key: str = ""  # base64-encoded PEM
    docusign_auth_server: str = "account-d.docusign.com"
    docusign_base_url: str = "https://demo.docusign.net/restapi"
    mock_mode: bool = False
    port: int = 3005
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


class FTSettings(BaseSettings):
    """Flight Tracker MCP server settings."""
    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    mock_mode: bool = False
    port: int = 3004
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


class SAPSettings(BaseSettings):
    """SAP S/4HANA MCP server settings."""
    sap_mode: str = "sandbox"
    sap_api_key: str = ""
    sap_tenant_url: str = ""
    sap_username: str = ""
    sap_password: str = ""
    port: int = 3002
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


class SFSettings(BaseSettings):
    """Salesforce CRM MCP server settings."""
    sf_instance_url: str = ""
    sf_client_id: str = ""
    sf_client_secret: str = ""
    port: int = 3000
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


class CoupaMCPSettings(BaseSettings):
    """Coupa Procurement MCP server settings."""
    coupa_instance_url: str = "https://mock.coupahost.com"
    coupa_mock: bool = True
    port: int = 3008
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


class JiraMCPSettings(BaseSettings):
    """Jira Project Management MCP server settings."""
    jira_base_url: str = ""
    jira_project_key: str = ""
    port: int = 3009
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


class SapHRSettings(BaseSettings):
    """SAP SuccessFactors HR MCP server settings."""
    port: int = 3006
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}


class WorkdayMCPSettings(BaseSettings):
    """Workday HR MCP server settings."""
    port: int = 3007
    cors_origins: str = "*"

    model_config = {"env_prefix": "", "case_sensitive": False}
