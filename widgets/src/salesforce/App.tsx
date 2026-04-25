import React, { useState, useEffect } from 'react';
import {
  Badge, Button, Field, Input, Spinner,
  Table, TableBody, TableCell, TableHeader, TableHeaderCell, TableRow,
  Text, makeStyles,
} from '@fluentui/react-components';
import { AddRegular, SearchRegular } from '@fluentui/react-icons';
import { useToolData, useMcpBridge, useTheme } from '../shared/McpBridge';
import { ExpandButton } from '../shared/ExpandButton';
import { useToast } from '../shared/Toast';
import type {
  SfData, SfListData, SfDetailData, SalesDashboardData, SupportDashboardData,
  LeadDetail, CaseDetail, TaskDetail,
} from './types';

// ── SLDS Color Tokens ──────────────────────────────────────────────────────
const SLDS_LIGHT = {
  brand: '#0176D3', brandHover: '#014486', accent: '#1B96FF',
  background: '#F3F3F3', surface: '#FFFFFF', text: '#181818',
  textWeak: '#706E6B', border: '#DDDBDA', headerBg: '#FAFAF9',
  success: '#2E844A', danger: '#BA0517', warn: '#DD7A01',
};
const SLDS_DARK = {
  brand: '#1B96FF', brandHover: '#0176D3', accent: '#1B96FF',
  background: '#16325C', surface: '#1A3A65', text: '#F3F3F3',
  textWeak: '#A0B0C0', border: '#2D4B6D', headerBg: '#1A3A65',
  success: '#2E844A', danger: '#BA0517', warn: '#DD7A01',
};
function slds(theme: 'light' | 'dark') { return theme === 'dark' ? SLDS_DARK : SLDS_LIGHT; }

// ── Constants ──────────────────────────────────────────────────────────────
const LEAD_STATUSES = ['Open - Not Contacted', 'Working - Contacted', 'Closed - Converted', 'Closed - Not Converted'];
const LEAD_SOURCES  = ['Web', 'Phone Inquiry', 'Partner Referral', 'Purchased List', 'Other'];
const OPP_STAGES    = ['Prospecting', 'Qualification', 'Needs Analysis', 'Proposal/Price Quote', 'Negotiation/Review', 'Closed Won', 'Closed Lost'];
const CASE_STATUSES = ['New', 'Open', 'Working', 'Escalated', 'Closed'];
const CASE_PRIOS    = ['Low', 'Medium', 'High', 'Critical'];
const TASK_STATUSES = ['Not Started', 'In Progress', 'Completed', 'Waiting on someone else', 'Deferred'];
const TASK_PRIOS    = ['Low', 'Normal', 'High'];
const ACCT_INDUSTRIES = ['Technology', 'Healthcare', 'Finance', 'Manufacturing', 'Retail', 'Education', 'Other'];
const ACCT_TYPES    = ['Prospect', 'Customer', 'Partner', 'Competitor', 'Other'];
const CAMP_TYPES    = ['Email', 'Phone', 'Web', 'Event', 'Other'];
const CAMP_STATUSES = ['Planning', 'Active', 'Completed', 'Aborted'];

// ── Status pill styles ─────────────────────────────────────────────────────
type PillStyle = { background: string; color: string; border: string };
const STATUS_STYLES: Record<string, { light: PillStyle; dark: PillStyle }> = {
  open:      { light: { background: '#EEF4FF', color: '#0176D3', border: '#B9D6F5' }, dark: { background: '#0b3573', color: '#8dc7ff', border: '#2b5797' } },
  contacted: { light: { background: '#FEF0CD', color: '#8C4B02', border: '#E4C546' }, dark: { background: '#5c3b0a', color: '#f5c451', border: '#8c6e2e' } },
  qualified: { light: { background: '#EBF7E6', color: '#2E844A', border: '#91DB8B' }, dark: { background: '#1a3a2a', color: '#7cd992', border: '#2e6a3e' } },
  closed:    { light: { background: '#FEF1EE', color: '#BA0517', border: '#FE9F9B' }, dark: { background: '#5c1a1a', color: '#fe9f9b', border: '#9c3030' } },
  warn:      { light: { background: '#FEF0CD', color: '#8C4B02', border: '#E4C546' }, dark: { background: '#5c3b0a', color: '#f5c451', border: '#8c6e2e' } },
};
function getStatusKey(s: string): string {
  const v = s.toLowerCase();
  if (v.includes('not converted') || v.includes('lost') || v.includes('closed') || v.includes('aborted')) return 'closed';
  if (v.includes('converted') || v.includes('won') || v.includes('qualified') || v.includes('completed')) return 'qualified';
  if (v.includes('working') || v.includes('contacted') || v.includes('needs') || v.includes('proposal') || v.includes('negotiation') || v.includes('escalated') || v.includes('active') || v.includes('in progress')) return 'contacted';
  if (v.includes('high') || v.includes('critical')) return 'warn';
  return 'open';
}
function fmt$(v: number | null | undefined) { return v == null ? '—' : '$' + Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 }); }
function fmtDate(v?: string | null) { return v ? v.slice(0, 10) : '—'; }

// ── Styles ─────────────────────────────────────────────────────────────────
const useStyles = makeStyles({
  shell:      { margin: '0 auto', padding: '12px', fontFamily: "'Salesforce Sans','Segoe UI',system-ui,sans-serif", fontSize: '13px' },
  card:       { borderRadius: '4px', overflow: 'hidden', boxShadow: '0 2px 4px rgba(0,0,0,0.07)', overflowX: 'auto' as const },
  headerBar:  { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px' },
  headerLeft: { display: 'flex', alignItems: 'center', gap: '10px' },
  formPanel:  { padding: '14px 16px', borderLeft: '3px solid #0176D3' },
  formTitle:  { fontSize: '14px', fontWeight: 600 as any, marginBottom: '10px' },
  formGrid:   { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: '10px 12px', marginBottom: '12px' },
  formActions:{ display: 'flex', gap: '8px', justifyContent: 'flex-end' },
  amount:     { fontWeight: 500 as any, fontVariantNumeric: 'tabular-nums' },
  empty:      { padding: '16px', textAlign: 'center' as const, fontSize: '13px' },
  mcpFooter:  { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 16px', fontSize: '11px' },
  filterBar:  { display: 'flex', gap: '8px', alignItems: 'center', padding: '8px 12px', flexWrap: 'wrap' as const },
  childTable: { padding: '0 24px 10px', background: 'transparent' },
  kpiGrid:    { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '12px', padding: '14px 16px' },
  kpiCard:    { borderRadius: '6px', padding: '12px', textAlign: 'center' as const },
});

const H_CELL: React.CSSProperties = { fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '6px 10px' };
const D_CELL: React.CSSProperties = { padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle' };

// ── StatusPill ─────────────────────────────────────────────────────────────
function StatusPill({ status, theme }: { status: string; theme: 'light' | 'dark' }) {
  const key = getStatusKey(status);
  const s = STATUS_STYLES[key]?.[theme] || STATUS_STYLES.open[theme];
  return (
    <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: '15px', fontSize: '11px', fontWeight: 600, background: s.background, color: s.color, border: `1px solid ${s.border}` }}>
      {status || '—'}
    </span>
  );
}

// ── SldsFooter ─────────────────────────────────────────────────────────────
function SldsFooter({ theme }: { theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const { openExternal } = useMcpBridge();
  return (
    <div className={styles.mcpFooter} style={{ background: theme === 'dark' ? '#0f2440' : '#F3F3F3', borderTop: `1px solid ${t.border}`, color: t.textWeak }}>
      <span>⚡ <strong>MCP</strong> · Salesforce CRM</span>
      <div style={{ display: 'flex', gap: '12px' }}>
        <span style={{ cursor: 'pointer', textDecoration: 'underline' }} onClick={() => openExternal('https://login.salesforce.com')}>Open in Salesforce ↗</span>
        <span>⚓ GTC</span>
      </div>
    </div>
  );
}

// ── FormSelect ─────────────────────────────────────────────────────────────
function FormSelect({ label, value, options, onChange, theme }: { label: string; value: string; options: string[]; onChange: (v: string) => void; theme: 'light' | 'dark' }) {
  const t = slds(theme);
  return (
    <Field label={label} size="small">
      <select value={value} onChange={e => onChange(e.target.value)}
        style={{ width: '100%', padding: '5px 8px', borderRadius: '4px', border: `1px solid ${t.border}`, background: t.surface, color: t.text, fontSize: '13px', fontFamily: 'inherit', height: '32px' }}>
        <option value="">— Select —</option>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
    </Field>
  );
}

// ── FilterBar ──────────────────────────────────────────────────────────────
function FilterBar({ placeholder, value, onValue, onSearch, loading, theme, extra }: {
  placeholder: string; value: string; onValue: (v: string) => void;
  onSearch: () => void; loading: boolean; theme: 'light' | 'dark';
  extra?: React.ReactNode;
}) {
  const t = slds(theme);
  return (
    <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '8px 12px', flexWrap: 'wrap', borderBottom: `1px solid ${t.border}`, background: theme === 'dark' ? '#1a3a65' : '#FAFAF9' }}>
      <Input size="small" placeholder={placeholder} value={value} onChange={(_, d) => onValue(d.value)}
        onKeyDown={e => e.key === 'Enter' && onSearch()}
        style={{ minWidth: '180px', flex: 1, maxWidth: '260px' }} />
      {extra}
      <Button size="small" appearance="primary" icon={loading ? <Spinner size="tiny" /> : <SearchRegular />}
        onClick={onSearch} disabled={loading}
        style={{ background: t.brand, borderColor: t.brand, height: '30px', minWidth: '80px' }}>
        {loading ? '' : 'Search'}
      </Button>
      {value && (
        <Button size="small" appearance="subtle" onClick={() => { onValue(''); onSearch(); }}
          style={{ height: '30px', color: t.textWeak }}>✕ Clear</Button>
      )}
    </div>
  );
}

