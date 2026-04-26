"""Flight Tracker tool handlers, TOOL_SPECS, PROMPT_SPECS. No MCP bootstrap here."""
from __future__ import annotations

from datetime import date, datetime, timezone

import structlog
from mcp import types
from mcp.types import PromptMessage, TextContent

from .flight_client import format_unix, heading_to_compass, is_mock, opensky_request

log = structlog.get_logger("ft")


# ── Shared helpers ────────────────────────────────────────────────────────────

def _error_result(msg: str) -> types.CallToolResult:
    log.error("tool_error", msg=msg)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=msg)],
        isError=True,
    )


# ── Mock data ─────────────────────────────────────────────────────────────────

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
    summary = f"[demo] Aircraft {icao24} (GTC001) is airborne. Alt: 35009ft | Speed: 892 km/h | Heading: 270° W"
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
    summary = f"[demo] Track for {icao24} (GTC001): 312 waypoints from 2026-04-22 06:00 UTC to 2026-04-22 14:15 UTC."
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=summary)],
        structuredContent=structured,
    )


# ── Tool handlers ─────────────────────────────────────────────────────────────

async def ft__get_flights_by_aircraft(
    icao24: str,
    begin_date: str,
    end_date: str,
) -> types.CallToolResult:
    if is_mock():
        return _mock_flights_by_aircraft(icao24, begin_date, end_date)

    begin = int(datetime.fromisoformat(begin_date).replace(tzinfo=timezone.utc).timestamp())
    end = int(datetime.fromisoformat(end_date + "T23:59:59").replace(tzinfo=timezone.utc).timestamp())

    if end - begin > 2 * 24 * 3600:
        return _error_result("Date range cannot exceed 2 days.")

    try:
        resp = await opensky_request("GET", "/flights/aircraft", params={"icao24": icao24, "begin": begin, "end": end})
        flights_raw = [] if resp.status_code == 404 else (resp.raise_for_status() or (resp.json() if resp.content else []))
    except Exception as e:
        return _error_result(f"Failed to fetch flights: {e}")

    flights = [
        {
            "callsign": (f.get("callsign") or "").strip() or None,
            "from":     f.get("estDepartureAirport"),
            "to":       f.get("estArrivalAirport"),
            "departed": format_unix(f["firstSeen"]),
            "arrived":  format_unix(f["lastSeen"]),
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


async def ft__get_aircraft_state(icao24: str) -> types.CallToolResult:
    if is_mock():
        return _mock_aircraft_state(icao24)

    try:
        resp = await opensky_request("GET", "/states/all", params={"icao24": icao24})
        states = [] if resp.status_code == 404 else (resp.raise_for_status() or (resp.json().get("states") or []))
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


async def ft__get_airport_departures(
    airport: str,
    begin_date: str,
    end_date: str,
) -> types.CallToolResult:
    if is_mock():
        return _mock_airport_departures(airport, begin_date, end_date)

    begin = int(datetime.fromisoformat(begin_date).replace(tzinfo=timezone.utc).timestamp())
    end = int(datetime.fromisoformat(end_date + "T23:59:59").replace(tzinfo=timezone.utc).timestamp())

    if end - begin > 24 * 3600:
        return _error_result("Date range cannot exceed 1 day for airport queries.")

    try:
        resp = await opensky_request("GET", "/flights/departure", params={"airport": airport.upper(), "begin": begin, "end": end})
        flights_raw = [] if resp.status_code == 404 else (resp.raise_for_status() or (resp.json() if resp.content else []))
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
    structured = {"type": "departures", "airport": airport.upper(), "total_flights": len(flights), "flights": flights}
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


async def ft__get_airport_arrivals(
    airport: str,
    begin_date: str,
    end_date: str,
) -> types.CallToolResult:
    if is_mock():
        return _mock_airport_arrivals(airport, begin_date, end_date)

    begin = int(datetime.fromisoformat(begin_date).replace(tzinfo=timezone.utc).timestamp())
    end = int(datetime.fromisoformat(end_date + "T23:59:59").replace(tzinfo=timezone.utc).timestamp())

    if end - begin > 24 * 3600:
        return _error_result("Date range cannot exceed 1 day for airport queries.")

    try:
        resp = await opensky_request("GET", "/flights/arrival", params={"airport": airport.upper(), "begin": begin, "end": end})
        flights_raw = [] if resp.status_code == 404 else (resp.raise_for_status() or (resp.json() if resp.content else []))
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
    structured = {"type": "arrivals", "airport": airport.upper(), "total_flights": len(flights), "flights": flights}
    today_str = date.today().isoformat()
    if not flights:
        if begin_date >= today_str:
            summary = (
                f"No arrivals found at {airport.upper()} for {begin_date}. "
                "Same-day arrival data is not yet available — try yesterday's date."
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


async def ft__get_aircraft_track(icao24: str, time: int = 0) -> types.CallToolResult:
    if is_mock():
        return _mock_aircraft_track(icao24)

    try:
        resp = await opensky_request("GET", "/tracks/all", params={"icao24": icao24, "time": time})
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


# ── Prompt handlers ───────────────────────────────────────────────────────────

def lookup_flights_prompt(icao24: str, date_str: str) -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text", text=(
        f"Show me all flights for aircraft {icao24} on {date_str}. "
        f"Call ft__get_flights_by_aircraft with icao24='{icao24}', "
        f"begin_date='{date_str}', end_date='{date_str}'."
    )))]


