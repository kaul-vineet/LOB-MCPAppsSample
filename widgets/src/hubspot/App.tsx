import React, { useState, useCallback, useEffect } from 'react';
import {
  Button,
  Field,
  Input,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
  tokens,
  makeStyles,
} from '@fluentui/react-components';
import {
  EditRegular,
  AddRegular,
  ArrowLeftRegular,
  DismissRegular,
  MailRegular,
  PeopleRegular,
  PersonRegular,
} from '@fluentui/react-icons';
import { useToolData, useMcpBridge, useTheme } from '../shared/McpBridge';
import { McpFooter } from '../shared/McpFooter';
import { useToast } from '../shared/Toast';
import type { HubSpotData, Email, ContactList, Contact } from './types';

// HubSpot Canvas palette
const HS = {
  coral: '#FF7A59',
  coralDark: '#E8563D',
  coralHover: 'rgba(255,122,89,0.08)',
  teal: '#00BDA5',
  error: '#F2545B',
  manual: '#7C98B6',
  // Light
  bgLight: '#ffffff',
  surfaceLight: '#F5F8FA',
  textLight: '#33475B',
  textLightSec: '#516F90',
  borderLight: '#CBD6E2',
  barBgLight: '#EAF0F6',
  // Dark
  coralDarkMode: '#FF8F73',
  tealDarkMode: '#33D6C1',
  bgDark: '#1a1a2e',
  surfaceDark: '#16213e',
  textDark: '#F5F8FA',
  textDarkSec: '#99ACC2',
  borderDark: '#2C3E50',
  barBgDark: '#2C3E50',
};

const useStyles = makeStyles({
  shell: {
    maxWidth: '1120px',
    margin: '0 auto',
    padding: '20px 24px',
    fontFamily: tokens.fontFamilyBase,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    marginBottom: '16px',
    borderRadius: '4px',
    flexWrap: 'wrap',
    gap: '8px',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '12px',
    marginBottom: '16px',
  },
  metricCard: {
    padding: '16px',
    borderRadius: '8px',
    textAlign: 'center',
  },
  tableWrapper: {
    borderRadius: '8px',
    overflow: 'hidden',
  },
  headerCell: {
    fontWeight: tokens.fontWeightSemibold,
    fontSize: '14px',
    padding: '12px 16px',
  },
  cell: {
    padding: '12px 16px',
    verticalAlign: 'middle',
    fontSize: '14px',
    lineHeight: '1.5',
  },
  editPanel: {
    padding: '16px 20px',
  },
  editPanelTitle: {
    fontSize: tokens.fontSizeBase400,
    fontWeight: tokens.fontWeightSemibold,
    marginBottom: '12px',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    marginBottom: '16px',
  },
  formActions: {
    display: 'flex',
    gap: '8px',
    justifyContent: 'flex-end',
  },
  breadcrumb: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '12px',
    fontSize: '14px',
  },
  breadcrumbLink: {
    cursor: 'pointer',
    fontWeight: 600,
    fontSize: '14px',
    background: 'none',
    border: 'none',
    padding: 0,
    textDecoration: 'none',
    ':hover': { textDecoration: 'underline' },
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '60px 20px',
    gap: '16px',
  },
  badge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '3px',
    fontSize: '12px',
    fontWeight: 600,
    lineHeight: '1.5',
  },
  rateCell: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  rateBar: {
    display: 'inline-block',
    height: '6px',
    borderRadius: '3px',
    width: '60px',
    verticalAlign: 'middle',
    position: 'relative' as const,
    overflow: 'hidden',
  },
  lifecycleDot: {
    display: 'inline-block',
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    marginRight: '6px',
    verticalAlign: 'middle',
  },
  emptyState: {
    textAlign: 'center',
    padding: '48px 20px',
  },
});

// ── Helpers ──────────────────────────────────────────────────────────
function pct(num: number, denom: number): string {
  if (!denom || denom === 0) return '0.0%';
  return (num / denom * 100).toFixed(1) + '%';
}

function pctNum(num: number, denom: number): number {
  if (!denom || denom === 0) return 0;
  return num / denom * 100;
}

function fmtNum(n: number | undefined): string {
  return (n || 0).toLocaleString();
}

// ── Shimmer CSS & Skeleton Components ────────────────────────────────
const shimmerCSS = `
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.skel {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, #e8e8e8 25%, #f5f5f5 50%, #e8e8e8 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skel-dark {
  background: linear-gradient(90deg, #2C3E50 25%, #3a4f65 50%, #2C3E50 75%);
  background-size: 200% 100%;
}`;

let shimmerInjected = false;
function ensureShimmerCSS() {
  if (shimmerInjected) return;
  const style = document.createElement('style');
  style.textContent = shimmerCSS;
  document.head.appendChild(style);
  shimmerInjected = true;
}

