"""
Flight Tracker MCP Server — 5 tools for aircraft & airport flight data.

Uses the OpenSky Network API with OAuth2 client_credentials authentication.
All tools return structuredContent for the widget, with _meta on the
decorator to ensure M365 Copilot discovers the widget URI from tools/list.
"""

import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

import httpx
import structlog
import uvicorn
from dotenv import load_dotenv


def _load_env() -> None:
    explicit = os.environ.get("MCP_SERVERS_ENV_FILE")
    if explicit:
        load_dotenv(explicit, override=True)
        return
    # Sibling project convention: C:\demoprojects\flight-tracker\.env
    sibling_env = Path(__file__).parent.parent.parent.parent / "flight-tracker" / ".env"
    if sibling_env.exists():
        load_dotenv(sibling_env, override=True)
        return
    project_env = Path.cwd() / "env" / ".env.flight"
    if project_env.exists():
        load_dotenv(project_env, override=True)
        return
    load_dotenv()
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
from pydantic_settings import BaseSettings
from starlette.middleware.cors import CORSMiddleware
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

_load_env()

log = structlog.get_logger()


# ── Typed Configuration ────────────────────────────────────────────────────────


class FTSettings(BaseSettings):
    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    mock_mode: bool = False
    port: int = 3004
    cors_origins: str = "*"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> FTSettings:
    return FTSettings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


settings = get_settings()


# ── Widget ─────────────────────────────────────────────────────────────────────

WIDGET_URI = "ui://widget/flights.html"
RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
WIDGET_HTML = (Path(__file__).parent / "web" / "widget.html").read_text(encoding="utf-8")


# ── MCP Server ─────────────────────────────────────────────────────────────────

mcp = FastMCP("flight-tracker")


@mcp.resource(WIDGET_URI, mime_type=RESOURCE_MIME_TYPE)
async def flight_widget() -> str:
    """UI widget for displaying flight results."""
    return WIDGET_HTML


# ── OpenSky API ────────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), retry=retry_if_exception_type(httpx.RequestError))
async def _opensky_request(method: str, path: str, **kwargs) -> httpx.Response:
    """Make authenticated request to OpenSky API with retry."""
    token = await get_opensky_token()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.request(
            method,
            f"https://opensky-network.org/api{path}",
            headers={"Authorization": f"Bearer {token}"},
            **kwargs,
        )
    return resp


_token_cache: dict = {"token": None, "expires_at": 0.0}


def clear_token_cache() -> None:
    """Force re-authentication on the next API call."""
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
                "grant_type": "client_credentials",
                "client_id": settings.opensky_client_id,
                "client_secret": settings.opensky_client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 3600)
        return _token_cache["token"]


def format_unix(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def heading_to_compass(deg: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]


def _error_result(msg: str) -> types.CallToolResult:
    log.error("tool_error", msg=msg)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=msg)],
        isError=True,
    )


def _is_mock() -> bool:
    return settings.mock_mode or (not settings.opensky_client_id and not settings.opensky_client_secret)


# ── Mock Data ─────────────────────────────────────────────────────────────────

def _mock_flights_by_aircraft(icao24: str, begin_date: str, end_date: str) -> types.CallToolResult:
    flights = [
        {"callsign": "GTC001", "from": "EGLL", "to": "KJFK",  "departed": "2026-04-22 08:15 UTC", "arrived": "2026-04-22 16:40 UTC"},
        {"callsign": "GTC002", "from": "KJFK", "to": "OMDB",  "departed": "2026-04-21 22:00 UTC", "arrived": "2026-04-22 18:30 UTC"},
        {"callsign": "GTC003", "from": "OMDB", "to": "VHHH",  "departed": "2026-04-20 14:00 UTC", "arrived": "2026-04-20 22:05 UTC"},
    ]
    structured = {"icao24": icao24, "total_flights": len(flights), "flights": flights, "_mock": True}
    lines = [f"[demo] Found {len(flights)} flight(s) for {icao24} ({begin_date} – {end_date}):"]
    for fl in flights:
        lines.append(f"  {fl['callsign']}: {fl['from']} -> {fl['to']} | Dep: {fl['departed']} | Arr: {fl['arrived']}")
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(lines))],
        structuredContent=structured,
    )


