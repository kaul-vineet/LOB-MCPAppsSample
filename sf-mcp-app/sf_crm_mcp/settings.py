"""Salesforce CRM settings — sourced from shared-mcp-lib."""
from functools import lru_cache
from shared_mcp.settings import SFSettings


@lru_cache(maxsize=1)
def get_settings() -> SFSettings:
    return SFSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
