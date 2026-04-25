import React, { useState, useEffect } from 'react';
import {
  Badge,
  Button,
  Field,
  Input,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableHeaderCell,
  TableRow,
  Text,
  Textarea,
  makeStyles,
} from '@fluentui/react-components';
import { useToolData, useMcpBridge, useTheme } from '../shared/McpBridge';
import { ExpandButton } from '../shared/ExpandButton';
import { useToast } from '../shared/Toast';
import type {
  SnowData, Incident, ServiceRequest, RequestItem,
  ChangeRequest, ChangeTask, Problem, KnowledgeArticle, CatalogItem, SnowApproval,
} from './types';

// ── Now Design System Color Tokens ──────────────────────────────────────────
const NOW_LIGHT = {
  shell: '#293E40',
  brand: '#81B5A1',
  bg: '#F1F1F1',
  surface: '#FFFFFF',
  text: '#2E3D49',
  textWeak: '#6B7C93',
  border: '#D6D6D6',
  p1: '#FF402C',
  p2: '#FF8C00',
  p3: '#FFD700',
  p4: '#2E844A',
  success: '#2E8540',
  error: '#D63B20',
  headerBg: '#F4F5F7',
};

const NOW_DARK = {
  shell: '#161B22',
  brand: '#81B5A1',
  bg: '#161B22',
  surface: '#21262D',
  text: '#E6EDF3',
  textWeak: '#8B949E',
  border: '#30363D',
  p1: '#FF402C',
  p2: '#FF8C00',
  p3: '#FFD700',
  p4: '#2E844A',
  success: '#81B5A1',
  error: '#D63B20',
  headerBg: '#232A32',
};

function now(theme: 'light' | 'dark') {
  return theme === 'dark' ? NOW_DARK : NOW_LIGHT;
}

// ── Dropdown options ────────────────────────────────────────────────────────
const PRIORITIES = ['1', '2', '3', '4'];
const PRIORITY_LABELS: Record<string, string> = {
  '1': '1 – Critical', '2': '2 – High', '3': '3 – Moderate', '4': '4 – Low',
};
const INCIDENT_STATES = ['New', 'In Progress', 'On Hold', 'Resolved', 'Closed'];
const CATEGORIES = ['inquiry', 'software', 'hardware', 'network', 'database'];
const APPROVAL_OPTIONS = ['not requested', 'requested', 'approved', 'rejected'];
const CHANGE_CATEGORIES = ['Normal', 'Standard', 'Emergency'];
const RISK_OPTIONS = ['low', 'medium', 'high'];

// ── Priority pill styles ────────────────────────────────────────────────────
type PillStyle = { background: string; color: string };
type PillStyleMap = { light: PillStyle; dark: PillStyle };

const PRIORITY_STYLES: Record<string, PillStyleMap> = {
  '1': { light: { background: '#FDE7E7', color: '#A80000' }, dark: { background: '#3D1111', color: '#F87171' } },
  '2': { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
  '3': { light: { background: '#FFF8E0', color: '#7A6800' }, dark: { background: '#3D3511', color: '#FFD700' } },
  '4': { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
};

const STATE_STYLES: Record<string, PillStyleMap> = {
  'new':         { light: { background: '#EEF4FF', color: '#0066CC' }, dark: { background: '#0B3573', color: '#8DC7FF' } },
  'in progress': { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
  'on hold':     { light: { background: '#EAEAEA', color: '#555555' }, dark: { background: '#333333', color: '#AAAAAA' } },
  'resolved':    { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
  'closed':      { light: { background: '#2E3D49', color: '#FFFFFF' }, dark: { background: '#1A2030', color: '#8B949E' } },
  'published':   { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
  'requested':   { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
};

const APPROVAL_STYLES: Record<string, PillStyleMap> = {
  'approved':      { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
  'requested':     { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
  'not requested': { light: { background: '#EAEAEA', color: '#555555' }, dark: { background: '#333333', color: '#AAAAAA' } },
  'rejected':      { light: { background: '#FDE7E7', color: '#A80000' }, dark: { background: '#3D1111', color: '#F87171' } },
};

const RISK_STYLES: Record<string, PillStyleMap> = {
  'low':    { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
  'medium': { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
  'high':   { light: { background: '#FDE7E7', color: '#A80000' }, dark: { background: '#3D1111', color: '#F87171' } },
};

function PriorityPill({ priority, theme }: { priority: string; theme: 'light' | 'dark' }) {
  const key = String(priority).charAt(0);
  const style = PRIORITY_STYLES[key]?.[theme] || PRIORITY_STYLES['3'][theme];
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: '15px',
      fontSize: '11px', fontWeight: 600, letterSpacing: '0.2px',
      background: style.background, color: style.color,
    }}>
      {PRIORITY_LABELS[key] || priority || '—'}
    </span>
  );
}

function StatePill({ state, theme }: { state: string; theme: 'light' | 'dark' }) {
  const key = (state || '').toLowerCase();
  const style = STATE_STYLES[key]?.[theme] || { background: '#EAEAEA', color: '#555' };
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: '15px',
      fontSize: '11px', fontWeight: 500,
      background: style.background, color: style.color,
    }}>
      {state || '—'}
    </span>
  );
}

function ApprovalPill({ approval, theme }: { approval: string; theme: 'light' | 'dark' }) {
  const key = (approval || '').toLowerCase();
  const style = APPROVAL_STYLES[key]?.[theme] || APPROVAL_STYLES['not requested'][theme];
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: '15px',
      fontSize: '11px', fontWeight: 500,
      background: style.background, color: style.color,
    }}>
      {approval || '—'}
    </span>
  );
}

function RiskPill({ risk, theme }: { risk: string; theme: 'light' | 'dark' }) {
  const key = (risk || '').toLowerCase();
  const style = RISK_STYLES[key]?.[theme] || RISK_STYLES['medium'][theme];
  return (
    <span style={{
      display: 'inline-block', padding: '2px 10px', borderRadius: '15px',
      fontSize: '11px', fontWeight: 500,
      background: style.background, color: style.color,
    }}>
      {risk || '—'}
    </span>
  );
}

function SlaPill({ slaDue, madeSla, theme }: { slaDue?: string; madeSla?: boolean; theme: 'light' | 'dark' }) {
  if (!slaDue) return <span style={{ color: theme === 'dark' ? '#8B949E' : '#aaa', fontSize: '11px' }}>—</span>;
  const breached = madeSla === false;
  const met = madeSla === true;
  const bg = breached ? (theme === 'dark' ? '#3D1111' : '#FDE7E7') : met ? (theme === 'dark' ? '#1A3320' : '#E3F2E8') : (theme === 'dark' ? '#333' : '#EAEAEA');
  const color = breached ? (theme === 'dark' ? '#F87171' : '#A80000') : met ? (theme === 'dark' ? '#6EE7B7' : '#2E844A') : (theme === 'dark' ? '#aaa' : '#555');
  const label = breached ? '⚠ Breached' : met ? '✓ Met' : slaDue;
  return (
    <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: '15px', fontSize: '11px', fontWeight: 500, background: bg, color }}>
      {label}
    </span>
  );
}

// ── Styles ─────────────────────────────────────────────────────────────────
const useStyles = makeStyles({
  shell: {
    margin: '0 auto',
    padding: '12px',
    fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif",
    fontSize: '13px',
  },
  card: {
    borderRadius: '8px',
    overflow: 'hidden',
    boxShadow: '0 2px 4px rgba(0,0,0,0.07)',
    overflowX: 'auto' as const,
  },
  headerBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '10px 16px',
    color: '#fff',
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
  formPanel: {
    padding: '14px 16px',
    borderLeft: '3px solid #81B5A1',
  },
  formTitle: {
    fontSize: '14px',
    fontWeight: 600 as any,
    marginBottom: '10px',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '10px 12px',
    marginBottom: '12px',
  },
  formActions: {
    display: 'flex',
    gap: '8px',
    justifyContent: 'flex-end',
  },
  filterBar: {
    display: 'flex',
    gap: '6px',
    alignItems: 'center',
    padding: '8px 12px',
    borderBottom: '1px solid transparent',
  },
  empty: {
    padding: '16px',
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
  subTableWrap: {
    padding: '12px 16px',
  },
});

// ── Inline select ─────────────────────────────────────────────────────────
function FormSelect({ label, value, options, labels, onChange, theme }: {
  label: string;
  value: string;
  options: string[];
  labels?: Record<string, string>;
  onChange: (v: string) => void;
  theme: 'light' | 'dark';
}) {
  const t = now(theme);
  return (
    <Field label={label} size="small">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: '100%', padding: '5px 8px', borderRadius: '4px',
          border: `1px solid ${t.border}`, background: t.surface,
          color: t.text, fontSize: '13px', fontFamily: 'inherit', height: '32px',
        }}
      >
        <option value="">— Select —</option>
        {options.map((o) => <option key={o} value={o}>{labels?.[o] || o}</option>)}
      </select>
    </Field>
  );
}