def _mock_aircraft_state(icao24: str) -> types.CallToolResult:
    structured = {
        "icao24": icao24, "found": True,
        "callsign": "GTC001", "origin_country": "Ireland",
        "latitude": 51.477, "longitude": -0.461,
        "altitude_m": 10670, "altitude_ft": 35009,
        "on_ground": False,
        "velocity_kmh": 892, "heading_deg": 270, "heading_compass": "W",
        "vertical_rate": 0.0,
        "last_contact": "2026-04-22 14:32 UTC",
        "_mock": True,
    }
    summary = (
        f"[demo] Aircraft {icao24} (GTC001) is airborne. "
        f"Alt: 35009ft | Speed: 892 km/h | Heading: 270° W"
    )
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


def _mock_airport_departures(airport: str, begin_date: str, end_date: str) -> types.CallToolResult:
    flights = [
        {"icao24": "4ca2bf", "callsign": "GTC001", "from": airport, "to": "KJFK",  "departed": "2026-04-22 06:00 UTC", "arrived": "2026-04-22 14:15 UTC", "first_seen_ts": 1745294400},
        {"icao24": "4ca2c0", "callsign": "GTC004", "from": airport, "to": "OMDB",  "departed": "2026-04-22 09:30 UTC", "arrived": "2026-04-22 19:55 UTC", "first_seen_ts": 1745306200},
        {"icao24": "4ca2c1", "callsign": "GTC007", "from": airport, "to": "VHHH",  "departed": "2026-04-22 11:00 UTC", "arrived": "2026-04-22 23:40 UTC", "first_seen_ts": 1745312400},
        {"icao24": "4ca2c2", "callsign": "GTC010", "from": airport, "to": "YSSY",  "departed": "2026-04-22 13:20 UTC", "arrived": "2026-04-23 09:10 UTC", "first_seen_ts": 1745320200},
        {"icao24": "4ca2c3", "callsign": "GTC013", "from": airport, "to": "FACT",  "departed": "2026-04-22 15:45 UTC", "arrived": "2026-04-22 23:00 UTC", "first_seen_ts": 1745329500},
    ]
    structured = {"type": "departures", "airport": airport, "total_flights": len(flights), "flights": flights, "_mock": True}
    lines = [f"[demo] Found {len(flights)} departure(s) from {airport} ({begin_date}):"]
    for fl in flights:
        lines.append(f"  {fl['callsign']}: -> {fl['to']} | Dep: {fl['departed']}")
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(lines))],
        structuredContent=structured,
    )


def _mock_airport_arrivals(airport: str, begin_date: str, end_date: str) -> types.CallToolResult:
    flights = [
        {"icao24": "4ca2bf", "callsign": "GTC002", "from": "KJFK",  "to": airport, "departed": "2026-04-21 22:00 UTC", "arrived": "2026-04-22 08:20 UTC", "first_seen_ts": 1745281200},
        {"icao24": "4ca2c4", "callsign": "GTC005", "from": "OMDB",  "to": airport, "departed": "2026-04-21 18:30 UTC", "arrived": "2026-04-22 06:45 UTC", "first_seen_ts": 1745277900},
        {"icao24": "4ca2c5", "callsign": "GTC008", "from": "VHHH",  "to": airport, "departed": "2026-04-21 08:00 UTC", "arrived": "2026-04-22 13:55 UTC", "first_seen_ts": 1745319300},
        {"icao24": "4ca2c6", "callsign": "GTC011", "from": "YSSY",  "to": airport, "departed": "2026-04-20 20:00 UTC", "arrived": "2026-04-22 05:30 UTC", "first_seen_ts": 1745274600},
    ]
    structured = {"type": "arrivals", "airport": airport, "total_flights": len(flights), "flights": flights, "_mock": True}
    lines = [f"[demo] Found {len(flights)} arrival(s) at {airport} ({begin_date}):"]
    for fl in flights:
        lines.append(f"  {fl['callsign']}: {fl['from']} -> | Arr: {fl['arrived']}")
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="\n".join(lines))],
        structuredContent=structured,
    )


