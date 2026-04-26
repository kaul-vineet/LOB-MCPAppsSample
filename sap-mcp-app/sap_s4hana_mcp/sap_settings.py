"""SAP S/4HANA settings — sourced from shared-mcp-lib."""
from functools import lru_cache
from shared_mcp.settings import SAPSettings


@lru_cache(maxsize=1)
def get_settings() -> SAPSettings:
    return SAPSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