// ── Filter Bar ─────────────────────────────────────────────────────────────
function FilterBar({ value, onChange, onSearch, placeholder, theme }: {
  value: string;
  onChange: (v: string) => void;
  onSearch?: () => void;
  placeholder?: string;
  theme: 'light' | 'dark';
}) {
  const t = now(theme);
  const styles = useStyles();
  return (
    <div className={styles.filterBar} style={{ borderBottomColor: t.border, background: t.headerBg }}>
      <Input
        size="small"
        value={value}
        onChange={(_, d) => onChange(d.value)}
        onKeyDown={(e) => e.key === 'Enter' && onSearch?.()}
        placeholder={placeholder || 'Filter…'}
        style={{ flex: 1, maxWidth: '260px' }}
      />
      {onSearch && (
        <button
          onClick={onSearch}
          style={{
            padding: '4px 12px', borderRadius: '4px',
            border: `1px solid ${t.border}`, background: '#293E40',
            color: '#fff', fontSize: '12px', cursor: 'pointer', fontFamily: 'inherit',
          }}
        >
          Search
        </button>
      )}
    </div>
  );
}

// ── Now Footer ──────────────────────────────────────────────────────────────
function NowFooter({ theme }: { theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = now(theme);
  const { openExternal } = useMcpBridge();
  return (
    <div className={styles.mcpFooter} style={{
      background: theme === 'dark' ? '#1C2229' : '#F4F5F7',
      borderTop: `1px solid ${t.border}`, color: t.textWeak,
    }}>
      <span>⚡ <strong>MCP Widget</strong> · ServiceNow ITSM</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ cursor: 'pointer', textDecoration: 'underline' }}
          onClick={() => openExternal('https://developer.servicenow.com')}>
          Open in ServiceNow ↗
        </span>
        <span>⚓ GTC</span>
      </div>
    </div>
  );
}