// ── ExpandToggle (row-level) ───────────────────────────────────────────────
function ExpandToggle({ expanded, onClick, theme }: { expanded: boolean; onClick: () => void; theme: 'light' | 'dark' }) {
  const t = slds(theme);
  return (
    <button onClick={onClick} title={expanded ? 'Collapse' : 'Expand'}
      style={{ width: '22px', height: '22px', border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '12px', color: t.brand, fontWeight: 700, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
      {expanded ? '▼' : '▶'}
    </button>
  );
}

// ── SkeletonTable ──────────────────────────────────────────────────────────
function SkeletonTable() {
  return (
    <div style={{ padding: '16px' }}>
      <style>{`@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}.skel{height:14px;border-radius:4px;background:linear-gradient(90deg,#e8e8e8 25%,#f5f5f5 50%,#e8e8e8 75%);background-size:200% 100%;animation:shimmer 1.5s infinite}[data-theme="dark"] .skel{background:linear-gradient(90deg,#333 25%,#444 50%,#333 75%);background-size:200% 100%}`}</style>
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <div className="skel" style={{ width: '200px', height: '24px' }} />
        <div className="skel" style={{ width: '80px', height: '24px' }} />
      </div>
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
          <div className="skel" style={{ width: '120px' }} />
          <div className="skel" style={{ width: '150px' }} />
          <div className="skel" style={{ width: '100px' }} />
          <div className="skel" style={{ width: '90px' }} />
        </div>
      ))}
    </div>
  );
}