def _mock_aircraft_track(icao24: str) -> types.CallToolResult:
    structured = {
        "icao24": icao24, "found": True,
        "callsign": "GTC001",
        "start_time": "2026-04-22 06:00 UTC",
        "end_time":   "2026-04-22 14:15 UTC",
        "waypoints": 312,
        "first_position": {"lat": 51.477, "lon": -0.461},
        "last_position":  {"lat": 40.641, "lon": -73.778},
        "_mock": True,
    }
    summary = (
        f"[demo] Track for {icao24} (GTC001): "
        f"312 waypoints from 2026-04-22 06:00 UTC to 2026-04-22 14:15 UTC."
    )
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TOOLS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.tool(
    description=(
        "Retrieve flight history for an aircraft by its ICAO 24-bit transponder address. "
        "icao24 must be a 6-character lowercase hex string (e.g. '3c675a'). "
        "Date range must not exceed 2 days. "
        "Current-day and recent historical flights are available."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def ft__get_flights_by_aircraft(
    icao24: str,
    begin_date: str,
    end_date: str,
) -> types.CallToolResult:
    """
    Args:
        icao24:     Aircraft transponder address, e.g. '3c675a'
        begin_date: Start date YYYY-MM-DD
        end_date:   End date YYYY-MM-DD (max 2 days from begin_date)
    """
    if _is_mock():
        return _mock_flights_by_aircraft(icao24, begin_date, end_date)

    begin = int(datetime.fromisoformat(begin_date).replace(tzinfo=timezone.utc).timestamp())
    end = int(datetime.fromisoformat(end_date + "T23:59:59").replace(tzinfo=timezone.utc).timestamp())

    if end - begin > 2 * 24 * 3600:
        return _error_result("Date range cannot exceed 2 days.")

    try:
        resp = await _opensky_request("GET", "/flights/aircraft", params={"icao24": icao24, "begin": begin, "end": end})
        if resp.status_code == 404:
            flights_raw = []
        else:
            resp.raise_for_status()
            flights_raw = resp.json() if resp.content else []
    except Exception as e:
        return _error_result(f"Failed to fetch flights: {e}")

    flights = [
        {
            "callsign": (f.get("callsign") or "").strip() or None,
            "from": f.get("estDepartureAirport"),
            "to": f.get("estArrivalAirport"),
            "departed": format_unix(f["firstSeen"]),
            "arrived": format_unix(f["lastSeen"]),
        }
        for f in flights_raw
    ]

    structured = {"icao24": icao24, "total_flights": len(flights), "flights": flights}

    if not flights:
        summary = f"No flights found for {icao24} between {begin_date} and {end_date}."
    else:
        lines = [f"Found {len(flights)} flight(s) for {icao24}:"]
        for fl in flights:
            lines.append(f"- {fl['callsign'] or '?'}: {fl['from']} → {fl['to']} | Dep: {fl['departed']} | Arr: {fl['arrived']}")
        summary = "\n".join(lines)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Get the last known live state of an aircraft: position, altitude, speed, heading. "
        "icao24 must be a 6-character lowercase hex string (e.g. '3c675a')."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def ft__get_aircraft_state(icao24: str) -> types.CallToolResult:
    """
    Args:
        icao24: Aircraft transponder address, e.g. '3c675a'
    """
    if _is_mock():
        return _mock_aircraft_state(icao24)

    try:
        resp = await _opensky_request("GET", "/states/all", params={"icao24": icao24})
        if resp.status_code == 404:
            states = []
        else:
            resp.raise_for_status()
            states = resp.json().get("states") or []
    except Exception as e:
        return _error_result(f"Failed to fetch aircraft state: {e}")

    if not states:
        structured: dict = {"icao24": icao24, "found": False}
        summary = f"No live state found for {icao24}. It may be on the ground or out of coverage."
    else:
        s = states[0]
        vel_ms = s[9]
        alt_m = s[7]
        track = s[10]
        structured = {
            "icao24":          icao24,
            "found":           True,
            "callsign":        (s[1] or "").strip() or None,
            "origin_country":  s[2],
            "latitude":        s[6],
            "longitude":       s[5],
            "altitude_m":      round(alt_m) if alt_m is not None else None,
            "altitude_ft":     round(alt_m * 3.281) if alt_m is not None else None,
            "on_ground":       s[8],
            "velocity_kmh":    round(vel_ms * 3.6) if vel_ms is not None else None,
            "heading_deg":     round(track) if track is not None else None,
            "heading_compass": heading_to_compass(track) if track is not None else None,
            "vertical_rate":   s[11],
            "last_contact":    format_unix(s[4]) if s[4] is not None else None,
        }
        status = "on the ground" if s[8] else "airborne"
        summary = (
            f"Aircraft {icao24} is {status}. "
            f"Alt: {structured['altitude_ft']}ft | "
            f"Speed: {structured['velocity_kmh']} km/h | "
            f"Heading: {structured['heading_deg']}° {structured['heading_compass']}"
        )

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Retrieve flights departing from an airport within a date range. "
        "airport must be an ICAO airport code (e.g. 'EGLL' for Heathrow, 'KJFK' for JFK). "
        "Date range must not exceed 1 day."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def ft__get_airport_departures(
    airport: str,
    begin_date: str,
    end_date: str,
) -> types.CallToolResult:
    """
    Args:
        airport:    ICAO airport code, e.g. 'EGLL'
        begin_date: Start date YYYY-MM-DD
        end_date:   End date YYYY-MM-DD (same as begin_date for a single day)
    """
    if _is_mock():
        return _mock_airport_departures(airport, begin_date, end_date)

    begin = int(datetime.fromisoformat(begin_date).replace(tzinfo=timezone.utc).timestamp())
    end = int(datetime.fromisoformat(end_date + "T23:59:59").replace(tzinfo=timezone.utc).timestamp())

    if end - begin > 24 * 3600:
        return _error_result("Date range cannot exceed 1 day for airport queries.")

    try:
        resp = await _opensky_request("GET", "/flights/departure", params={"airport": airport.upper(), "begin": begin, "end": end})
        if resp.status_code == 404:
            flights_raw = []
        else:
            resp.raise_for_status()
            flights_raw = resp.json() if resp.content else []
    except Exception as e:
        return _error_result(f"Failed to fetch departures: {e}")

    flights = [
        {
            "icao24":        f.get("icao24"),
            "callsign":      (f.get("callsign") or "").strip() or None,
            "from":          f.get("estDepartureAirport"),
            "to":            f.get("estArrivalAirport"),
            "departed":      format_unix(f["firstSeen"]),
            "arrived":       format_unix(f["lastSeen"]),
            "first_seen_ts": f["firstSeen"],
        }
        for f in flights_raw
    ]

    structured = {
        "type": "departures",
        "airport": airport.upper(),
        "total_flights": len(flights),
        "flights": flights,
    }

    if not flights:
        summary = f"No departures found from {airport.upper()} between {begin_date} and {end_date}."
    else:
        lines = [f"Found {len(flights)} departure(s) from {airport.upper()}:"]
        for fl in flights[:5]:
            lines.append(f"- {fl['callsign'] or fl['icao24']}: → {fl['to'] or '?'} | Dep: {fl['departed']}")
        if len(flights) > 5:
            lines.append(f"  ... and {len(flights) - 5} more")
        summary = "\n".join(lines)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Retrieve flights arriving at an airport within a date range. "
        "airport must be an ICAO airport code (e.g. 'EGLL' for Heathrow, 'KJFK' for JFK). "
        "Date range must not exceed 1 day. "
        "Use yesterday's date — same-day arrival data is not yet available."
    ),
    meta={"ui": {"resourceUri": WIDGET_URI}},
)
async def ft__get_airport_arrivals(
    airport: str,
    begin_date: str,
    end_date: str,
) -> types.CallToolResult:
    """
    Args:
        airport:    ICAO airport code, e.g. 'EGLL'
        begin_date: Start date YYYY-MM-DD
        end_date:   End date YYYY-MM-DD (same as begin_date for a single day)
    """
    if _is_mock():
        return _mock_airport_arrivals(airport, begin_date, end_date)

    begin = int(datetime.fromisoformat(begin_date).replace(tzinfo=timezone.utc).timestamp())
    end = int(datetime.fromisoformat(end_date + "T23:59:59").replace(tzinfo=timezone.utc).timestamp())

    if end - begin > 24 * 3600:
        return _error_result("Date range cannot exceed 1 day for airport queries.")

    try:
        resp = await _opensky_request("GET", "/flights/arrival", params={"airport": airport.upper(), "begin": begin, "end": end})
        if resp.status_code == 404:
            flights_raw = []
        else:
            resp.raise_for_status()
            flights_raw = resp.json() if resp.content else []
    except Exception as e:
        return _error_result(f"Failed to fetch arrivals: {e}")

    flights = [
        {
            "icao24":        f.get("icao24"),
            "callsign":      (f.get("callsign") or "").strip() or None,
            "from":          f.get("estDepartureAirport"),
            "to":            f.get("estArrivalAirport"),
            "departed":      format_unix(f["firstSeen"]),
            "arrived":       format_unix(f["lastSeen"]),
            "first_seen_ts": f["firstSeen"],
        }
        for f in flights_raw
    ]

    structured = {
        "type": "arrivals",
        "airport": airport.upper(),
        "total_flights": len(flights),
        "flights": flights,
    }

    today_str = date.today().isoformat()
    if not flights:
        if begin_date >= today_str:
            summary = (
                f"No arrivals found at {airport.upper()} for {begin_date}. "
                f"Same-day arrival data is not yet available — try yesterday's date."
            )
        else:
            summary = f"No arrivals found at {airport.upper()} between {begin_date} and {end_date}."
    else:
        lines = [f"Found {len(flights)} arrival(s) at {airport.upper()}:"]
        for fl in flights[:5]:
            lines.append(f"- {fl['callsign'] or fl['icao24']}: {fl['from'] or '?'} → | Arr: {fl['arrived']}")
        if len(flights) > 5:
            lines.append(f"  ... and {len(flights) - 5} more")
        summary = "\n".join(lines)

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


