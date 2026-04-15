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
  tokens,
  makeStyles,
} from '@fluentui/react-components';
import { EditRegular, AddRegular } from '@fluentui/react-icons';
import { useToolData, useMcpBridge, useTheme } from '../shared/McpBridge';
import { ExpandButton } from '../shared/ExpandButton';
import { useToast } from '../shared/Toast';
import type { SfData, Lead, Opportunity } from './types';

// ── SLDS Color Tokens ───────────────────────────────────────────────────────
const SLDS_LIGHT = {
  brand: '#0176D3',
  brandHover: '#014486',
  accent: '#1B96FF',
  background: '#F3F3F3',
  surface: '#FFFFFF',
  text: '#181818',
  textWeak: '#706E6B',
  border: '#DDDBDA',
  headerBg: '#FAFAF9',
  success: '#2E844A',
  danger: '#BA0517',
};

const SLDS_DARK = {
  brand: '#1B96FF',
  brandHover: '#0176D3',
  accent: '#1B96FF',
  background: '#16325C',
  surface: '#1A3A65',
  text: '#F3F3F3',
  textWeak: '#A0B0C0',
  border: '#2D4B6D',
  headerBg: '#1A3A65',
  success: '#2E844A',
  danger: '#BA0517',
};

function slds(theme: 'light' | 'dark') {
  return theme === 'dark' ? SLDS_DARK : SLDS_LIGHT;
}

// ── Dropdown options ────────────────────────────────────────────────────────
const LEAD_STATUSES = ['Open - Not Contacted', 'Working - Contacted', 'Closed - Converted', 'Closed - Not Converted'];
const LEAD_SOURCES = ['Web', 'Phone Inquiry', 'Partner Referral', 'Purchased List', 'Other'];
const OPP_STAGES = ['Prospecting', 'Qualification', 'Needs Analysis', 'Proposal/Price Quote', 'Negotiation/Review', 'Closed Won', 'Closed Lost'];

// ── Status → pill style maps ────────────────────────────────────────────────────
type PillStyle = { background: string; color: string; border: string };
type PillStyleMap = { light: PillStyle; dark: PillStyle };

const STATUS_STYLES: Record<string, PillStyleMap> = {
  open:      { light: { background: '#EEF4FF', color: '#0176D3', border: '#B9D6F5' }, dark: { background: '#0b3573', color: '#8dc7ff', border: '#2b5797' } },
  contacted: { light: { background: '#FEF0CD', color: '#8C4B02', border: '#E4C546' }, dark: { background: '#5c3b0a', color: '#f5c451', border: '#8c6e2e' } },
  qualified: { light: { background: '#EBF7E6', color: '#2E844A', border: '#91DB8B' }, dark: { background: '#1a3a2a', color: '#7cd992', border: '#2e6a3e' } },
  closed:    { light: { background: '#FEF1EE', color: '#BA0517', border: '#FE9F9B' }, dark: { background: '#5c1a1a', color: '#fe9f9b', border: '#9c3030' } },
};

function getStatusKey(status: string): string {
  const s = status.toLowerCase();
  if (s.includes('not converted') || s.includes('lost')) return 'closed';
  if (s.includes('converted') || s.includes('won') || s.includes('qualified')) return 'qualified';
  if (s.includes('working') || s.includes('needs') || s.includes('proposal') || s.includes('negotiation')) return 'contacted';
  return 'open';
}

function formatAmount(val: number | null | undefined): string {
  if (val == null) return '—';
  return '$' + Number(val).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

// ── Styles ─────────────────────────────────────────────────────────────────
const useStyles = makeStyles({
  shell: {
    margin: '0 auto',
    padding: '12px',
    fontFamily: "'Salesforce Sans', 'Segoe UI', system-ui, -apple-system, sans-serif",
    fontSize: '13px',
  },
  card: {
    borderRadius: '4px',
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
    borderLeft: '3px solid #0176D3',
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
  amount: {
    fontWeight: 500 as any,
    fontVariantNumeric: 'tabular-nums',
  },
  probability: {
    fontSize: '12px',
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
});

// ── Status Pill ────────────────────────────────────────────────────────────
function StatusPill({ status, theme }: { status: string; theme: 'light' | 'dark' }) {
  const key = getStatusKey(status);
  const style = STATUS_STYLES[key]?.[theme] || STATUS_STYLES.open[theme];
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 10px',
      borderRadius: '15px',
      fontSize: '11px',
      fontWeight: 600,
      letterSpacing: '0.2px',
      background: style.background,
      color: style.color,
      border: `1px solid ${style.border}`,
    }}>
      {status || '—'}
    </span>
  );
}