// ── DashBar (horizontal bar for analytics) ────────────────────────────────
function DashBar({ label, value, max, color, theme }: { label: string; value: number; max: number; color: string; theme: 'light' | 'dark' }) {
  const t = slds(theme);
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div style={{ marginBottom: '10px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: t.textWeak, marginBottom: '3px' }}>
        <span>{label}</span><span style={{ fontWeight: 600, color: t.text }}>{value.toLocaleString()}</span>
      </div>
      <div style={{ height: '12px', background: t.border, borderRadius: '6px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '6px', transition: 'width 0.4s' }} />
      </div>
    </div>
  );
}

// ── Shared header + table wrapper ──────────────────────────────────────────
function ViewHeader({ icon, title, count, brand, onNew, newLabel, theme }: {
  icon: string; title: string; count: number; brand: string;
  onNew?: () => void; newLabel?: string; theme: 'light' | 'dark';
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', background: brand }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <span style={{ fontSize: '18px' }}>{icon}</span>
        <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{title}</span>
        <Badge appearance="filled" size="small" style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
          {count} record{count !== 1 ? 's' : ''}
        </Badge>
      </div>
      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
        {onNew && (
          <Button appearance="primary" size="small" icon={<AddRegular />} onClick={onNew}
            style={{ background: 'rgba(255,255,255,0.15)', borderColor: 'rgba(255,255,255,0.3)', color: '#fff', borderRadius: '4px', height: '32px', padding: '0 16px' }}>
            {newLabel || '+ New'}
          </Button>
        )}
        <ExpandButton />
      </div>
    </div>
  );
}

// ── Inline form row ────────────────────────────────────────────────────────
function InlineFormRow({ colSpan, title, fields, onSave, onCancel, saving, theme }: {
  colSpan: number; title: string;
  fields: { label: string; key: string; value: string; onChange: (v: string) => void; type?: 'select'; options?: string[]; inputType?: string }[];
  onSave: () => void; onCancel: () => void; saving: boolean; theme: 'light' | 'dark';
}) {
  const t = slds(theme);
  const formBg = theme === 'dark' ? '#1a3050' : '#F3F3F3';
  return (
    <TableRow>
      <TableCell colSpan={colSpan} style={{ padding: 0 }}>
        <div style={{ padding: '14px 16px', borderLeft: `3px solid ${t.brand}`, background: formBg }}>
          <div style={{ fontSize: '14px', fontWeight: 600, color: t.brand, marginBottom: '10px' }}>{title}</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: '10px 12px', marginBottom: '12px' }}>
            {fields.map(f =>
              f.type === 'select' ? (
                <FormSelect key={f.key} label={f.label} value={f.value} options={f.options || []} onChange={f.onChange} theme={theme} />
              ) : (
                <Field key={f.key} label={f.label} size="small">
                  <Input size="small" type={f.inputType || 'text'} value={f.value} onChange={(_, d) => f.onChange(d.value)} />
                </Field>
              )
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <Button appearance="secondary" size="small" onClick={onCancel} disabled={saving}
              style={{ borderRadius: '4px', height: '32px', padding: '0 16px', border: `1px solid ${t.border}` }}>Cancel</Button>
            <Button appearance="primary" size="small" onClick={onSave} disabled={saving}
              style={{ background: t.brand, borderColor: t.brand, borderRadius: '4px', height: '32px', padding: '0 16px' }}>
              {saving ? 'Saving…' : title.includes('Edit') ? '✓ Save' : '✓ Create'}
            </Button>
          </div>
        </div>
      </TableCell>
    </TableRow>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── AccountsView ───────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function AccountsView({ items: initItems, callTool, toast, theme }: { items: any[]; callTool: (n: string, a?: any) => Promise<any>; toast: (m: string, t?: any) => void; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const [localItems, setLocalItems] = useState(initItems);
  const [filterName, setFilterName] = useState('');
  const [filterIndustry, setFilterIndustry] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [childContacts, setChildContacts] = useState<Record<string, any[]>>({});
  const [loadingChild, setLoadingChild] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', industry: '', phone: '', website: '', type: '', billing_city: '' });

  useEffect(() => setLocalItems(initItems), [initItems]);

  const doSearch = async () => {
    setFiltering(true);
    try {
      const res = await callTool('search_accounts', { name: filterName, industry: filterIndustry });
      setLocalItems(res?.items || []);
    } finally { setFiltering(false); }
  };

  const openEdit = (a: any) => { setCreating(false); setEditingId(a.id); setForm({ name: a.name || '', industry: a.industry || '', phone: a.phone || '', website: a.website || '', type: a.type || '', billing_city: a.billing_city || '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ name: '', industry: '', phone: '', website: '', type: '', billing_city: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) { await callTool('create_account', form); toast('✓ Account created'); }
      else { await callTool('update_account', { account_id: editingId, ...form }); toast('✓ Account updated'); setLastSavedId(editingId); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  useEffect(() => { if (lastSavedId) { const x = setTimeout(() => setLastSavedId(null), 1600); return () => clearTimeout(x); } }, [lastSavedId]);

  const toggleExpand = async (id: string) => {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    if (childContacts[id]) return;
    setLoadingChild(id);
    try {
      const res = await callTool('get_account_contacts', { account_id: id });
      setChildContacts(p => ({ ...p, [id]: res?.items || [] }));
    } catch { setChildContacts(p => ({ ...p, [id]: [] })); }
    finally { setLoadingChild(null); }
  };

  const fFields = (f: typeof form, set: (k: string, v: string) => void) => [
    { label: 'Account Name *', key: 'name', value: f.name, onChange: (v: string) => set('name', v) },
    { label: 'Industry', key: 'industry', value: f.industry, onChange: (v: string) => set('industry', v), type: 'select' as const, options: ACCT_INDUSTRIES },
    { label: 'Phone', key: 'phone', value: f.phone, onChange: (v: string) => set('phone', v) },
    { label: 'Website', key: 'website', value: f.website, onChange: (v: string) => set('website', v) },
    { label: 'Type', key: 'type', value: f.type, onChange: (v: string) => set('type', v), type: 'select' as const, options: ACCT_TYPES },
    { label: 'City', key: 'billing_city', value: f.billing_city, onChange: (v: string) => set('billing_city', v) },
  ];
  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="🏢" title="Accounts" count={localItems.length} brand={t.brand} onNew={openCreate} newLabel="+ New Account" theme={theme} />
      <FilterBar placeholder="Search by name…" value={filterName} onValue={setFilterName} onSearch={doSearch} loading={filtering} theme={theme}
        extra={<FormSelect label="" value={filterIndustry} options={ACCT_INDUSTRIES} onChange={setFilterIndustry} theme={theme} />} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={{ ...H_CELL, width: 28, color: t.textWeak }} />
            <TableHeaderCell style={{ ...H_CELL, color: t.textWeak }}>Account Name</TableHeaderCell>
            <TableHeaderCell style={{ ...H_CELL, color: t.textWeak }}>Industry</TableHeaderCell>
            <TableHeaderCell style={{ ...H_CELL, color: t.textWeak }}>City</TableHeaderCell>
            <TableHeaderCell style={{ ...H_CELL, color: t.textWeak }}>Phone</TableHeaderCell>
            <TableHeaderCell style={{ ...H_CELL, color: t.textWeak }}>Type</TableHeaderCell>
            <TableHeaderCell style={{ ...H_CELL, width: 32, color: t.textWeak }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <InlineFormRow colSpan={7} title="➕ New Account" fields={fFields(form, setF)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={7} className={styles.empty}><Text>No accounts found.</Text></TableCell></TableRow>}
          {localItems.map((a, idx) => (
            <React.Fragment key={a.id}>
              <TableRow style={{ borderBottom: `1px solid ${t.border}`, ...(lastSavedId === a.id ? { animation: 'sfRowFlash 1.5s ease-out' } : {}) }}>
                <TableCell style={{ ...D_CELL, width: 28 }}>
                  <ExpandToggle expanded={expandedId === a.id} onClick={() => toggleExpand(a.id)} theme={theme} />
                </TableCell>
                <TableCell style={D_CELL}><span style={{ fontWeight: 500, color: t.brand }}>{a.name}</span></TableCell>
                <TableCell style={D_CELL}>{a.industry || '—'}</TableCell>
                <TableCell style={D_CELL}>{a.billing_city || '—'}</TableCell>
                <TableCell style={D_CELL}>{a.phone || '—'}</TableCell>
                <TableCell style={D_CELL}>{a.type || '—'}</TableCell>
                <TableCell style={D_CELL}><button title="Edit" onClick={() => openEdit(a)} className="slds-edit-btn" style={{ width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer', color: t.textWeak, fontSize: '14px', padding: 0 }}>✏️</button></TableCell>
              </TableRow>
              {editingId === a.id && <InlineFormRow colSpan={7} title="✏️ Edit Account" fields={fFields(form, setF)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
              {expandedId === a.id && (
                <TableRow>
                  <TableCell colSpan={7} style={{ padding: 0, background: theme === 'dark' ? '#142a50' : '#f8f9fb' }}>
                    <div style={{ padding: '8px 28px 12px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: t.textWeak, marginBottom: '6px' }}>Contacts</div>
                      {loadingChild === a.id ? (
                        <Spinner size="tiny" label="Loading contacts…" />
                      ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                          <thead>
                            <tr style={{ background: t.headerBg }}>
                              {['Name', 'Email', 'Phone', 'Title'].map(h => <th key={h} style={{ ...H_CELL, color: t.textWeak, textAlign: 'left' }}>{h}</th>)}
                            </tr>
                          </thead>
                          <tbody>
                            {(childContacts[a.id] || []).length === 0 ? (
                              <tr><td colSpan={4} style={{ padding: '10px', color: t.textWeak, textAlign: 'center' }}>No contacts found.</td></tr>
                            ) : (childContacts[a.id] || []).map((c: any) => (
                              <tr key={c.id} style={{ borderBottom: `1px solid ${t.border}` }}>
                                <td style={D_CELL}>{c.first_name} {c.last_name}</td>
                                <td style={D_CELL}>{c.email || '—'}</td>
                                <td style={D_CELL}>{c.phone || '—'}</td>
                                <td style={D_CELL}>{c.title || '—'}</td>
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
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── LeadsView ──────────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function LeadsView({ items: initItems, callTool, toast, theme }: { items: any[]; callTool: (n: string, a?: any) => Promise<any>; toast: (m: string, t?: any) => void; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const [localItems, setLocalItems] = useState(initItems);
  const [filterName, setFilterName] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [converting, setConverting] = useState<string | null>(null);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [form, setForm] = useState({ first_name: '', last_name: '', company: '', email: '', phone: '', status: '', lead_source: '' });

  useEffect(() => setLocalItems(initItems), [initItems]);

  const doSearch = async () => {
    if (!filterName.trim()) { setLocalItems(initItems); return; }
    setFiltering(true);
    try { const res = await callTool('search_leads', { name: filterName }); setLocalItems(res?.items || []); }
    finally { setFiltering(false); }
  };

  const openEdit = (l: any) => { setCreating(false); setEditingId(l.id); setForm({ first_name: l.first_name || '', last_name: l.last_name || '', company: l.company || '', email: l.email || '', phone: l.phone || '', status: l.status || '', lead_source: l.lead_source || '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ first_name: '', last_name: '', company: '', email: '', phone: '', status: '', lead_source: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) { await callTool('create_lead', form); toast('✓ Lead created'); }
      else { await callTool('update_lead', { lead_id: editingId, ...form }); toast('✓ Lead updated'); setLastSavedId(editingId); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  const handleConvert = async (leadId: string, leadName: string) => {
    setConverting(leadId);
    try {
      await callTool('convert_lead', { lead_id: leadId });
      toast(`✓ ${leadName} converted to Account/Contact`);
      setLocalItems(p => p.filter(x => x.id !== leadId));
    } catch (e: any) { toast(e.message || 'Convert failed', 'error'); }
    finally { setConverting(null); }
  };

  useEffect(() => { if (lastSavedId) { const x = setTimeout(() => setLastSavedId(null), 1600); return () => clearTimeout(x); } }, [lastSavedId]);

  const fFields = (f: typeof form, set: (k: string, v: string) => void) => [
    { label: 'First Name', key: 'first_name', value: f.first_name, onChange: (v: string) => set('first_name', v) },
    { label: 'Last Name *', key: 'last_name', value: f.last_name, onChange: (v: string) => set('last_name', v) },
    { label: 'Company *', key: 'company', value: f.company, onChange: (v: string) => set('company', v) },
    { label: 'Email', key: 'email', value: f.email, onChange: (v: string) => set('email', v), inputType: 'email' },
    { label: 'Phone', key: 'phone', value: f.phone, onChange: (v: string) => set('phone', v) },
    { label: 'Status', key: 'status', value: f.status, onChange: (v: string) => set('status', v), type: 'select' as const, options: LEAD_STATUSES },
    { label: 'Lead Source', key: 'lead_source', value: f.lead_source, onChange: (v: string) => set('lead_source', v), type: 'select' as const, options: LEAD_SOURCES },
  ];
  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="👤" title="Leads" count={localItems.length} brand={t.brand} onNew={openCreate} newLabel="+ New Lead" theme={theme} />
      <FilterBar placeholder="Search by name or company…" value={filterName} onValue={setFilterName} onSearch={doSearch} loading={filtering} theme={theme} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            {['Name', 'Company', 'Status', 'Source', 'Email', ''].map(h => <TableHeaderCell key={h} style={{ ...H_CELL, color: t.textWeak }}>{h}</TableHeaderCell>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <InlineFormRow colSpan={6} title="➕ New Lead" fields={fFields(form, setF)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={6} className={styles.empty}><Text>No leads found.</Text></TableCell></TableRow>}
          {localItems.map((l: any) => (
            <React.Fragment key={l.id}>
              <TableRow style={{ borderBottom: `1px solid ${t.border}`, ...(lastSavedId === l.id ? { animation: 'sfRowFlash 1.5s ease-out' } : {}) }}>
                <TableCell style={D_CELL}>{l.first_name} {l.last_name}</TableCell>
                <TableCell style={D_CELL}>{l.company || '—'}</TableCell>
                <TableCell style={D_CELL}><StatusPill status={l.status} theme={theme} /></TableCell>
                <TableCell style={D_CELL}>{l.lead_source || '—'}</TableCell>
                <TableCell style={D_CELL}>{l.email || '—'}</TableCell>
                <TableCell style={{ ...D_CELL, width: 100 }}>
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button title="Edit" onClick={() => openEdit(l)} className="slds-edit-btn" style={{ width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer', color: t.textWeak, fontSize: '14px', padding: 0 }}>✏️</button>
                    <button title="Convert" onClick={() => handleConvert(l.id, `${l.first_name} ${l.last_name}`)} disabled={converting === l.id}
                      style={{ height: '28px', padding: '0 8px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer', color: t.success, fontSize: '11px', fontWeight: 600 }}>
                      {converting === l.id ? '…' : '⇄ Convert'}
                    </button>
                  </div>
                </TableCell>
              </TableRow>
              {editingId === l.id && <InlineFormRow colSpan={6} title="✏️ Edit Lead" fields={fFields(form, setF)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── ContactsView ───────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function ContactsView({ items: initItems, callTool, toast, theme }: { items: any[]; callTool: (n: string, a?: any) => Promise<any>; toast: (m: string, t?: any) => void; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const [localItems, setLocalItems] = useState(initItems);
  const [filterName, setFilterName] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', phone: '', title: '', account_name: '' });

  useEffect(() => setLocalItems(initItems), [initItems]);

  const doSearch = async () => {
    if (!filterName.trim()) { setLocalItems(initItems); return; }
    setFiltering(true);
    try { const res = await callTool('search_contacts', { name: filterName }); setLocalItems(res?.items || []); }
    finally { setFiltering(false); }
  };

  const openEdit = (c: any) => { setCreating(false); setEditingId(c.id); setForm({ first_name: c.first_name || '', last_name: c.last_name || '', email: c.email || '', phone: c.phone || '', title: c.title || '', account_name: c.account_name || '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ first_name: '', last_name: '', email: '', phone: '', title: '', account_name: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) { await callTool('create_contact', form); toast('✓ Contact created'); }
      else { await callTool('update_contact', { contact_id: editingId, ...form }); toast('✓ Contact updated'); setLastSavedId(editingId); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  useEffect(() => { if (lastSavedId) { const x = setTimeout(() => setLastSavedId(null), 1600); return () => clearTimeout(x); } }, [lastSavedId]);

  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));
  const fFields = (f: typeof form) => [
    { label: 'First Name', key: 'first_name', value: f.first_name, onChange: (v: string) => setF('first_name', v) },
    { label: 'Last Name *', key: 'last_name', value: f.last_name, onChange: (v: string) => setF('last_name', v) },
    { label: 'Email', key: 'email', value: f.email, onChange: (v: string) => setF('email', v), inputType: 'email' },
    { label: 'Phone', key: 'phone', value: f.phone, onChange: (v: string) => setF('phone', v) },
    { label: 'Title', key: 'title', value: f.title, onChange: (v: string) => setF('title', v) },
    { label: 'Account', key: 'account_name', value: f.account_name, onChange: (v: string) => setF('account_name', v) },
  ];

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="👥" title="Contacts" count={localItems.length} brand={t.brand} onNew={openCreate} newLabel="+ New Contact" theme={theme} />
      <FilterBar placeholder="Search by name…" value={filterName} onValue={setFilterName} onSearch={doSearch} loading={filtering} theme={theme} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            {['Name', 'Account', 'Title', 'Email', 'Phone', ''].map(h => <TableHeaderCell key={h} style={{ ...H_CELL, color: t.textWeak }}>{h}</TableHeaderCell>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <InlineFormRow colSpan={6} title="➕ New Contact" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={6} className={styles.empty}><Text>No contacts found.</Text></TableCell></TableRow>}
          {localItems.map((c: any) => (
            <React.Fragment key={c.id}>
              <TableRow style={{ borderBottom: `1px solid ${t.border}`, ...(lastSavedId === c.id ? { animation: 'sfRowFlash 1.5s ease-out' } : {}) }}>
                <TableCell style={D_CELL}>{c.first_name} {c.last_name}</TableCell>
                <TableCell style={D_CELL}>{c.account_name || '—'}</TableCell>
                <TableCell style={D_CELL}>{c.title || '—'}</TableCell>
                <TableCell style={D_CELL}>{c.email || '—'}</TableCell>
                <TableCell style={D_CELL}>{c.phone || '—'}</TableCell>
                <TableCell style={D_CELL}><button title="Edit" onClick={() => openEdit(c)} className="slds-edit-btn" style={{ width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer', color: t.textWeak, fontSize: '14px', padding: 0 }}>✏️</button></TableCell>
              </TableRow>
              {editingId === c.id && <InlineFormRow colSpan={6} title="✏️ Edit Contact" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── OpportunitiesView ──────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function OpportunitiesView({ items: initItems, callTool, toast, theme }: { items: any[]; callTool: (n: string, a?: any) => Promise<any>; toast: (m: string, t?: any) => void; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const [localItems, setLocalItems] = useState(initItems);
  const [filterName, setFilterName] = useState('');
  const [filterStage, setFilterStage] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', account_name: '', stage: '', amount: '', close_date: '', probability: '' });

  useEffect(() => setLocalItems(initItems), [initItems]);

  const doSearch = async () => {
    setFiltering(true);
    try { const res = await callTool('search_opportunities', { name: filterName, stage: filterStage }); setLocalItems(res?.items || []); }
    finally { setFiltering(false); }
  };

  const openEdit = (o: any) => { setCreating(false); setEditingId(o.id); setForm({ name: o.name || '', account_name: o.account_name || '', stage: o.stage || '', amount: o.amount != null ? String(o.amount) : '', close_date: o.close_date || '', probability: o.probability != null ? String(o.probability) : '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ name: '', account_name: '', stage: '', amount: '', close_date: '', probability: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      const args = { ...form, amount: form.amount ? parseFloat(form.amount) : null, probability: form.probability ? parseInt(form.probability) : null };
      if (creating) { await callTool('create_opportunity', args); toast('✓ Opportunity created'); }
      else { await callTool('update_opportunity', { opportunity_id: editingId, ...args }); toast('✓ Opportunity updated'); setLastSavedId(editingId); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  useEffect(() => { if (lastSavedId) { const x = setTimeout(() => setLastSavedId(null), 1600); return () => clearTimeout(x); } }, [lastSavedId]);

  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));
  const fFields = (f: typeof form) => [
    { label: 'Opportunity Name *', key: 'name', value: f.name, onChange: (v: string) => setF('name', v) },
    { label: 'Account Name', key: 'account_name', value: f.account_name, onChange: (v: string) => setF('account_name', v) },
    { label: 'Stage', key: 'stage', value: f.stage, onChange: (v: string) => setF('stage', v), type: 'select' as const, options: OPP_STAGES },
    { label: 'Amount ($)', key: 'amount', value: f.amount, onChange: (v: string) => setF('amount', v), inputType: 'number' },
    { label: 'Close Date', key: 'close_date', value: f.close_date, onChange: (v: string) => setF('close_date', v), inputType: 'date' },
    { label: 'Probability (%)', key: 'probability', value: f.probability, onChange: (v: string) => setF('probability', v), inputType: 'number' },
  ];

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="💰" title="Opportunities" count={localItems.length} brand={t.brand} onNew={openCreate} newLabel="+ New Opportunity" theme={theme} />
      <FilterBar placeholder="Search by name…" value={filterName} onValue={setFilterName} onSearch={doSearch} loading={filtering} theme={theme}
        extra={<FormSelect label="" value={filterStage} options={OPP_STAGES} onChange={setFilterStage} theme={theme} />} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            {['Name', 'Account', 'Stage', 'Amount', 'Close Date', 'Prob %', ''].map(h => <TableHeaderCell key={h} style={{ ...H_CELL, color: t.textWeak }}>{h}</TableHeaderCell>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <InlineFormRow colSpan={7} title="➕ New Opportunity" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={7} className={styles.empty}><Text>No opportunities found.</Text></TableCell></TableRow>}
          {localItems.map((o: any) => (
            <React.Fragment key={o.id}>
              <TableRow style={{ borderBottom: `1px solid ${t.border}`, ...(lastSavedId === o.id ? { animation: 'sfRowFlash 1.5s ease-out' } : {}) }}>
                <TableCell style={D_CELL}>{o.name}</TableCell>
                <TableCell style={D_CELL}>{o.account_name || '—'}</TableCell>
                <TableCell style={D_CELL}><StatusPill status={o.stage} theme={theme} /></TableCell>
                <TableCell style={{ ...D_CELL, fontWeight: 500 }}>{fmt$(o.amount)}</TableCell>
                <TableCell style={D_CELL}>{fmtDate(o.close_date)}</TableCell>
                <TableCell style={D_CELL}>{o.probability != null ? o.probability + '%' : '—'}</TableCell>
                <TableCell style={D_CELL}><button title="Edit" onClick={() => openEdit(o)} className="slds-edit-btn" style={{ width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer', color: t.textWeak, fontSize: '14px', padding: 0 }}>✏️</button></TableCell>
              </TableRow>
              {editingId === o.id && <InlineFormRow colSpan={7} title="✏️ Edit Opportunity" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── CasesView ──────────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function CasesView({ items: initItems, callTool, toast, theme }: { items: any[]; callTool: (n: string, a?: any) => Promise<any>; toast: (m: string, t?: any) => void; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const [localItems, setLocalItems] = useState(initItems);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterPrio, setFilterPrio] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [childComments, setChildComments] = useState<Record<string, any[]>>({});
  const [loadingChild, setLoadingChild] = useState<string | null>(null);
  const [form, setForm] = useState({ subject: '', status: '', priority: '', account_name: '', description: '' });

  useEffect(() => setLocalItems(initItems), [initItems]);

  const doSearch = async () => {
    setFiltering(true);
    try { const res = await callTool('search_cases', { status: filterStatus, priority: filterPrio }); setLocalItems(res?.items || []); }
    finally { setFiltering(false); }
  };

  const openEdit = (c: any) => { setCreating(false); setEditingId(c.id); setForm({ subject: c.subject || '', status: c.status || '', priority: c.priority || '', account_name: c.account_name || '', description: c.description || '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ subject: '', status: 'New', priority: 'Medium', account_name: '', description: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) { await callTool('create_case', form); toast('✓ Case created'); }
      else { await callTool('update_case', { case_id: editingId, ...form }); toast('✓ Case updated'); setLastSavedId(editingId); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  useEffect(() => { if (lastSavedId) { const x = setTimeout(() => setLastSavedId(null), 1600); return () => clearTimeout(x); } }, [lastSavedId]);

  const toggleExpand = async (id: string) => {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    if (childComments[id]) return;
    setLoadingChild(id);
    try { const res = await callTool('get_case_comments', { case_id: id }); setChildComments(p => ({ ...p, [id]: res?.items || [] })); }
    catch { setChildComments(p => ({ ...p, [id]: [] })); }
    finally { setLoadingChild(null); }
  };

  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));
  const fFields = (f: typeof form) => [
    { label: 'Subject *', key: 'subject', value: f.subject, onChange: (v: string) => setF('subject', v) },
    { label: 'Status', key: 'status', value: f.status, onChange: (v: string) => setF('status', v), type: 'select' as const, options: CASE_STATUSES },
    { label: 'Priority', key: 'priority', value: f.priority, onChange: (v: string) => setF('priority', v), type: 'select' as const, options: CASE_PRIOS },
    { label: 'Account', key: 'account_name', value: f.account_name, onChange: (v: string) => setF('account_name', v) },
    { label: 'Description', key: 'description', value: f.description, onChange: (v: string) => setF('description', v) },
  ];

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="🎫" title="Cases" count={localItems.length} brand="#706E6B" onNew={openCreate} newLabel="+ New Case" theme={theme} />
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '8px 12px', flexWrap: 'wrap', borderBottom: `1px solid ${t.border}`, background: theme === 'dark' ? '#1a3a65' : '#FAFAF9' }}>
        <FormSelect label="" value={filterStatus} options={CASE_STATUSES} onChange={setFilterStatus} theme={theme} />
        <FormSelect label="" value={filterPrio} options={CASE_PRIOS} onChange={setFilterPrio} theme={theme} />
        <Button size="small" appearance="primary" icon={filtering ? <Spinner size="tiny" /> : <SearchRegular />} onClick={doSearch} disabled={filtering}
          style={{ background: t.brand, borderColor: t.brand, height: '30px', minWidth: '80px' }}>Search</Button>
      </div>
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={{ ...H_CELL, width: 28, color: t.textWeak }} />
            {['Case #', 'Subject', 'Status', 'Priority', 'Account', 'Created', ''].map(h => <TableHeaderCell key={h} style={{ ...H_CELL, color: t.textWeak }}>{h}</TableHeaderCell>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <InlineFormRow colSpan={8} title="➕ New Case" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={8} className={styles.empty}><Text>No cases found.</Text></TableCell></TableRow>}
          {localItems.map((c: any) => (
            <React.Fragment key={c.id}>
              <TableRow style={{ borderBottom: `1px solid ${t.border}`, ...(lastSavedId === c.id ? { animation: 'sfRowFlash 1.5s ease-out' } : {}) }}>
                <TableCell style={{ ...D_CELL, width: 28 }}><ExpandToggle expanded={expandedId === c.id} onClick={() => toggleExpand(c.id)} theme={theme} /></TableCell>
                <TableCell style={D_CELL}>{c.case_number || '—'}</TableCell>
                <TableCell style={D_CELL}>{c.subject}</TableCell>
                <TableCell style={D_CELL}><StatusPill status={c.status} theme={theme} /></TableCell>
                <TableCell style={D_CELL}><StatusPill status={c.priority} theme={theme} /></TableCell>
                <TableCell style={D_CELL}>{c.account_name || '—'}</TableCell>
                <TableCell style={D_CELL}>{fmtDate(c.created_date)}</TableCell>
                <TableCell style={D_CELL}><button title="Edit" onClick={() => openEdit(c)} className="slds-edit-btn" style={{ width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer', color: t.textWeak, fontSize: '14px', padding: 0 }}>✏️</button></TableCell>
              </TableRow>
              {editingId === c.id && <InlineFormRow colSpan={8} title="✏️ Edit Case" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
              {expandedId === c.id && (
                <TableRow>
                  <TableCell colSpan={8} style={{ padding: 0, background: theme === 'dark' ? '#142a50' : '#f8f9fb' }}>
                    <div style={{ padding: '8px 28px 12px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: t.textWeak, marginBottom: '6px' }}>Case Comments</div>
                      {loadingChild === c.id ? <Spinner size="tiny" label="Loading comments…" /> : (
                        (childComments[c.id] || []).length === 0 ? <div style={{ color: t.textWeak, fontSize: '12px', padding: '8px 0' }}>No comments.</div> :
                          (childComments[c.id] || []).map((cm: any, i: number) => (
                            <div key={cm.id || i} style={{ padding: '8px', marginBottom: '6px', borderRadius: '4px', background: theme === 'dark' ? '#1a3a65' : '#fff', border: `1px solid ${t.border}` }}>
                              <div style={{ fontSize: '11px', color: t.textWeak, marginBottom: '4px' }}>{cm.created_by_name || 'System'} · {fmtDate(cm.created_date)}</div>
                              <div style={{ fontSize: '12px', color: t.text }}>{cm.body}</div>
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
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── TasksView ──────────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function TasksView({ items: initItems, callTool, toast, theme }: { items: any[]; callTool: (n: string, a?: any) => Promise<any>; toast: (m: string, t?: any) => void; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const [localItems, setLocalItems] = useState(initItems);
  const [filterStatus, setFilterStatus] = useState('');
  const [filtering, setFiltering] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [form, setForm] = useState({ subject: '', status: '', priority: '', activity_date: '', description: '' });

  useEffect(() => setLocalItems(initItems), [initItems]);

  const doSearch = async () => {
    setFiltering(true);
    try { const res = await callTool('search_tasks', { status: filterStatus }); setLocalItems(res?.items || []); }
    finally { setFiltering(false); }
  };

  const openEdit = (t2: any) => { setCreating(false); setEditingId(t2.id); setForm({ subject: t2.subject || '', status: t2.status || '', priority: t2.priority || '', activity_date: t2.activity_date || '', description: t2.description || '' }); };
  const openCreate = () => { setEditingId(null); setCreating(true); setForm({ subject: '', status: 'Not Started', priority: 'Normal', activity_date: '', description: '' }); };
  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) { await callTool('create_task', form); toast('✓ Task created'); }
      else { await callTool('update_task', { task_id: editingId, ...form }); toast('✓ Task updated'); setLastSavedId(editingId); }
      cancel();
    } catch (e: any) { toast(e.message || 'Failed', 'error'); }
    finally { setSaving(false); }
  };

  useEffect(() => { if (lastSavedId) { const x = setTimeout(() => setLastSavedId(null), 1600); return () => clearTimeout(x); } }, [lastSavedId]);

  const setF = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));
  const fFields = (f: typeof form) => [
    { label: 'Subject *', key: 'subject', value: f.subject, onChange: (v: string) => setF('subject', v) },
    { label: 'Status', key: 'status', value: f.status, onChange: (v: string) => setF('status', v), type: 'select' as const, options: TASK_STATUSES },
    { label: 'Priority', key: 'priority', value: f.priority, onChange: (v: string) => setF('priority', v), type: 'select' as const, options: TASK_PRIOS },
    { label: 'Due Date', key: 'activity_date', value: f.activity_date, onChange: (v: string) => setF('activity_date', v), inputType: 'date' },
    { label: 'Description', key: 'description', value: f.description, onChange: (v: string) => setF('description', v) },
  ];

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="✅" title="Tasks" count={localItems.length} brand="#2E844A" onNew={openCreate} newLabel="+ New Task" theme={theme} />
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '8px 12px', flexWrap: 'wrap', borderBottom: `1px solid ${t.border}`, background: theme === 'dark' ? '#1a3a65' : '#FAFAF9' }}>
        <FormSelect label="" value={filterStatus} options={TASK_STATUSES} onChange={setFilterStatus} theme={theme} />
        <Button size="small" appearance="primary" icon={filtering ? <Spinner size="tiny" /> : <SearchRegular />} onClick={doSearch} disabled={filtering}
          style={{ background: t.brand, borderColor: t.brand, height: '30px', minWidth: '80px' }}>Search</Button>
      </div>
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            {['Subject', 'Status', 'Priority', 'Due Date', 'Related To', ''].map(h => <TableHeaderCell key={h} style={{ ...H_CELL, color: t.textWeak }}>{h}</TableHeaderCell>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && <InlineFormRow colSpan={6} title="➕ New Task" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
          {localItems.length === 0 && !creating && <TableRow><TableCell colSpan={6} className={styles.empty}><Text>No tasks found.</Text></TableCell></TableRow>}
          {localItems.map((t2: any) => (
            <React.Fragment key={t2.id}>
              <TableRow style={{ borderBottom: `1px solid ${t.border}`, ...(lastSavedId === t2.id ? { animation: 'sfRowFlash 1.5s ease-out' } : {}) }}>
                <TableCell style={D_CELL}>{t2.subject}</TableCell>
                <TableCell style={D_CELL}><StatusPill status={t2.status} theme={theme} /></TableCell>
                <TableCell style={D_CELL}><StatusPill status={t2.priority} theme={theme} /></TableCell>
                <TableCell style={D_CELL}>{fmtDate(t2.activity_date)}</TableCell>
                <TableCell style={D_CELL}>{t2.what_name || t2.who_name || '—'}</TableCell>
                <TableCell style={D_CELL}><button title="Edit" onClick={() => openEdit(t2)} className="slds-edit-btn" style={{ width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer', color: t.textWeak, fontSize: '14px', padding: 0 }}>✏️</button></TableCell>
              </TableRow>
              {editingId === t2.id && <InlineFormRow colSpan={6} title="✏️ Edit Task" fields={fFields(form)} onSave={handleSave} onCancel={cancel} saving={saving} theme={theme} />}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── CampaignsView ──────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function CampaignsView({ items, callTool, theme }: { items: any[]; callTool: (n: string, a?: any) => Promise<any>; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [childLeads, setChildLeads] = useState<Record<string, any[]>>({});
  const [loadingChild, setLoadingChild] = useState<string | null>(null);

  const toggleExpand = async (id: string) => {
    if (expandedId === id) { setExpandedId(null); return; }
    setExpandedId(id);
    if (childLeads[id]) return;
    setLoadingChild(id);
    try { const res = await callTool('get_campaign_leads', { campaign_id: id }); setChildLeads(p => ({ ...p, [id]: res?.items || [] })); }
    catch { setChildLeads(p => ({ ...p, [id]: [] })); }
    finally { setLoadingChild(null); }
  };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="📣" title="Campaigns" count={items.length} brand="#6B5B95" theme={theme} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={{ ...H_CELL, width: 28, color: t.textWeak }} />
            {['Name', 'Status', 'Type', 'Start', 'End', '# Leads'].map(h => <TableHeaderCell key={h} style={{ ...H_CELL, color: t.textWeak }}>{h}</TableHeaderCell>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.length === 0 && <TableRow><TableCell colSpan={7} className={styles.empty}><Text>No campaigns found.</Text></TableCell></TableRow>}
          {items.map((c: any) => (
            <React.Fragment key={c.id}>
              <TableRow style={{ borderBottom: `1px solid ${t.border}` }}>
                <TableCell style={{ ...D_CELL, width: 28 }}><ExpandToggle expanded={expandedId === c.id} onClick={() => toggleExpand(c.id)} theme={theme} /></TableCell>
                <TableCell style={D_CELL}><span style={{ fontWeight: 500 }}>{c.name}</span></TableCell>
                <TableCell style={D_CELL}><StatusPill status={c.status} theme={theme} /></TableCell>
                <TableCell style={D_CELL}>{c.type || '—'}</TableCell>
                <TableCell style={D_CELL}>{fmtDate(c.start_date)}</TableCell>
                <TableCell style={D_CELL}>{fmtDate(c.end_date)}</TableCell>
                <TableCell style={D_CELL}>{c.number_of_leads ?? '—'}</TableCell>
              </TableRow>
              {expandedId === c.id && (
                <TableRow>
                  <TableCell colSpan={7} style={{ padding: 0, background: theme === 'dark' ? '#142a50' : '#f8f9fb' }}>
                    <div style={{ padding: '8px 28px 12px' }}>
                      <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: t.textWeak, marginBottom: '6px' }}>Campaign Leads</div>
                      {loadingChild === c.id ? <Spinner size="tiny" label="Loading leads…" /> : (
                        (childLeads[c.id] || []).length === 0 ? <div style={{ color: t.textWeak, fontSize: '12px', padding: '8px 0' }}>No leads in this campaign.</div> :
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                            <thead><tr>{['Name', 'Company', 'Status', 'Email'].map(h => <th key={h} style={{ ...H_CELL, color: t.textWeak, textAlign: 'left' }}>{h}</th>)}</tr></thead>
                            <tbody>{(childLeads[c.id] || []).map((l: any) => (
                              <tr key={l.id} style={{ borderBottom: `1px solid ${t.border}` }}>
                                <td style={D_CELL}>{l.first_name} {l.last_name}</td>
                                <td style={D_CELL}>{l.company || '—'}</td>
                                <td style={D_CELL}><StatusPill status={l.status} theme={theme} /></td>
                                <td style={D_CELL}>{l.email || '—'}</td>
                              </tr>
                            ))}</tbody>
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
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── ApprovalsView ──────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function ApprovalsView({ items, theme }: { items: any[]; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="⏳" title="Pending Approvals" count={items.length} brand="#DD7A01" theme={theme} />
      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            {['Record', 'Type', 'Submitted By', 'Status', 'Created'].map(h => <TableHeaderCell key={h} style={{ ...H_CELL, color: t.textWeak }}>{h}</TableHeaderCell>)}
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.length === 0 && <TableRow><TableCell colSpan={5} className={styles.empty}><Text>No pending approvals.</Text></TableCell></TableRow>}
          {items.map((a: any) => (
            <TableRow key={a.id} style={{ borderBottom: `1px solid ${t.border}` }}>
              <TableCell style={{ ...D_CELL, fontWeight: 500 }}>{a.target_name || a.id}</TableCell>
              <TableCell style={D_CELL}>{a.target_type || '—'}</TableCell>
              <TableCell style={D_CELL}>{a.submitted_by || '—'}</TableCell>
              <TableCell style={D_CELL}><StatusPill status={a.status || 'Pending'} theme={theme} /></TableCell>
              <TableCell style={D_CELL}>{fmtDate(a.created_date)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── SalesDashboardView ─────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function SalesDashboardView({ data, theme }: { data: SalesDashboardData; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const maxAmt = Math.max(...(data.pipeline_by_stage || []).map((s: any) => s.amount || 0), 1);
  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="📊" title="Sales Dashboard" count={0} brand={t.brand} theme={theme} />
      <div style={{ padding: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '12px', marginBottom: '16px' }}>
          {[
            { label: 'Closed Won', value: fmt$(data.closed_won_this_month), color: '#2E844A' },
            { label: 'Closed Lost', value: fmt$(data.closed_lost_this_month), color: '#BA0517' },
            { label: 'Pipeline Stages', value: String(data.pipeline_by_stage?.length || 0), color: t.brand },
          ].map(k => (
            <div key={k.label} style={{ borderRadius: '6px', padding: '12px', background: theme === 'dark' ? '#1a3a65' : '#f3f3f3', textAlign: 'center', border: `1px solid ${t.border}` }}>
              <div style={{ fontSize: '11px', color: t.textWeak, marginBottom: '4px' }}>{k.label}</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: k.color }}>{k.value}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '10px' }}>Pipeline by Stage (Amount)</div>
            {(data.pipeline_by_stage || []).map((s: any) => (
              <DashBar key={s.stage} label={s.stage} value={s.amount || 0} max={maxAmt} color={t.brand} theme={theme} />
            ))}
          </div>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '10px' }}>Top Accounts</div>
            {(data.top_accounts || []).map((a: any, i: number) => (
              <div key={a.id || i} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: `1px solid ${t.border}`, fontSize: '12px' }}>
                <span style={{ color: t.text }}>{a.name}</span>
                <span style={{ color: t.brand, fontWeight: 600 }}>{fmt$(a.amount)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── SupportDashboardView ───────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function SupportDashboardView({ data, theme }: { data: SupportDashboardData; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const maxStatus = Math.max(...(data.by_status || []).map((s: any) => s.count || 0), 1);
  const maxPrio   = Math.max(...(data.by_priority || []).map((p: any) => p.count || 0), 1);
  const prioColors: Record<string, string> = { Low: '#2E844A', Medium: t.brand, High: '#DD7A01', Critical: '#BA0517' };
  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <ViewHeader icon="🛡️" title="Support Dashboard" count={0} brand="#706E6B" theme={theme} />
      <div style={{ padding: '16px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '12px', marginBottom: '16px' }}>
          {[
            { label: 'Total Open', value: String(data.total_open || 0), color: t.brand },
            { label: 'Opened This Month', value: String(data.opened_this_month || 0), color: '#DD7A01' },
          ].map(k => (
            <div key={k.label} style={{ borderRadius: '6px', padding: '12px', background: theme === 'dark' ? '#1a3a65' : '#f3f3f3', textAlign: 'center', border: `1px solid ${t.border}` }}>
              <div style={{ fontSize: '11px', color: t.textWeak, marginBottom: '4px' }}>{k.label}</div>
              <div style={{ fontSize: '22px', fontWeight: 700, color: k.color }}>{k.value}</div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '10px' }}>By Status</div>
            {(data.by_status || []).map((s: any) => <DashBar key={s.status} label={s.status} value={s.count || 0} max={maxStatus} color={t.brand} theme={theme} />)}
          </div>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '10px' }}>By Priority</div>
            {(data.by_priority || []).map((p: any) => <DashBar key={p.priority} label={p.priority} value={p.count || 0} max={maxPrio} color={prioColors[p.priority] || t.brand} theme={theme} />)}
          </div>
        </div>
      </div>
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── FormView (standalone – from show_create_form tool) ─────────────────────
// ────────────────────────────────────────────────────────────────────────────
const FORM_DEFS: Record<string, { label: string; key: string; required?: boolean; type?: 'select'; options?: string[]; inputType?: string }[]> = {
  lead: [
    { label: 'First Name', key: 'first_name' }, { label: 'Last Name *', key: 'last_name', required: true },
    { label: 'Company *', key: 'company', required: true }, { label: 'Email', key: 'email', inputType: 'email' },
    { label: 'Phone', key: 'phone' }, { label: 'Status', key: 'status', type: 'select', options: LEAD_STATUSES },
    { label: 'Lead Source', key: 'lead_source', type: 'select', options: LEAD_SOURCES },
  ],
  account: [
    { label: 'Account Name *', key: 'name', required: true }, { label: 'Industry', key: 'industry', type: 'select', options: ACCT_INDUSTRIES },
    { label: 'Phone', key: 'phone' }, { label: 'Website', key: 'website' },
    { label: 'Type', key: 'type', type: 'select', options: ACCT_TYPES }, { label: 'City', key: 'billing_city' },
  ],
  contact: [
    { label: 'First Name', key: 'first_name' }, { label: 'Last Name *', key: 'last_name', required: true },
    { label: 'Email', key: 'email', inputType: 'email' }, { label: 'Phone', key: 'phone' },
    { label: 'Title', key: 'title' }, { label: 'Account Name', key: 'account_name' },
  ],
  opportunity: [
    { label: 'Name *', key: 'name', required: true }, { label: 'Account Name', key: 'account_name' },
    { label: 'Stage', key: 'stage', type: 'select', options: OPP_STAGES }, { label: 'Amount ($)', key: 'amount', inputType: 'number' },
    { label: 'Close Date', key: 'close_date', inputType: 'date' }, { label: 'Probability (%)', key: 'probability', inputType: 'number' },
  ],
  case: [
    { label: 'Subject *', key: 'subject', required: true }, { label: 'Status', key: 'status', type: 'select', options: CASE_STATUSES },
    { label: 'Priority', key: 'priority', type: 'select', options: CASE_PRIOS }, { label: 'Account', key: 'account_name' },
    { label: 'Description', key: 'description' },
  ],
  task: [
    { label: 'Subject *', key: 'subject', required: true }, { label: 'Status', key: 'status', type: 'select', options: TASK_STATUSES },
    { label: 'Priority', key: 'priority', type: 'select', options: TASK_PRIOS }, { label: 'Due Date', key: 'activity_date', inputType: 'date' },
    { label: 'Description', key: 'description' },
  ],
};

const FORM_TOOL: Record<string, string> = { lead: 'create_lead', account: 'create_account', contact: 'create_contact', opportunity: 'create_opportunity', case: 'create_case', task: 'create_task' };
const FORM_ICONS: Record<string, string> = { lead: '👤', account: '🏢', contact: '👥', opportunity: '💰', case: '🎫', task: '✅' };

function FormView({ entity, prefill, callTool, toast, theme }: { entity: string; prefill?: Record<string, string>; callTool: (n: string, a?: any) => Promise<any>; toast: (m: string, t?: any) => void; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const fields = FORM_DEFS[entity] || [];
  const [values, setValues] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    fields.forEach(f => { init[f.key] = prefill?.[f.key] || ''; });
    return init;
  });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const set = (k: string, v: string) => setValues(p => ({ ...p, [k]: v }));

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const args: Record<string, string> = {};
      fields.forEach(f => { if (values[f.key]) args[f.key] = values[f.key]; });
      await callTool(FORM_TOOL[entity] || `create_${entity}`, args);
      toast(`${entity.charAt(0).toUpperCase() + entity.slice(1)} created!`, 'success');
      setDone(true);
    } catch (e: any) { toast(e?.message || 'Failed to create.', 'error'); }
    finally { setSubmitting(false); }
  };

  const handleReset = () => {
    const init: Record<string, string> = {};
    fields.forEach(f => { init[f.key] = ''; });
    setValues(init);
    setDone(false);
  };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}`, background: t.surface }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', background: `linear-gradient(135deg, ${t.brand}, ${t.brandHover})` }}>
        <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{FORM_ICONS[entity] || '✨'} New {entity.charAt(0).toUpperCase() + entity.slice(1)}</span>
        <ExpandButton />
      </div>
      {done ? (
        <div style={{ padding: '32px 16px', textAlign: 'center' }}>
          <div style={{ fontSize: '36px', marginBottom: '12px' }}>✅</div>
          <Text weight="semibold" size={400} style={{ color: t.text }}>{entity.charAt(0).toUpperCase() + entity.slice(1)} created successfully!</Text>
          <div style={{ marginTop: '16px' }}>
            <Button appearance="primary" onClick={handleReset} style={{ background: t.brand, borderColor: t.brand, color: '#fff' }}>Create Another</Button>
          </div>
        </div>
      ) : (
        <div style={{ padding: '16px' }}>
          <div className={styles.formGrid}>
            {fields.map(f =>
              f.type === 'select' ? (
                <FormSelect key={f.key} label={f.label} value={values[f.key]} options={f.options || []} onChange={v => set(f.key, v)} theme={theme} />
              ) : (
                <Field key={f.key} label={f.label} size="small">
                  <Input size="small" type={f.inputType || 'text'} value={values[f.key]} onChange={(_, d) => set(f.key, d.value)} style={{ background: t.surface, color: t.text }} />
                </Field>
              )
            )}
          </div>
          <div className={styles.formActions}>
            <Button size="small" appearance="subtle" onClick={handleReset} style={{ color: t.textWeak }}>Cancel</Button>
            <Button size="small" appearance="primary" onClick={handleSubmit} disabled={submitting}
              style={{ background: t.brand, borderColor: t.brand, color: '#fff', minWidth: '90px' }}>
              {submitting ? <Spinner size="tiny" /> : 'Submit'}
            </Button>
          </div>
        </div>
      )}
      <SldsFooter theme={theme} />
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// ── DetailView (legacy) ────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
function DetailField({ label, value, theme }: { label: string; value?: string | number | null; theme: 'light' | 'dark' }) {
  const t = slds(theme);
  if (!value && value !== 0) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
      <span style={{ fontSize: '10px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px', color: t.textWeak }}>{label}</span>
      <span style={{ fontSize: '13px', color: t.text, wordBreak: 'break-word' }}>{String(value)}</span>
    </div>
  );
}

function DetailView({ type, record, theme }: { type: 'lead_detail' | 'case_detail' | 'task_detail'; record: LeadDetail | CaseDetail | TaskDetail; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const icons = { lead_detail: '👤', case_detail: '🎫', task_detail: '✅' };
  const labels = { lead_detail: 'Lead Detail', case_detail: 'Case Detail', task_detail: 'Task Detail' };
  const title = type === 'lead_detail' ? `${(record as LeadDetail).first_name} ${(record as LeadDetail).last_name}`.trim() || '—'
    : type === 'case_detail' ? `${(record as CaseDetail).case_number} — ${(record as CaseDetail).subject}`
    : (record as TaskDetail).subject;
  const fields: { label: string; value?: string | number | null }[] =
    type === 'lead_detail' ? [
      { label: 'Company', value: (record as LeadDetail).company }, { label: 'Email', value: (record as LeadDetail).email },
      { label: 'Phone', value: (record as LeadDetail).phone }, { label: 'Status', value: (record as LeadDetail).status },
      { label: 'Lead Source', value: (record as LeadDetail).lead_source }, { label: 'Title', value: (record as LeadDetail).title },
      { label: 'Revenue', value: (record as LeadDetail).annual_revenue != null ? '$' + Number((record as LeadDetail).annual_revenue).toLocaleString() : null },
      { label: 'Created', value: (record as LeadDetail).created_date }, { label: 'Description', value: (record as LeadDetail).description },
    ] : type === 'case_detail' ? [
      { label: 'Status', value: (record as CaseDetail).status }, { label: 'Priority', value: (record as CaseDetail).priority },
      { label: 'Account', value: (record as CaseDetail).account_name }, { label: 'Origin', value: (record as CaseDetail).origin },
      { label: 'Created', value: (record as CaseDetail).created_date }, { label: 'Closed', value: (record as CaseDetail).closed_date },
      { label: 'Description', value: (record as CaseDetail).description }, { label: 'Comments', value: (record as CaseDetail).comments },
    ] : [
      { label: 'Status', value: (record as TaskDetail).status }, { label: 'Priority', value: (record as TaskDetail).priority },
      { label: 'Due Date', value: (record as TaskDetail).activity_date }, { label: 'Related To', value: (record as TaskDetail).what_id },
      { label: 'Created', value: (record as TaskDetail).created_date }, { label: 'Description', value: (record as TaskDetail).description },
    ];

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 16px', background: t.brand }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '18px' }}>{icons[type]}</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>{labels[type]}</span>
        </div>
        <ExpandButton />
      </div>
      <div style={{ padding: '16px' }}>
        <div style={{ fontSize: '15px', fontWeight: 600, color: t.text, marginBottom: '16px' }}>{title}</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '14px 20px' }}>
          {fields.map(f => <DetailField key={f.label} label={f.label} value={f.value} theme={theme} />)}
        </div>
      </div>
      <SldsFooter theme={theme} />
    </div>
  );
}

// ── Global CSS ─────────────────────────────────────────────────────────────
const _styleId = 'slds-global-style';
if (typeof document !== 'undefined' && !document.getElementById(_styleId)) {
  const s = document.createElement('style');
  s.id = _styleId;
  s.textContent = `
    @keyframes sfRowFlash { 0%{background:#EBF7E6}100%{background:transparent} }
    .slds-row:hover { background: #F3F3F3; }
    [data-theme="dark"] .slds-row:hover { background: #1E4474; }
    .slds-edit-btn:hover { color: #0176D3 !important; border-color: #0176D3 !important; }
    .fui-Input:focus-within { box-shadow: 0 0 3px #0176D3; border-color: #0176D3; }
    select:focus { outline: none; box-shadow: 0 0 3px #0176D3; border-color: #0176D3 !important; }
  `;
  document.head.appendChild(s);
}

// ────────────────────────────────────────────────────────────────────────────
// ── Main App ───────────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────────────
export function SalesforceApp() {
  const styles = useStyles();
  const data = useToolData<SfData>();
  const { callTool } = useMcpBridge();
  const toast = useToast();
  const theme = useTheme();
  const t = slds(theme);
  const shellStyle: React.CSSProperties = { padding: '12px', fontSize: '12px' };

  if (!data) return <div className={styles.shell} style={shellStyle}><SkeletonTable /></div>;

  // ── Form (standalone create form from tool) ──
  if ((data as any).type === 'form') {
    const fd = data as any;
    return <div className={styles.shell} style={shellStyle}><FormView entity={fd.entity} prefill={fd.prefill} callTool={callTool} toast={toast} theme={theme} /></div>;
  }

  // ── Detail views ──
  if ((data as any).type === 'lead_detail' || (data as any).type === 'case_detail' || (data as any).type === 'task_detail') {
    const dd = data as SfDetailData;
    return <div className={styles.shell} style={shellStyle}><DetailView type={dd.type} record={dd.record as any} theme={theme} /></div>;
  }

  // ── Dashboards ──
  if ((data as any).type === 'sales_dashboard') {
    return <div className={styles.shell} style={shellStyle}><SalesDashboardView data={data as SalesDashboardData} theme={theme} /></div>;
  }
  if ((data as any).type === 'support_dashboard') {
    return <div className={styles.shell} style={shellStyle}><SupportDashboardView data={data as SupportDashboardData} theme={theme} /></div>;
  }

  // ── Error ──
  if ((data as any).error) {
    const ed = data as any;
    return (
      <div className={styles.shell} style={shellStyle}>
        <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
          <div style={{ display: 'flex', alignItems: 'center', padding: '10px 16px', background: t.brand }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>⚠️ Error</span>
          </div>
          <div style={{ padding: '12px 16px', background: theme === 'dark' ? '#3c1a1a' : '#FEF1EE', color: theme === 'dark' ? '#fe9f9b' : t.danger, borderLeft: `3px solid ${t.danger}`, fontSize: '13px', fontWeight: 500 }}>
            {ed.message || 'An unknown error occurred.'}
          </div>
          <SldsFooter theme={theme} />
        </div>
      </div>
    );
  }

  // ── List views ──
  const ld = data as SfListData;
  const items = ld.items || [];

  return (
    <div className={styles.shell} style={shellStyle}>
      {ld.type === 'accounts'     && <AccountsView     items={items} callTool={callTool} toast={toast} theme={theme} />}
      {ld.type === 'leads'        && <LeadsView        items={items} callTool={callTool} toast={toast} theme={theme} />}
      {ld.type === 'contacts'     && <ContactsView     items={items} callTool={callTool} toast={toast} theme={theme} />}
      {ld.type === 'opportunities'&& <OpportunitiesView items={items} callTool={callTool} toast={toast} theme={theme} />}
      {ld.type === 'cases'        && <CasesView        items={items} callTool={callTool} toast={toast} theme={theme} />}
      {ld.type === 'tasks'        && <TasksView        items={items} callTool={callTool} toast={toast} theme={theme} />}
      {ld.type === 'campaigns'    && <CampaignsView    items={items} callTool={callTool} theme={theme} />}
      {ld.type === 'approvals'    && <ApprovalsView    items={items} theme={theme} />}
    </div>
  );
}
