"""Flight Tracker API client — OpenSky auth, HTTP, helpers. No MCP imports."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import structlog
from dotenv import load_dotenv
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .settings import get_settings

log = structlog.get_logger("ft")


def _load_env() -> None:
    explicit = os.environ.get("MCP_SERVERS_ENV_FILE")
    if explicit:
        load_dotenv(explicit, override=True)
        return
    sibling_env = Path(__file__).parent.parent.parent.parent / "flight-tracker" / ".env"
    if sibling_env.exists():
        load_dotenv(sibling_env, override=True)
        return
    project_env = Path.cwd() / "env" / ".env.flight"
    if project_env.exists():
        load_dotenv(project_env, override=True)
        return
    load_dotenv()


_load_env()
_settings = get_settings()

# ── Token cache ───────────────────────────────────────────────────────────────

_token_cache: dict = {"token": None, "expires_at": 0.0}


def clear_token_cache() -> None:
    _token_cache["token"] = None
    _token_cache["expires_at"] = 0.0


async def get_opensky_token() -> str:
    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
            data={
                "grant_type":    "client_credentials",
                "client_id":     _settings.opensky_client_id,
                "client_secret": _settings.opensky_client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 3600)
        return _token_cache["token"]


# ── HTTP client ───────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type(httpx.RequestError),
)
async def opensky_request(method: str, path: str, **kwargs) -> httpx.Response:
    token = await get_opensky_token()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(
            method,
            f"https://opensky-network.org/api{path}",
            headers={"Authorization": f"Bearer {token}"},
            **kwargs,
        )
    return resp


# ── Helpers ───────────────────────────────────────────────────────────────────

def format_unix(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def heading_to_compass(deg: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]


def is_mock() -> bool:
    return _settings.mock_mode or (not _settings.opensky_client_id and not _settings.opensky_client_secret)
