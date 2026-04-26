"""SAP SuccessFactors HR MCP settings — sourced from shared-mcp-lib."""
from functools import lru_cache

from shared_mcp.settings import SapHRSettings


@lru_cache(maxsize=1)
def get_settings() -> SapHRSettings:
    return SapHRSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