function SkeletonBlock({ width = '100%', height = 14, style }: { width?: string | number; height?: number; style?: React.CSSProperties }) {
  const theme = useTheme();
  useEffect(ensureShimmerCSS, []);
  return <div className={theme === 'dark' ? 'skel skel-dark' : 'skel'} style={{ width, height, ...style }} />;
}

function SkeletonMetricCard({ isFullscreen }: { isFullscreen?: boolean }) {
  const c = useHsColors();
  const styles = useStyles();
  return (
    <div
      className={styles.metricCard}
      style={{
        backgroundColor: c.bg,
        border: `1px solid ${c.border}`,
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        padding: isFullscreen ? '24px' : '16px',
      }}
    >
      <SkeletonBlock width="50%" height={isFullscreen ? 32 : 24} style={{ margin: '0 auto 8px' }} />
      <SkeletonBlock width="40%" height={12} style={{ margin: '0 auto' }} />
    </div>
  );
}

function EmailsSkeleton({ isFullscreen }: { isFullscreen?: boolean }) {
  const styles = useStyles();
  const c = useHsColors();
  const cols = isFullscreen ? 7 : 5;
  return (
    <>
      <div
        className={styles.header}
        style={{ backgroundColor: c.bg, border: `1px solid ${c.border}`, borderLeftWidth: '4px', borderLeftColor: c.border }}
      >
        <div>
          <SkeletonBlock width={180} height={18} />
          <SkeletonBlock width={100} height={13} style={{ marginTop: 6 }} />
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${isFullscreen ? 6 : 4}, 1fr)`, gap: '12px', marginBottom: '16px' }}>
        {Array.from({ length: isFullscreen ? 6 : 4 }).map((_, i) => (
          <SkeletonMetricCard key={i} isFullscreen={isFullscreen} />
        ))}
      </div>
      <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: c.bg }}>
              {Array.from({ length: cols }).map((_, i) => (
                <TableHeaderCell key={i} className={styles.headerCell} style={{ borderBottom: `2px solid ${c.border}` }}>
                  <SkeletonBlock width={50 + i * 10} />
                </TableHeaderCell>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, row) => (
              <TableRow key={row} style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}>
                {Array.from({ length: cols }).map((_, col) => (
                  <TableCell key={col} className={styles.cell}>
                    <SkeletonBlock width={`${50 + col * 8}%`} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}

function ListsSkeleton() {
  const styles = useStyles();
  const c = useHsColors();
  return (
    <>
      <div className={styles.header} style={{ backgroundColor: c.bg, border: `1px solid ${c.border}`, borderLeftWidth: '4px', borderLeftColor: c.border }}>
        <div>
          <SkeletonBlock width={160} height={18} />
          <SkeletonBlock width={80} height={13} style={{ marginTop: 6 }} />
        </div>
      </div>
      <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: c.bg }}>
              {['Name', 'Type', 'Size', ''].map((_, i) => (
                <TableHeaderCell key={i} className={styles.headerCell} style={{ borderBottom: `2px solid ${c.border}` }}>
                  <SkeletonBlock width={60 + i * 12} />
                </TableHeaderCell>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, row) => (
              <TableRow key={row} style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}>
                {Array.from({ length: 4 }).map((_, col) => (
                  <TableCell key={col} className={styles.cell}>
                    <SkeletonBlock width={`${45 + col * 10}%`} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}

function ContactsSkeleton() {
  const styles = useStyles();
  const c = useHsColors();
  return (
    <>
      <div className={styles.header} style={{ backgroundColor: c.bg, border: `1px solid ${c.border}`, borderLeftWidth: '4px', borderLeftColor: c.border }}>
        <div>
          <SkeletonBlock width={140} height={18} />
          <SkeletonBlock width={90} height={13} style={{ marginTop: 6 }} />
        </div>
      </div>
      <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: c.bg }}>
              {Array.from({ length: 5 }).map((_, i) => (
                <TableHeaderCell key={i} className={styles.headerCell} style={{ borderBottom: `2px solid ${c.border}` }}>
                  <SkeletonBlock width={55 + i * 15} />
                </TableHeaderCell>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, row) => (
              <TableRow key={row} style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}>
                {Array.from({ length: 5 }).map((_, col) => (
                  <TableCell key={col} className={styles.cell}>
                    <SkeletonBlock width={`${40 + col * 12}%`} />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}

function FullscreenToggle({ isFullscreen, onToggle }: { isFullscreen: boolean; onToggle: () => void }) {
  const c = useHsColors();
  return (
    <button
      onClick={onToggle}
      style={{
        backgroundColor: 'transparent',
        border: `1px solid ${c.border}`,
        color: c.textSec,
        borderRadius: '3px',
        padding: '8px 12px',
        fontWeight: 600,
        cursor: 'pointer',
        fontSize: '13px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        whiteSpace: 'nowrap' as const,
      }}
    >
      {isFullscreen ? '✕ Exit Full Screen' : '⛶ Expand'}
    </button>
  );
}

// ── Themed style helpers ─────────────────────────────────────────────
function useHsColors() {
  const theme = useTheme();
  const dark = theme === 'dark';
  return {
    bg: dark ? HS.bgDark : HS.bgLight,
    surface: dark ? HS.surfaceDark : HS.surfaceLight,
    text: dark ? HS.textDark : HS.textLight,
    textSec: dark ? HS.textDarkSec : HS.textLightSec,
    border: dark ? HS.borderDark : HS.borderLight,
    coral: dark ? HS.coralDarkMode : HS.coral,
    coralDark: HS.coralDark,
    teal: dark ? HS.tealDarkMode : HS.teal,
    error: HS.error,
    manual: HS.manual,
    hoverBg: dark ? 'rgba(255,143,115,0.10)' : '#F5F8FA',
    editPanelBg: dark ? '#1e2a45' : '#fef6f3',
    editPanelBorder: dark ? HS.coralDarkMode : HS.coral,
    badgeDraft: dark ? '#3a4a5c' : '#CBD6E2',
    badgeDraftText: dark ? '#d0d0d0' : '#33475B',
    barBg: dark ? HS.barBgDark : HS.barBgLight,
  };
}

// ── Lifecycle dot color ──────────────────────────────────────────────
function lifecycleDotColor(stage: string): string {
  switch (stage?.toLowerCase()) {
    case 'customer': return '#00BDA5';
    case 'lead': return '#FF7A59';
    case 'subscriber': return '#0091AE';
    default: return '#7C98B6';
  }
}

// ── MetricCard ───────────────────────────────────────────────────────
function MetricCard({ label, value, negative, isFullscreen }: { label: string; value: string | number; negative?: boolean; isFullscreen?: boolean }) {
  const styles = useStyles();
  const c = useHsColors();
  return (
    <div
      className={styles.metricCard}
      style={{
        backgroundColor: c.bg,
        border: `1px solid ${c.border}`,
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        padding: isFullscreen ? '24px' : '16px',
      }}
    >
      <div style={{ fontSize: isFullscreen ? '32px' : '24px', fontWeight: 700, color: negative ? c.error : c.teal, lineHeight: 1.2 }}>
        {value}
      </div>
      <div style={{ fontSize: isFullscreen ? '13px' : '12px', color: c.textSec, marginTop: '4px' }}>{label}</div>
    </div>
  );
}

// ── Emails View ──────────────────────────────────────────────────────
function EmailsView({ items, total, onNavigateLists, callTool, toast, isFullscreen, onToggleFullscreen }: {
  items: Email[];
  total?: number;
  onNavigateLists: () => void;
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
}){
  const styles = useStyles();
  const c = useHsColors();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({ name: '', subject: '' });
  const [saving, setSaving] = useState(false);

  const openEdit = (em: Email) => {
    setEditingId(em.id);
    setFormData({ name: em.name, subject: em.subject });
  };
  const cancel = () => setEditingId(null);

  const handleSave = async () => {
    setSaving(true);
    try {
      await callTool('update_email', { email_id: editingId, name: formData.name, subject: formData.subject });
      toast('Email updated');
      cancel();
    } catch (e: any) {
      toast(e.message || 'Failed to update email', 'error');
    } finally {
      setSaving(false);
    }
  };

  // Compute aggregate metrics
  const totalSent = items.reduce((s, em) => s + (em.stats.sent || 0), 0);
  const totalBounced = items.reduce((s, em) => s + (em.stats.bounced || 0), 0);
  const totalDelivered = items.reduce((s, em) => s + (em.stats.delivered || 0), 0);
  const totalOpened = items.reduce((s, em) => s + (em.stats.opened || 0), 0);
  const totalClicked = items.reduce((s, em) => s + (em.stats.clicked || 0), 0);
  const totalUnsub = items.reduce((s, em) => s + (em.stats.unsubscribed || 0), 0);
  const avgOpenRate = totalDelivered ? (totalOpened / totalDelivered * 100).toFixed(1) : '0.0';
  const avgClickRate = totalDelivered ? (totalClicked / totalDelivered * 100).toFixed(1) : '0.0';

  return (
    <>
      {/* Header bar with left accent border */}
      <div
        className={styles.header}
        style={{
          backgroundColor: c.bg,
          borderLeft: `4px solid ${c.coral}`,
          border: `1px solid ${c.border}`,
          borderLeftWidth: '4px',
          borderLeftColor: c.coral,
        }}
      >
        <div>
          <div className={styles.titleRow}>
            <MailRegular style={{ color: c.coral, fontSize: 22 }} />
            <Text style={{ color: c.text, fontSize: '18px', fontWeight: 600 }}>Marketing Emails</Text>
          </div>
          <Text style={{ color: c.textSec, fontSize: '13px', marginLeft: '32px' }}>
            {total ?? items.length} campaigns
          </Text>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {onToggleFullscreen && <FullscreenToggle isFullscreen={!!isFullscreen} onToggle={onToggleFullscreen} />}
          <button
            onClick={onNavigateLists}
            style={{
              backgroundColor: 'transparent',
              border: `1px solid ${c.coral}`,
              color: c.coral,
              borderRadius: '3px',
              padding: '8px 24px',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <PeopleRegular style={{ fontSize: 16 }} /> View Lists
          </button>
        </div>
      </div>

      {/* Metrics summary cards */}
      <div className={styles.metricsGrid} style={isFullscreen ? { gridTemplateColumns: 'repeat(6, 1fr)' } : undefined}>
        <MetricCard label="Total Sent" value={fmtNum(totalSent)} isFullscreen={isFullscreen} />
        {isFullscreen && <MetricCard label="Delivered" value={fmtNum(totalDelivered)} isFullscreen />}
        <MetricCard label="Avg Open Rate" value={avgOpenRate + '%'} isFullscreen={isFullscreen} />
        <MetricCard label="Avg Click Rate" value={avgClickRate + '%'} isFullscreen={isFullscreen} />
        <MetricCard label="Total Bounced" value={fmtNum(totalBounced)} negative isFullscreen={isFullscreen} />
        {isFullscreen && <MetricCard label="Unsubscribed" value={fmtNum(totalUnsub)} negative isFullscreen />}
      </div>

      {/* Emails table — Canvas style */}
      <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: c.bg }}>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Name</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Subject</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Status</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Sent</TableHeaderCell>
              {isFullscreen && <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Delivered</TableHeaderCell>}
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Open Rate</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Click Rate</TableHeaderCell>
              {isFullscreen && <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Bounced</TableHeaderCell>}
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}`, width: 60 }} />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((em) => {
              const openRate = pctNum(em.stats.opened, em.stats.delivered);
              const clickRate = pctNum(em.stats.clicked, em.stats.delivered);
              return (
                <React.Fragment key={em.id}>
                  <TableRow
                    style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}
                    onMouseEnter={e => (e.currentTarget.style.backgroundColor = c.hoverBg)}
                    onMouseLeave={e => (e.currentTarget.style.backgroundColor = c.bg)}
                  >
                    <TableCell className={styles.cell} style={{ color: c.text, fontWeight: 600 }}>{em.name}</TableCell>
                    <TableCell className={styles.cell} style={{ color: c.text }}>{em.subject}</TableCell>
                    <TableCell className={styles.cell}>
                      {em.status?.toUpperCase() === 'PUBLISHED' ? (
                        <span className={styles.badge} style={{ backgroundColor: c.teal, color: '#fff' }}>PUBLISHED</span>
                      ) : (
                        <span className={styles.badge} style={{ backgroundColor: c.badgeDraft, color: c.badgeDraftText }}>{em.status?.toUpperCase() || 'DRAFT'}</span>
                      )}
                    </TableCell>
                    <TableCell className={styles.cell} style={{ color: c.text }}>{fmtNum(em.stats.sent)}</TableCell>
                    {isFullscreen && <TableCell className={styles.cell} style={{ color: c.text }}>{fmtNum(em.stats.delivered)}</TableCell>}
                    <TableCell className={styles.cell}>
                      <div className={styles.rateCell}>
                        <span
                          className={styles.rateBar}
                          style={{ backgroundColor: c.barBg }}
                        >
                          <span style={{
                            display: 'block',
                            height: '100%',
                            width: `${Math.min(openRate, 100)}%`,
                            borderRadius: '3px',
                            background: `linear-gradient(90deg, ${c.coral}, ${c.teal})`,
                          }} />
                        </span>
                        <span style={{ fontWeight: 700, fontSize: '13px', color: c.teal }}>{pct(em.stats.opened, em.stats.delivered)}</span>
                      </div>
                    </TableCell>
                    <TableCell className={styles.cell}>
                      <div className={styles.rateCell}>
                        <span
                          className={styles.rateBar}
                          style={{ backgroundColor: c.barBg }}
                        >
                          <span style={{
                            display: 'block',
                            height: '100%',
                            width: `${Math.min(clickRate, 100)}%`,
                            borderRadius: '3px',
                            background: `linear-gradient(90deg, ${c.coral}, ${c.teal})`,
                          }} />
                        </span>
                        <span style={{ fontWeight: 700, fontSize: '13px', color: c.coral }}>{pct(em.stats.clicked, em.stats.delivered)}</span>
                      </div>
                    </TableCell>
                    {isFullscreen && <TableCell className={styles.cell} style={{ color: c.error }}>{fmtNum(em.stats.bounced)}</TableCell>}
                    <TableCell className={styles.cell}>
                      <Button appearance="subtle" icon={<EditRegular />} size="small" title="Edit" onClick={() => openEdit(em)} />
                    </TableCell>
                  </TableRow>
                  {editingId === em.id && (
                    <TableRow>
                      <TableCell colSpan={isFullscreen ? 9 : 7} style={{ padding: 0 }}>
                        <div className={styles.editPanel} style={{ backgroundColor: c.editPanelBg, borderTop: `2px solid ${c.editPanelBorder}` }}>
                          <div className={styles.editPanelTitle} style={{ color: c.text }}>✏️ Edit Email</div>
                          <div className={styles.formGrid}>
                            <Field label={<span style={{ fontSize: '12px', color: c.textSec, fontWeight: 600, textTransform: 'uppercase' }}>Name</span>}>
                              <Input
                                value={formData.name}
                                onChange={(_, d) => setFormData(f => ({ ...f, name: d.value }))}
                                style={{ border: `1px solid ${c.border}`, borderRadius: '3px' }}
                              />
                            </Field>
                            <Field label={<span style={{ fontSize: '12px', color: c.textSec, fontWeight: 600, textTransform: 'uppercase' }}>Subject</span>}>
                              <Input
                                value={formData.subject}
                                onChange={(_, d) => setFormData(f => ({ ...f, subject: d.value }))}
                                style={{ border: `1px solid ${c.border}`, borderRadius: '3px' }}
                              />
                            </Field>
                          </div>
                          <div className={styles.formActions}>
                            <button
                              onClick={cancel}
                              disabled={saving}
                              style={{
                                backgroundColor: 'transparent',
                                border: `1px solid ${c.coral}`,
                                color: c.coral,
                                borderRadius: '3px',
                                padding: '8px 24px',
                                fontWeight: 600,
                                cursor: 'pointer',
                                fontSize: '14px',
                              }}
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleSave}
                              disabled={saving}
                              style={{
                                backgroundColor: c.coral,
                                border: 'none',
                                color: '#fff',
                                borderRadius: '3px',
                                padding: '8px 24px',
                                fontWeight: 600,
                                cursor: 'pointer',
                                fontSize: '14px',
                              }}
                            >
                              {saving ? 'Saving…' : 'Save'}
                            </button>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </>
  );
}

// ── Lists View ───────────────────────────────────────────────────────
function ListsView({ items, total, onBack, onViewContacts, callTool, toast, isFullscreen, onToggleFullscreen }: {
  items: ContactList[];
  total?: number;
  onBack: () => void;
  onViewContacts: (listId: string) => void;
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
}){
  const styles = useStyles();
  const c = useHsColors();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formName, setFormName] = useState('');
  const [saving, setSaving] = useState(false);

  const openEdit = (li: ContactList) => {
    setEditingId(li.id);
    setFormName(li.name);
  };
  const cancel = () => setEditingId(null);

  const handleSave = async () => {
    setSaving(true);
    try {
      await callTool('update_list', { list_id: editingId, name: formName });
      toast('List renamed');
      cancel();
    } catch (e: any) {
      toast(e.message || 'Failed to update list', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className={styles.breadcrumb}>
        <button className={styles.breadcrumbLink} style={{ color: c.coral }} onClick={onBack}>Emails</button>
        <Text style={{ color: c.textSec, fontSize: '14px' }}>&gt;</Text>
        <Text style={{ color: c.text, fontSize: '14px', fontWeight: 600 }}>Lists</Text>
      </div>

      <div
        className={styles.header}
        style={{
          backgroundColor: c.bg,
          borderLeft: `4px solid ${c.coral}`,
          border: `1px solid ${c.border}`,
          borderLeftWidth: '4px',
          borderLeftColor: c.coral,
        }}
      >
        <div>
          <div className={styles.titleRow}>
            <PeopleRegular style={{ color: c.coral, fontSize: 22 }} />
            <Text style={{ color: c.text, fontSize: '18px', fontWeight: 600 }}>Contact Lists</Text>
          </div>
          <Text style={{ color: c.textSec, fontSize: '13px', marginLeft: '32px' }}>
            {total ?? items.length} lists
          </Text>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {onToggleFullscreen && <FullscreenToggle isFullscreen={!!isFullscreen} onToggle={onToggleFullscreen} />}
          <button
            onClick={onBack}
            style={{
              backgroundColor: 'transparent',
              border: `1px solid ${c.coral}`,
              color: c.coral,
              borderRadius: '3px',
              padding: '8px 24px',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <ArrowLeftRegular style={{ fontSize: 14 }} /> Back to Emails
          </button>
        </div>
      </div>

      <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: c.bg }}>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Name</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Type</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Size</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}`, width: 180 }} />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((li) => (
              <React.Fragment key={li.id}>
                <TableRow
                  style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = c.hoverBg)}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = c.bg)}
                >
                  <TableCell className={styles.cell} style={{ color: c.text, fontWeight: 600 }}>{li.name}</TableCell>
                  <TableCell className={styles.cell}>
                    {li.type?.toUpperCase() === 'MANUAL' ? (
                      <span className={styles.badge} style={{ backgroundColor: c.manual, color: '#fff' }}>MANUAL</span>
                    ) : (
                      <span className={styles.badge} style={{ backgroundColor: c.teal, color: '#fff' }}>DYNAMIC</span>
                    )}
                  </TableCell>
                  <TableCell className={styles.cell} style={{ color: c.text }}>{fmtNum(li.size)}</TableCell>
                  <TableCell className={styles.cell}>
                    <button
                      onClick={() => onViewContacts(li.id)}
                      style={{
                        backgroundColor: c.coral,
                        border: 'none',
                        color: '#fff',
                        borderRadius: '3px',
                        padding: '6px 16px',
                        fontWeight: 600,
                        cursor: 'pointer',
                        fontSize: '13px',
                        marginRight: '4px',
                      }}
                    >
                      View →
                    </button>
                    <Button appearance="subtle" icon={<EditRegular />} size="small" title="Edit" onClick={() => openEdit(li)} />
                  </TableCell>
                </TableRow>
                {editingId === li.id && (
                  <TableRow>
                    <TableCell colSpan={4} style={{ padding: 0 }}>
                      <div className={styles.editPanel} style={{ backgroundColor: c.editPanelBg, borderTop: `2px solid ${c.editPanelBorder}` }}>
                        <div className={styles.editPanelTitle} style={{ color: c.text }}>✏️ Rename List</div>
                        <div style={{ marginBottom: 12, maxWidth: 320 }}>
                          <Field label={<span style={{ fontSize: '12px', color: c.textSec, fontWeight: 600, textTransform: 'uppercase' }}>Name</span>}>
                            <Input value={formName} onChange={(_, d) => setFormName(d.value)} style={{ border: `1px solid ${c.border}`, borderRadius: '3px' }} />
                          </Field>
                        </div>
                        <div className={styles.formActions}>
                          <button
                            onClick={cancel}
                            disabled={saving}
                            style={{
                              backgroundColor: 'transparent',
                              border: `1px solid ${c.coral}`,
                              color: c.coral,
                              borderRadius: '3px',
                              padding: '8px 24px',
                              fontWeight: 600,
                              cursor: 'pointer',
                              fontSize: '14px',
                            }}
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleSave}
                            disabled={saving}
                            style={{
                              backgroundColor: c.coral,
                              border: 'none',
                              color: '#fff',
                              borderRadius: '3px',
                              padding: '8px 24px',
                              fontWeight: 600,
                              cursor: 'pointer',
                              fontSize: '14px',
                            }}
                          >
                            {saving ? 'Saving…' : 'Save'}
                          </button>
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  );
}

// ── Contacts View ────────────────────────────────────────────────────
function ContactsView({ items, total, listName, listId, onBack, callTool, toast, isFullscreen, onToggleFullscreen }: {
  items: Contact[];
  total?: number;
  listName: string;
  listId: string;
  onBack: () => void;
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
}){
  const styles = useStyles();
  const c = useHsColors();
  const [addingContact, setAddingContact] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [saving, setSaving] = useState(false);

  const handleRemove = async (contactId: string) => {
    try {
      await callTool('remove_from_list', { list_id: listId, contact_id: contactId });
      toast('Contact removed');
    } catch (e: any) {
      toast(e.message || 'Failed to remove contact', 'error');
    }
  };

  const handleAdd = async () => {
    if (!newEmail.trim()) return;
    setSaving(true);
    try {
      await callTool('add_to_list', { list_id: listId, contact_email: newEmail.trim() });
      toast('Contact added');
      setAddingContact(false);
      setNewEmail('');
    } catch (e: any) {
      toast(e.message || 'Failed to add contact', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className={styles.breadcrumb}>
        <button className={styles.breadcrumbLink} style={{ color: c.coral }} onClick={() => {}}>Emails</button>
        <Text style={{ color: c.textSec, fontSize: '14px' }}>&gt;</Text>
        <button className={styles.breadcrumbLink} style={{ color: c.coral }} onClick={onBack}>Lists</button>
        <Text style={{ color: c.textSec, fontSize: '14px' }}>&gt;</Text>
        <Text style={{ color: c.text, fontSize: '14px', fontWeight: 600 }}>{listName}</Text>
      </div>

      <div
        className={styles.header}
        style={{
          backgroundColor: c.bg,
          borderLeft: `4px solid ${c.coral}`,
          border: `1px solid ${c.border}`,
          borderLeftWidth: '4px',
          borderLeftColor: c.coral,
        }}
      >
        <div>
          <div className={styles.titleRow}>
            <PersonRegular style={{ color: c.coral, fontSize: 22 }} />
            <Text style={{ color: c.text, fontSize: '18px', fontWeight: 600 }}>{listName}</Text>
          </div>
          <Text style={{ color: c.textSec, fontSize: '13px', marginLeft: '32px' }}>
            {total ?? items.length} contacts
          </Text>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {onToggleFullscreen && <FullscreenToggle isFullscreen={!!isFullscreen} onToggle={onToggleFullscreen} />}
          <button
            onClick={onBack}
            style={{
              backgroundColor: 'transparent',
              border: `1px solid ${c.coral}`,
              color: c.coral,
              borderRadius: '3px',
              padding: '8px 24px',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <ArrowLeftRegular style={{ fontSize: 14 }} /> Back to Lists
          </button>
          <button
            onClick={() => setAddingContact(true)}
            style={{
              backgroundColor: c.coral,
              border: 'none',
              color: '#fff',
              borderRadius: '3px',
              padding: '8px 24px',
              fontWeight: 600,
              cursor: 'pointer',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <AddRegular style={{ fontSize: 14 }} /> Add Contact
          </button>
        </div>
      </div>

      {addingContact && (
        <div style={{ padding: 16, marginBottom: 12, borderRadius: 8, backgroundColor: c.editPanelBg, border: `1px solid ${c.border}` }}>
          <div className={styles.editPanelTitle} style={{ color: c.text }}>➕ Add Contact to List</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'end', maxWidth: 400 }}>
            <Field label={<span style={{ fontSize: '12px', color: c.textSec, fontWeight: 600, textTransform: 'uppercase' }}>Email Address</span>} style={{ flex: 1 }}>
              <Input type="email" value={newEmail} onChange={(_, d) => setNewEmail(d.value)} placeholder="contact@example.com" style={{ border: `1px solid ${c.border}`, borderRadius: '3px' }} />
            </Field>
            <button
              onClick={() => { setAddingContact(false); setNewEmail(''); }}
              disabled={saving}
              style={{
                backgroundColor: 'transparent',
                border: `1px solid ${c.coral}`,
                color: c.coral,
                borderRadius: '3px',
                padding: '8px 24px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '14px',
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={saving}
              style={{
                backgroundColor: c.coral,
                border: 'none',
                color: '#fff',
                borderRadius: '3px',
                padding: '8px 24px',
                fontWeight: 600,
                cursor: 'pointer',
                fontSize: '14px',
              }}
            >
              {saving ? 'Adding…' : 'Add'}
            </button>
          </div>
        </div>
      )}

      <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
        <Table>
          <TableHeader>
            <TableRow style={{ backgroundColor: c.bg }}>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Name</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Email</TableHeaderCell>
              {isFullscreen && <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Phone</TableHeaderCell>}
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Company</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Lifecycle Stage</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}`, width: 60 }} />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={isFullscreen ? 6 : 5}>
                  <div className={styles.emptyState}>
                    <PersonRegular style={{ fontSize: 48, color: c.border, display: 'block', margin: '0 auto 12px' }} />
                    <Text style={{ color: c.textSec, fontSize: '15px' }}>No contacts in this list yet</Text>
                    <br />
                    <Text style={{ color: c.textSec, fontSize: '13px' }}>Add contacts to get started</Text>
                  </div>
                </TableCell>
              </TableRow>
            ) : (
              items.map((ct) => (
                <TableRow
                  key={ct.id}
                  style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}
                  onMouseEnter={e => (e.currentTarget.style.backgroundColor = c.hoverBg)}
                  onMouseLeave={e => (e.currentTarget.style.backgroundColor = c.bg)}
                >
                  <TableCell className={styles.cell} style={{ color: c.text, fontWeight: 600 }}>
                    {ct.firstname} {ct.lastname}
                  </TableCell>
                  <TableCell className={styles.cell} style={{ color: c.text }}>{ct.email}</TableCell>
                  {isFullscreen && <TableCell className={styles.cell} style={{ color: c.text }}>{ct.phone || '—'}</TableCell>}
                  <TableCell className={styles.cell} style={{ color: c.text }}>{ct.company}</TableCell>
                  <TableCell className={styles.cell}>
                    <span className={styles.lifecycleDot} style={{ backgroundColor: lifecycleDotColor(ct.lifecyclestage) }} />
                    <span style={{ color: c.text, fontSize: '14px' }}>{ct.lifecyclestage || '—'}</span>
                  </TableCell>
                  <TableCell className={styles.cell}>
                    <Button
                      appearance="subtle"
                      icon={<DismissRegular />}
                      size="small"
                      title="Remove"
                      onClick={() => handleRemove(ct.id)}
                      style={{ color: c.error }}
                    />
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </>
  );
}

