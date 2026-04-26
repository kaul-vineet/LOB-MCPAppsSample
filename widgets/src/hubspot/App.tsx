import React, { useState, useCallback, useEffect } from 'react';
import {
  Button,
  Field,
  Input,
  Select,
  Spinner,
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
import { ExpandButton } from '../shared/ExpandButton';
import { McpFooter } from '../shared/McpFooter';
import { useToast } from '../shared/Toast';
import type { HubSpotData, Email, ContactList, Contact, CrmContact, Company, Deal, Ticket } from './types';

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
    gridTemplateColumns: 'repeat(3, 1fr)',
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

function SkeletonMetricCard() {
  const c = useHsColors();
  const styles = useStyles();
  return (
    <div
      className={styles.metricCard}
      style={{
        backgroundColor: c.bg,
        border: `1px solid ${c.border}`,
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        padding: '16px',
      }}
    >
      <SkeletonBlock width="50%" height={24} style={{ margin: '0 auto 8px' }} />
      <SkeletonBlock width="40%" height={12} style={{ margin: '0 auto' }} />
    </div>
  );
}

function EmailsSkeleton() {
  const styles = useStyles();
  const c = useHsColors();
  const cols = 5;
  return (
    <>
      <div style={{ textAlign: 'center', padding: '8px 0 12px', fontSize: '13px', color: '#888' }}>
        ⏳ Loading data…
      </div>
      <div
        className={styles.header}
        style={{ backgroundColor: c.bg, border: `1px solid ${c.border}`, borderLeftWidth: '4px', borderLeftColor: c.border }}
      >
        <div>
          <SkeletonBlock width={180} height={18} />
          <SkeletonBlock width={100} height={13} style={{ marginTop: 6 }} />
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '16px' }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <SkeletonMetricCard key={i} />
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
function MetricCard({ label, value, negative }: { label: string; value: string | number; negative?: boolean }) {
  const styles = useStyles();
  const c = useHsColors();
  return (
    <div
      className={styles.metricCard}
      style={{
        backgroundColor: c.bg,
        border: `1px solid ${c.border}`,
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        padding: '16px',
      }}
    >
      <div style={{ fontSize: '24px', fontWeight: 700, color: negative ? c.error : c.teal, lineHeight: 1.2 }}>
        {value}
      </div>
      <div style={{ fontSize: '12px', color: c.textSec, marginTop: '4px' }}>{label}</div>
    </div>
  );
}

// ── Emails View ──────────────────────────────────────────────────────
function EmailsView({ items, total, onNavigateLists, callTool, toast }: {
  items: Email[];
  total?: number;
  onNavigateLists: () => void;
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
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
      await callTool('hs__update_email', { email_id: editingId, name: formData.name, subject: formData.subject });
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
          <ExpandButton />
        </div>
      </div>

      {/* Metrics summary cards */}
      <div className={styles.metricsGrid}>
        <MetricCard label="Total Sent" value={fmtNum(totalSent)} />
        <MetricCard label="Avg Open Rate" value={avgOpenRate + '%'} />
        <MetricCard label="Avg Click Rate" value={avgClickRate + '%'} />
        <MetricCard label="Total Bounced" value={fmtNum(totalBounced)} negative />
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
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Open Rate</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Click Rate</TableHeaderCell>
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
                    <TableCell className={styles.cell}>
                      <Button appearance="subtle" icon={<EditRegular />} size="small" title="Edit" onClick={() => openEdit(em)} />
                    </TableCell>
                  </TableRow>
                  {editingId === em.id && (
                    <TableRow>
                      <TableCell colSpan={6} style={{ padding: 0 }}>
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
function ListsView({ items, total, onBack, onViewContacts, callTool, toast }: {
  items: ContactList[];
  total?: number;
  onBack: () => void;
  onViewContacts: (listId: string) => void;
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
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
      await callTool('hs__update_list', { list_id: editingId, name: formName });
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
          <ExpandButton />
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
function ContactsView({ items, total, listName, listId, onBack, callTool, toast }: {
  items: Contact[];
  total?: number;
  listName: string;
  listId: string;
  onBack: () => void;
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}){
  const styles = useStyles();
  const c = useHsColors();
  const [addingContact, setAddingContact] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [saving, setSaving] = useState(false);

  const handleRemove = async (contactId: string) => {
    try {
      await callTool('hs__remove_from_list', { list_id: listId, contact_id: contactId });
      toast('Contact removed');
    } catch (e: any) {
      toast(e.message || 'Failed to remove contact', 'error');
    }
  };

  const handleAdd = async () => {
    if (!newEmail.trim()) return;
    setSaving(true);
    try {
      await callTool('hs__add_to_list', { list_id: listId, contact_email: newEmail.trim() });
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
          <ExpandButton />
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
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Company</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}` }}>Lifecycle Stage</TableHeaderCell>
              <TableHeaderCell className={styles.headerCell} style={{ color: c.text, borderBottom: `2px solid ${c.border}`, width: 60 }} />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>
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

// ── FormView (Create Contact / Deal) ─────────────────────────────────
const DEAL_STAGES = [
  { value: '', label: '— Select —' },
  { value: 'appointmentscheduled', label: 'Appointment Scheduled' },
  { value: 'qualifiedtobuy', label: 'Qualified to Buy' },
  { value: 'presentationscheduled', label: 'Presentation Scheduled' },
  { value: 'decisionmakerboughtin', label: 'Decision Maker Bought-In' },
  { value: 'contractsent', label: 'Contract Sent' },
  { value: 'closedwon', label: 'Closed Won' },
  { value: 'closedlost', label: 'Closed Lost' },
];

function FormView({
  entity,
  prefill,
  callTool,
  toast,
}: {
  entity: 'contact' | 'deal' | 'company' | 'ticket';
  prefill?: Record<string, string>;
  callTool: (tool: string, args: Record<string, unknown>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  theme?: string;
}) {
  const styles = useStyles();
  const c = useHsColors();

  const [fields, setFields] = useState<Record<string, string>>(() => ({
    ...(prefill || {}),
  }));
  const [submitting, setSubmitting] = useState(false);

  const set = (key: string, value: string) =>
    setFields((prev) => ({ ...prev, [key]: value }));

  const titleMap: Record<typeof entity, string> = {
    contact: 'New Contact',
    deal: 'New Deal',
    company: 'New Company',
    ticket: 'New Ticket',
  };

  const handleSubmit = async () => {
    if (entity === 'contact' && !fields.email) { toast('Email is required', 'error'); return; }
    if (entity === 'deal' && !fields.deal_name) { toast('Deal Name is required', 'error'); return; }
    if (entity === 'company' && !fields.name) { toast('Company Name is required', 'error'); return; }
    if (entity === 'ticket' && !fields.subject) { toast('Subject is required', 'error'); return; }
    setSubmitting(true);
    try {
      if (entity === 'contact') {
        await callTool('hs__create_contact', { email: fields.email || '', firstname: fields.firstname || '', lastname: fields.lastname || '', phone: fields.phone || '', company: fields.company || '' });
        toast('Contact created successfully!', 'success');
      } else if (entity === 'deal') {
        await callTool('hs__create_deal', { deal_name: fields.deal_name || '', amount: fields.amount || '', pipeline: fields.pipeline || '', deal_stage: fields.deal_stage || '' });
        toast('Deal created successfully!', 'success');
      } else if (entity === 'company') {
        await callTool('hs__create_company', { name: fields.name || '', domain: fields.domain || '', phone: fields.phone || '', city: fields.city || '', industry: fields.industry || '' });
        toast('Company created successfully!', 'success');
      } else {
        await callTool('hs__create_ticket', { subject: fields.subject || '', status: fields.status || 'new', priority: fields.priority || 'MEDIUM', category: fields.category || '', description: fields.description || '' });
        toast('Ticket created successfully!', 'success');
      }
    } catch (e: any) {
      toast(e.message || `Failed to create ${entity}`, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => setFields(prefill ? { ...prefill } : {});

  return (
    <>
      <div
        className={styles.header}
        style={{ background: `linear-gradient(135deg, ${c.coral}, ${c.coralDark})`, color: '#fff' }}
      >
        <div className={styles.titleRow}>
          <Text size={500} weight="bold" style={{ color: '#fff' }}>✨ {titleMap[entity]}</Text>
        </div>
      </div>

      <div style={{ background: c.surface, border: `1px solid ${c.border}`, borderRadius: '8px', padding: '20px' }}>
        {entity === 'contact' && (
          <>
            <Field label="First Name" style={{ marginBottom: 12 }}><Input value={fields.firstname || ''} onChange={(_, d) => set('firstname', d.value)} placeholder="Jane" /></Field>
            <Field label="Last Name *" style={{ marginBottom: 12 }}><Input value={fields.lastname || ''} onChange={(_, d) => set('lastname', d.value)} placeholder="Doe" /></Field>
            <Field label="Email *" style={{ marginBottom: 12 }}><Input value={fields.email || ''} onChange={(_, d) => set('email', d.value)} placeholder="jane@example.com" type="email" /></Field>
            <Field label="Phone" style={{ marginBottom: 12 }}><Input value={fields.phone || ''} onChange={(_, d) => set('phone', d.value)} placeholder="+1 555-0100" /></Field>
            <Field label="Company" style={{ marginBottom: 12 }}><Input value={fields.company || ''} onChange={(_, d) => set('company', d.value)} placeholder="Acme Inc." /></Field>
          </>
        )}
        {entity === 'deal' && (
          <>
            <Field label="Deal Name *" style={{ marginBottom: 12 }}><Input value={fields.deal_name || ''} onChange={(_, d) => set('deal_name', d.value)} placeholder="Enterprise License" /></Field>
            <Field label="Amount" style={{ marginBottom: 12 }}><Input value={fields.amount || ''} onChange={(_, d) => set('amount', d.value)} placeholder="50000" /></Field>
            <Field label="Pipeline" style={{ marginBottom: 12 }}>
              <Select value={fields.pipeline || 'default'} onChange={(_, d) => set('pipeline', d.value)}><option value="default">Default</option></Select>
            </Field>
            <Field label="Deal Stage" style={{ marginBottom: 12 }}>
              <Select value={fields.deal_stage || ''} onChange={(_, d) => set('deal_stage', d.value)}>
                {DEAL_STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </Select>
            </Field>
          </>
        )}
        {entity === 'company' && (
          <>
            <Field label="Company Name *" style={{ marginBottom: 12 }}><Input value={fields.name || ''} onChange={(_, d) => set('name', d.value)} placeholder="Acme Corp" /></Field>
            <Field label="Domain" style={{ marginBottom: 12 }}><Input value={fields.domain || ''} onChange={(_, d) => set('domain', d.value)} placeholder="acme.com" /></Field>
            <Field label="Phone" style={{ marginBottom: 12 }}><Input value={fields.phone || ''} onChange={(_, d) => set('phone', d.value)} placeholder="+1 555-0100" /></Field>
            <Field label="City" style={{ marginBottom: 12 }}><Input value={fields.city || ''} onChange={(_, d) => set('city', d.value)} placeholder="San Francisco" /></Field>
            <Field label="Industry" style={{ marginBottom: 12 }}>
              <Select value={fields.industry || ''} onChange={(_, d) => set('industry', d.value)}>
                <option value="">— Select —</option>
                {HS_INDUSTRIES.map(i => <option key={i} value={i}>{i}</option>)}
              </Select>
            </Field>
          </>
        )}
        {entity === 'ticket' && (
          <>
            <Field label="Subject *" style={{ marginBottom: 12 }}><Input value={fields.subject || ''} onChange={(_, d) => set('subject', d.value)} placeholder="Login issue" /></Field>
            <Field label="Status" style={{ marginBottom: 12 }}>
              <Select value={fields.status || 'new'} onChange={(_, d) => set('status', d.value)}>
                {HS_TICKET_STATUS.map(s => <option key={s} value={s}>{s}</option>)}
              </Select>
            </Field>
            <Field label="Priority" style={{ marginBottom: 12 }}>
              <Select value={fields.priority || 'MEDIUM'} onChange={(_, d) => set('priority', d.value)}>
                {HS_TICKET_PRIORITY.map(p => <option key={p} value={p}>{p}</option>)}
              </Select>
            </Field>
            <Field label="Category" style={{ marginBottom: 12 }}><Input value={fields.category || ''} onChange={(_, d) => set('category', d.value)} placeholder="Billing" /></Field>
            <Field label="Description" style={{ marginBottom: 12 }}><Input value={fields.description || ''} onChange={(_, d) => set('description', d.value)} placeholder="Describe the issue…" /></Field>
          </>
        )}

        <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
          <Button appearance="primary" onClick={handleSubmit} disabled={submitting}
            style={!submitting ? { backgroundColor: c.coral, borderColor: c.coral } : undefined}>
            {submitting ? <Spinner size="tiny" /> : 'Submit'}
          </Button>
          <Button appearance="subtle" onClick={handleCancel} disabled={submitting}>Cancel</Button>
        </div>
      </div>
    </>
  );
}

// ── CRM constants ────────────────────────────────────────────────────
const HS_LIFECYCLE_STAGES = ['subscriber', 'lead', 'marketing qualified lead', 'sales qualified lead', 'opportunity', 'customer', 'evangelist'];
const HS_INDUSTRIES = ['Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail', 'Education', 'Other'];
const HS_TICKET_STATUS = ['new', 'waiting on contact', 'waiting on us', 'closed'];
const HS_TICKET_PRIORITY = ['LOW', 'MEDIUM', 'HIGH'];
const HS_PIPELINES = ['Default Pipeline', 'Support Pipeline'];

// ── Shared CRM inline form row ────────────────────────────────────────
function HsFormRow({ colSpan, title, fields, onSave, onCancel, saving }: {
  colSpan: number; title: string;
  fields: { label: string; key: string; value: string; onChange: (v: string) => void; type?: 'select'; options?: string[]; optionLabels?: Record<string, string> }[];
  onSave: () => void; onCancel: () => void; saving: boolean;
}) {
  const styles = useStyles();
  const c = useHsColors();
  return (
    <TableRow>
      <TableCell colSpan={colSpan} style={{ padding: 0 }}>
        <div style={{ padding: '14px 16px', backgroundColor: c.editPanelBg, borderTop: `2px solid ${c.editPanelBorder}` }}>
          <div style={{ fontSize: '14px', fontWeight: 600, color: c.text, marginBottom: '10px' }}>{title}</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px 12px', marginBottom: '14px' }}>
            {fields.map(f => (
              <Field key={f.key} label={<span style={{ fontSize: '11px', color: c.textSec, fontWeight: 600, textTransform: 'uppercase' }}>{f.label}</span>} size="small">
                {f.type === 'select' ? (
                  <select value={f.value} onChange={e => f.onChange(e.target.value)}
                    style={{ width: '100%', padding: '4px 8px', borderRadius: '3px', border: `1px solid ${c.border}`, backgroundColor: c.bg, color: c.text, fontSize: '13px', height: '28px' }}>
                    <option value="">— Select —</option>
                    {(f.options || []).map(o => <option key={o} value={o}>{f.optionLabels?.[o] || o}</option>)}
                  </select>
                ) : (
                  <Input size="small" value={f.value} onChange={(_, d) => f.onChange(d.value)}
                    style={{ border: `1px solid ${c.border}`, borderRadius: '3px' }} />
                )}
              </Field>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button onClick={onCancel} disabled={saving}
              style={{ backgroundColor: 'transparent', border: `1px solid ${c.coral}`, color: c.coral, borderRadius: '3px', padding: '6px 20px', fontWeight: 600, cursor: 'pointer', fontSize: '13px' }}>
              Cancel
            </button>
            <button onClick={onSave} disabled={saving}
              style={{ backgroundColor: c.coral, border: 'none', color: '#fff', borderRadius: '3px', padding: '6px 20px', fontWeight: 600, cursor: 'pointer', fontSize: '13px' }}>
              {saving ? 'Saving…' : title.includes('Edit') ? 'Save' : 'Create'}
            </button>
          </div>
        </div>
      </TableCell>
    </TableRow>
  );
}

// ── Shared CRM view header ────────────────────────────────────────────
function HsViewHeader({ icon, title, count, onNew, newLabel }: {
  icon: React.ReactNode; title: string; count: number; onNew?: () => void; newLabel?: string;
}) {
  const styles = useStyles();
  const c = useHsColors();
  return (
    <div className={styles.header} style={{ backgroundColor: c.bg, border: `1px solid ${c.border}`, borderLeftWidth: '4px', borderLeftColor: c.coral }}>
      <div>
        <div className={styles.titleRow}>
          {icon}
          <Text style={{ color: c.text, fontSize: '18px', fontWeight: 600 }}>{title}</Text>
        </div>
        <Text style={{ color: c.textSec, fontSize: '13px', marginLeft: '32px' }}>{count} record{count !== 1 ? 's' : ''}</Text>
      </div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {onNew && (
          <button onClick={onNew}
            style={{ backgroundColor: c.coral, border: 'none', color: '#fff', borderRadius: '3px', padding: '7px 18px', fontWeight: 600, cursor: 'pointer', fontSize: '13px', display: 'flex', alignItems: 'center', gap: 6 }}>
            <AddRegular style={{ fontSize: 13 }} /> {newLabel || 'New'}
          </button>
        )}
        <ExpandButton />
      </div>
    </div>
  );
}

// ── Shared CRM filter bar ─────────────────────────────────────────────
function HsFilterBar({ value, onChange, onSearch, placeholder, loading, hidden }: {
  value: string; onChange: (v: string) => void; onSearch: () => void;
  placeholder: string; loading: boolean; hidden?: boolean;
}) {
  const c = useHsColors();
  if (hidden) return null;
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', padding: '8px 12px', borderBottom: `1px solid ${c.border}`, backgroundColor: c.bg, flexWrap: 'wrap' }}>
      <Input size="small" value={value} onChange={(_, d) => onChange(d.value)} onKeyDown={e => e.key === 'Enter' && onSearch()}
        placeholder={placeholder} style={{ flex: 1, maxWidth: 280, border: `1px solid ${c.border}`, borderRadius: '3px' }} />
      <button onClick={onSearch} disabled={loading}
        style={{ padding: '5px 14px', borderRadius: '3px', border: 'none', backgroundColor: c.coral, color: '#fff', fontSize: '12px', fontWeight: 600, cursor: 'pointer' }}>
        {loading ? '…' : 'Search'}
      </button>
      {value && <button onClick={() => { onChange(''); onSearch(); }}
        style={{ padding: '5px 8px', borderRadius: '3px', border: `1px solid ${c.border}`, backgroundColor: 'transparent', color: c.textSec, fontSize: '12px', cursor: 'pointer' }}>✕ Clear</button>}
    </div>
  );
}

// ── CRM Contacts View ─────────────────────────────────────────────────
function CrmContactsView({ items: initItems, total, callTool, toast }: {
  items: any[]; total?: number;
  callTool: (n: string, a?: any) => Promise<any>;
  toast: (m: string, t?: any) => void;
}) {
  const styles = useStyles();
  const c = useHsColors();
  const [localItems, setLocalItems] = useState(initItems);
  const [filterName, setFilterName] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ firstname: '', lastname: '', email: '', phone: '', company: '', jobtitle: '', lifecyclestage: '' });
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loadingExpand, setLoadingExpand] = useState<string | null>(null);
  const [contactDeals, setContactDeals] = useState<Record<string, any[]>>({});

  useEffect(() => setLocalItems(initItems), [initItems]);

  const doSearch = async () => {
    if (!filterName.trim()) { setLocalItems(initItems); return; }
    setFiltering(true);
    try { const r = await callTool('hs__get_contacts', { name: filterName }); setLocalItems(r?.items || []); }
    finally { setFiltering(false); }
  };

  const toggleExpand = useCallback(async (ctId: string) => {
    if (expandedId === ctId) { setExpandedId(null); return; }
    setExpandedId(ctId);
    if (contactDeals[ctId]) return;
    setLoadingExpand(ctId);
    try {
      const r = await callTool('hs__get_contact_deals', { contact_id: ctId });
      setContactDeals(p => ({ ...p, [ctId]: r?.items || [] }));
    } catch { setContactDeals(p => ({ ...p, [ctId]: [] })); }
    finally { setLoadingExpand(null); }
  }, [expandedId, contactDeals, callTool]);

  const openEdit = (ct: any) => { setCreating(false); setExpandedId(null); setEditingId(ct.id); setForm({ firstname: ct.firstname || '', lastname: ct.lastname || '', email: ct.email || '', phone: ct.phone || '', company: ct.company || '', jobtitle: ct.jobtitle || '', lifecyclestage: ct.lifecyclestage || '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ firstname: '', lastname: '', email: '', phone: '', company: '', jobtitle: '', lifecyclestage: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) { await callTool('hs__create_contact', form); toast('✓ Contact created'); }
      else { await callTool('hs__update_contact', { contact_id: editingId, ...form }); toast('✓ Contact updated'); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));
  const fFields = (f: typeof form) => [
    { label: 'First Name', key: 'firstname', value: f.firstname, onChange: (v: string) => setF('firstname', v) },
    { label: 'Last Name *', key: 'lastname', value: f.lastname, onChange: (v: string) => setF('lastname', v) },
    { label: 'Email *', key: 'email', value: f.email, onChange: (v: string) => setF('email', v) },
    { label: 'Phone', key: 'phone', value: f.phone, onChange: (v: string) => setF('phone', v) },
    { label: 'Company', key: 'company', value: f.company, onChange: (v: string) => setF('company', v) },
    { label: 'Job Title', key: 'jobtitle', value: f.jobtitle, onChange: (v: string) => setF('jobtitle', v) },
    { label: 'Lifecycle Stage', key: 'lifecyclestage', value: f.lifecyclestage, onChange: (v: string) => setF('lifecyclestage', v), type: 'select' as const, options: HS_LIFECYCLE_STAGES },
  ];

  const H_STYLE: React.CSSProperties = { fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.4px', padding: '8px 12px' };

  return (
    <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
      <HsViewHeader icon={<PeopleRegular style={{ color: c.coral, fontSize: 22 }} />} title="Contacts" count={total ?? localItems.length} onNew={openCreate} newLabel="New Contact" />
      <HsFilterBar value={filterName} onChange={setFilterName} onSearch={doSearch} placeholder="Search by name or email…" loading={filtering} hidden={creating} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ backgroundColor: c.surface }}>
            {['', 'Name', 'Email', 'Company', 'Stage', ''].map((h, i) => (
              <TableHeaderCell key={i} className={styles.headerCell} style={{ color: c.textSec, borderBottom: `2px solid ${c.border}`, ...H_STYLE, ...(i === 0 ? { width: 28 } : {}) }}>{h}</TableHeaderCell>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <HsFormRow colSpan={6} title="➕ New Contact" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={6} style={{ textAlign: 'center', padding: 32, color: c.textSec }}>No contacts found.</TableCell></TableRow>}
          {localItems.map((ct: any) => (
            <React.Fragment key={ct.id}>
              <TableRow style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = c.hoverBg)}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = c.bg)}>
                <TableCell className={styles.cell} style={{ width: 28, padding: '6px 8px' }}>
                  <button onClick={() => toggleExpand(ct.id)}
                    style={{ width: 22, height: 22, border: `1px solid ${c.border}`, borderRadius: '3px', background: expandedId === ct.id ? c.surface : 'transparent', cursor: 'pointer', fontSize: '11px', color: c.coral, fontWeight: 700, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                    {loadingExpand === ct.id ? '…' : expandedId === ct.id ? '▼' : '▶'}
                  </button>
                </TableCell>
                <TableCell className={styles.cell} style={{ color: c.text, fontWeight: 600 }}>{ct.firstname} {ct.lastname}</TableCell>
                <TableCell className={styles.cell} style={{ color: c.textSec }}>{ct.email || '—'}</TableCell>
                <TableCell className={styles.cell} style={{ color: c.text }}>{ct.company || '—'}</TableCell>
                <TableCell className={styles.cell}>
                  {ct.lifecyclestage ? <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 600, backgroundColor: c.surface, color: c.coral, border: `1px solid ${c.border}` }}>{ct.lifecyclestage}</span> : '—'}
                </TableCell>
                <TableCell className={styles.cell}><Button appearance="subtle" icon={<EditRegular />} size="small" title="Edit" onClick={() => openEdit(ct)} /></TableCell>
              </TableRow>
              {editingId === ct.id && <HsFormRow colSpan={6} title="✏️ Edit Contact" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} />}
              {expandedId === ct.id && (
                <TableRow>
                  <TableCell colSpan={6} style={{ padding: 0, backgroundColor: c.surface }}>
                    <div style={{ padding: '10px 20px 14px', borderTop: `2px solid ${c.coral}` }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: c.textSec, marginBottom: 8 }}>Associated Deals</div>
                      {(contactDeals[ct.id] || []).length === 0 ? (
                        <div style={{ fontSize: '13px', color: c.textSec, fontStyle: 'italic' }}>No deals associated.</div>
                      ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                          <thead>
                            <tr style={{ backgroundColor: c.bg }}>
                              {['Deal', 'Stage', 'Amount', 'Close Date'].map(h => (
                                <th key={h} style={{ padding: '4px 10px', textAlign: 'left', color: c.textSec, borderBottom: `1px solid ${c.border}`, fontWeight: 600 }}>{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {(contactDeals[ct.id] || []).map((d: any) => (
                              <tr key={d.id} style={{ borderBottom: `1px solid ${c.border}` }}>
                                <td style={{ padding: '4px 10px', color: c.text, fontWeight: 500 }}>{d.dealname}</td>
                                <td style={{ padding: '4px 10px', color: c.teal }}>{d.dealstage || '—'}</td>
                                <td style={{ padding: '4px 10px', color: c.teal }}>{d.amount != null ? '$' + Number(d.amount).toLocaleString() : '—'}</td>
                                <td style={{ padding: '4px 10px', color: c.textSec }}>{d.closedate ? d.closedate.slice(0, 10) : '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ── Companies View ────────────────────────────────────────────────────
function CompaniesView({ items: initItems, total, callTool, toast }: {
  items: any[]; total?: number;
  callTool: (n: string, a?: any) => Promise<any>;
  toast: (m: string, t?: any) => void;
}) {
  const styles = useStyles();
  const c = useHsColors();
  const [localItems, setLocalItems] = useState(initItems);
  const [filterName, setFilterName] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', domain: '', phone: '', city: '', industry: '' });
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loadingExpand, setLoadingExpand] = useState<string | null>(null);
  type CompanyDetails = { contacts: any[]; deals: any[]; tickets: any[] };
  const [companyDetails, setCompanyDetails] = useState<Record<string, CompanyDetails>>({});

  useEffect(() => setLocalItems(initItems), [initItems]);

  const doSearch = async () => {
    if (!filterName.trim()) { setLocalItems(initItems); return; }
    setFiltering(true);
    try { const r = await callTool('hs__get_companies', { name: filterName }); setLocalItems(r?.items || []); }
    finally { setFiltering(false); }
  };

  const toggleExpand = useCallback(async (coId: string) => {
    if (expandedId === coId) { setExpandedId(null); return; }
    setExpandedId(coId);
    if (companyDetails[coId]) return;
    setLoadingExpand(coId);
    try {
      const [rc, rd, rt] = await Promise.all([
        callTool('hs__get_company_contacts', { company_id: coId }),
        callTool('hs__get_company_deals', { company_id: coId }),
        callTool('hs__get_company_tickets', { company_id: coId }),
      ]);
      setCompanyDetails(p => ({ ...p, [coId]: { contacts: rc?.items || [], deals: rd?.items || [], tickets: rt?.items || [] } }));
    } catch { setCompanyDetails(p => ({ ...p, [coId]: { contacts: [], deals: [], tickets: [] } })); }
    finally { setLoadingExpand(null); }
  }, [expandedId, companyDetails, callTool]);

  const openEdit = (co: any) => { setCreating(false); setExpandedId(null); setEditingId(co.id); setForm({ name: co.name || '', domain: co.domain || '', phone: co.phone || '', city: co.city || '', industry: co.industry || '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ name: '', domain: '', phone: '', city: '', industry: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) { await callTool('hs__create_company', form); toast('✓ Company created'); }
      else { await callTool('hs__update_company', { company_id: editingId, ...form }); toast('✓ Company updated'); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));
  const fFields = (f: typeof form) => [
    { label: 'Company Name *', key: 'name', value: f.name, onChange: (v: string) => setF('name', v) },
    { label: 'Domain', key: 'domain', value: f.domain, onChange: (v: string) => setF('domain', v) },
    { label: 'Phone', key: 'phone', value: f.phone, onChange: (v: string) => setF('phone', v) },
    { label: 'City', key: 'city', value: f.city, onChange: (v: string) => setF('city', v) },
    { label: 'Industry', key: 'industry', value: f.industry, onChange: (v: string) => setF('industry', v), type: 'select' as const, options: HS_INDUSTRIES },
  ];

  const H_STYLE: React.CSSProperties = { fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.4px', padding: '8px 12px' };

  const SubTable = ({ headers, rows }: { headers: string[]; rows: React.ReactNode[][] }) => (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
      <thead>
        <tr style={{ backgroundColor: c.bg }}>
          {headers.map(h => <th key={h} style={{ padding: '4px 10px', textAlign: 'left', color: c.textSec, borderBottom: `1px solid ${c.border}`, fontWeight: 600 }}>{h}</th>)}
        </tr>
      </thead>
      <tbody>
        {rows.length === 0 ? (
          <tr><td colSpan={headers.length} style={{ padding: '6px 10px', color: c.textSec, fontStyle: 'italic' }}>None</td></tr>
        ) : rows.map((cells, i) => (
          <tr key={i} style={{ borderBottom: `1px solid ${c.border}` }}>
            {cells.map((cell, j) => <td key={j} style={{ padding: '4px 10px', color: j === 0 ? c.text : c.textSec }}>{cell}</td>)}
          </tr>
        ))}
      </tbody>
    </table>
  );

  return (
    <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
      <HsViewHeader icon={<span style={{ fontSize: 20, color: c.coral }}>🏢</span>} title="Companies" count={total ?? localItems.length} onNew={openCreate} newLabel="New Company" />
      <HsFilterBar value={filterName} onChange={setFilterName} onSearch={doSearch} placeholder="Search by name…" loading={filtering} hidden={creating} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ backgroundColor: c.surface }}>
            {['', 'Name', 'Domain', 'City', 'Industry', ''].map((h, i) => (
              <TableHeaderCell key={i} className={styles.headerCell} style={{ color: c.textSec, borderBottom: `2px solid ${c.border}`, ...H_STYLE, ...(i === 0 ? { width: 28 } : {}) }}>{h}</TableHeaderCell>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <HsFormRow colSpan={6} title="➕ New Company" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={6} style={{ textAlign: 'center', padding: 32, color: c.textSec }}>No companies found.</TableCell></TableRow>}
          {localItems.map((co: any) => (
            <React.Fragment key={co.id}>
              <TableRow style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = c.hoverBg)}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = c.bg)}>
                <TableCell className={styles.cell} style={{ width: 28, padding: '6px 8px' }}>
                  <button onClick={() => toggleExpand(co.id)}
                    style={{ width: 22, height: 22, border: `1px solid ${c.border}`, borderRadius: '3px', background: expandedId === co.id ? c.surface : 'transparent', cursor: 'pointer', fontSize: '11px', color: c.coral, fontWeight: 700, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                    {loadingExpand === co.id ? '…' : expandedId === co.id ? '▼' : '▶'}
                  </button>
                </TableCell>
                <TableCell className={styles.cell} style={{ color: c.text, fontWeight: 600 }}>{co.name}</TableCell>
                <TableCell className={styles.cell} style={{ color: c.textSec }}>{co.domain || '—'}</TableCell>
                <TableCell className={styles.cell} style={{ color: c.text }}>{co.city || '—'}</TableCell>
                <TableCell className={styles.cell} style={{ color: c.textSec }}>{co.industry || '—'}</TableCell>
                <TableCell className={styles.cell}><Button appearance="subtle" icon={<EditRegular />} size="small" title="Edit" onClick={() => openEdit(co)} /></TableCell>
              </TableRow>
              {editingId === co.id && <HsFormRow colSpan={6} title="✏️ Edit Company" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} />}
              {expandedId === co.id && companyDetails[co.id] && (
                <TableRow>
                  <TableCell colSpan={6} style={{ padding: 0, backgroundColor: c.surface }}>
                    <div style={{ padding: '12px 20px 16px', borderTop: `2px solid ${c.coral}`, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                      <div>
                        <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: c.textSec, marginBottom: 6 }}>Contacts</div>
                        <SubTable headers={['Name', 'Email']}
                          rows={companyDetails[co.id].contacts.map((ct: any) => [`${ct.firstname || ''} ${ct.lastname || ''}`.trim() || '—', ct.email || '—'])} />
                      </div>
                      <div>
                        <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: c.textSec, marginBottom: 6 }}>Deals</div>
                        <SubTable headers={['Deal', 'Amount']}
                          rows={companyDetails[co.id].deals.map((d: any) => [d.dealname || '—', d.amount != null ? '$' + Number(d.amount).toLocaleString() : '—'])} />
                      </div>
                      <div>
                        <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: c.textSec, marginBottom: 6 }}>Tickets</div>
                        <SubTable headers={['Subject', 'Status']}
                          rows={companyDetails[co.id].tickets.map((tk: any) => [tk.subject || '—', tk.status || '—'])} />
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
  );
}

// ── Deals View ────────────────────────────────────────────────────────
function DealsView({ items: initItems, total, callTool, toast }: {
  items: any[]; total?: number;
  callTool: (n: string, a?: any) => Promise<any>;
  toast: (m: string, t?: any) => void;
}) {
  const styles = useStyles();
  const c = useHsColors();
  const [localItems, setLocalItems] = useState(initItems);
  const [filterName, setFilterName] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ dealname: '', amount: '', dealstage: '', closedate: '', pipeline: '' });
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loadingExpand, setLoadingExpand] = useState<string | null>(null);
  const [dealContacts, setDealContacts] = useState<Record<string, any[]>>({});

  useEffect(() => setLocalItems(initItems), [initItems]);

  const stageLabels: Record<string, string> = Object.fromEntries(DEAL_STAGES.filter(s => s.value).map(s => [s.value, s.label]));

  const doSearch = async () => {
    if (!filterName.trim()) { setLocalItems(initItems); return; }
    setFiltering(true);
    try { const r = await callTool('hs__get_deals', { name: filterName }); setLocalItems(r?.items || []); }
    finally { setFiltering(false); }
  };

  const toggleExpand = useCallback(async (dId: string) => {
    if (expandedId === dId) { setExpandedId(null); return; }
    setExpandedId(dId);
    if (dealContacts[dId]) return;
    setLoadingExpand(dId);
    try {
      const r = await callTool('hs__get_deal_contacts', { deal_id: dId });
      setDealContacts(p => ({ ...p, [dId]: r?.items || [] }));
    } catch { setDealContacts(p => ({ ...p, [dId]: [] })); }
    finally { setLoadingExpand(null); }
  }, [expandedId, dealContacts, callTool]);

  const openEdit = (d: any) => { setCreating(false); setExpandedId(null); setEditingId(d.id); setForm({ dealname: d.dealname || '', amount: d.amount != null ? String(d.amount) : '', dealstage: d.dealstage || '', closedate: d.closedate || '', pipeline: d.pipeline || '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ dealname: '', amount: '', dealstage: '', closedate: '', pipeline: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      const args = { ...form, amount: form.amount ? parseFloat(form.amount) : undefined };
      if (creating) { await callTool('hs__create_deal', args); toast('✓ Deal created'); }
      else { await callTool('hs__update_deal', { deal_id: editingId, ...args }); toast('✓ Deal updated'); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));
  const fFields = (f: typeof form) => [
    { label: 'Deal Name *', key: 'dealname', value: f.dealname, onChange: (v: string) => setF('dealname', v) },
    { label: 'Amount ($)', key: 'amount', value: f.amount, onChange: (v: string) => setF('amount', v) },
    { label: 'Stage', key: 'dealstage', value: f.dealstage, onChange: (v: string) => setF('dealstage', v), type: 'select' as const, options: DEAL_STAGES.filter(s => s.value).map(s => s.value), optionLabels: stageLabels },
    { label: 'Close Date', key: 'closedate', value: f.closedate, onChange: (v: string) => setF('closedate', v) },
    { label: 'Pipeline', key: 'pipeline', value: f.pipeline, onChange: (v: string) => setF('pipeline', v), type: 'select' as const, options: HS_PIPELINES },
  ];

  const H_STYLE: React.CSSProperties = { fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.4px', padding: '8px 12px' };

  return (
    <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
      <HsViewHeader icon={<span style={{ fontSize: 20, color: c.teal }}>💰</span>} title="Deals" count={total ?? localItems.length} onNew={openCreate} newLabel="New Deal" />
      <HsFilterBar value={filterName} onChange={setFilterName} onSearch={doSearch} placeholder="Search by deal name…" loading={filtering} hidden={creating} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ backgroundColor: c.surface }}>
            {['', 'Deal Name', 'Amount', 'Stage', 'Close Date', ''].map((h, i) => (
              <TableHeaderCell key={i} className={styles.headerCell} style={{ color: c.textSec, borderBottom: `2px solid ${c.border}`, ...H_STYLE, ...(i === 0 ? { width: 28 } : {}) }}>{h}</TableHeaderCell>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <HsFormRow colSpan={6} title="➕ New Deal" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={6} style={{ textAlign: 'center', padding: 32, color: c.textSec }}>No deals found.</TableCell></TableRow>}
          {localItems.map((d: any) => (
            <React.Fragment key={d.id}>
              <TableRow style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = c.hoverBg)}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = c.bg)}>
                <TableCell className={styles.cell} style={{ width: 28, padding: '6px 8px' }}>
                  <button onClick={() => toggleExpand(d.id)}
                    style={{ width: 22, height: 22, border: `1px solid ${c.border}`, borderRadius: '3px', background: expandedId === d.id ? c.surface : 'transparent', cursor: 'pointer', fontSize: '11px', color: c.teal, fontWeight: 700, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                    {loadingExpand === d.id ? '…' : expandedId === d.id ? '▼' : '▶'}
                  </button>
                </TableCell>
                <TableCell className={styles.cell} style={{ color: c.text, fontWeight: 600 }}>{d.dealname}</TableCell>
                <TableCell className={styles.cell} style={{ color: c.teal, fontWeight: 500 }}>{d.amount != null ? '$' + Number(d.amount).toLocaleString() : '—'}</TableCell>
                <TableCell className={styles.cell}>
                  {d.dealstage ? <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 600, backgroundColor: c.surface, color: c.teal, border: `1px solid ${c.border}` }}>{stageLabels[d.dealstage] || d.dealstage}</span> : '—'}
                </TableCell>
                <TableCell className={styles.cell} style={{ color: c.textSec }}>{d.closedate ? d.closedate.slice(0, 10) : '—'}</TableCell>
                <TableCell className={styles.cell}><Button appearance="subtle" icon={<EditRegular />} size="small" title="Edit" onClick={() => openEdit(d)} /></TableCell>
              </TableRow>
              {editingId === d.id && <HsFormRow colSpan={6} title="✏️ Edit Deal" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} />}
              {expandedId === d.id && (
                <TableRow>
                  <TableCell colSpan={6} style={{ padding: 0, backgroundColor: c.surface }}>
                    <div style={{ padding: '10px 20px 14px', borderTop: `2px solid ${c.teal}` }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: c.textSec, marginBottom: 8 }}>Associated Contacts</div>
                      {(dealContacts[d.id] || []).length === 0 ? (
                        <div style={{ fontSize: '13px', color: c.textSec, fontStyle: 'italic' }}>No contacts associated.</div>
                      ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                          <thead>
                            <tr style={{ backgroundColor: c.bg }}>
                              {['Name', 'Email', 'Company', 'Stage'].map(h => (
                                <th key={h} style={{ padding: '4px 10px', textAlign: 'left', color: c.textSec, borderBottom: `1px solid ${c.border}`, fontWeight: 600 }}>{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {(dealContacts[d.id] || []).map((ct: any) => (
                              <tr key={ct.id} style={{ borderBottom: `1px solid ${c.border}` }}>
                                <td style={{ padding: '4px 10px', color: c.text, fontWeight: 500 }}>{`${ct.firstname || ''} ${ct.lastname || ''}`.trim() || '—'}</td>
                                <td style={{ padding: '4px 10px', color: c.textSec }}>{ct.email || '—'}</td>
                                <td style={{ padding: '4px 10px', color: c.textSec }}>{ct.company || '—'}</td>
                                <td style={{ padding: '4px 10px', color: c.coral }}>{ct.lifecyclestage || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ── Tickets View ──────────────────────────────────────────────────────
function TicketsView({ items: initItems, total, callTool, toast }: {
  items: any[]; total?: number;
  callTool: (n: string, a?: any) => Promise<any>;
  toast: (m: string, t?: any) => void;
}) {
  const styles = useStyles();
  const c = useHsColors();
  const [localItems, setLocalItems] = useState(initItems);
  const [filterSubject, setFilterSubject] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loadingExpand, setLoadingExpand] = useState<string | null>(null);
  const [ticketNotes, setTicketNotes] = useState<Record<string, any[]>>({});
  const [form, setForm] = useState({ subject: '', status: '', priority: '', category: '', description: '' });

  useEffect(() => setLocalItems(initItems), [initItems]);

  const doSearch = async () => {
    if (!filterSubject.trim()) { setLocalItems(initItems); return; }
    setFiltering(true);
    try { const r = await callTool('hs__get_tickets', { subject: filterSubject }); setLocalItems(r?.items || []); }
    finally { setFiltering(false); }
  };

  const toggleExpand = useCallback(async (tkId: string) => {
    if (expandedId === tkId) { setExpandedId(null); return; }
    setExpandedId(tkId);
    if (ticketNotes[tkId]) return;
    setLoadingExpand(tkId);
    try {
      const r = await callTool('hs__get_ticket_notes', { ticket_id: tkId });
      setTicketNotes(p => ({ ...p, [tkId]: r?.items || [] }));
    } catch { setTicketNotes(p => ({ ...p, [tkId]: [] })); }
    finally { setLoadingExpand(null); }
  }, [expandedId, ticketNotes, callTool]);

  const openEdit = (tk: any) => { setCreating(false); setExpandedId(null); setEditingId(tk.id); setForm({ subject: tk.subject || '', status: tk.status || '', priority: tk.priority || '', category: tk.category || '', description: tk.description || '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ subject: '', status: 'new', priority: 'MEDIUM', category: '', description: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) { await callTool('hs__create_ticket', form); toast('✓ Ticket created'); }
      else { await callTool('hs__update_ticket', { ticket_id: editingId, ...form }); toast('✓ Ticket updated'); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));
  const fFields = (f: typeof form) => [
    { label: 'Subject *', key: 'subject', value: f.subject, onChange: (v: string) => setF('subject', v) },
    { label: 'Status', key: 'status', value: f.status, onChange: (v: string) => setF('status', v), type: 'select' as const, options: HS_TICKET_STATUS },
    { label: 'Priority', key: 'priority', value: f.priority, onChange: (v: string) => setF('priority', v), type: 'select' as const, options: HS_TICKET_PRIORITY },
    { label: 'Category', key: 'category', value: f.category, onChange: (v: string) => setF('category', v) },
    { label: 'Description', key: 'description', value: f.description, onChange: (v: string) => setF('description', v) },
  ];

  const priorityColor = (p: string) => p === 'HIGH' ? c.error : p === 'MEDIUM' ? '#DD7A01' : c.textSec;
  const H_STYLE: React.CSSProperties = { fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.4px', padding: '8px 12px' };

  return (
    <div className={styles.tableWrapper} style={{ border: `1px solid ${c.border}` }}>
      <HsViewHeader icon={<span style={{ fontSize: 20, color: c.coral }}>🎫</span>} title="Tickets" count={total ?? localItems.length} onNew={openCreate} newLabel="New Ticket" />
      <HsFilterBar value={filterSubject} onChange={setFilterSubject} onSearch={doSearch} placeholder="Search by subject…" loading={filtering} hidden={creating} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ backgroundColor: c.surface }}>
            {['', 'Subject', 'Status', 'Priority', 'Category', ''].map((h, i) => (
              <TableHeaderCell key={i} className={styles.headerCell} style={{ color: c.textSec, borderBottom: `2px solid ${c.border}`, ...H_STYLE, ...(i === 0 ? { width: 28 } : {}) }}>{h}</TableHeaderCell>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <HsFormRow colSpan={6} title="➕ New Ticket" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={6} style={{ textAlign: 'center', padding: 32, color: c.textSec }}>No tickets found.</TableCell></TableRow>}
          {localItems.map((tk: any) => (
            <React.Fragment key={tk.id}>
              <TableRow style={{ backgroundColor: c.bg, borderBottom: `1px solid ${c.border}` }}
                onMouseEnter={e => (e.currentTarget.style.backgroundColor = c.hoverBg)}
                onMouseLeave={e => (e.currentTarget.style.backgroundColor = c.bg)}>
                <TableCell className={styles.cell} style={{ width: 28, padding: '6px 8px' }}>
                  <button onClick={() => toggleExpand(tk.id)}
                    style={{ width: 22, height: 22, border: `1px solid ${c.border}`, borderRadius: '3px', background: expandedId === tk.id ? c.surface : 'transparent', cursor: 'pointer', fontSize: '11px', color: c.coral, fontWeight: 700, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                    {loadingExpand === tk.id ? '…' : expandedId === tk.id ? '▼' : '▶'}
                  </button>
                </TableCell>
                <TableCell className={styles.cell} style={{ color: c.text, fontWeight: 600 }}>{tk.subject}</TableCell>
                <TableCell className={styles.cell}>
                  {tk.status ? <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: '3px', fontSize: '11px', fontWeight: 600, backgroundColor: c.surface, color: c.coral, border: `1px solid ${c.border}` }}>{tk.status}</span> : '—'}
                </TableCell>
                <TableCell className={styles.cell}>
                  {tk.priority ? <span style={{ fontWeight: 700, fontSize: '12px', color: priorityColor(tk.priority) }}>{tk.priority}</span> : '—'}
                </TableCell>
                <TableCell className={styles.cell} style={{ color: c.textSec }}>{tk.category || '—'}</TableCell>
                <TableCell className={styles.cell}><Button appearance="subtle" icon={<EditRegular />} size="small" title="Edit" onClick={() => openEdit(tk)} /></TableCell>
              </TableRow>
              {editingId === tk.id && <HsFormRow colSpan={6} title="✏️ Edit Ticket" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} />}
              {expandedId === tk.id && (
                <TableRow>
                  <TableCell colSpan={6} style={{ padding: 0, backgroundColor: c.editPanelBg }}>
                    <div style={{ padding: '10px 20px 14px', borderTop: `2px solid ${c.coral}` }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: c.textSec, marginBottom: 8 }}>Notes</div>
                      {(ticketNotes[tk.id] || []).length === 0 ? (
                        <div style={{ fontSize: '13px', color: c.textSec, fontStyle: 'italic' }}>No notes on this ticket.</div>
                      ) : (
                        (ticketNotes[tk.id] || []).map((note: any, idx: number) => (
                          <div key={idx} style={{ marginBottom: 8, padding: '6px 10px', backgroundColor: c.surface, borderRadius: 4, borderLeft: `3px solid ${c.coral}` }}>
                            <div style={{ fontSize: '11px', color: c.textSec, marginBottom: 3 }}>{note.created_at || ''}</div>
                            <div style={{ fontSize: '13px', color: c.text }}>{note.body || note.content || '—'}</div>
                          </div>
                        ))
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
    </div>
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
  const [listsCache, setListsCache] = useState<HubSpotData | null>(null);

  const navigateToLists = useCallback(async () => {
    if (listsCache) {
      setNav({ view: 'lists', data: listsCache });
      return;
    }
    setLoadingView('lists');
    try {
      const result = await callTool('hs__get_lists', {});
      setListsCache(result);
      setNav({ view: 'lists', data: result });
    } catch (e: any) {
      toast(e.message || 'Failed to load lists', 'error');
    } finally {
      setLoadingView(null);
    }
  }, [callTool, toast, listsCache]);

  const navigateToContacts = useCallback(async (listId: string, listName?: string) => {
    setLoadingView('contacts');
    try {
      const result = await callTool('hs__get_list_contacts', { list_id: listId });
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

  const backToEmails = useCallback(() => {
    setNav({ view: 'emails' });
  }, []);

  const backToLists = useCallback(() => {
    if (listsCache) {
      setNav({ view: 'lists', data: listsCache });
    } else {
      setNav({ view: 'emails' });
    }
  }, [listsCache]);

  // Initial loading skeleton
  if (!initialData && nav.view === 'emails') {
    return (
      <div className={styles.shell}>
        <EmailsSkeleton />
      </div>
    );
  }

  // Navigation loading skeleton
  if (loadingView) {
    return (
      <div className={styles.shell}>
        {loadingView === 'emails' && <EmailsSkeleton />}
        {loadingView === 'lists' && <ListsSkeleton />}
        {loadingView === 'contacts' && <ContactsSkeleton />}
      </div>
    );
  }

  // Contacts view
  if (nav.view === 'contacts' && nav.data) {
    return (
      <div className={styles.shell}>
        <ContactsView
          items={(nav.data.items || []) as Contact[]}
          total={nav.data.total}
          listName={nav.listName}
          listId={nav.listId}
          onBack={backToLists}
          callTool={callTool}
          toast={toast}
        />
        <McpFooter label="HubSpot Marketing" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
      </div>
    );
  }

  // Lists view
  if (nav.view === 'lists' && nav.data) {
    return (
      <div className={styles.shell}>
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
        />
        <McpFooter label="HubSpot Marketing" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
      </div>
    );
  }

  // Emails view (entry point) — also handle toolData pushing lists/contacts
  const data = initialData!;

  if (data.type === 'form') {
    return (
      <div className={styles.shell}>
        <FormView
          entity={data.entity || 'contact'}
          prefill={data.prefill}
          callTool={callTool}
          toast={toast}
        />
        <McpFooter label="HubSpot Marketing" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
      </div>
    );
  }

  if (data.type === 'lists') {
    return (
      <div className={styles.shell}>
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
        />
        <McpFooter label="HubSpot Marketing" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
      </div>
    );
  }

  if (data.type === 'list_contacts') {
    return (
      <div className={styles.shell}>
        <ContactsView
          items={(data.items || []) as Contact[]}
          total={data.total}
          listName={data.list_name || 'List'}
          listId={data.list_id || ''}
          onBack={backToLists}
          callTool={callTool}
          toast={toast}
        />
        <McpFooter label="HubSpot Marketing" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
      </div>
    );
  }

  if (data.type === 'contacts') {
    return (
      <div className={styles.shell}>
        <CrmContactsView items={(data.items || []) as CrmContact[]} total={data.total} callTool={callTool} toast={toast} />
        <McpFooter label="HubSpot CRM" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
      </div>
    );
  }

  if (data.type === 'companies') {
    return (
      <div className={styles.shell}>
        <CompaniesView items={(data.items || []) as Company[]} total={data.total} callTool={callTool} toast={toast} />
        <McpFooter label="HubSpot CRM" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
      </div>
    );
  }

  if (data.type === 'deals') {
    return (
      <div className={styles.shell}>
        <DealsView items={(data.items || []) as Deal[]} total={data.total} callTool={callTool} toast={toast} />
        <McpFooter label="HubSpot CRM" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
      </div>
    );
  }

  if (data.type === 'tickets') {
    return (
      <div className={styles.shell}>
        <TicketsView items={(data.items || []) as Ticket[]} total={data.total} callTool={callTool} toast={toast} />
        <McpFooter label="HubSpot CRM" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
      </div>
    );
  }

  // Default: emails
  return (
    <div className={styles.shell}>
      <EmailsView
        items={(data.items || []) as Email[]}
        total={data.total}
        onNavigateLists={navigateToLists}
        callTool={callTool}
        toast={toast}
      />
      <McpFooter label="HubSpot Marketing" openInLabel="Open in HubSpot" openInUrl="https://app.hubspot.com" />
    </div>
  );
}


