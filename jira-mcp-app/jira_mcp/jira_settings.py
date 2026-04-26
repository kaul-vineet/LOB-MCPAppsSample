"""Jira Project Management MCP settings — sourced from shared-mcp-lib."""
from functools import lru_cache

from shared_mcp.settings import JiraMCPSettings


@lru_cache(maxsize=1)
def get_settings() -> JiraMCPSettings:
    return JiraMCPSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