// ── SLDS Footer ───────────────────────────────────────────────────────────
function SldsFooter({ theme }: { theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = slds(theme);
  const { openExternal } = useMcpBridge();
  return (
    <div className={styles.mcpFooter} style={{
      background: theme === 'dark' ? '#0f2440' : '#F3F3F3',
      borderTop: `1px solid ${t.border}`,
      color: t.textWeak,
    }}>
      <span>⚡ <strong>MCP Widget</strong> · Salesforce CRM</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ cursor: 'pointer', textDecoration: 'underline' }}
          onClick={() => openExternal('https://login.salesforce.com')}>
          Open in Salesforce ↗
        </span>
        <span>⚓ GTC</span>
      </div>
    </div>
  );
}

// ── Inline select (native) ────────────────────────────────────────────────────
function FormSelect({ label, value, options, onChange, theme }: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  theme: 'light' | 'dark';
}) {
  const t = slds(theme);
  return (
    <Field label={label} size="small">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: '100%',
          padding: '5px 8px',
          borderRadius: '4px',
          border: `1px solid ${t.border}`,
          background: t.surface,
          color: t.text,
          fontSize: '13px',
          fontFamily: 'inherit',
          height: '32px',
        }}
      >
        <option value="">— Select —</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </Field>
  );
}

