"""Workday HR MCP settings — sourced from shared-mcp-lib."""
from functools import lru_cache

from shared_mcp.settings import WorkdayMCPSettings


@lru_cache(maxsize=1)
def get_settings() -> WorkdayMCPSettings:
    return WorkdayMCPSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
