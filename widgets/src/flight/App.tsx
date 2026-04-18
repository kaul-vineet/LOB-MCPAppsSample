import React, { useState } from 'react';
import {
  Badge,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
  makeStyles,
} from '@fluentui/react-components';
import { useToolData, useMcpBridge, useTheme } from '../shared/McpBridge';
import { ExpandButton } from '../shared/ExpandButton';
import type {
  FlightToolData,
  FlightsData,
  AircraftStateData,
  AirportFlightsData,
  AirportFlight,
  TrackData,
} from './types';

// ── Aviation Color Tokens ───────────────────────────────────────────────
const AVIATION_LIGHT = {
  brand: '#0066cc',
  brandHover: '#004499',
  accent: '#0088ff',
  background: '#ffffff',
  surface: '#f5f8fc',
  text: '#1a1a1a',
  textWeak: '#666666',
  border: '#dce3ed',
  headerBg: '#f0f4f9',
  success: '#0d7d3b',
  warning: '#b35c00',
};

const AVIATION_DARK = {
  brand: '#3399ff',
  brandHover: '#1a3a5c',
  accent: '#66b3ff',
  background: '#1a1a1a',
  surface: '#252830',
  text: '#e0e0e0',
  textWeak: '#999999',
  border: '#3a3f4b',
  headerBg: '#252830',
  success: '#4caf50',
  warning: '#ff9800',
};

function av(theme: 'light' | 'dark') {
  return theme === 'dark' ? AVIATION_DARK : AVIATION_LIGHT;
}

function brandGrad(theme: 'light' | 'dark') {
  return theme === 'dark'
    ? 'linear-gradient(135deg, #1a3a5c 0%, #0d2137 100%)'
    : 'linear-gradient(135deg, #0066cc 0%, #004499 100%)';
}

// ── Styles ──────────────────────────────────────────────────────────────
const useStyles = makeStyles({
  shell: {
    margin: '0 auto',
    padding: '12px',
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
    fontSize: '13px',
  },
  card: {
    borderRadius: '6px',
    overflow: 'hidden',
    boxShadow: '0 2px 6px rgba(0,0,0,0.08)',
  },
  headerBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 16px',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  headerCell: {
    fontWeight: 700 as any,
    fontSize: '10px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    padding: '6px 10px',
  },
  cell: {
    padding: '6px 10px',
    verticalAlign: 'middle',
    fontSize: '12px',
    whiteSpace: 'nowrap' as const,
    overflow: 'hidden' as const,
    textOverflow: 'ellipsis' as const,
    maxWidth: '180px',
  },
  splitLayout: {
    display: 'flex',
    minHeight: '200px',
  },
  listPane: {
    flex: '3',
    overflowX: 'auto' as const,
    borderRight: '1px solid transparent',
  },
  detailPane: {
    flex: '2',
    padding: '16px',
    overflowY: 'auto' as const,
  },
  stateCard: {
    padding: '16px',
  },
  stateGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))',
    gap: '12px',
  },
  statItem: {
    padding: '10px 12px',
    borderRadius: '6px',
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    gap: '16px',
  },
  errorBanner: {
    padding: '12px 16px',
    fontSize: '13px',
    fontWeight: 500 as any,
  },
  empty: {
    padding: '24px 16px',
    textAlign: 'center' as const,
    fontSize: '13px',
  },
  mcpFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 16px',
    fontSize: '11px',
  },
});

// ── Type guards ─────────────────────────────────────────────────────────
function isAirportFlights(d: FlightToolData): d is AirportFlightsData {
  return 'type' in d && (d.type === 'departures' || d.type === 'arrivals');
}

function isFlights(d: FlightToolData): d is FlightsData {
  return 'flights' in d && 'total_flights' in d && !('type' in d);
}

function isState(d: FlightToolData): d is AircraftStateData {
  return 'found' in d && 'icao24' in d && !('waypoints' in d) && !('flights' in d);
}

function isTrack(d: FlightToolData): d is TrackData {
  return 'waypoints' in d;
}