// ── Leads View ────────────────────────────────────────────────────────────
function LeadsView({ items, callTool, toast, theme }: {
  items: Lead[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  theme: 'light' | 'dark';
}){
  const styles = useStyles();
  const t = slds(theme);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [form, setForm] = useState({
    first_name: '', last_name: '', company: '', email: '', phone: '', status: '', lead_source: '',
  });

  const openEdit = (lead: Lead) => {
    setCreating(false);
    setEditingId(lead.id);
    setForm({
      first_name: lead.first_name || '',
      last_name: lead.last_name || '',
      company: lead.company || '',
      email: lead.email || '',
      phone: lead.phone || '',
      status: lead.status || '',
      lead_source: lead.lead_source || '',
    });
  };

  const openCreate = () => {
    setEditingId(null);
    setCreating(true);
    setForm({ first_name: '', last_name: '', company: '', email: '', phone: '', status: '', lead_source: '' });
  };

  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) {
        await callTool('create_lead', { ...form });
        toast('✓ Record created successfully');
      } else {
        await callTool('update_lead', { lead_id: editingId, ...form });
        toast('✓ Record updated successfully');
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
      const t = setTimeout(() => setLastSavedId(null), 1600);
      return () => clearTimeout(t);
    }
  }, [lastSavedId]);

  const formBg = theme === 'dark' ? '#1a3050' : '#F3F3F3';

  const colSpan = 5;

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle',
  };

  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };

  const renderForm = (title: string) => (
    <TableRow>
      <TableCell colSpan={colSpan}style={{ padding: 0 }}>
        <div className={styles.formPanel} style={{
          background: formBg,
          borderColor: t.brand,
        }}>
          <div className={styles.formTitle} style={{ color: t.brand }}>{title}</div>
          <div className={styles.formGrid}>
            <Field label="First Name" size="small">
              <Input size="small" value={form.first_name} onChange={(_, d) => setForm(f => ({ ...f, first_name: d.value }))} />
            </Field>
            <Field label="Last Name" size="small">
              <Input size="small" value={form.last_name} onChange={(_, d) => setForm(f => ({ ...f, last_name: d.value }))} />
            </Field>
            <Field label="Company" size="small">
              <Input size="small" value={form.company} onChange={(_, d) => setForm(f => ({ ...f, company: d.value }))} />
            </Field>
            <Field label="Email" size="small">
              <Input size="small" type="email" value={form.email} onChange={(_, d) => setForm(f => ({ ...f, email: d.value }))} />
            </Field>
            <Field label="Phone" size="small">
              <Input size="small" type="tel" value={form.phone} onChange={(_, d) => setForm(f => ({ ...f, phone: d.value }))} />
            </Field>
            <FormSelect label="Status" value={form.status} options={LEAD_STATUSES} onChange={v => setForm(f => ({ ...f, status: v }))} theme={theme} />
            <FormSelect label="Lead Source" value={form.lead_source} options={LEAD_SOURCES} onChange={v => setForm(f => ({ ...f, lead_source: v }))} theme={theme} />
          </div>
          <div className={styles.formActions}>
            <Button appearance="secondary" size="small" onClick={cancel} disabled={saving}
              style={{ borderRadius: '4px', height: '32px', padding: '0 16px', border: `1px solid ${t.border}` }}>
              Cancel
            </Button>
            <Button appearance="primary" size="small" onClick={handleSave} disabled={saving}
              style={{ background: t.brand, borderColor: t.brand, borderRadius: '4px', height: '32px', padding: '0 16px' }}>
              {saving ? 'Saving…' : creating ? '✓ Create' : '✓ Save'}
            </Button>
          </div>
        </div>
      </TableCell>
    </TableRow>
  );
  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <div className={styles.headerBar} style={{ background: t.brand }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>🏛️</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Salesforce CRM — Trade Ledger</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
            {items.length} record{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <Button appearance="primary" size="small" icon={<AddRegular />}
            onClick={openCreate}
            style={{ background: 'rgba(255,255,255,0.15)', borderColor: 'rgba(255,255,255,0.3)', color: '#fff', borderRadius: '4px', height: '32px', padding: '0 16px' }}>
            + New Lead
          </Button>
          <ExpandButton />
        </div>
      </div>

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Name</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Company</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Status</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Source</TableHeaderCell>
            <TableHeaderCell style={{ ...headerCellStyle, width: 50 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && renderForm('➕ New Lead')}
          {items.length === 0 && !creating && (
            <TableRow>
              <TableCell colSpan={colSpan} className={styles.empty}>
                <Text>No leads found.</Text>
              </TableCell>
            </TableRow>
          )}
          {items.map((lead, idx) => (
            <React.Fragment key={lead.id}>
              <TableRow
                className="slds-row"
                style={{
                  borderBottom: idx === items.length - 1 ? 'none' : `1px solid ${t.border}`,
                  ...(lastSavedId === lead.id ? { animation: 'sfRowFlash 1.5s ease-out' } : {}),
                }}
              >
                <TableCell style={cellStyle}>{lead.first_name} {lead.last_name}</TableCell>
                <TableCell style={cellStyle}>{lead.company || '—'}</TableCell>
                <TableCell style={cellStyle}>
                  <StatusPill status={lead.status} theme={theme} />
                </TableCell>
                <TableCell style={cellStyle}>{lead.lead_source || '—'}</TableCell>
                <TableCell style={cellStyle}>
                  <button
                    title="Edit"
                    onClick={() => openEdit(lead)}
                    className="slds-edit-btn"
                    style={{
                      width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer',
                      color: t.textWeak, fontSize: '14px', padding: 0,
                    }}
                  >✏️</button>
                </TableCell>
              </TableRow>
              {editingId === lead.id && renderForm('✏️ Edit Lead')}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>

      <SldsFooter theme={theme} />
    </div>
  );
}

// ── Opportunities View ──────────────────────────────────────────────────────
function OpportunitiesView({ items, callTool, toast, theme }: {
  items: Opportunity[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
  theme: 'light' | 'dark';
}){
  const styles = useStyles();
  const t = slds(theme);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [lastSavedId, setLastSavedId] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: '', account_name: '', stage: '', amount: '', close_date: '', probability: '',
  });

  const openEdit = (opp: Opportunity) => {
    setCreating(false);
    setEditingId(opp.id);
    setForm({
      name: opp.name || '',
      account_name: opp.account_name || '',
      stage: opp.stage || '',
      amount: opp.amount != null ? String(opp.amount) : '',
      close_date: opp.close_date || '',
      probability: opp.probability != null ? String(opp.probability) : '',
    });
  };

  const openCreate = () => {
    setEditingId(null);
    setCreating(true);
    setForm({ name: '', account_name: '', stage: '', amount: '', close_date: '', probability: '' });
  };

  const cancel = () => { setEditingId(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      const args: Record<string, any> = {
        name: form.name,
        account_name: form.account_name,
        stage: form.stage,
        amount: form.amount ? parseFloat(form.amount) : null,
        close_date: form.close_date,
        probability: form.probability ? parseInt(form.probability) : null,
      };

      if (creating) {
        await callTool('create_opportunity', args);
        toast('✓ Record created successfully');
      } else {
        await callTool('update_opportunity', { opportunity_id: editingId, ...args });
        toast('✓ Record updated successfully');
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
      const t = setTimeout(() => setLastSavedId(null), 1600);
      return () => clearTimeout(t);
    }
  }, [lastSavedId]);

  const formBg = theme === 'dark' ? '#1a3050' : '#F3F3F3';

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: '12px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '180px', verticalAlign: 'middle',
  };

  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };

  const renderForm = (title: string) => (
    <TableRow>
      <TableCell colSpan={7} style={{ padding: 0 }}>
        <div className={styles.formPanel} style={{
          background: formBg,
          borderColor: t.brand,
        }}>
          <div className={styles.formTitle} style={{ color: t.brand }}>{title}</div>
          <div className={styles.formGrid}>
            <Field label="Opportunity Name" size="small">
              <Input size="small" value={form.name} onChange={(_, d) => setForm(f => ({ ...f, name: d.value }))} />
            </Field>
            <Field label="Account Name" size="small">
              <Input size="small" value={form.account_name} onChange={(_, d) => setForm(f => ({ ...f, account_name: d.value }))} />
            </Field>
            <FormSelect label="Stage" value={form.stage} options={OPP_STAGES} onChange={v => setForm(f => ({ ...f, stage: v }))} theme={theme} />
            <Field label="Amount ($)" size="small">
              <Input size="small" type="number" value={form.amount} onChange={(_, d) => setForm(f => ({ ...f, amount: d.value }))} />
            </Field>
            <Field label="Close Date" size="small">
              <Input size="small" type="date" value={form.close_date} onChange={(_, d) => setForm(f => ({ ...f, close_date: d.value }))} />
            </Field>
            <Field label="Probability (%)" size="small">
              <Input size="small" type="number" value={form.probability} onChange={(_, d) => setForm(f => ({ ...f, probability: d.value }))} />
            </Field>
          </div>
          <div className={styles.formActions}>
            <Button appearance="secondary" size="small" onClick={cancel} disabled={saving}
              style={{ borderRadius: '4px', height: '32px', padding: '0 16px', border: `1px solid ${t.border}` }}>
              Cancel
            </Button>
            <Button appearance="primary" size="small" onClick={handleSave} disabled={saving}
              style={{ background: t.brand, borderColor: t.brand, borderRadius: '4px', height: '32px', padding: '0 16px' }}>
              {saving ? 'Saving…' : creating ? '✓ Create' : '✓ Save'}
            </Button>
          </div>
        </div>
      </TableCell>
    </TableRow>
  );

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <div className={styles.headerBar} style={{ background: t.brand }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: '18px' }}>💰</span>
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Opportunities</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: '10px' }}>
            {items.length} record{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <Button appearance="primary" size="small" icon={<AddRegular />}
            onClick={openCreate}
            style={{ background: 'rgba(255,255,255,0.15)', borderColor: 'rgba(255,255,255,0.3)', color: '#fff', borderRadius: '4px', height: '32px', padding: '0 16px' }}>
            + New Opportunity
          </Button>
          <ExpandButton />
        </div>
      </div>

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Name</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Account</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Stage</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Amount</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Close Date</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Probability</TableHeaderCell>
            <TableHeaderCell style={{ ...headerCellStyle, width: 50 }} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {creating && renderForm('➕ New Opportunity')}
          {items.length === 0 && !creating && (
            <TableRow>
              <TableCell colSpan={7} className={styles.empty}>
                <Text>No opportunities found.</Text>
              </TableCell>
            </TableRow>
          )}
          {items.map((opp, idx) => (
            <React.Fragment key={opp.id}>
              <TableRow
                className="slds-row"
                style={{
                  borderBottom: idx === items.length - 1 ? 'none' : `1px solid ${t.border}`,
                  ...(lastSavedId === opp.id ? { animation: 'sfRowFlash 1.5s ease-out' } : {}),
                }}
              >
                <TableCell style={cellStyle}>{opp.name}</TableCell>
                <TableCell style={cellStyle}>{opp.account_name || '—'}</TableCell>
                <TableCell style={cellStyle}>
                  <StatusPill status={opp.stage} theme={theme} />
                </TableCell>
                <TableCell style={cellStyle}>
                  <span className={styles.amount}>{formatAmount(opp.amount)}</span>
                </TableCell>
                <TableCell style={cellStyle}>{opp.close_date || '—'}</TableCell>
                <TableCell style={cellStyle}>
                  <span className={styles.probability}>{opp.probability != null ? opp.probability + '%' : '—'}</span>
                </TableCell>
                <TableCell style={cellStyle}>
                  <button
                    title="Edit"
                    onClick={() => openEdit(opp)}
                    className="slds-edit-btn"
                    style={{
                      width: '28px', height: '28px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                      border: `1px solid ${t.border}`, borderRadius: '4px', background: 'transparent', cursor: 'pointer',
                      color: t.textWeak, fontSize: '14px', padding: 0,
                    }}
                  >✏️</button>
                </TableCell>
              </TableRow>
              {editingId === opp.id && renderForm('✏️ Edit Opportunity')}
            </React.Fragment>
          ))}
        </TableBody>
      </Table>

      <SldsFooter theme={theme} />
    </div>
  );
}

