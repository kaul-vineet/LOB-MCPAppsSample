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
import type { HRData, HRCase, HRService, HRApproval } from './types';

// ── NOW Design System tokens (HR: teal-green brand, same shell) ─────────────
const NOW_LIGHT = {
  shell: '#293E40', brand: '#1B7A6E', brandHover: '#155F55',
  bg: '#F1F1F1', surface: '#FFFFFF', text: '#2E3D49', textWeak: '#6B7C93',
  border: '#D6D6D6', headerBg: '#F4F5F7',
  success: '#2E8540', error: '#D63B20',
};
const NOW_DARK = {
  shell: '#161B22', brand: '#1B7A6E', brandHover: '#155F55',
  bg: '#161B22', surface: '#21262D', text: '#E6EDF3', textWeak: '#8B949E',
  border: '#30363D', headerBg: '#232A32',
  success: '#81B5A1', error: '#D63B20',
};
function now(theme: 'light' | 'dark') { return theme === 'dark' ? NOW_DARK : NOW_LIGHT; }

const PRIORITIES = ['1', '2', '3', '4'];
const PRIORITY_LABELS: Record<string, string> = {
  '1': '1 – Critical', '2': '2 – High', '3': '3 – Moderate', '4': '4 – Low',
};
const PRIORITY_STYLES: Record<string, Record<'light' | 'dark', { background: string; color: string }>> = {
  '1': { light: { background: '#FDE7E7', color: '#A80000' }, dark: { background: '#3D1111', color: '#F87171' } },
  '2': { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
  '3': { light: { background: '#FFF8E0', color: '#7A6800' }, dark: { background: '#3D3511', color: '#FFD700' } },
  '4': { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
};
const STATE_STYLES: Record<string, Record<'light' | 'dark', { background: string; color: string }>> = {
  'open':       { light: { background: '#EEF4FF', color: '#0066CC' }, dark: { background: '#0B3573', color: '#8DC7FF' } },
  'in progress':{ light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
  'resolved':   { light: { background: '#E3F2E8', color: '#2E844A' }, dark: { background: '#1A3320', color: '#6EE7B7' } },
  'closed':     { light: { background: '#2E3D49', color: '#FFFFFF' }, dark: { background: '#1A2030', color: '#8B949E' } },
  'requested':  { light: { background: '#FFF1E0', color: '#8A4B00' }, dark: { background: '#3D2E11', color: '#FBBF24' } },
};

function PriorityPill({ priority, theme }: { priority: string; theme: 'light' | 'dark' }) {
  const key = String(priority).charAt(0);
  const s = PRIORITY_STYLES[key]?.[theme] || PRIORITY_STYLES['3'][theme];
  return <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: '15px', fontSize: '11px', fontWeight: 600, background: s.background, color: s.color }}>{PRIORITY_LABELS[key] || priority || '—'}</span>;
}

function StatePill({ state, theme }: { state: string; theme: 'light' | 'dark' }) {
  const key = (state || '').toLowerCase();
  const s = STATE_STYLES[key]?.[theme] || { background: '#EAEAEA', color: '#555' };
  return <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: '15px', fontSize: '11px', fontWeight: 500, background: s.background, color: s.color }}>{state || '—'}</span>;
}

// ── Styles ───────────────────────────────────────────────────────────────────
const useStyles = makeStyles({
  shell: { margin: '0 auto', padding: '12px', fontFamily: "system-ui, -apple-system, 'Segoe UI', sans-serif", fontSize: '13px' },
  card: { borderRadius: '8px', overflow: 'hidden', boxShadow: '0 2px 4px rgba(0,0,0,0.07)', overflowX: 'auto' as const },
  headerBar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', color: '#fff' },
  headerLeft: { display: 'flex', alignItems: 'center', gap: '10px' },
  formPanel: { padding: '14px 16px', borderLeft: '3px solid #1B7A6E' },
  formTitle: { fontSize: '14px', fontWeight: 600 as any, marginBottom: '10px' },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px 12px', marginBottom: '12px' },
  formActions: { display: 'flex', gap: '8px', justifyContent: 'flex-end' },
  filterBar: { display: 'flex', gap: '6px', alignItems: 'center', padding: '8px 12px', borderBottom: '1px solid transparent' },
  empty: { padding: '16px', textAlign: 'center' as const, fontSize: '13px' },
  mcpFooter: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 16px', fontSize: '11px' },
  subTableWrap: { padding: '12px 16px' },
});

