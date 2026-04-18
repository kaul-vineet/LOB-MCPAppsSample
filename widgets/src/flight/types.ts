// ── ft__get_flights_by_aircraft ──────────────────────────────────────────
export interface FlightRecord {
  callsign: string | null;
  from: string | null;
  to: string | null;
  departed: string | null;
  arrived: string | null;
}

export interface FlightsData {
  icao24: string;
  total_flights: number;
  flights: FlightRecord[];
  error?: boolean;
  message?: string;
}

// ── ft__get_aircraft_state ──────────────────────────────────────────────
export interface AircraftStateData {
  icao24: string;
  found: boolean;
  callsign?: string | null;
  origin_country?: string;
  latitude?: number | null;
  longitude?: number | null;
  altitude_m?: number | null;
  altitude_ft?: number | null;
  on_ground?: boolean;
  velocity_kmh?: number | null;
  heading_deg?: number | null;
  heading_compass?: string | null;
  vertical_rate?: number | null;
  last_contact?: string | null;
  error?: boolean;
  message?: string;
}

// ── ft__get_airport_departures / ft__get_airport_arrivals ───────────────
export interface AirportFlight {
  icao24: string;
  callsign: string | null;
  from: string | null;
  to: string | null;
  departed: string | null;
  arrived: string | null;
  first_seen_ts: number;
}

export interface AirportFlightsData {
  type: 'departures' | 'arrivals';
  airport: string;
  total_flights: number;
  flights: AirportFlight[];
  error?: boolean;
  message?: string;
}

// ── ft__get_aircraft_track ──────────────────────────────────────────────
export interface Position {
  lat: number;
  lon: number;
}

export interface TrackData {
  icao24: string;
  found: boolean;
  callsign?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  waypoints?: number;
  first_position?: Position | null;
  last_position?: Position | null;
  error?: boolean;
  message?: string;
}

// ── Union type for all tool responses ───────────────────────────────────
export type FlightToolData =
  | FlightsData
  | AircraftStateData
  | AirportFlightsData
  | TrackData;
