"""HubSpot settings — sourced from shared-mcp-lib."""
from functools import lru_cache
from shared_mcp.settings import HSSettings


@lru_cache(maxsize=1)
def get_settings() -> HSSettings:
    return HSSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