function FormSelect({ label, value, options, labels, onChange, theme }: {
  label: string; value: string; options: string[]; labels?: Record<string, string>; onChange: (v: string) => void; theme: 'light' | 'dark';
}) {
  const t = now(theme);
  return (
    <Field label={label} size="small">
      <select value={value} onChange={e => onChange(e.target.value)} style={{ width: '100%', padding: '5px 8px', borderRadius: '4px', border: `1px solid ${t.border}`, background: t.surface, color: t.text, fontSize: '13px', fontFamily: 'inherit', height: '32px' }}>
        <option value="">— Select —</option>
        {options.map(o => <option key={o} value={o}>{labels?.[o] || o}</option>)}
      </select>
    </Field>
  );
}

function FilterBar({ value, onChange, onSearch, placeholder, theme }: { value: string; onChange: (v: string) => void; onSearch?: () => void; placeholder?: string; theme: 'light' | 'dark' }) {
  const t = now(theme); const styles = useStyles();
  return (
    <div className={styles.filterBar} style={{ borderBottomColor: t.border, background: t.headerBg }}>
      <Input size="small" value={value} onChange={(_, d) => onChange(d.value)} onKeyDown={e => e.key === 'Enter' && onSearch?.()} placeholder={placeholder || 'Filter…'} style={{ flex: 1, maxWidth: '260px' }} />
      {onSearch && <button onClick={onSearch} style={{ padding: '4px 12px', borderRadius: '4px', border: `1px solid ${t.border}`, background: '#293E40', color: '#fff', fontSize: '12px', cursor: 'pointer', fontFamily: 'inherit' }}>Search</button>}
    </div>
  );
}

function NowHRFooter({ theme }: { theme: 'light' | 'dark' }) {
  const styles = useStyles(); const t = now(theme); const { openExternal } = useMcpBridge();
  return (
    <div className={styles.mcpFooter} style={{ background: theme === 'dark' ? '#1C2229' : '#F4F5F7', borderTop: `1px solid ${t.border}`, color: t.textWeak }}>
      <span>⚡ <strong>MCP Widget</strong> · ServiceNow HR Service Delivery</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => openExternal('https://developer.servicenow.com')}>Open in ServiceNow ↗</span>
        <span>⚓ GTC</span>
      </div>
    </div>
  );
}

// ── Global CSS ───────────────────────────────────────────────────────────────
const hrStyleId = 'now-hr-global-style';
if (typeof document !== 'undefined' && !document.getElementById(hrStyleId)) {
  const style = document.createElement('style');
  style.id = hrStyleId;
  style.textContent = `
    @keyframes hrRowFlash { 0% { background: #E3F2E8; } 100% { background: transparent; } }
    @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
    .hr-row:hover { background: #EDF5F3 !important; }
    .hr-edit-btn:hover { color: #1B7A6E !important; border-color: #1B7A6E !important; }
    .skel { height: 14px; border-radius: 4px; background: linear-gradient(90deg, #e0e0e0 25%, #f0f0f0 50%, #e0e0e0 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite; }
  `;
  document.head.appendChild(style);
}