@mcp.tool(
    description=(
        "Get the flight track (waypoints) for an aircraft. "
        "icao24 must be a 6-character lowercase hex string (e.g. '3c675a'). "
        "time is a Unix timestamp within the flight's time window; pass 0 for most recent track."
    ),
)
async def ft__get_aircraft_track(icao24: str, time: int = 0) -> types.CallToolResult:
    """
    Args:
        icao24: Aircraft transponder address, e.g. '3c675a'
        time:   Unix timestamp within the flight window, or 0 for most recent track
    """
    if _is_mock():
        return _mock_aircraft_track(icao24)

    try:
        resp = await _opensky_request("GET", "/tracks/all", params={"icao24": icao24, "time": time})
        if resp.status_code == 404:
            structured: dict = {"icao24": icao24, "found": False}
            summary = f"No track found for {icao24}."
        else:
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
            path = data.get("path") or []
            first = path[0] if path else None
            last = path[-1] if path else None
            structured = {
                "icao24":         icao24,
                "found":          True,
                "callsign":       (data.get("callsign") or "").strip() or None,
                "start_time":     format_unix(data["startTime"]) if data.get("startTime") else None,
                "end_time":       format_unix(data["endTime"]) if data.get("endTime") else None,
                "waypoints":      len(path),
                "first_position": {"lat": first[1], "lon": first[2]} if first else None,
                "last_position":  {"lat": last[1], "lon": last[2]} if last else None,
            }
            summary = (
                f"Track for {icao24} ({structured['callsign'] or 'unknown'}): "
                f"{len(path)} waypoints from {structured['start_time']} to {structured['end_time']}."
            )
    except Exception as e:
        return _error_result(f"Failed to fetch track: {e}")

    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROMPTS
# ══════════════════════════════════════════════════════════════════════════════


@mcp.prompt()
def lookup_flights(icao24: str, date_str: str) -> list[PromptMessage]:
    """Look up all flights for an aircraft on a specific date."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"Show me all flights for aircraft {icao24} on {date_str}. "
                    f"Call ft__get_flights_by_aircraft with icao24='{icao24}', "
                    f"begin_date='{date_str}', end_date='{date_str}'."
                ),
            ),
        )
    ]


@mcp.prompt()
def lookup_departures(airport: str, date_str: str) -> list[PromptMessage]:
    """Look up all departures from an airport on a specific date."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"Show me all departures from airport {airport.upper()} on {date_str}. "
                    f"Call ft__get_airport_departures with airport='{airport.upper()}', "
                    f"begin_date='{date_str}', end_date='{date_str}'."
                ),
            ),
        )
    ]


@mcp.prompt()
def lookup_arrivals(airport: str, date_str: str) -> list[PromptMessage]:
    """Look up all arrivals at an airport on a specific date."""
    return [
        PromptMessage(
            role="user",
            content=TextContent(
                type="text",
                text=(
                    f"Show me all arrivals at airport {airport.upper()} on {date_str}. "
                    f"Call ft__get_airport_arrivals with airport='{airport.upper()}', "
                    f"begin_date='{date_str}', end_date='{date_str}'."
                ),
            ),
        )
    ]