// ── Global CSS for SLDS ──────────────────────────────────────────────────────
const sldsStyleId = 'slds-global-style';
if (typeof document !== 'undefined' && !document.getElementById(sldsStyleId)) {
  const style = document.createElement('style');
  style.id = sldsStyleId;
  style.textContent = `
    @keyframes sfRowFlash {
      0%   { background: #EBF7E6; }
      100% { background: transparent; }
    }
    [data-theme="dark"] .slds-row:hover,
    .fui-FluentProvider[data-theme="dark"] .slds-row:hover {
      background: #1E4474;
    }
    .slds-row:hover {
      background: #F3F3F3;
    }
    .slds-edit-btn:hover {
      color: #0176D3 !important;
      border-color: #0176D3 !important;
    }
    /* SLDS input focus */
    .fui-Input:focus-within {
      box-shadow: 0 0 3px #0176D3;
      border-color: #0176D3;
    }
    select:focus {
      outline: none;
      box-shadow: 0 0 3px #0176D3;
      border-color: #0176D3 !important;
    }
  `;
  document.head.appendChild(style);
}

// ── Skeleton Loading Shimmer ──────────────────────────────────────────────
function SkeletonTable() {
  return (
    <div style={{ padding: '16px' }}>
      <style>{`
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
        [data-theme="dark"] .skel {
          background: linear-gradient(90deg, #333 25%, #444 50%, #333 75%);
          background-size: 200% 100%;
        }
      `}</style>
      {/* Header skeleton */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <div className="skel" style={{ width: '200px', height: '24px' }} />
        <div className="skel" style={{ width: '80px', height: '24px' }} />
      </div>
      {/* Row skeletons */}
      {[1, 2, 3, 4, 5].map(i => (
        <div key={i} style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
          <div className="skel" style={{ width: '120px' }} />
          <div className="skel" style={{ width: '150px' }} />
          <div className="skel" style={{ width: '180px' }} />
          <div className="skel" style={{ width: '100px' }} />
          <div className="skel" style={{ width: '90px' }} />
        </div>
      ))}
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────
export function SalesforceApp() {
  const styles = useStyles();
  const data = useToolData<SfData>();
  const { callTool } = useMcpBridge();
  const toast = useToast();
  const theme = useTheme();
  const t = slds(theme);

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
          <div className={styles.headerBar} style={{ background: t.brand }}>
            <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>⚠️ Error</span>
          </div>
          <div className={styles.errorBanner} style={{
            background: theme === 'dark' ? '#3c1a1a' : '#FEF1EE',
            color: theme === 'dark' ? '#fe9f9b' : t.danger,
            borderLeft: `3px solid ${t.danger}`,
          }}>
            {data.message || 'An unknown error occurred.'}
          </div>
          <SldsFooter theme={theme} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.shell} style={shellStyle}>
      {data.type === 'leads' && (
        <LeadsView
          items={(data.items || []) as Lead[]}
          callTool={callTool}
          toast={toast}
          theme={theme}
        />
      )}
      {data.type === 'opportunities' && (
        <OpportunitiesView
          items={(data.items || []) as Opportunity[]}
          callTool={callTool}
          toast={toast}
          theme={theme}
        />
      )}
    </div>
  );
}