// ── Main App ─────────────────────────────────────────────────────────
type ViewState =
  | { view: 'emails' }
  | { view: 'lists'; data: HubSpotData | null }
  | { view: 'contacts'; data: HubSpotData | null; listId: string; listName: string };

export function HubSpotApp() {
  const styles = useStyles();
  const initialData = useToolData<HubSpotData>();
  const { callTool } = useMcpBridge();
  const toast = useToast();
  const c = useHsColors();

  const [nav, setNav] = useState<ViewState>({ view: 'emails' });
  const [loadingView, setLoadingView] = useState<'emails' | 'lists' | 'contacts' | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const toggleFullscreen = useCallback(() => {
    const next = !isFullscreen;
    setIsFullscreen(next);
    window.parent.postMessage({
      jsonrpc: '2.0',
      method: 'ui/request-display-mode',
      params: { mode: next ? 'fullscreen' : 'inline' },
    }, '*');
  }, [isFullscreen]);

  const shellStyle = isFullscreen ? { maxWidth: 'none', padding: '28px 40px' } : undefined;

  const navigateToLists = useCallback(async () => {
    setLoadingView('lists');
    try {
      const result = await callTool('get_lists', {});
      setNav({ view: 'lists', data: result });
    } catch (e: any) {
      toast(e.message || 'Failed to load lists', 'error');
    } finally {
      setLoadingView(null);
    }
  }, [callTool, toast]);

  const navigateToContacts = useCallback(async (listId: string, listName?: string) => {
    setLoadingView('contacts');
    try {
      const result = await callTool('get_list_contacts', { list_id: listId });
      setNav({
        view: 'contacts',
        data: result,
        listId,
        listName: result?.list_name || listName || 'List',
      });
    } catch (e: any) {
      toast(e.message || 'Failed to load contacts', 'error');
    } finally {
      setLoadingView(null);
    }
  }, [callTool, toast]);

  const backToEmails = useCallback(async () => {
    setLoadingView('emails');
    try {
      await callTool('get_emails', {});
      setNav({ view: 'emails' });
    } catch (e: any) {
      toast(e.message || 'Failed to load emails', 'error');
    } finally {
      setLoadingView(null);
    }
  }, [callTool, toast]);

  const backToLists = useCallback(async () => {
    setLoadingView('lists');
    try {
      const result = await callTool('get_lists', {});
      setNav({ view: 'lists', data: result });
    } catch (e: any) {
      toast(e.message || 'Failed to load lists', 'error');
    } finally {
      setLoadingView(null);
    }
  }, [callTool, toast]);

  // Initial loading skeleton
  if (!initialData && nav.view === 'emails') {
    return (
      <div className={styles.shell} style={shellStyle}>
        <EmailsSkeleton isFullscreen={isFullscreen} />
      </div>
    );
  }

  // Navigation loading skeleton
  if (loadingView) {
    return (
      <div className={styles.shell} style={shellStyle}>
        {loadingView === 'emails' && <EmailsSkeleton isFullscreen={isFullscreen} />}
        {loadingView === 'lists' && <ListsSkeleton />}
        {loadingView === 'contacts' && <ContactsSkeleton />}
      </div>
    );
  }

  // Contacts view
  if (nav.view === 'contacts' && nav.data) {
    return (
      <div className={styles.shell} style={shellStyle}>
        <ContactsView
          items={(nav.data.items || []) as Contact[]}
          total={nav.data.total}
          listName={nav.listName}
          listId={nav.listId}
          onBack={backToLists}
          callTool={callTool}
          toast={toast}
          isFullscreen={isFullscreen}
          onToggleFullscreen={toggleFullscreen}
        />
        <McpFooter label="HubSpot Marketing" />
      </div>
    );
  }

  // Lists view
  if (nav.view === 'lists' && nav.data) {
    return (
      <div className={styles.shell} style={shellStyle}>
        <ListsView
          items={(nav.data.items || []) as ContactList[]}
          total={nav.data.total}
          onBack={backToEmails}
          onViewContacts={(listId) => {
            const list = ((nav.data?.items || []) as ContactList[]).find(l => l.id === listId);
            navigateToContacts(listId, list?.name);
          }}
          callTool={callTool}
          toast={toast}
          isFullscreen={isFullscreen}
          onToggleFullscreen={toggleFullscreen}
        />
        <McpFooter label="HubSpot Marketing" />
      </div>
    );
  }

  // Emails view (entry point) — also handle toolData pushing lists/contacts
  const data = initialData!;
  if (data.type === 'lists') {
    return (
      <div className={styles.shell} style={shellStyle}>
        <ListsView
          items={(data.items || []) as ContactList[]}
          total={data.total}
          onBack={backToEmails}
          onViewContacts={(listId) => {
            const list = ((data.items || []) as ContactList[]).find(l => l.id === listId);
            navigateToContacts(listId, list?.name);
          }}
          callTool={callTool}
          toast={toast}
          isFullscreen={isFullscreen}
          onToggleFullscreen={toggleFullscreen}
        />
        <McpFooter label="HubSpot Marketing" />
      </div>
    );
  }

  if (data.type === 'list_contacts') {
    return (
      <div className={styles.shell} style={shellStyle}>
        <ContactsView
          items={(data.items || []) as Contact[]}
          total={data.total}
          listName={data.list_name || 'List'}
          listId={data.list_id || ''}
          onBack={backToLists}
          callTool={callTool}
          toast={toast}
          isFullscreen={isFullscreen}
          onToggleFullscreen={toggleFullscreen}
        />
        <McpFooter label="HubSpot Marketing" />
      </div>
    );
  }

  // Default: emails
  return (
    <div className={styles.shell} style={shellStyle}>
      <EmailsView
        items={(data.items || []) as Email[]}
        total={data.total}
        onNavigateLists={navigateToLists}
        callTool={callTool}
        toast={toast}
        isFullscreen={isFullscreen}
        onToggleFullscreen={toggleFullscreen}
      />
      <McpFooter label="HubSpot Marketing" />
    </div>
  );
}

