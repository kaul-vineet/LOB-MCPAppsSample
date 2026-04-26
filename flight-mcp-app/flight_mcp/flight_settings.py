"""Flight Tracker settings — sourced from shared-mcp-lib."""
from functools import lru_cache
from shared_mcp.settings import FTSettings


@lru_cache(maxsize=1)
def get_settings() -> FTSettings:
    return FTSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
