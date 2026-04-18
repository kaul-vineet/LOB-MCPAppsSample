"""
Flight Tracker MCP Server — 5 tools for aircraft & airport flight data.

Uses the OpenSky Network API with OAuth2 client_credentials authentication.
All tools return structuredContent for the widget, with _meta on the
decorator to ensure M365 Copilot discovers the widget URI from tools/list.
"""

import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import structlog
import uvicorn
from dotenv import load_dotenv
from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.types import PromptMessage, TextContent
from pydantic_settings import BaseSettings
from starlette.middleware.cors import CORSMiddleware
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

log = structlog.get_logger()


# ── Typed Configuration ────────────────────────────────────────────────────────


class FTSettings(BaseSettings):
    opensky_client_id: str = ""
    opensky_client_secret: str = ""
    port: int = 3004
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = FTSettings()


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


async def get_opensky_token() -> str:
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
        return resp.json()["access_token"]


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
        log.error("missing_env_vars", vars=missing)
        print(f"\n  ❌ Missing required env vars: {', '.join(missing)}")
        print("  Copy .env.example to .env and fill in your OpenSky credentials.")
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
