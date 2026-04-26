"""ServiceNow settings — sourced from shared-mcp-lib."""
from functools import lru_cache
from shared_mcp.settings import SNSettings


@lru_cache(maxsize=1)
def get_settings() -> SNSettings:
    return SNSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
