import React, { useState } from 'react';
import {
  Badge,
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
  makeStyles,
} from '@fluentui/react-components';
import { useToolData, useMcpBridge, useTheme } from '../shared/McpBridge';
import { useToast } from '../shared/Toast';
import type { SnowData, Incident, ServiceRequest, RequestItem } from './types';

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

// ── Priority pill styles ────────────────────────────────────────────────────
type PillStyle = { background: string; color: string };
type PillStyleMap = { light: PillStyle; dark: PillStyle };

const PRIORITY_STYLES: Record<string, PillStyleMap> = {
  '1': { light: { background: '#FDE7E7', color: '#A80000' }, dark: { background: '#3D1111', color: '#F87171' } },
  '2': { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
  '3': { light: { background: '#FFF8E0', color: '#7A6800' }, dark: { background: '#3D3511', color: '#FFD700' } },
  '4': { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
};

// ── State pill styles ───────────────────────────────────────────────────────
const STATE_STYLES: Record<string, PillStyleMap> = {
  'new':         { light: { background: '#EEF4FF', color: '#0066CC' }, dark: { background: '#0B3573', color: '#8DC7FF' } },
  'in progress': { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
  'on hold':     { light: { background: '#EAEAEA', color: '#555555' }, dark: { background: '#333333', color: '#AAAAAA' } },
  'resolved':    { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
  'closed':      { light: { background: '#2E3D49', color: '#FFFFFF' }, dark: { background: '#1A2030', color: '#8B949E' } },
};

// ── Approval pill styles ────────────────────────────────────────────────────
const APPROVAL_STYLES: Record<string, PillStyleMap> = {
  'approved':      { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
  'requested':     { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
  'not requested': { light: { background: '#EAEAEA', color: '#555555' }, dark: { background: '#333333', color: '#AAAAAA' } },
  'rejected':      { light: { background: '#FDE7E7', color: '#A80000' }, dark: { background: '#3D1111', color: '#F87171' } },
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
  const style = STATE_STYLES[key]?.[theme] || STATE_STYLES['new'][theme];
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
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
    gap: '10px 12px',
    marginBottom: '12px',
  },
  formActions: {
    display: 'flex',
    gap: '8px',
    justifyContent: 'flex-end',
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

// ── Now Footer ──────────────────────────────────────────────────────────────
function NowFooter({ theme }: { theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = now(theme);
  return (
    <div className={styles.mcpFooter} style={{
      background: theme === 'dark' ? '#1C2229' : '#F4F5F7',
      borderTop: `1px solid ${t.border}`, color: t.textWeak,
    }}>
      <span>⚡ <strong>MCP Widget</strong> · ServiceNow ITSM</span>
      <span>⚓ GTC</span>
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

  const handleQtyChange = (sysId: string, val: string) => {
    setEditingQty(prev => ({ ...prev, [sysId]: val }));
  };

  const saveQty = async (item: RequestItem) => {
    const qty = editingQty[item.sys_id] ?? String(item.quantity);
    setSavingId(item.sys_id);
    try {
      await callTool('update_request_item', { sys_id: item.sys_id, quantity: qty });
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
                  onChange={(e) => handleQtyChange(item.sys_id, e.target.value)}
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
}){
  const styles = useStyles();
  const t = now(theme);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [form, setForm] = useState({
    short_description: '', description: '', priority: '3', state: 'New', category: 'inquiry',
  });

  const openEdit = (inc: Incident) => {
    setCreating(false);
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
    setCreating(true);
    setForm({ short_description: '', description: '', priority: '3', state: 'New', category: 'inquiry' });
  };

  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) {
        await callTool('create_incident', {
          short_description: form.short_description,
          description: form.description,
          priority: form.priority,
          category: form.category,
        });
        toast('✓ Incident created');
      } else {
        await callTool('update_incident', {
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

  React.useEffect(() => {
    if (lastSavedId) {
      const timer = setTimeout(() => setLastSavedId(null), 1600);
      return () => clearTimeout(timer);
    }
  }, [lastSavedId]);

  const formBg = theme === 'dark' ? '#1A2E25' : '#F4F5F7';
  const colSpan = 5;

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle',
  };

  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
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
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>ServiceNow ITSM — Service Manifest</span>
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
        </div>
      </div>

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Number</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Priority</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>State</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Assigned To</TableHeaderCell>
            <TableHeaderCell style={{ ...headerCellStyle, width: 50 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && renderForm('➕ New Incident')}
          {items.length === 0 && !creating && (
            <TableRow>
              <TableCell colSpan={colSpan} className={styles.empty}>
                <Text>No incidents found.</Text>
              </TableCell>
            </TableRow>
          )}
          {items.map((inc, idx) => (
            <React.Fragment key={inc.sys_id}>
              <TableRow
                className="snow-row"
                style={{
                  borderBottom: idx === items.length - 1 ? 'none' : `1px solid ${t.border}`,
                  ...(lastSavedId === inc.sys_id ? { animation: 'snowRowFlash 1.5s ease-out' } : {}),
                }}
              >
                <TableCell style={cellStyle}>
                  <span style={{ fontFamily: 'monospace', fontWeight: 500, color: '#293E40' }}>{inc.number}</span>
                </TableCell>
                <TableCell style={cellStyle}><PriorityPill priority={inc.priority} theme={theme} /></TableCell>
                <TableCell style={cellStyle}><StatePill state={inc.state} theme={theme} /></TableCell>
                <TableCell style={cellStyle}>{inc.assigned_to || '—'}</TableCell>
                <TableCell style={cellStyle}>
                  <button title="Edit" onClick={() => openEdit(inc)} className="snow-edit-btn"
                    style={{
                      width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer',
                      color: t.textWeak, fontSize: '14px', padding: 0,
                    }}>✏️</button>
                </TableCell>
              </TableRow>
              {editingId === inc.sys_id && renderForm('✏️ Edit Incident ' + inc.number)}
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
}){
  const styles = useStyles();
  const t = now(theme);
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

  const toggleExpand = async (req: ServiceRequest) => {
    if (expandedId === req.sys_id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(req.sys_id);
    if (!reqItems[req.sys_id]) {
      setLoadingItems(req.sys_id);
      try {
        const result = await callTool('get_request_items', { request_sys_id: req.sys_id });
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
        await callTool('create_request', {
          short_description: form.short_description,
          description: form.description,
          priority: form.priority,
        });
        toast('✓ Request created');
      } else {
        await callTool('update_request', {
          sys_id: editingId,
          approval: form.approval,
        });
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

  React.useEffect(() => {
    if (lastSavedId) {
      const timer = setTimeout(() => setLastSavedId(null), 1600);
      return () => clearTimeout(timer);
    }
  }, [lastSavedId]);

  const formBg = theme === 'dark' ? '#1A2E25' : '#F4F5F7';
  const colSpan = 5;

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle',
  };

  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
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
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>ServiceNow ITSM — Service Manifest</span>
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
        </div>
      </div>

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Number</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>State</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Priority</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Approval</TableHeaderCell>
            <TableHeaderCell style={{ ...headerCellStyle, width: 50 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && renderForm('➕ New Request')}
          {items.length === 0 && !creating && (
            <TableRow>
              <TableCell colSpan={colSpan} className={styles.empty}>
                <Text>No requests found.</Text>
              </TableCell>
            </TableRow>
          )}
          {items.map((req, idx) => (
            <React.Fragment key={req.sys_id}>
              <TableRow
                className="snow-row"
                onClick={() => toggleExpand(req)}
                style={{
                  cursor: 'pointer',
                  borderBottom: idx === items.length - 1 && expandedId !== req.sys_id ? 'none' : `1px solid ${t.border}`,
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
                        <RequestItemsTable
                          items={reqItems[req.sys_id] || []}
                          callTool={callTool}
                          toast={toast}
                          theme={theme}
                        />
                      )}
                      <button
                        onClick={() => setExpandedId(null)}
                        style={{
                          marginTop: '8px', padding: '4px 12px', borderRadius: '4px',
                          border: `1px solid ${t.border}`, background: 'transparent',
                          color: t.textWeak, fontSize: '11px', cursor: 'pointer', fontFamily: 'inherit',
                        }}>
                        ▲ Collapse
                      </button>
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

// ── Skeleton Loading Shimmer ────────────────────────────────────────────────
function SkeletonTable() {
  return (
    <div style={{ padding: '16px' }}>
      {/* Header skeleton */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <div className="skel" style={{ width: '220px', height: '24px' }} />
        <div className="skel" style={{ width: '80px', height: '24px' }} />
      </div>
      {/* Row skeletons with varying widths */}
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
        <IncidentsView
          items={(data.incidents || []) as Incident[]}
          callTool={callTool}
          toast={toast}
          theme={theme}
        />
      )}
      {data.type === 'requests' && (
        <RequestsView
          items={(data.requests || []) as ServiceRequest[]}
          callTool={callTool}
          toast={toast}
          theme={theme}
        />
      )}
    </div>
  );
}