# ══════════════════════════════════════════════════════════════════════════════
# SERVER ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════


def _validate_env() -> None:
    """Check required environment variables and print startup checklist."""
    log.info("validating_env")
    print("  ┌─ Environment ─────────────────────────────────")
    print(f"  │ OPENSKY_CLIENT_ID     {'✓ ' + settings.opensky_client_id[:8] + '...' if settings.opensky_client_id else '✗ MISSING'}")
    print(f"  │ OPENSKY_CLIENT_SECRET {'✓ (set)' if settings.opensky_client_secret else '✗ MISSING'}")
    print("  └────────────────────────────────────────────────")

    missing = []
    if not settings.opensky_client_id:
        missing.append("OPENSKY_CLIENT_ID")
    if not settings.opensky_client_secret:
        missing.append("OPENSKY_CLIENT_SECRET")
    if missing:
        if _is_mock():
            print("  [demo mode] No OpenSky credentials — running with mock data (set MOCK_MODE=false to use live API)")
        else:
            log.error("missing_env_vars", vars=missing)
            print(f"\n  Missing required env vars: {', '.join(missing)}")
            print("  Copy .env.example to .env and fill in your OpenSky credentials.")
            print("  Or set MOCK_MODE=true to run with demo data.")
            sys.exit(1)


def main() -> None:
    _validate_env()
    log.info("starting", port=settings.port)
    print(f"✈️  GTC — Flight Tracker starting on port {settings.port}")

    app = mcp.streamable_http_app()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "mcp-session-id"],
    )

    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