// ── Detail panel for airport flight ─────────────────────────────────────
function FlightDetailPanel({ flight, theme }: { flight: AirportFlight; theme: 'light' | 'dark' }) {
  const t = av(theme);
  const styles = useStyles();

  const fields: [string, string | null][] = [
    ['ICAO24', flight.icao24],
    ['Callsign', flight.callsign],
    ['Origin', flight.from],
    ['Destination', flight.to],
    ['Departed', flight.departed],
    ['Arrived', flight.arrived],
  ];

  return (
    <div>
      <div style={{ fontSize: '14px', fontWeight: 600, color: t.brand, marginBottom: '14px' }}>
        ✈️ {flight.callsign || flight.icao24}
      </div>
      <div className={styles.stateGrid} style={{ gridTemplateColumns: '1fr' }}>
        {fields.map(([label, value]) => (
          <div key={label} className={styles.statItem} style={{ background: t.surface, border: `1px solid ${t.border}` }}>
            <div style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', color: t.textWeak, marginBottom: '4px' }}>
              {label}
            </div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: t.text }}>
              {value || '—'}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Airport Flights (Departures / Arrivals) ─────────────────────────────
function AirportFlightsView({ data, theme }: { data: AirportFlightsData; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = av(theme);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const isDepartures = data.type === 'departures';

  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };
  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px', verticalAlign: 'middle',
  };

  const selected = selectedIdx !== null ? data.flights[selectedIdx] : null;

  return (
    <>
      <div className={styles.splitLayout} style={{ borderRight: selected ? undefined : 'none' }}>
        <div className={styles.listPane} style={{ borderRightColor: selected ? t.border : 'transparent', flex: selected ? 3 : 1 }}>
          <Table size="small" style={{ borderCollapse: 'collapse' }}>
            <TableHeader>
              <TableRow style={{ background: t.headerBg }}>
                <TableHeaderCell style={headerCellStyle}>Callsign</TableHeaderCell>
                <TableHeaderCell style={headerCellStyle}>ICAO24</TableHeaderCell>
                <TableHeaderCell style={headerCellStyle}>{isDepartures ? 'Destination' : 'Origin'}</TableHeaderCell>
                <TableHeaderCell style={headerCellStyle}>{isDepartures ? 'Departed' : 'Arrived'}</TableHeaderCell>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.flights.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className={styles.empty}>
                    <Text style={{ color: t.textWeak }}>No {data.type} found for {data.airport}.</Text>
                  </TableCell>
                </TableRow>
              )}
              {data.flights.map((fl, idx) => (
                <TableRow
                  key={idx}
                  onClick={() => setSelectedIdx(selectedIdx === idx ? null : idx)}
                  style={{
                    cursor: 'pointer',
                    borderBottom: `1px solid ${t.border}`,
                    background: selectedIdx === idx
                      ? (theme === 'dark' ? '#1a3050' : '#e8f0fe')
                      : 'transparent',
                  }}
                >
                  <TableCell style={cellStyle}>
                    <span style={{ fontWeight: 600, color: t.brand }}>{fl.callsign || '—'}</span>
                  </TableCell>
                  <TableCell style={{ ...cellStyle, fontFamily: 'monospace', fontSize: '11px' }}>{fl.icao24}</TableCell>
                  <TableCell style={cellStyle}>{isDepartures ? (fl.to || '—') : (fl.from || '—')}</TableCell>
                  <TableCell style={cellStyle}>{isDepartures ? (fl.departed || '—') : (fl.arrived || '—')}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        {selected && (
          <div className={styles.detailPane} style={{ background: t.surface, borderTop: 'none' }}>
            <FlightDetailPanel flight={selected} theme={theme} />
          </div>
        )}
      </div>
    </>
  );
}

// ── Aircraft Flights (by ICAO24) ────────────────────────────────────────
function FlightsView({ data, theme }: { data: FlightsData; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = av(theme);

  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };
  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px', verticalAlign: 'middle',
  };

  return (
    <Table size="small" style={{ borderCollapse: 'collapse' }}>
      <TableHeader>
        <TableRow style={{ background: t.headerBg }}>
          <TableHeaderCell style={headerCellStyle}>Callsign</TableHeaderCell>
          <TableHeaderCell style={headerCellStyle}>From</TableHeaderCell>
          <TableHeaderCell style={headerCellStyle}>To</TableHeaderCell>
          <TableHeaderCell style={headerCellStyle}>Departed</TableHeaderCell>
          <TableHeaderCell style={headerCellStyle}>Arrived</TableHeaderCell>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.flights.length === 0 && (
          <TableRow>
            <TableCell colSpan={5} className={styles.empty}>
              <Text style={{ color: t.textWeak }}>No flights found for {data.icao24}.</Text>
            </TableCell>
          </TableRow>
        )}
        {data.flights.map((fl, idx) => (
          <TableRow key={idx} style={{ borderBottom: `1px solid ${t.border}` }}>
            <TableCell style={cellStyle}>
              <span style={{ fontWeight: 600, color: t.brand }}>{fl.callsign || '—'}</span>
            </TableCell>
            <TableCell style={cellStyle}>{fl.from || '—'}</TableCell>
            <TableCell style={cellStyle}>{fl.to || '—'}</TableCell>
            <TableCell style={cellStyle}>{fl.departed || '—'}</TableCell>
            <TableCell style={cellStyle}>{fl.arrived || '—'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// ── Aircraft State ──────────────────────────────────────────────────────
function StateView({ data, theme }: { data: AircraftStateData; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = av(theme);

  if (!data.found) {
    return (
      <div className={styles.empty}>
        <Text style={{ color: t.textWeak }}>
          No live state found for <strong>{data.icao24}</strong>. Aircraft may be on the ground or out of coverage.
        </Text>
      </div>
    );
  }

  const statusColor = data.on_ground ? t.warning : t.success;
  const statusLabel = data.on_ground ? '🛬 On Ground' : '🛫 Airborne';

  const fields: [string, string][] = [
    ['Callsign', data.callsign || '—'],
    ['Status', statusLabel],
    ['Country', data.origin_country || '—'],
    ['Latitude', data.latitude != null ? data.latitude.toFixed(4) + '°' : '—'],
    ['Longitude', data.longitude != null ? data.longitude.toFixed(4) + '°' : '—'],
    ['Altitude', data.altitude_ft != null ? `${data.altitude_ft.toLocaleString()} ft` : '—'],
    ['Speed', data.velocity_kmh != null ? `${data.velocity_kmh} km/h` : '—'],
    ['Heading', data.heading_deg != null ? `${data.heading_deg}° ${data.heading_compass || ''}` : '—'],
    ['Vertical Rate', data.vertical_rate != null ? `${data.vertical_rate} m/s` : '—'],
    ['Last Contact', data.last_contact || '—'],
  ];

  return (
    <div className={styles.stateCard}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
        <span style={{ fontSize: '11px', fontWeight: 600, padding: '3px 10px', borderRadius: '12px', background: statusColor + '22', color: statusColor, border: `1px solid ${statusColor}44` }}>
          {statusLabel}
        </span>
        <span style={{ fontFamily: 'monospace', fontSize: '12px', color: t.textWeak }}>{data.icao24}</span>
      </div>
      <div className={styles.stateGrid}>
        {fields.map(([label, value]) => (
          <div key={label} className={styles.statItem} style={{ background: t.surface, border: `1px solid ${t.border}` }}>
            <div style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', color: t.textWeak, marginBottom: '4px' }}>
              {label}
            </div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: t.text }}>
              {value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Track View ──────────────────────────────────────────────────────────
function TrackView({ data, theme }: { data: TrackData; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = av(theme);

  if (!data.found) {
    return (
      <div className={styles.empty}>
        <Text style={{ color: t.textWeak }}>No track found for <strong>{data.icao24}</strong>.</Text>
      </div>
    );
  }

  const fields: [string, string][] = [
    ['Callsign', data.callsign || '—'],
    ['Waypoints', data.waypoints != null ? String(data.waypoints) : '—'],
    ['Start Time', data.start_time || '—'],
    ['End Time', data.end_time || '—'],
    ['Start Position', data.first_position ? `${data.first_position.lat.toFixed(4)}, ${data.first_position.lon.toFixed(4)}` : '—'],
    ['End Position', data.last_position ? `${data.last_position.lat.toFixed(4)}, ${data.last_position.lon.toFixed(4)}` : '—'],
  ];

  return (
    <div className={styles.stateCard}>
      <div className={styles.stateGrid}>
        {fields.map(([label, value]) => (
          <div key={label} className={styles.statItem} style={{ background: t.surface, border: `1px solid ${t.border}` }}>
            <div style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', color: t.textWeak, marginBottom: '4px' }}>
              {label}
            </div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: t.text }}>
              {value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Footer ──────────────────────────────────────────────────────────────
function AviationFooter({ theme }: { theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = av(theme);
  return (
    <div className={styles.mcpFooter} style={{
      background: theme === 'dark' ? '#0d1a2a' : '#f0f4f9',
      borderTop: `1px solid ${t.border}`,
      color: t.textWeak,
    }}>
      <span>⚡ <strong>MCP Widget</strong> · Flight Tracker</span>
      <span>⚓ GTC</span>
    </div>
  );
}

// ── Skeleton Loading ────────────────────────────────────────────────────
function SkeletonLoading() {
  return (
    <div style={{ padding: '16px' }}>
      <style>{`
        @keyframes ftShimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        .ft-skel {
          height: 14px;
          border-radius: 4px;
          background: linear-gradient(90deg, #e8e8e8 25%, #f5f5f5 50%, #e8e8e8 75%);
          background-size: 200% 100%;
          animation: ftShimmer 1.5s infinite;
        }
        [data-theme="dark"] .ft-skel {
          background: linear-gradient(90deg, #333 25%, #444 50%, #333 75%);
          background-size: 200% 100%;
        }
      `}</style>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <div className="ft-skel" style={{ width: '200px', height: '24px' }} />
        <div className="ft-skel" style={{ width: '80px', height: '24px' }} />
      </div>
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
          <div className="ft-skel" style={{ width: '100px' }} />
          <div className="ft-skel" style={{ width: '80px' }} />
          <div className="ft-skel" style={{ width: '140px' }} />
          <div className="ft-skel" style={{ width: '120px' }} />
        </div>
      ))}
    </div>
  );
}

// ── Resolve title / icon / count ────────────────────────────────────────
function resolveHeader(data: FlightToolData): { icon: string; title: string; count: string } {
  if (isAirportFlights(data)) {
    const label = data.type === 'departures' ? 'Departures' : 'Arrivals';
    return { icon: data.type === 'departures' ? '🛫' : '🛬', title: `${data.airport} ${label}`, count: `${data.total_flights} flight${data.total_flights !== 1 ? 's' : ''}` };
  }
  if (isFlights(data)) {
    return { icon: '✈️', title: `Flights · ${data.icao24}`, count: `${data.total_flights} flight${data.total_flights !== 1 ? 's' : ''}` };
  }
  if (isTrack(data)) {
    return { icon: '📍', title: `Track · ${data.icao24}`, count: data.found ? `${data.waypoints ?? 0} waypoints` : 'not found' };
  }
  if (isState(data)) {
    return { icon: '📡', title: `State · ${data.icao24}`, count: data.found ? 'live' : 'not found' };
  }
  return { icon: '✈️', title: 'Flight Tracker', count: '' };
}

// ── Global CSS ──────────────────────────────────────────────────────────
const ftStyleId = 'ft-global-style';
if (typeof document !== 'undefined' && !document.getElementById(ftStyleId)) {
  const style = document.createElement('style');
  style.id = ftStyleId;
  style.textContent = `
    [data-theme="dark"] .ft-row:hover,
    .fui-FluentProvider[data-theme="dark"] .ft-row:hover {
      background: #1a3050;
    }
    .ft-row:hover {
      background: #f0f4f9;
    }
  `;
  document.head.appendChild(style);
}

// ── Main App ────────────────────────────────────────────────────────────
export function FlightApp() {
  const styles = useStyles();
  const data = useToolData<FlightToolData>();
  const { callTool } = useMcpBridge();
  const theme = useTheme();
  const t = av(theme);

  // Loading state
  if (!data) {
    return (
      <div className={styles.shell}>
        <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
          <div className={styles.headerBar} style={{ background: brandGrad(theme) }}>
            <div className={styles.headerLeft}>
              <span style={{ fontSize: '18px' }}>✈️</span>
              <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Flight Tracker</span>
            </div>
            <ExpandButton />
          </div>
          <SkeletonLoading />
          <AviationFooter theme={theme} />
        </div>
      </div>
    );
  }

  // Error state
  if ('error' in data && data.error) {
    return (
      <div className={styles.shell}>
        <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
          <div className={styles.headerBar} style={{ background: brandGrad(theme) }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>⚠️ Error</span>
          </div>
          <div className={styles.errorBanner} style={{
            background: theme === 'dark' ? '#3c1a1a' : '#fef1ee',
            color: theme === 'dark' ? '#ff9999' : '#ba0517',
            borderBottom: `1px solid ${t.border}`,
          }}>
            {'message' in data ? (data as any).message : 'An error occurred while fetching flight data.'}
          </div>
          <AviationFooter theme={theme} />
        </div>
      </div>
    );
  }

  const header = resolveHeader(data);

  // Data content
  let content: React.ReactNode;
  if (isAirportFlights(data)) {
    content = <AirportFlightsView data={data} theme={theme} />;
  } else if (isFlights(data)) {
    content = <FlightsView data={data} theme={theme} />;
  } else if (isState(data)) {
    content = <StateView data={data} theme={theme} />;
  } else if (isTrack(data)) {
    content = <TrackView data={data} theme={theme} />;
  } else {
    content = (
      <div className={styles.empty}>
        <Text style={{ color: t.textWeak }}>Unrecognized data format.</Text>
      </div>
    );
  }

  return (
    <div className={styles.shell}>
      <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.background }}>
        <div className={styles.headerBar} style={{ background: brandGrad(theme) }}>
          <div className={styles.headerLeft}>
            <span style={{ fontSize: '18px' }}>{header.icon}</span>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{header.title}</span>
            {header.count && (
              <Badge appearance="filled" size="small"
                style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
                {header.count}
              </Badge>
            )}
          </div>
          <ExpandButton />
        </div>

        {content}

        <AviationFooter theme={theme} />
      </div>
    </div>
  );
}