// ── HR Cases View ─────────────────────────────────────────────────────────────
function HRCasesView({ items, callTool, toast, theme }: {
  items: HRCase[];
  callTool: (n: string, a?: Record<string, any>) => Promise<any>;
  toast: (m: string, t?: any) => void;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles(); const t = now(theme);
  const [filter, setFilter] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState<Record<string, string>>({});
  const [addingNote, setAddingNote] = useState<string | null>(null);
  const [form, setForm] = useState({ subject: '', description: '', priority: '3', state: 'Open' });

  const filteredItems = items.filter(c => !filter || c.number?.toLowerCase().includes(filter.toLowerCase()) || c.subject?.toLowerCase().includes(filter.toLowerCase()) || c.opened_for?.toLowerCase().includes(filter.toLowerCase()));

  const openEdit = (c: HRCase) => { setCreating(false); setExpandedId(null); setEditingId(c.sys_id); setForm({ subject: c.subject || '', description: c.description || '', priority: String(c.priority).charAt(0) || '3', state: c.state || 'Open' }); };
  const openCreate = () => { setEditingId(null); setExpandedId(null); setCreating(true); setForm({ subject: '', description: '', priority: '3', state: 'Open' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };
  const toggleWorkNotes = (id: string) => { if (editingId) return; setExpandedId(prev => prev === id ? null : id); };

  useEffect(() => { if (lastSavedId) { const x = setTimeout(() => setLastSavedId(null), 1600); return () => clearTimeout(x); } }, [lastSavedId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) {
        await callTool('sn__create_hr_case', { subject: form.subject, description: form.description, priority: form.priority });
        toast('✓ HR Case created');
      } else {
        await callTool('sn__update_hr_case', { sys_id: editingId, subject: form.subject, priority: form.priority, state: form.state });
        toast('✓ HR Case updated');
        setLastSavedId(editingId);
      }
      cancel();
    } catch (e: any) { toast(e.message || 'Operation failed', 'error'); }
    finally { setSaving(false); }
  };

  const submitNote = async (sys_id: string) => {
    const text = (noteText[sys_id] || '').trim();
    if (!text) { toast('Enter a work note first', 'error'); return; }
    setAddingNote(sys_id);
    try {
      await callTool('sn__add_hr_work_note', { sys_id, work_note: text });
      toast('✓ Work note added');
      setNoteText(p => ({ ...p, [sys_id]: '' }));
      setExpandedId(null);
    } catch (e: any) { toast(e.message || 'Failed to add work note', 'error'); }
    finally { setAddingNote(null); }
  };

  const formBg = theme === 'dark' ? '#1A2E25' : '#F4F5F7';
  const colSpan = 6;
  const cellStyle: React.CSSProperties = { padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle' };
  const hcs: React.CSSProperties = { fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak };

  const renderForm = (title: string) => (
    <TableRow>
      <TableCell colSpan={colSpan} style={{ padding: 0 }}>
        <div className={styles.formPanel} style={{ background: formBg, borderColor: t.brand }}>
          <div className={styles.formTitle} style={{ color: '#293E40' }}>{title}</div>
          <div className={styles.formGrid}>
            {creating && (
              <Field label="Subject *" size="small" style={{ gridColumn: '1 / -1' }}>
                <Input size="small" value={form.subject} onChange={(_, d) => setForm(f => ({ ...f, subject: d.value }))} />
              </Field>
            )}
            <Field label="Description" size="small" style={{ gridColumn: '1 / -1' }}>
              <Input size="small" value={form.description} onChange={(_, d) => setForm(f => ({ ...f, description: d.value }))} />
            </Field>
            <FormSelect label="Priority" value={form.priority} options={PRIORITIES} labels={PRIORITY_LABELS} onChange={v => setForm(f => ({ ...f, priority: v }))} theme={theme} />
            {!creating && <FormSelect label="State" value={form.state} options={['Open', 'In Progress', 'Resolved', 'Closed']} onChange={v => setForm(f => ({ ...f, state: v }))} theme={theme} />}
          </div>
          <div className={styles.formActions}>
            <Button appearance="secondary" size="small" onClick={cancel} disabled={saving} style={{ borderRadius: '4px', height: '32px', padding: '0 16px', border: `1px solid ${t.border}` }}>Cancel</Button>
            <Button appearance="primary" size="small" onClick={handleSave} disabled={saving} style={{ background: '#1B7A6E', borderColor: '#1B7A6E', borderRadius: '4px', height: '32px', padding: '0 16px' }}>
              {saving ? 'Saving…' : creating ? '✓ Create' : '✓ Save'}
            </Button>
          </div>
        </div>
      </TableCell>
    </TableRow>
  );

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#1B7A6E' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>🧑‍💼</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>HR Cases</span>
          <Badge appearance="filled" size="small" style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>{items.length} record{items.length !== 1 ? 's' : ''}</Badge>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button onClick={openCreate} style={{ background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)', color: '#fff', borderRadius: '4px', height: '32px', padding: '0 16px', cursor: 'pointer', fontSize: '12px', fontFamily: 'inherit', fontWeight: 500 }}>+ New HR Case</button>
          <ExpandButton />
        </div>
      </div>
      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by number, subject, employee…" theme={theme} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={hcs}>Number</TableHeaderCell>
            <TableHeaderCell style={hcs}>Subject</TableHeaderCell>
            <TableHeaderCell style={hcs}>Opened For</TableHeaderCell>
            <TableHeaderCell style={hcs}>Priority</TableHeaderCell>
            <TableHeaderCell style={hcs}>State</TableHeaderCell>
            <TableHeaderCell style={{ ...hcs, width: 50 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && renderForm('➕ New HR Case')}
          {filteredItems.length === 0 && !creating && <TableRow><TableCell colSpan={colSpan} className={styles.empty}><Text>{filter ? 'No matching HR cases.' : 'No HR cases found.'}</Text></TableCell></TableRow>}
          {filteredItems.map((c, idx) => (
            <React.Fragment key={c.sys_id}>
              <TableRow className="hr-row" onClick={() => toggleWorkNotes(c.sys_id)}
                style={{ cursor: 'pointer', borderBottom: idx === filteredItems.length - 1 && expandedId !== c.sys_id ? 'none' : `1px solid ${t.border}`, background: expandedId === c.sys_id ? (theme === 'dark' ? '#1A2E25' : '#EDF5F3') : 'transparent', ...(lastSavedId === c.sys_id ? { animation: 'hrRowFlash 1.5s ease-out' } : {}) }}>
                <TableCell style={cellStyle}><span style={{ fontFamily: 'monospace', fontWeight: 500, color: '#1B7A6E' }}>{expandedId === c.sys_id ? '▼' : '▶'} {c.number}</span></TableCell>
                <TableCell style={{ ...cellStyle, maxWidth: '220px' }}>{c.subject || '—'}</TableCell>
                <TableCell style={cellStyle}>{c.opened_for || '—'}</TableCell>
                <TableCell style={cellStyle}><PriorityPill priority={c.priority} theme={theme} /></TableCell>
                <TableCell style={cellStyle}><StatePill state={c.state} theme={theme} /></TableCell>
                <TableCell style={cellStyle}>
                  <button title="Edit" onClick={e => { e.stopPropagation(); openEdit(c); }} className="hr-edit-btn"
                    style={{ width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer', color: t.textWeak, fontSize: '14px', padding: 0 }}>✏️</button>
                </TableCell>
              </TableRow>
              {editingId === c.sys_id && renderForm('✏️ Edit HR Case ' + c.number)}
              {expandedId === c.sys_id && (
                <TableRow>
                  <TableCell colSpan={colSpan} style={{ padding: 0 }}>
                    <div className={styles.subTableWrap} style={{ background: theme === 'dark' ? '#1A2E25' : '#EDF5F3', borderBottom: `1px solid ${t.border}` }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: t.text, marginBottom: '8px' }}>📝 Add Work Note — {c.number}</div>
                      <textarea value={noteText[c.sys_id] || ''} onChange={e => setNoteText(p => ({ ...p, [c.sys_id]: e.target.value }))}
                        placeholder="Enter work note (internal — HR staff only)…" rows={3}
                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: `1px solid ${t.border}`, background: t.surface, color: t.text, fontSize: '12px', fontFamily: 'inherit', resize: 'vertical', boxSizing: 'border-box' }} />
                      <div style={{ display: 'flex', gap: '8px', marginTop: '8px', justifyContent: 'flex-end' }}>
                        <button onClick={() => setExpandedId(null)} style={{ padding: '4px 12px', borderRadius: '4px', border: `1px solid ${t.border}`, background: 'transparent', color: t.textWeak, fontSize: '11px', cursor: 'pointer', fontFamily: 'inherit' }}>▲ Collapse</button>
                        <button onClick={() => submitNote(c.sys_id)} disabled={addingNote === c.sys_id}
                          style={{ padding: '4px 14px', borderRadius: '4px', border: 'none', background: '#1B7A6E', color: '#fff', fontSize: '12px', cursor: addingNote === c.sys_id ? 'not-allowed' : 'pointer', fontFamily: 'inherit', opacity: addingNote === c.sys_id ? 0.6 : 1 }}>
                          {addingNote === c.sys_id ? '…' : '+ Add Note'}
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
      <NowHRFooter theme={theme} />
    </div>
  );
}

// ── HR Services View ──────────────────────────────────────────────────────────
function HRServicesView({ items, theme }: { items: HRService[]; theme: 'light' | 'dark' }) {
  const styles = useStyles(); const t = now(theme);
  const [filter, setFilter] = useState('');
  const filteredItems = items.filter(s => !filter || s.name?.toLowerCase().includes(filter.toLowerCase()) || s.category?.toLowerCase().includes(filter.toLowerCase()));
  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#1B7A6E' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>📋</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>HR Services</span>
          <Badge appearance="filled" size="small" style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>{items.length} service{items.length !== 1 ? 's' : ''}</Badge>
        </div>
        <ExpandButton />
      </div>
      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by name or category…" theme={theme} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '10px', padding: '12px' }}>
        {filteredItems.length === 0 && <div className={styles.empty} style={{ gridColumn: '1 / -1', color: t.textWeak }}>{filter ? 'No matching HR services.' : 'No HR services found.'}</div>}
        {filteredItems.map(s => (
          <div key={s.sys_id} style={{ border: `1px solid ${t.border}`, borderRadius: '6px', padding: '12px', background: t.surface, boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: t.text, marginBottom: '4px' }}>{s.name}</div>
            <div style={{ fontSize: '11px', color: t.textWeak, marginBottom: '6px', lineHeight: 1.4 }}>{s.short_description || '—'}</div>
            <span style={{ fontSize: '11px', color: t.textWeak, background: theme === 'dark' ? '#2a2a2a' : '#f0f0f0', padding: '2px 8px', borderRadius: '10px' }}>{s.category || '—'}</span>
          </div>
        ))}
      </div>
      <NowHRFooter theme={theme} />
    </div>
  );
}

// ── HR Approvals View ─────────────────────────────────────────────────────────
function HRApprovalsView({ items, callTool, toast, theme }: {
  items: HRApproval[];
  callTool: (n: string, a?: Record<string, any>) => Promise<any>;
  toast: (m: string, t?: any) => void;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles(); const t = now(theme);
  const [filter, setFilter] = useState('');
  const [actingId, setActingId] = useState<string | null>(null);
  const filteredItems = items.filter(a => !filter || a.approver?.toLowerCase().includes(filter.toLowerCase()) || a.document?.toLowerCase().includes(filter.toLowerCase()));

  const act = async (sys_id: string, action: 'approve' | 'reject') => {
    setActingId(sys_id);
    try {
      await callTool(action === 'approve' ? 'sn__hr_approve_record' : 'sn__hr_reject_record', { sys_id });
      toast(action === 'approve' ? '✓ Approved' : '✓ Rejected', 'success');
    } catch (e: any) { toast(e.message || `Failed to ${action}`, 'error'); }
    finally { setActingId(null); }
  };

  const cellStyle: React.CSSProperties = { padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle' };
  const hcs: React.CSSProperties = { fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: '#1B7A6E' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>✅</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>HR Approvals</span>
          <Badge appearance="filled" size="small" style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>{items.length} record{items.length !== 1 ? 's' : ''}</Badge>
        </div>
        <ExpandButton />
      </div>
      <FilterBar value={filter} onChange={setFilter} placeholder="Filter by approver or document…" theme={theme} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={hcs}>Approver</TableHeaderCell>
            <TableHeaderCell style={hcs}>Document</TableHeaderCell>
            <TableHeaderCell style={hcs}>State</TableHeaderCell>
            <TableHeaderCell style={hcs}>Due Date</TableHeaderCell>
            <TableHeaderCell style={{ ...hcs, width: 140 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {filteredItems.length === 0 && <TableRow><TableCell colSpan={5} className={styles.empty}><Text>{filter ? 'No matching approvals.' : 'No HR approvals.'}</Text></TableCell></TableRow>}
          {filteredItems.map((a, idx) => (
            <TableRow key={a.sys_id} className="hr-row" style={{ borderBottom: idx === filteredItems.length - 1 ? 'none' : `1px solid ${t.border}` }}>
              <TableCell style={cellStyle}>{a.approver || '—'}</TableCell>
              <TableCell style={cellStyle}><span style={{ fontFamily: 'monospace', color: '#1B7A6E' }}>{a.document || '—'}</span></TableCell>
              <TableCell style={cellStyle}><StatePill state={a.state} theme={theme} /></TableCell>
              <TableCell style={cellStyle}>{a.due_date || '—'}</TableCell>
              <TableCell style={{ ...cellStyle, maxWidth: 'none' }}>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button onClick={() => act(a.sys_id, 'approve')} disabled={actingId === a.sys_id}
                    style={{ padding: '3px 10px', borderRadius: '3px', border: 'none', background: '#2E844A', color: '#fff', fontSize: '11px', fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', opacity: actingId === a.sys_id ? 0.6 : 1 }}>✓ Approve</button>
                  <button onClick={() => act(a.sys_id, 'reject')} disabled={actingId === a.sys_id}
                    style={{ padding: '3px 10px', borderRadius: '3px', border: 'none', background: '#D63B20', color: '#fff', fontSize: '11px', fontWeight: 500, cursor: 'pointer', fontFamily: 'inherit', opacity: actingId === a.sys_id ? 0.6 : 1 }}>✗ Reject</button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <NowHRFooter theme={theme} />
    </div>
  );
}

// ── HR Form View ──────────────────────────────────────────────────────────────
function HRFormView({ entity = 'hr_case', prefill, fkSelections, callTool, toast, theme }: {
  entity?: string;
  prefill?: Record<string, string>;
  fkSelections?: Record<string, { label: string; options: { id: string; name: string }[] }>;
  callTool: (n: string, a?: Record<string, any>) => Promise<any>;
  toast: (m: string, t?: any) => void;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles(); const t = now(theme);
  const [subject, setSubject] = useState(prefill?.subject || '');
  const [description, setDescription] = useState(prefill?.description || '');
  const [priority, setPriority] = useState(prefill?.priority || '3');
  const [fkChoices, setFkChoices] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const setFk = (k: string, v: string) => setFkChoices(p => ({ ...p, [k]: v }));

  const handleSubmit = async () => {
    if (!subject.trim()) { toast('Subject is required', 'error'); return; }
    if (fkSelections?.opened_for && !fkChoices.opened_for) { toast('Please select an employee (Opened For)', 'error'); return; }
    setSubmitting(true);
    try {
      const fkArgs: Record<string, string> = {};
      Object.entries(fkChoices).forEach(([k, v]) => { if (v) fkArgs[k] = v; });
      await callTool('sn__create_hr_case', { subject: subject.trim(), description: description.trim(), priority, ...fkArgs });
      toast('✓ HR Case created successfully', 'success');
      setSubmitted(true);
    } catch (e: any) { toast(e.message || 'Failed to create HR case', 'error'); }
    finally { setSubmitting(false); }
  };

  const handleReset = () => { setSubject(''); setDescription(''); setPriority('3'); setFkChoices({}); setSubmitted(false); };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div className={styles.headerBar} style={{ background: 'linear-gradient(135deg, #1B7A6E 0%, #155F55 100%)', borderBottom: '2px solid #81B5A1' }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>✨ New HR Case</span>
        </div>
      </div>
      {submitted ? (
        <div style={{ padding: '24px 16px', textAlign: 'center' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>✅</div>
          <Text weight="semibold" style={{ color: t.success, fontSize: '14px' }}>HR Case created successfully!</Text>
          <div style={{ marginTop: '12px' }}>
            <Button appearance="primary" size="small" onClick={handleReset} style={{ background: '#1B7A6E', borderColor: '#1B7A6E' }}>Create Another</Button>
          </div>
        </div>
      ) : (
        <div style={{ padding: '16px' }}>
          {fkSelections && Object.keys(fkSelections).length > 0 && (
            <div style={{ marginBottom: '16px', padding: '10px 12px', background: theme === 'dark' ? '#1A2E25' : '#EDF5F3', border: `1px solid ${t.border}`, borderRadius: '6px' }}>
              {Object.entries(fkSelections).map(([fkKey, fkDef]) => (
                <div key={fkKey} style={{ marginBottom: '8px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: t.textWeak, marginBottom: '4px' }}>{fkDef.label} *</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {fkDef.options.map(opt => (
                      <label key={opt.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: t.text }}>
                        <input type="radio" name={fkKey} value={opt.name} checked={fkChoices[fkKey] === opt.name} onChange={() => setFk(fkKey, opt.name)} style={{ accentColor: '#1B7A6E' }} />
                        {opt.name}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          <div style={{ marginBottom: '12px' }}>
            <label style={{ color: t.text, fontSize: '12px', fontWeight: 600 }}>Subject *</label>
            <Input size="small" value={subject} onChange={(_, d) => setSubject(d.value)} placeholder="Brief summary of the HR case" style={{ width: '100%', marginTop: '4px' }} />
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ color: t.text, fontSize: '12px', fontWeight: 600 }}>Description</label>
            <Textarea size="small" value={description} onChange={(_, d) => setDescription(d.value)} placeholder="Detailed description (optional)" rows={3} resize="vertical" style={{ width: '100%', marginTop: '4px' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px 20px', marginBottom: '20px' }}>
            <FormSelect label="Priority" value={priority} options={PRIORITIES} labels={PRIORITY_LABELS} onChange={setPriority} theme={theme} />
          </div>
          <div className={styles.formActions}>
            <Button size="small" appearance="primary" onClick={handleSubmit} disabled={submitting || !subject.trim()} style={{ background: '#1B7A6E', borderColor: '#1B7A6E', minWidth: '90px' }}>
              {submitting ? <Spinner size="tiny" /> : 'Submit'}
            </Button>
            <Button size="small" appearance="subtle" onClick={handleReset} disabled={submitting} style={{ color: t.textWeak }}>Reset</Button>
          </div>
        </div>
      )}
      <NowHRFooter theme={theme} />
    </div>
  );
}

// ── Skeleton ─────────────────────────────────────────────────────────────────
function SkeletonTable() {
  return (
    <div style={{ padding: '16px' }}>
      <div style={{ textAlign: 'center', padding: '8px 0 16px', fontSize: '13px', color: '#888' }}>⏳ Loading data…</div>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <div className="skel" style={{ width: '220px', height: '24px' }} />
        <div className="skel" style={{ width: '80px', height: '24px' }} />
      </div>
      {[1, 2, 3].map(i => (
        <div key={i} style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
          <div className="skel" style={{ width: `${80 + i * 10}px` }} />
          <div className="skel" style={{ width: `${160 - i * 8}px` }} />
          <div className="skel" style={{ width: `${70 + i * 5}px` }} />
        </div>
      ))}
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export function ServiceNowHRApp() {
  const styles = useStyles();
  const data = useToolData<HRData>();
  const { callTool } = useMcpBridge();
  const toast = useToast();
  const theme = useTheme();
  const t = now(theme);
  const shellStyle: React.CSSProperties = { padding: '12px', fontSize: '12px' };

  if (!data) return <div className={styles.shell} style={shellStyle}><SkeletonTable /></div>;

  if (data.error) {
    return (
      <div className={styles.shell} style={shellStyle}>
        <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
          <div className={styles.headerBar} style={{ background: '#1B7A6E' }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>⚠️ Error</span>
          </div>
          <div style={{ padding: '12px 16px', fontSize: '13px', fontWeight: 500, background: theme === 'dark' ? '#3D1111' : '#FDE7E7', color: theme === 'dark' ? '#F87171' : t.error, borderLeft: `3px solid ${t.error}` }}>
            {data.message || 'An unknown error occurred.'}
          </div>
          <NowHRFooter theme={theme} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.shell} style={shellStyle}>
      {data.type === 'hr_cases' && (
        <HRCasesView items={(data.items || []) as HRCase[]} callTool={callTool} toast={toast} theme={theme} />
      )}
      {data.type === 'hr_services' && (
        <HRServicesView items={(data.items || []) as HRService[]} theme={theme} />
      )}
      {data.type === 'hr_approvals' && (
        <HRApprovalsView items={(data.items || []) as HRApproval[]} callTool={callTool} toast={toast} theme={theme} />
      )}
      {data.type === 'form' && (
        <HRFormView entity={data.entity} prefill={data.prefill} fkSelections={data.fkSelections} callTool={callTool} toast={toast} theme={theme} />
      )}
    </div>
  );
}