def lookup_departures_prompt(airport: str, date_str: str) -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text", text=(
        f"Show me all departures from airport {airport.upper()} on {date_str}. "
        f"Call ft__get_airport_departures with airport='{airport.upper()}', "
        f"begin_date='{date_str}', end_date='{date_str}'."
    )))]


def lookup_arrivals_prompt(airport: str, date_str: str) -> list[PromptMessage]:
    return [PromptMessage(role="user", content=TextContent(type="text", text=(
        f"Show me all arrivals at airport {airport.upper()} on {date_str}. "
        f"Call ft__get_airport_arrivals with airport='{airport.upper()}', "
        f"begin_date='{date_str}', end_date='{date_str}'."
    )))]


# ── Registries ────────────────────────────────────────────────────────────────

TOOL_SPECS = [
    {
        "name": "ft__get_flights_by_aircraft",
        "description": (
            "Retrieve flight history for an aircraft by its ICAO 24-bit transponder address. "
            "icao24 must be a 6-character lowercase hex string (e.g. '3c675a'). "
            "Date range must not exceed 2 days."
        ),
        "handler": ft__get_flights_by_aircraft,
    },
    {
        "name": "ft__get_aircraft_state",
        "description": (
            "Get the last known live state of an aircraft: position, altitude, speed, heading. "
            "icao24 must be a 6-character lowercase hex string (e.g. '3c675a')."
        ),
        "handler": ft__get_aircraft_state,
    },
    {
        "name": "ft__get_airport_departures",
        "description": (
            "Retrieve flights departing from an airport within a date range. "
            "airport must be an ICAO airport code (e.g. 'EGLL' for Heathrow). "
            "Date range must not exceed 1 day."
        ),
        "handler": ft__get_airport_departures,
    },
    {
        "name": "ft__get_airport_arrivals",
        "description": (
            "Retrieve flights arriving at an airport within a date range. "
            "airport must be an ICAO airport code (e.g. 'EGLL' for Heathrow). "
            "Date range must not exceed 1 day. "
            "Use yesterday's date — same-day arrival data is not yet available."
        ),
        "handler": ft__get_airport_arrivals,
    },
    {
        "name": "ft__get_aircraft_track",
        "description": (
            "Get the flight track (waypoints) for an aircraft. "
            "icao24 must be a 6-character lowercase hex string. "
            "time is a Unix timestamp within the flight's time window; pass 0 for most recent track."
        ),
        "handler": ft__get_aircraft_track,
    },
]

PROMPT_SPECS = [
    {
        "name": "lookup_flights",
        "description": "Look up all flights for an aircraft on a specific date.",
        "handler": lookup_flights_prompt,
    },
    {
        "name": "lookup_departures",
        "description": "Look up all departures from an airport on a specific date.",
        "handler": lookup_departures_prompt,
    },
    {
        "name": "lookup_arrivals",
        "description": "Look up all arrivals at an airport on a specific date.",
        "handler": lookup_arrivals_prompt,
    },
]