// ── Request Items sub-table ─────────────────────────────────────────────────
function RequestItemsTable({ items, callTool, toast, theme }: {
  items: RequestItem[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  theme: 'light' | 'dark';
}) {
  const t = now(theme);
  const [editingQty, setEditingQty] = useState<Record<string, string>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  const saveQty = async (item: RequestItem) => {
    const qty = editingQty[item.sys_id] ?? String(item.quantity);
    setSavingId(item.sys_id);
    try {
      await callTool('sn__update_request_item', { sys_id: item.sys_id, quantity: qty });
      toast('✓ Quantity updated');
    } catch (e: any) {
      toast(e.message || 'Failed to update quantity', 'error');
    } finally {
      setSavingId(null);
    }
  };

  const subHeaderStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '9px', textTransform: 'uppercase',
    letterSpacing: '0.5px', padding: '4px 8px', color: t.textWeak,
    background: 'transparent',
  };
  const subCellStyle: React.CSSProperties = {
    padding: '4px 8px', fontSize: '12px', verticalAlign: 'middle',
    borderBottom: `1px solid ${t.border}`,
  };

  if (items.length === 0) {
    return <div style={{ padding: '8px', color: t.textWeak, fontSize: '12px', fontStyle: 'italic' }}>No request items.</div>;
  }

  return (
    <div>
      <div style={{ fontSize: '12px', fontWeight: 600, color: t.text, marginBottom: '4px' }}>
        📦 Request Items ({items.length})
      </div>
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow>
            <TableHeaderCell style={subHeaderStyle}>Item</TableHeaderCell>
            <TableHeaderCell style={subHeaderStyle}>Category</TableHeaderCell>
            <TableHeaderCell style={subHeaderStyle}>Qty</TableHeaderCell>
            <TableHeaderCell style={subHeaderStyle}>Stage</TableHeaderCell>
            <TableHeaderCell style={subHeaderStyle}>Price</TableHeaderCell>
            <TableHeaderCell style={{ ...subHeaderStyle, width: 60 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.sys_id}>
              <TableCell style={subCellStyle}>{item.short_description || '—'}</TableCell>
              <TableCell style={subCellStyle}>{item.cat_item || '—'}</TableCell>
              <TableCell style={subCellStyle}>
                <input
                  type="number"
                  min="1"
                  value={editingQty[item.sys_id] ?? String(item.quantity || 1)}
                  onChange={(e) => setEditingQty(prev => ({ ...prev, [item.sys_id]: e.target.value }))}
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    width: '56px', padding: '3px 6px', borderRadius: '4px',
                    border: `1px solid ${t.border}`, background: t.surface,
                    color: t.text, fontSize: '12px', textAlign: 'center',
                    fontFamily: 'inherit',
                  }}
                />
              </TableCell>
              <TableCell style={subCellStyle}>{item.stage || '—'}</TableCell>
              <TableCell style={subCellStyle}>{item.price || '—'}</TableCell>
              <TableCell style={subCellStyle}>
                <button
                  onClick={(e) => { e.stopPropagation(); saveQty(item); }}
                  disabled={savingId === item.sys_id}
                  style={{
                    padding: '3px 8px', borderRadius: '3px', border: 'none',
                    background: '#293E40', color: '#fff', fontSize: '10px',
                    fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit',
                    opacity: savingId === item.sys_id ? 0.6 : 1,
                  }}
                >
                  {savingId === item.sys_id ? '…' : 'Save'}
                </button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ── Incidents View ──────────────────────────────────────────────────────────
function IncidentsView({ items, callTool, toast, theme }: {
  items: Incident[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles();
  const t = now(theme);
  const [filter, setFilter] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState<Record<string, string>>({});
  const [addingNote, setAddingNote] = useState<string | null>(null);
  const [form, setForm] = useState({
    short_description: '', description: '', priority: '3', state: 'New', category: 'inquiry',
  });

  const filteredItems = items.filter(inc =>
    !filter ||
    inc.number?.toLowerCase().includes(filter.toLowerCase()) ||
    inc.short_description?.toLowerCase().includes(filter.toLowerCase()) ||
    inc.assigned_to?.toLowerCase().includes(filter.toLowerCase())
  );

  const openEdit = (inc: Incident) => {
    setCreating(false);
    setExpandedId(null);
    setEditingId(inc.sys_id);
    setForm({
      short_description: inc.short_description || '',
      description: inc.description || '',
      priority: String(inc.priority).charAt(0) || '3',
      state: inc.state || 'New',
      category: 'inquiry',
    });
  };

  const openCreate = () => {
    setEditingId(null);
    setExpandedId(null);
    setCreating(true);
    setForm({ short_description: '', description: '', priority: '3', state: 'New', category: 'inquiry' });
  };

  const cancel = () => { setEditingId(null); setCreating(false); };

  const toggleWorkNotes = (id: string) => {
    if (editingId) return;
    setExpandedId(prev => prev === id ? null : id);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) {
        await callTool('sn__create_incident', {
          short_description: form.short_description,
          description: form.description,
          priority: form.priority,
          category: form.category,
        });
        toast('✓ Incident created');
      } else {
        await callTool('sn__update_incident', {
          sys_id: editingId,
          description: form.description,
          priority: form.priority,
        });
        toast('✓ Incident updated');
        setLastSavedId(editingId);
      }
      cancel();
    } catch (e: any) {
      toast(e.message || 'Operation failed', 'error');
    } finally {
      setSaving(false);
    }
  };

  const submitNote = async (sys_id: string) => {
    const text = (noteText[sys_id] || '').trim();
    if (!text) { toast('Enter a work note first', 'error'); return; }
    setAddingNote(sys_id);
    try {
      await callTool('sn__add_work_note', { sys_id, work_note: text });
      toast('✓ Work note added');
      setNoteText(p => ({ ...p, [sys_id]: '' }));
      setExpandedId(null);
    } catch (e: any) {
      toast(e.message || 'Failed to add work note', 'error');
    } finally {
      setAddingNote(null);
    }
  };

  useEffect(() => {
    if (lastSavedId) {
      const t2 = setTimeout(() => setLastSavedId(null), 1600);
      return () => clearTimeout(t2);
    }
  }, [lastSavedId]);

  const formBg = theme === 'dark' ? '#1A2E25' : '#F4F5F7';
  const colSpan = 7;

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden',
    textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle',
  };
  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase',
    letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };

  const renderForm = (title: string) => (
    <TableRow>
      <TableCell colSpan={colSpan} style={{ padding: 0 }}>
        <div className={styles.formPanel} style={{ background: formBg, borderColor: t.brand }}>
          <div className={styles.formTitle} style={{ color: '#293E40' }}>{title}</div>
          <div className={styles.formGrid}>
            {creating && (
              <Field label="Short Description" size="small" style={{ gridColumn: '1 / -1' }}>
                <Input size="small" value={form.short_description} onChange={(_, d) => setForm(f => ({ ...f, short_description: d.value }))} />
              </Field>
            )}
            <Field label="Description" size="small" style={{ gridColumn: '1 / -1' }}>
              <Input size="small" value={form.description} onChange={(_, d) => setForm(f => ({ ...f, description: d.value }))} />
            </Field>
            <FormSelect label="Priority" value={form.priority} options={PRIORITIES} labels={PRIORITY_LABELS} onChange={v => setForm(f => ({ ...f, priority: v }))} theme={theme} />
            {creating && (
              <FormSelect label="Category" value={form.category} options={CATEGORIES} onChange={v => setForm(f => ({ ...f, category: v }))} theme={theme} />
            )}
          </div>
          <div className={styles.formActions}>
            <Button appearance="secondary" size="small" onClick={cancel} disabled={saving}
              style={{ borderRadius: '4px', height: '32px', padding: '0 16px', border: `1px solid ${t.border}` }}>
              Cancel
            </Button>
            <Button appearance="primary" size="small" onClick={handleSave} disabled={saving}
              style={{ background: '#293E40', borderColor: '#293E40', borderRadius: '4px', height: '32px', padding: '0 16px' }}>
              {saving ? 'Saving…' : creating ? '✓ Create' : '✓ Save'}
            </Button>
          </div>
        </div>
      </TableCell>
    </TableRow>
  );

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#293E40' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>🎫</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Incidents</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
            {items.length} record{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button onClick={openCreate}
            style={{
              background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)',
              color: '#fff', borderRadius: '4px', height: '32px', padding: '0 16px',
              cursor: 'pointer', fontSize: '12px', fontFamily: 'inherit', fontWeight: 500,
            }}>
            + New Incident
          </button>
          <ExpandButton />
        </div>
      </div>

      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by number, description, assignee…" theme={theme} />

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Number</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Short Description</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Priority</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>State</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Assigned To</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>SLA</TableHeaderCell>
            <TableHeaderCell style={{ ...headerCellStyle, width: 50 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && renderForm('➕ New Incident')}
          {filteredItems.length === 0 && !creating && (
            <TableRow>
              <TableCell colSpan={colSpan} className={styles.empty}>
                <Text>{filter ? 'No matching incidents.' : 'No incidents found.'}</Text>
              </TableCell>
            </TableRow>
          )}
          {filteredItems.map((inc, idx) => (
            <React.Fragment key={inc.sys_id}>
              <TableRow
                className="snow-row"
                onClick={() => toggleWorkNotes(inc.sys_id)}
                style={{
                  cursor: 'pointer',
                  borderBottom: idx === filteredItems.length - 1 && expandedId !== inc.sys_id ? 'none' : `1px solid ${t.border}`,
                  background: expandedId === inc.sys_id ? (theme === 'dark' ? '#1A2E25' : '#EEF6F1') : 'transparent',
                  ...(lastSavedId === inc.sys_id ? { animation: 'snowRowFlash 1.5s ease-out' } : {}),
                }}
              >
                <TableCell style={cellStyle}>
                  <span style={{ fontFamily: 'monospace', fontWeight: 500, color: '#293E40' }}>
                    {expandedId === inc.sys_id ? '▼' : '▶'} {inc.number}
                  </span>
                </TableCell>
                <TableCell style={{ ...cellStyle, maxWidth: '220px' }}>{inc.short_description || '—'}</TableCell>
                <TableCell style={cellStyle}><PriorityPill priority={inc.priority} theme={theme} /></TableCell>
                <TableCell style={cellStyle}><StatePill state={inc.state} theme={theme} /></TableCell>
                <TableCell style={cellStyle}>{inc.assigned_to || '—'}</TableCell>
                <TableCell style={cellStyle}><SlaPill slaDue={inc.sla_due} madeSla={inc.made_sla} theme={theme} /></TableCell>
                <TableCell style={cellStyle}>
                  <button title="Edit" onClick={(e) => { e.stopPropagation(); openEdit(inc); }} className="snow-edit-btn"
                    style={{
                      width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer',
                      color: t.textWeak, fontSize: '14px', padding: 0,
                    }}>✏️</button>
                </TableCell>
              </TableRow>
              {editingId === inc.sys_id && renderForm('✏️ Edit Incident ' + inc.number)}
              {expandedId === inc.sys_id && (
                <TableRow>
                  <TableCell colSpan={colSpan} style={{ padding: 0 }}>
                    <div className={styles.subTableWrap} style={{
                      background: theme === 'dark' ? '#1A2E25' : '#EEF6F1',
                      borderBottom: `1px solid ${t.border}`,
                    }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: t.text, marginBottom: '8px' }}>
                        📝 Add Work Note — {inc.number}
                      </div>
                      <textarea
                        value={noteText[inc.sys_id] || ''}
                        onChange={(e) => setNoteText(p => ({ ...p, [inc.sys_id]: e.target.value }))}
                        placeholder="Enter work note (internal — visible to IT staff only)…"
                        rows={3}
                        style={{
                          width: '100%', padding: '8px', borderRadius: '4px',
                          border: `1px solid ${t.border}`, background: t.surface,
                          color: t.text, fontSize: '12px', fontFamily: 'inherit',
                          resize: 'vertical', boxSizing: 'border-box',
                        }}
                      />
                      <div style={{ display: 'flex', gap: '8px', marginTop: '8px', justifyContent: 'flex-end' }}>
                        <button onClick={() => setExpandedId(null)} style={{
                          padding: '4px 12px', borderRadius: '4px', border: `1px solid ${t.border}`,
                          background: 'transparent', color: t.textWeak, fontSize: '11px', cursor: 'pointer', fontFamily: 'inherit',
                        }}>▲ Collapse</button>
                        <button
                          onClick={() => submitNote(inc.sys_id)}
                          disabled={addingNote === inc.sys_id}
                          style={{
                            padding: '4px 14px', borderRadius: '4px', border: 'none',
                            background: '#293E40', color: '#fff', fontSize: '12px',
                            cursor: addingNote === inc.sys_id ? 'not-allowed' : 'pointer',
                            fontFamily: 'inherit', opacity: addingNote === inc.sys_id ? 0.6 : 1,
                          }}>
                          {addingNote === inc.sys_id ? '…' : '+ Add Note'}
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

      <NowFooter theme={theme} />
    </div>
  );
}

// ── Requests View ───────────────────────────────────────────────────────────
function RequestsView({ items, callTool, toast, theme }: {
  items: ServiceRequest[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles();
  const t = now(theme);
  const [filter, setFilter] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [reqItems, setReqItems] = useState<Record<string, RequestItem[]>>({});
  const [loadingItems, setLoadingItems] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [form, setForm] = useState({
    short_description: '', description: '', priority: '3', approval: 'not requested',
  });

  const filteredItems = items.filter(req =>
    !filter ||
    req.number?.toLowerCase().includes(filter.toLowerCase()) ||
    req.short_description?.toLowerCase().includes(filter.toLowerCase())
  );

  const toggleExpand = async (req: ServiceRequest) => {
    if (expandedId === req.sys_id) { setExpandedId(null); return; }
    setExpandedId(req.sys_id);
    if (!reqItems[req.sys_id]) {
      setLoadingItems(req.sys_id);
      try {
        const result = await callTool('sn__get_request_items', { request_sys_id: req.sys_id });
        setReqItems(prev => ({ ...prev, [req.sys_id]: result?.items || [] }));
      } catch {
        setReqItems(prev => ({ ...prev, [req.sys_id]: [] }));
      } finally {
        setLoadingItems(null);
      }
    }
  };

  const openEdit = (req: ServiceRequest) => {
    setCreating(false);
    setEditingId(req.sys_id);
    setForm({
      short_description: req.short_description || '',
      description: '',
      priority: String(req.priority).charAt(0) || '3',
      approval: (req.approval || 'not requested').toLowerCase(),
    });
  };

  const openCreate = () => {
    setEditingId(null);
    setCreating(true);
    setForm({ short_description: '', description: '', priority: '3', approval: 'not requested' });
  };

  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) {
        await callTool('sn__create_request', {
          short_description: form.short_description,
          description: form.description,
          priority: form.priority,
        });
        toast('✓ Request created');
      } else {
        await callTool('sn__update_request', { sys_id: editingId, approval: form.approval });
        toast('✓ Request updated');
        setLastSavedId(editingId);
      }
      cancel();
    } catch (e: any) {
      toast(e.message || 'Operation failed', 'error');
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    if (lastSavedId) {
      const t2 = setTimeout(() => setLastSavedId(null), 1600);
      return () => clearTimeout(t2);
    }
  }, [lastSavedId]);

  const formBg = theme === 'dark' ? '#1A2E25' : '#F4F5F7';
  const colSpan = 6;

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden',
    textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle',
  };
  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase',
    letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };

  const renderForm = (title: string) => (
    <TableRow>
      <TableCell colSpan={colSpan} style={{ padding: 0 }}>
        <div className={styles.formPanel} style={{ background: formBg, borderColor: t.brand }}>
          <div className={styles.formTitle} style={{ color: '#293E40' }}>{title}</div>
          <div className={styles.formGrid}>
            {creating && (
              <>
                <Field label="Short Description" size="small" style={{ gridColumn: '1 / -1' }}>
                  <Input size="small" value={form.short_description} onChange={(_, d) => setForm(f => ({ ...f, short_description: d.value }))} />
                </Field>
                <Field label="Description" size="small" style={{ gridColumn: '1 / -1' }}>
                  <Input size="small" value={form.description} onChange={(_, d) => setForm(f => ({ ...f, description: d.value }))} />
                </Field>
                <FormSelect label="Priority" value={form.priority} options={PRIORITIES} labels={PRIORITY_LABELS} onChange={v => setForm(f => ({ ...f, priority: v }))} theme={theme} />
              </>
            )}
            {!creating && (
              <FormSelect label="Approval" value={form.approval} options={APPROVAL_OPTIONS} onChange={v => setForm(f => ({ ...f, approval: v }))} theme={theme} />
            )}
          </div>
          <div className={styles.formActions}>
            <Button appearance="secondary" size="small" onClick={cancel} disabled={saving}
              style={{ borderRadius: '4px', height: '32px', padding: '0 16px', border: `1px solid ${t.border}` }}>
              Cancel
            </Button>
            <Button appearance="primary" size="small" onClick={handleSave} disabled={saving}
              style={{ background: '#293E40', borderColor: '#293E40', borderRadius: '4px', height: '32px', padding: '0 16px' }}>
              {saving ? 'Saving…' : creating ? '✓ Create' : '✓ Save'}
            </Button>
          </div>
        </div>
      </TableCell>
    </TableRow>
  );

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#293E40' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>📋</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Service Requests</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
            {items.length} record{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button onClick={openCreate}
            style={{
              background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)',
              color: '#fff', borderRadius: '4px', height: '32px', padding: '0 16px',
              cursor: 'pointer', fontSize: '12px', fontFamily: 'inherit', fontWeight: 500,
            }}>
            + New Request
          </button>
          <ExpandButton />
        </div>
      </div>

      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by number or description…" theme={theme} />

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Number</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>State</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Priority</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Approval</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>SLA</TableHeaderCell>
            <TableHeaderCell style={{ ...headerCellStyle, width: 50 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && renderForm('➕ New Request')}
          {filteredItems.length === 0 && !creating && (
            <TableRow>
              <TableCell colSpan={colSpan} className={styles.empty}>
                <Text>{filter ? 'No matching requests.' : 'No requests found.'}</Text>
              </TableCell>
            </TableRow>
          )}
          {filteredItems.map((req, idx) => (
            <React.Fragment key={req.sys_id}>
              <TableRow
                className="snow-row"
                onClick={() => toggleExpand(req)}
                style={{
                  cursor: 'pointer',
                  borderBottom: idx === filteredItems.length - 1 && expandedId !== req.sys_id ? 'none' : `1px solid ${t.border}`,
                  background: expandedId === req.sys_id ? (theme === 'dark' ? '#1A2E25' : '#EEF6F1') : 'transparent',
                  ...(lastSavedId === req.sys_id ? { animation: 'snowRowFlash 1.5s ease-out' } : {}),
                }}
              >
                <TableCell style={cellStyle}>
                  <span style={{ fontFamily: 'monospace', fontWeight: 500, color: '#293E40' }}>
                    {expandedId === req.sys_id ? '▼' : '▶'} {req.number}
                  </span>
                </TableCell>
                <TableCell style={cellStyle}><StatePill state={req.request_state} theme={theme} /></TableCell>
                <TableCell style={cellStyle}><PriorityPill priority={req.priority} theme={theme} /></TableCell>
                <TableCell style={cellStyle}><ApprovalPill approval={req.approval} theme={theme} /></TableCell>
                <TableCell style={cellStyle}><SlaPill slaDue={req.sla_due} madeSla={req.made_sla} theme={theme} /></TableCell>
                <TableCell style={cellStyle}>
                  <button title="Edit" onClick={(e) => { e.stopPropagation(); openEdit(req); }} className="snow-edit-btn"
                    style={{
                      width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer',
                      color: t.textWeak, fontSize: '14px', padding: 0,
                    }}>✏️</button>
                </TableCell>
              </TableRow>
              {editingId === req.sys_id && renderForm('✏️ Edit Request ' + req.number)}
              {expandedId === req.sys_id && (
                <TableRow>
                  <TableCell colSpan={colSpan} style={{ padding: 0 }}>
                    <div className={styles.subTableWrap} style={{
                      background: theme === 'dark' ? '#1A2E25' : '#EEF6F1',
                      borderBottom: `1px solid ${t.border}`,
                    }}>
                      {loadingItems === req.sys_id ? (
                        <div style={{ padding: '8px', color: t.textWeak, fontSize: '12px', fontStyle: 'italic' }}>
                          Fetching request items…
                        </div>
                      ) : (
                        <RequestItemsTable items={reqItems[req.sys_id] || []} callTool={callTool} toast={toast} theme={theme} />
                      )}
                      <button onClick={() => setExpandedId(null)} style={{
                        marginTop: '8px', padding: '4px 12px', borderRadius: '4px',
                        border: `1px solid ${t.border}`, background: 'transparent',
                        color: t.textWeak, fontSize: '11px', cursor: 'pointer', fontFamily: 'inherit',
                      }}>▲ Collapse</button>
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>

      <NowFooter theme={theme} />
    </div>
  );
}

// ── Change Tasks sub-table ──────────────────────────────────────────────────
function ChangeTasksTable({ items, theme }: { items: ChangeTask[]; theme: 'light' | 'dark' }) {
  const t = now(theme);
  const subHeaderStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '9px', textTransform: 'uppercase',
    letterSpacing: '0.5px', padding: '4px 8px', color: t.textWeak, background: 'transparent',
  };
  const subCellStyle: React.CSSProperties = {
    padding: '4px 8px', fontSize: '12px', verticalAlign: 'middle', borderBottom: `1px solid ${t.border}`,
  };
  if (items.length === 0) {
    return <div style={{ padding: '8px', color: t.textWeak, fontSize: '12px', fontStyle: 'italic' }}>No change tasks.</div>;
  }
  return (
    <div>
      <div style={{ fontSize: '12px', fontWeight: 600, color: t.text, marginBottom: '4px' }}>🔧 Change Tasks ({items.length})</div>
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow>
            <TableHeaderCell style={subHeaderStyle}>Number</TableHeaderCell>
            <TableHeaderCell style={subHeaderStyle}>Short Description</TableHeaderCell>
            <TableHeaderCell style={subHeaderStyle}>State</TableHeaderCell>
            <TableHeaderCell style={subHeaderStyle}>Assigned To</TableHeaderCell>
            <TableHeaderCell style={subHeaderStyle}>Planned Start</TableHeaderCell>
            <TableHeaderCell style={subHeaderStyle}>Planned End</TableHeaderCell>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map(task => (
            <TableRow key={task.sys_id}>
              <TableCell style={subCellStyle}><span style={{ fontFamily: 'monospace', color: '#293E40', fontWeight: 500 }}>{task.number}</span></TableCell>
              <TableCell style={subCellStyle}>{task.short_description || '—'}</TableCell>
              <TableCell style={subCellStyle}><StatePill state={task.state} theme={theme} /></TableCell>
              <TableCell style={subCellStyle}>{task.assigned_to || '—'}</TableCell>
              <TableCell style={subCellStyle}>{task.planned_start || '—'}</TableCell>
              <TableCell style={subCellStyle}>{task.planned_end || '—'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ── Changes View ────────────────────────────────────────────────────────────
function ChangesView({ items, callTool, toast, theme }: {
  items: ChangeRequest[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles();
  const t = now(theme);
  const [filter, setFilter] = useState('');
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [changeTasks, setChangeTasks] = useState<Record<string, ChangeTask[]>>({});
  const [loadingTasks, setLoadingTasks] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [form, setForm] = useState({ short_description: '', category: 'Normal', risk: 'medium', priority: '3' });

  const filteredItems = items.filter(c =>
    !filter ||
    c.number?.toLowerCase().includes(filter.toLowerCase()) ||
    c.short_description?.toLowerCase().includes(filter.toLowerCase())
  );

  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ short_description: '', category: 'Normal', risk: 'medium', priority: '3' }); };
  const openEdit = (cr: ChangeRequest) => { setCreating(false); setEditingId(cr.sys_id); setForm({ short_description: cr.short_description || '', category: cr.category || 'Normal', risk: cr.risk || 'medium', priority: String(cr.priority).charAt(0) || '3' }); };
  const cancel = () => { setCreating(false); setEditingId(null); };

  const toggleExpand = async (id: string) => {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    if (!changeTasks[id]) {
      setLoadingTasks(id);
      try {
        const result = await callTool('sn__get_change_tasks', { change_sys_id: id });
        setChangeTasks(prev => ({ ...prev, [id]: result?.items || [] }));
      } catch {
        setChangeTasks(prev => ({ ...prev, [id]: [] }));
      } finally {
        setLoadingTasks(null);
      }
    }
  };

  useEffect(() => {
    if (lastSavedId) { const x = setTimeout(() => setLastSavedId(null), 1600); return () => clearTimeout(x); }
  }, [lastSavedId]);

  const handleSave = async () => {
    if (!form.short_description.trim() && !editingId) { toast('Short Description is required', 'error'); return; }
    setSaving(true);
    try {
      if (creating) {
        await callTool('sn__create_change_request', {
          short_description: form.short_description,
          category: form.category,
          risk: form.risk,
          priority: form.priority,
        });
        toast('✓ Change Request created');
      } else {
        await callTool('sn__update_change_request', {
          sys_id: editingId,
          short_description: form.short_description,
          category: form.category,
          risk: form.risk,
          priority: form.priority,
        });
        toast('✓ Change Request updated');
        setLastSavedId(editingId);
      }
      cancel();
    } catch (e: any) {
      toast(e.message || 'Failed to create change request', 'error');
    } finally {
      setSaving(false);
    }
  };

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden',
    textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle',
  };
  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase',
    letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#293E40' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>🔄</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Change Requests</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
            {items.length} record{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button onClick={openCreate}
            style={{
              background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)',
              color: '#fff', borderRadius: '4px', height: '32px', padding: '0 16px',
              cursor: 'pointer', fontSize: '12px', fontFamily: 'inherit', fontWeight: 500,
            }}>
            + New Change
          </button>
          <ExpandButton />
        </div>
      </div>

      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by number or description…" theme={theme} />

      {creating && (
        <div style={{ padding: '14px 16px', borderLeft: '3px solid #81B5A1', background: theme === 'dark' ? '#1A2E25' : '#F4F5F7', borderBottom: `1px solid ${t.border}` }}>
          <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '10px', color: '#293E40' }}>➕ New Change Request</div>
          <div className={styles.formGrid}>
            <Field label="Short Description" size="small" style={{ gridColumn: '1 / -1' }}>
              <Input size="small" value={form.short_description} onChange={(_, d) => setForm(f => ({ ...f, short_description: d.value }))} />
            </Field>
            <FormSelect label="Category" value={form.category} options={CHANGE_CATEGORIES} onChange={v => setForm(f => ({ ...f, category: v }))} theme={theme} />
            <FormSelect label="Risk" value={form.risk} options={RISK_OPTIONS} onChange={v => setForm(f => ({ ...f, risk: v }))} theme={theme} />
            <FormSelect label="Priority" value={form.priority} options={PRIORITIES} labels={PRIORITY_LABELS} onChange={v => setForm(f => ({ ...f, priority: v }))} theme={theme} />
          </div>
          <div className={styles.formActions}>
            <Button appearance="secondary" size="small" onClick={cancel} disabled={saving}
              style={{ borderRadius: '4px', height: '32px', padding: '0 16px', border: `1px solid ${t.border}` }}>Cancel</Button>
            <Button appearance="primary" size="small" onClick={handleSave} disabled={saving}
              style={{ background: '#293E40', borderColor: '#293E40', borderRadius: '4px', height: '32px', padding: '0 16px' }}>
              {saving ? 'Saving…' : '✓ Create'}
            </Button>
          </div>
        </div>
      )}

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={{ ...headerCellStyle, width: 28 }} />
            <TableHeaderCell style={headerCellStyle}>Number</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Short Description</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>State</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Priority</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Risk</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Category</TableHeaderCell>
            <TableHeaderCell style={{ ...headerCellStyle, width: 32 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredItems.length === 0 && (
            <TableRow><TableCell colSpan={8} className={styles.empty}><Text>{filter ? 'No matching change requests.' : 'No change requests found.'}</Text></TableCell></TableRow>
          )}
          {filteredItems.map((cr, idx) => (
            <React.Fragment key={cr.sys_id}>
              <TableRow className="snow-row"
                onClick={() => toggleExpand(cr.sys_id)}
                style={{
                  cursor: 'pointer',
                  borderBottom: idx === filteredItems.length - 1 && expandedId !== cr.sys_id ? 'none' : `1px solid ${t.border}`,
                  background: expandedId === cr.sys_id ? (theme === 'dark' ? '#1A2E25' : '#EEF6F1') : 'transparent',
                  ...(lastSavedId === cr.sys_id ? { animation: 'snowRowFlash 1.5s ease-out' } : {}),
                }}>
                <TableCell style={{ ...cellStyle, width: 28 }}>
                  <span style={{ fontFamily: 'monospace', fontSize: '10px', color: t.textWeak }}>{expandedId === cr.sys_id ? '▼' : '▶'}</span>
                </TableCell>
                <TableCell style={cellStyle}><span style={{ fontFamily: 'monospace', fontWeight: 500, color: '#293E40' }}>{cr.number}</span></TableCell>
                <TableCell style={{ ...cellStyle, maxWidth: '220px' }}>{cr.short_description || '—'}</TableCell>
                <TableCell style={cellStyle}><StatePill state={cr.state} theme={theme} /></TableCell>
                <TableCell style={cellStyle}><PriorityPill priority={cr.priority} theme={theme} /></TableCell>
                <TableCell style={cellStyle}><RiskPill risk={cr.risk} theme={theme} /></TableCell>
                <TableCell style={cellStyle}>{cr.category || '—'}</TableCell>
                <TableCell style={cellStyle}>
                  <button title="Edit" onClick={(e) => { e.stopPropagation(); openEdit(cr); }} className="snow-edit-btn"
                    style={{ width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer', color: t.textWeak, fontSize: '14px', padding: 0 }}>✏️</button>
                </TableCell>
              </TableRow>
              {editingId === cr.sys_id && (
                <TableRow>
                  <TableCell colSpan={8} style={{ padding: 0 }}>
                    <div style={{ padding: '14px 16px', borderLeft: '3px solid #81B5A1', background: theme === 'dark' ? '#1A2E25' : '#F4F5F7', borderBottom: `1px solid ${t.border}` }}>
                      <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '10px', color: '#293E40' }}>✏️ Edit Change Request {cr.number}</div>
                      <div className={styles.formGrid}>
                        <Field label="Short Description" size="small" style={{ gridColumn: '1 / -1' }}>
                          <Input size="small" value={form.short_description} onChange={(_, d) => setForm(f => ({ ...f, short_description: d.value }))} />
                        </Field>
                        <FormSelect label="Category" value={form.category} options={CHANGE_CATEGORIES} onChange={v => setForm(f => ({ ...f, category: v }))} theme={theme} />
                        <FormSelect label="Risk" value={form.risk} options={RISK_OPTIONS} onChange={v => setForm(f => ({ ...f, risk: v }))} theme={theme} />
                        <FormSelect label="Priority" value={form.priority} options={PRIORITIES} labels={PRIORITY_LABELS} onChange={v => setForm(f => ({ ...f, priority: v }))} theme={theme} />
                      </div>
                      <div className={styles.formActions}>
                        <Button appearance="secondary" size="small" onClick={cancel} disabled={saving} style={{ borderRadius: '4px', height: '32px', padding: '0 16px', border: `1px solid ${t.border}` }}>Cancel</Button>
                        <Button appearance="primary" size="small" onClick={handleSave} disabled={saving} style={{ background: '#293E40', borderColor: '#293E40', borderRadius: '4px', height: '32px', padding: '0 16px' }}>
                          {saving ? 'Saving…' : '✓ Save'}
                        </Button>
                      </div>
                    </div>
                  </TableCell>
                </TableRow>
              )}
              {expandedId === cr.sys_id && (
                <TableRow>
                  <TableCell colSpan={8} style={{ padding: 0 }}>
                    <div className={styles.subTableWrap} style={{ background: theme === 'dark' ? '#1A2E25' : '#EEF6F1', borderBottom: `1px solid ${t.border}` }}>
                      {loadingTasks === cr.sys_id ? (
                        <div style={{ padding: '8px', color: t.textWeak, fontSize: '12px', fontStyle: 'italic' }}>Fetching change tasks…</div>
                      ) : (
                        <ChangeTasksTable items={changeTasks[cr.sys_id] || []} theme={theme} />
                      )}
                      <button onClick={() => setExpandedId(null)} style={{ marginTop: '8px', padding: '4px 12px', borderRadius: '4px', border: `1px solid ${t.border}`, background: 'transparent', color: t.textWeak, fontSize: '11px', cursor: 'pointer', fontFamily: 'inherit' }}>▲ Collapse</button>
                    </div>
                  </TableCell>
                </TableRow>
              )}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>

      <NowFooter theme={theme} />
    </div>
  );
}

// ── Problems View ───────────────────────────────────────────────────────────
function ProblemsView({ items, theme }: { items: Problem[]; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = now(theme);
  const [filter, setFilter] = useState('');

  const filteredItems = items.filter(p =>
    !filter ||
    p.number?.toLowerCase().includes(filter.toLowerCase()) ||
    p.short_description?.toLowerCase().includes(filter.toLowerCase())
  );

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden',
    textOverflow: 'ellipsis', maxWidth: '200px', verticalAlign: 'middle',
  };
  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase',
    letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#293E40' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>⚠️</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Problems</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
            {items.length} record{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <ExpandButton />
      </div>

      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by number or description…" theme={theme} />

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Number</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Short Description</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Priority</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>State</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Assigned To</TableHeaderCell>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredItems.length === 0 && (
            <TableRow><TableCell colSpan={5} className={styles.empty}><Text>{filter ? 'No matching problems.' : 'No problems found.'}</Text></TableCell></TableRow>
          )}
          {filteredItems.map((p, idx) => (
            <TableRow key={p.sys_id} className="snow-row"
              style={{ borderBottom: idx === filteredItems.length - 1 ? 'none' : `1px solid ${t.border}` }}>
              <TableCell style={cellStyle}><span style={{ fontFamily: 'monospace', fontWeight: 500, color: '#293E40' }}>{p.number}</span></TableCell>
              <TableCell style={{ ...cellStyle, maxWidth: '240px' }}>{p.short_description || '—'}</TableCell>
              <TableCell style={cellStyle}><PriorityPill priority={p.priority} theme={theme} /></TableCell>
              <TableCell style={cellStyle}><StatePill state={p.state} theme={theme} /></TableCell>
              <TableCell style={cellStyle}>{p.assigned_to || '—'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <NowFooter theme={theme} />
    </div>
  );
}

// ── Knowledge View ──────────────────────────────────────────────────────────
function KnowledgeView({ items, theme }: { items: KnowledgeArticle[]; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = now(theme);
  const [filter, setFilter] = useState('');

  const filteredItems = items.filter(a =>
    !filter ||
    a.number?.toLowerCase().includes(filter.toLowerCase()) ||
    a.short_description?.toLowerCase().includes(filter.toLowerCase()) ||
    a.category?.toLowerCase().includes(filter.toLowerCase())
  );

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden',
    textOverflow: 'ellipsis', maxWidth: '200px', verticalAlign: 'middle',
  };
  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase',
    letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#293E40' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>📚</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Knowledge Articles</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
            {items.length} article{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <ExpandButton />
      </div>

      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by number, title, or category…" theme={theme} />

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Number</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Title</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Category</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Author</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>State</TableHeaderCell>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredItems.length === 0 && (
            <TableRow><TableCell colSpan={5} className={styles.empty}><Text>{filter ? 'No matching articles.' : 'No knowledge articles found.'}</Text></TableCell></TableRow>
          )}
          {filteredItems.map((a, idx) => (
            <TableRow key={a.sys_id} className="snow-row"
              style={{ borderBottom: idx === filteredItems.length - 1 ? 'none' : `1px solid ${t.border}` }}>
              <TableCell style={cellStyle}><span style={{ fontFamily: 'monospace', fontWeight: 500, color: '#293E40' }}>{a.number}</span></TableCell>
              <TableCell style={{ ...cellStyle, maxWidth: '260px' }}>{a.short_description || '—'}</TableCell>
              <TableCell style={cellStyle}>{a.category || '—'}</TableCell>
              <TableCell style={cellStyle}>{a.author || '—'}</TableCell>
              <TableCell style={cellStyle}><StatePill state={a.state} theme={theme} /></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <NowFooter theme={theme} />
    </div>
  );
}

// ── Catalog View ────────────────────────────────────────────────────────────
function CatalogView({ items, theme }: { items: CatalogItem[]; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = now(theme);
  const [filter, setFilter] = useState('');

  const filteredItems = items.filter(item =>
    !filter ||
    item.name?.toLowerCase().includes(filter.toLowerCase()) ||
    item.category?.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#293E40' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>🛒</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Service Catalog</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
            {items.length} item{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <ExpandButton />
      </div>

      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by name or category…" theme={theme} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '10px', padding: '12px' }}>
        {filteredItems.length === 0 && (
          <div className={styles.empty} style={{ gridColumn: '1 / -1', color: t.textWeak }}>
            {filter ? 'No matching catalog items.' : 'No catalog items found.'}
          </div>
        )}
        {filteredItems.map(item => (
          <div key={item.sys_id} style={{
            border: `1px solid ${t.border}`, borderRadius: '6px', padding: '12px',
            background: t.surface, boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
          }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: t.text, marginBottom: '4px' }}>{item.name}</div>
            <div style={{ fontSize: '11px', color: t.textWeak, marginBottom: '6px', lineHeight: 1.4 }}>{item.short_description || '—'}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', color: t.textWeak }}>{item.category || '—'}</span>
              <span style={{
                fontSize: '12px', fontWeight: 600,
                color: item.price ? '#2E844A' : t.textWeak,
              }}>{item.price || 'Free'}</span>
            </div>
          </div>
        ))}
      </div>

      <NowFooter theme={theme} />
    </div>
  );
}

// ── Approvals View ──────────────────────────────────────────────────────────
function ApprovalsView({ items, callTool, toast, theme }: {
  items: SnowApproval[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles();
  const t = now(theme);
  const [filter, setFilter] = useState('');
  const [actingId, setActingId] = useState<string | null>(null);

  const filteredItems = items.filter(a =>
    !filter ||
    a.approver?.toLowerCase().includes(filter.toLowerCase()) ||
    a.document?.toLowerCase().includes(filter.toLowerCase())
  );

  const act = async (sys_id: string, action: 'approve' | 'reject') => {
    setActingId(sys_id);
    try {
      await callTool(action === 'approve' ? 'sn__approve_record' : 'sn__reject_record', { sys_id });
      toast(action === 'approve' ? '✓ Approved' : '✓ Rejected', 'success');
    } catch (e: any) {
      toast(e.message || `Failed to ${action}`, 'error');
    } finally {
      setActingId(null);
    }
  };

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden',
    textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle',
  };
  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase',
    letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#293E40' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>✅</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Pending Approvals</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
            {items.length} record{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <ExpandButton />
      </div>

      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by approver or document…" theme={theme} />

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Approver</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Document</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>State</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Due Date</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Created On</TableHeaderCell>
            <TableHeaderCell style={{ ...headerCellStyle, width: 140 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredItems.length === 0 && (
            <TableRow><TableCell colSpan={6} className={styles.empty}><Text>{filter ? 'No matching approvals.' : 'No pending approvals.'}</Text></TableCell></TableRow>
          )}
          {filteredItems.map((a, idx) => (
            <TableRow key={a.sys_id} className="snow-row"
              style={{ borderBottom: idx === filteredItems.length - 1 ? 'none' : `1px solid ${t.border}` }}>
              <TableCell style={cellStyle}>{a.approver || '—'}</TableCell>
              <TableCell style={cellStyle}><span style={{ fontFamily: 'monospace', color: '#293E40' }}>{a.document || '—'}</span></TableCell>
              <TableCell style={cellStyle}><ApprovalPill approval={a.state} theme={theme} /></TableCell>
              <TableCell style={cellStyle}>{a.due_date || '—'}</TableCell>
              <TableCell style={cellStyle}>{a.created_on || '—'}</TableCell>
              <TableCell style={{ ...cellStyle, maxWidth: 'none' }}>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    onClick={() => act(a.sys_id, 'approve')}
                    disabled={actingId === a.sys_id}
                    style={{ padding: '3px 10px', borderRadius: '3px', border: 'none', background: '#2E844A', color: '#fff', fontSize: '11px', fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', opacity: actingId === a.sys_id ? 0.6 : 1 }}>
                    ✓ Approve
                  </button>
                  <button
                    onClick={() => act(a.sys_id, 'reject')}
                    disabled={actingId === a.sys_id}
                    style={{ padding: '3px 10px', borderRadius: '3px', border: 'none', background: '#D63B20', color: '#fff', fontSize: '11px', fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', opacity: actingId === a.sys_id ? 0.6 : 1 }}>
                    ✗ Reject
                  </button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <NowFooter theme={theme} />
    </div>
  );
}

// ── Global CSS for Now Design System ────────────────────────────────────────
const nowStyleId = 'now-global-style';
if (typeof document !== 'undefined' && !document.getElementById(nowStyleId)) {
  const style = document.createElement('style');
  style.id = nowStyleId;
  style.textContent = `
    @keyframes snowRowFlash {
      0%   { background: #E3F2E8; }
      100% { background: transparent; }
    }
    @keyframes shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
    [data-theme="dark"] .snow-row:hover,
    .fui-FluentProvider[data-theme="dark"] .snow-row:hover {
      background: #1A2E25 !important;
    }
    .snow-row:hover {
      background: #EEF6F1 !important;
    }
    .snow-edit-btn:hover {
      color: #293E40 !important;
      border-color: #293E40 !important;
    }
    .fui-Input:focus-within {
      box-shadow: 0 0 3px #81B5A1;
      border-color: #81B5A1;
    }
    select:focus {
      outline: none;
      box-shadow: 0 0 3px #81B5A1;
      border-color: #81B5A1 !important;
    }
    .skel {
      height: 14px;
      border-radius: 4px;
      background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
    }
    [data-theme="dark"] .skel {
      background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%);
      background-size: 200% 100%;
    }
  `;
  document.head.appendChild(style);
}

// ── Form View (standalone create form) ──────────────────────────────────────
const FORM_URGENCIES = ['1', '2', '3'];
const FORM_URGENCY_LABELS: Record<string, string> = { '1': '1 – High', '2': '2 – Medium', '3': '3 – Low' };
const FORM_IMPACTS = ['1', '2', '3'];
const FORM_IMPACT_LABELS: Record<string, string> = { '1': '1 – High', '2': '2 – Medium', '3': '3 – Low' };
const FORM_CATEGORIES_LIST = ['inquiry', 'software', 'hardware', 'network', 'database'];
const FORM_CATEGORY_LABELS: Record<string, string> = {
  inquiry: 'Inquiry', software: 'Software', hardware: 'Hardware', network: 'Network', database: 'Database',
};

function FormView({ entity, prefill, fkSelections, mode = 'create', recordId, callTool, toast, theme }: {
  entity: 'incident' | 'request' | 'change_request';
  prefill?: Record<string, string>;
  fkSelections?: Record<string, { label: string; options: { id: string; name: string }[] }>;
  mode?: 'create' | 'edit';
  recordId?: string;
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles();
  const t = now(theme);
  const [shortDesc, setShortDesc] = useState(prefill?.short_description || '');
  const [description, setDescription] = useState(prefill?.description || '');
  const [urgency, setUrgency] = useState(prefill?.urgency || '2');
  const [impact, setImpact] = useState(prefill?.impact || '2');
  const [category, setCategory] = useState(prefill?.category || '');
  const [changeCategory, setChangeCategory] = useState(prefill?.category || 'Normal');
  const [risk, setRisk] = useState(prefill?.risk || 'medium');
  const [fkChoices, setFkChoices] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const setFk = (k: string, v: string) => setFkChoices(p => ({ ...p, [k]: v }));

  const isIncident = entity === 'incident';
  const isChange = entity === 'change_request';
  const isEdit = mode === 'edit';
  const entityLabel = isIncident ? 'Incident' : isChange ? 'Change Request' : 'Request';
  const title = `${isEdit ? '✏️ Edit' : '✨ New'} ${entityLabel}`;

  const handleSubmit = async () => {
    if (!shortDesc.trim()) { toast('Short Description is required', 'error'); return; }
    setSubmitting(true);
    try {
      const fkArgs: Record<string, string> = {};
      Object.entries(fkChoices).forEach(([k, v]) => { if (v) fkArgs[k] = v; });
      if (isEdit) {
        const toolName = isIncident ? 'sn__update_incident' : isChange ? 'sn__update_change_request' : 'sn__update_request';
        await callTool(toolName, { sys_id: recordId, short_description: shortDesc.trim(), description: description.trim(), priority: urgency, ...(isIncident ? { category } : {}), ...(isChange ? { category: changeCategory, risk } : {}), ...fkArgs });
      } else if (isIncident) {
        await callTool('sn__create_incident', { short_description: shortDesc.trim(), description: description.trim(), priority: urgency, category, ...fkArgs });
      } else if (isChange) {
        await callTool('sn__create_change_request', { short_description: shortDesc.trim(), description: description.trim(), category: changeCategory, risk, priority: urgency, ...fkArgs });
      } else {
        await callTool('sn__create_request', { short_description: shortDesc.trim(), description: description.trim(), priority: urgency, ...fkArgs });
      }
      toast(`✓ ${entityLabel} ${isEdit ? 'updated' : 'created'} successfully`, 'success');
      setSubmitted(true);
    } catch (e: any) {
      toast(e.message || `Failed to ${isEdit ? 'update' : 'create'} ${entity}`, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setShortDesc(''); setDescription(''); setUrgency('2'); setImpact('2'); setCategory('');
    setChangeCategory('Normal'); setRisk('medium'); setFkChoices({});
    setSubmitted(false);
  };

  const formGrid3: React.CSSProperties = {
    display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px 20px', marginBottom: '20px',
  };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{
        background: 'linear-gradient(135deg, #293E40 0%, #3A5A5C 100%)',
        borderBottom: '2px solid #81B5A1',
      }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>{title}</span>
        </div>
      </div>

      {submitted ? (
        <div style={{ padding: '24px 16px', textAlign: 'center' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>✅</div>
          <Text weight="semibold" style={{ color: t.success, fontSize: '14px' }}>
            {entityLabel} {isEdit ? 'updated' : 'created'} successfully!
          </Text>
          <div style={{ marginTop: '12px' }}>
            {!isEdit && <Button appearance="primary" size="small" onClick={handleReset} style={{ background: '#81B5A1', borderColor: '#81B5A1' }}>Create Another</Button>}
          </div>
        </div>
      ) : (
        <div style={{ padding: '16px' }}>
          {fkSelections && Object.keys(fkSelections).length > 0 && (
            <div style={{ marginBottom: '16px', padding: '10px 12px', background: theme === 'dark' ? '#1A2E25' : '#EEF6F1', border: `1px solid ${t.border}`, borderRadius: '6px' }}>
              {Object.entries(fkSelections).map(([fkKey, fkDef]) => (
                <div key={fkKey} style={{ marginBottom: '8px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: t.textWeak, marginBottom: '4px' }}>{fkDef.label}</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {fkDef.options.map(opt => (
                      <label key={opt.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: t.text }}>
                        <input type="radio" name={fkKey} value={opt.name} checked={fkChoices[fkKey] === opt.name} onChange={() => setFk(fkKey, opt.name)} style={{ accentColor: '#81B5A1' }} />
                        {opt.name}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          <div style={{ marginBottom: '12px' }}>
            <label style={{ color: t.text, fontSize: '12px', fontWeight: 600 }}>Short Description *</label>
            <Input size="small" value={shortDesc} onChange={(_, d) => setShortDesc(d.value)}
              placeholder={`Brief summary of the ${entity.replace('_', ' ')}`}
              style={{ width: '100%', marginTop: '4px' }} />
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ color: t.text, fontSize: '12px', fontWeight: 600 }}>Description</label>
            <Textarea size="small" value={description} onChange={(_, d) => setDescription(d.value)}
              placeholder="Detailed description (optional)" rows={3} resize="vertical"
              style={{ width: '100%', marginTop: '4px' }} />
          </div>
          <div style={formGrid3}>
            <FormSelect label="Priority" value={urgency} options={FORM_URGENCIES} labels={FORM_URGENCY_LABELS} onChange={setUrgency} theme={theme} />
            {isIncident && <FormSelect label="Impact" value={impact} options={FORM_IMPACTS} labels={FORM_IMPACT_LABELS} onChange={setImpact} theme={theme} />}
            {isIncident && <FormSelect label="Category" value={category} options={FORM_CATEGORIES_LIST} labels={FORM_CATEGORY_LABELS} onChange={setCategory} theme={theme} />}
            {isChange && <FormSelect label="Category" value={changeCategory} options={CHANGE_CATEGORIES} onChange={setChangeCategory} theme={theme} />}
            {isChange && <FormSelect label="Risk" value={risk} options={RISK_OPTIONS} onChange={setRisk} theme={theme} />}
          </div>
          <div className={styles.formActions}>
            <Button size="small" appearance="primary" onClick={handleSubmit}
              disabled={submitting || !shortDesc.trim()}
              style={{ background: '#81B5A1', borderColor: '#81B5A1', minWidth: '90px' }}>
              {submitting ? <Spinner size="tiny" /> : isEdit ? 'Save' : 'Submit'}
            </Button>
            <Button size="small" appearance="subtle" onClick={handleReset} disabled={submitting} style={{ color: t.textWeak }}>Reset</Button>
          </div>
        </div>
      )}

      <NowFooter theme={theme} />
    </div>
  );
}

// ── Skeleton Loading Shimmer ────────────────────────────────────────────────
function SkeletonTable() {
  return (
    <div style={{ padding: '16px' }}>
      <div style={{ textAlign: 'center', padding: '8px 0 16px', fontSize: '13px', color: '#888' }}>
        ⏳ Loading data…
      </div>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <div className="skel" style={{ width: '220px', height: '24px' }} />
        <div className="skel" style={{ width: '80px', height: '24px' }} />
      </div>
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
          <div className="skel" style={{ width: `${80 + (i * 10)}px` }} />
          <div className="skel" style={{ width: `${160 - (i * 8)}px` }} />
          <div className="skel" style={{ width: `${70 + (i * 5)}px` }} />
          <div className="skel" style={{ width: `${100 + (i * 12)}px` }} />
          <div className="skel" style={{ width: `${90 - (i * 6)}px` }} />
        </div>
      ))}
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────────
export function ServiceNowApp() {
  const styles = useStyles();
  const data = useToolData<SnowData>();
  const { callTool } = useMcpBridge();
  const toast = useToast();
  const theme = useTheme();
  const t = now(theme);

  const shellStyle: React.CSSProperties = { padding: '12px', fontSize: '12px' };

  if (!data) {
    return (
      <div className={styles.shell} style={shellStyle}>
        <SkeletonTable />
      </div>
    );
  }

  if (data.error) {
    return (
      <div className={styles.shell} style={shellStyle}>
        <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
          <div className={styles.headerBar} style={{ background: '#293E40' }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>⚠️ Error</span>
          </div>
          <div style={{
            padding: '12px 16px', fontSize: '13px', fontWeight: 500,
            background: theme === 'dark' ? '#3D1111' : '#FDE7E7',
            color: theme === 'dark' ? '#F87171' : t.error,
            borderLeft: `3px solid ${t.error}`,
          }}>
            {data.message || 'An unknown error occurred.'}
          </div>
          <NowFooter theme={theme} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.shell} style={shellStyle}>
      {data.type === 'incidents' && (
        <IncidentsView items={(data.incidents || []) as Incident[]} callTool={callTool} toast={toast} theme={theme} />
      )}
      {data.type === 'requests' && (
        <RequestsView items={(data.requests || []) as ServiceRequest[]} callTool={callTool} toast={toast} theme={theme} />
      )}
      {data.type === 'change_requests' && (
        <ChangesView items={(data.items || []) as ChangeRequest[]} callTool={callTool} toast={toast} theme={theme} />
      )}
      {data.type === 'problems' && (
        <ProblemsView items={(data.items || []) as Problem[]} theme={theme} />
      )}
      {data.type === 'knowledge_articles' && (
        <KnowledgeView items={(data.items || []) as KnowledgeArticle[]} theme={theme} />
      )}
      {data.type === 'service_catalog' && (
        <CatalogView items={(data.items || []) as CatalogItem[]} theme={theme} />
      )}
      {data.type === 'approvals' && (
        <ApprovalsView items={(data.items || []) as SnowApproval[]} callTool={callTool} toast={toast} theme={theme} />
      )}
      {data.type === 'form' && (
        <FormView
          entity={(data.entity || 'incident') as 'incident' | 'request' | 'change_request'}
          prefill={data.prefill}
          fkSelections={data.fkSelections}
          callTool={callTool}
          toast={toast}
          theme={theme}
        />
      )}
    </div>
  );
}
