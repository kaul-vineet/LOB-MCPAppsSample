import React, { useState } from 'react';
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
  DsData,
  Envelope,
  EnvelopeDetail,
  Template,
} from './types';

// ── DocuSign Color Tokens ───────────────────────────────────────────────────
const DS_LIGHT = {
  brand: '#4C00FF',
  brandHover: '#3a0099',
  accent: '#7B2FFF',
  background: '#ffffff',
  surface: '#f8f9fa',
  text: '#1a1a2e',
  textWeak: '#6c757d',
  border: '#e0e0e0',
  headerBg: '#f8f9fa',
  success: '#28a745',
  danger: '#dc3545',
  warning: '#ffc107',
};

const DS_DARK = {
  brand: '#7B2FFF',
  brandHover: '#4C00FF',
  accent: '#9B5FFF',
  background: '#1a1a2e',
  surface: '#16213e',
  text: '#eaeaea',
  textWeak: '#a0a0b0',
  border: '#2a2a4a',
  headerBg: '#16213e',
  success: '#28a745',
  danger: '#dc3545',
  warning: '#ffc107',
};

function ds(theme: 'light' | 'dark') {
  return theme === 'dark' ? DS_DARK : DS_LIGHT;
}

function headerGradient(theme: 'light' | 'dark') {
  return theme === 'dark'
    ? 'linear-gradient(135deg, #3a0099 0%, #1a0044 100%)'
    : 'linear-gradient(135deg, #4C00FF 0%, #7B2FFF 100%)';
}

// ── Status badge colors ─────────────────────────────────────────────────────
type BadgeStyle = { bg: string; color: string };
const STATUS_BADGE: Record<string, { light: BadgeStyle; dark: BadgeStyle }> = {
  created:   { light: { bg: '#e3e8f0', color: '#4a5568' }, dark: { bg: '#2d3748', color: '#a0aec0' } },
  sent:      { light: { bg: '#dbeafe', color: '#1e40af' }, dark: { bg: '#1e3a5f', color: '#90cdf4' } },
  delivered: { light: { bg: '#fef3c7', color: '#92400e' }, dark: { bg: '#5a4e1e', color: '#fbd38d' } },
  signed:    { light: { bg: '#d1fae5', color: '#065f46' }, dark: { bg: '#1a4731', color: '#9ae6b4' } },
  completed: { light: { bg: '#c6f6d5', color: '#22543d' }, dark: { bg: '#1c4532', color: '#9ae6b4' } },
  declined:  { light: { bg: '#fed7d7', color: '#9b2c2c' }, dark: { bg: '#4a1c1c', color: '#feb2b2' } },
  voided:    { light: { bg: '#e2e8f0', color: '#718096' }, dark: { bg: '#2d3748', color: '#a0aec0' } },
};

function badgeStyle(status: string, theme: 'light' | 'dark'): BadgeStyle {
  const key = (status || '').toLowerCase();
  return STATUS_BADGE[key]?.[theme] ?? STATUS_BADGE.created[theme];
}

// ── Pipeline stages ─────────────────────────────────────────────────────────
const STAGES = ['created', 'sent', 'delivered', 'signed', 'completed', 'declined', 'voided'] as const;
const STAGE_EMOJIS: Record<string, string> = {
  created: '📝', sent: '📤', delivered: '📬', signed: '✍️',
  completed: '✅', declined: '❌', voided: '🚫',
};

// ── Styles ─────────────────────────────────────────────────────────────────
const useStyles = makeStyles({
  shell: {
    margin: '0 auto',
    padding: '12px',
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
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
  pipeline: {
    display: 'flex',
    gap: '4px',
    padding: '8px',
    borderRadius: '8px',
    marginBottom: '12px',
  },
  stage: {
    flex: '1 1 0',
    textAlign: 'center' as const,
    padding: '8px 4px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: 600 as any,
    cursor: 'default',
    transition: 'all 0.2s',
  },
  stageCount: {
    fontSize: '18px',
    fontWeight: 700 as any,
    display: 'block',
  },
  stageLabel: {
    fontSize: '10px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  formPanel: {
    padding: '16px',
    borderLeft: '3px solid #4C00FF',
  },
  formTitle: {
    fontSize: '15px',
    fontWeight: 600 as any,
    marginBottom: '12px',
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '10px 14px',
    marginBottom: '14px',
  },
  formActions: {
    display: 'flex',
    gap: '8px',
    justifyContent: 'flex-end',
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
  detailSection: {
    padding: '16px',
  },
  signerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 0',
  },
  templateCard: {
    padding: '12px',
    borderRadius: '8px',
    marginBottom: '8px',
  },
});

// ── Helpers ────────────────────────────────────────────────────────────────
function formatDate(d?: string): string {
  if (!d) return '—';
  return new Date(d).toLocaleDateString();
}

function formatDateTime(d?: string): string {
  if (!d) return '—';
  return new Date(d).toLocaleString();
}

function shortId(id?: string): string {
  return id ? id.substring(0, 8) + '…' : '—';
}

// ── Skeleton loader ───────────────────────────────────────────────────────
function SkeletonLoader() {
  const shimmerStyle: React.CSSProperties = {
    height: 16, borderRadius: 4, marginBottom: 8,
    background: 'linear-gradient(90deg, #e8e0ff 25%, #d4c5ff 50%, #e8e0ff 75%)',
    backgroundSize: '200% 100%',
    animation: 'dsShimmer 1.5s infinite',
  };
  return (
    <div style={{ padding: 16 }}>
      <style>{`@keyframes dsShimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`}</style>
      <div style={{ ...shimmerStyle, width: '80%' }} />
      <div style={{ ...shimmerStyle, width: '60%' }} />
      <div style={{ ...shimmerStyle, height: 120, width: '100%' }} />
      <div style={{ ...shimmerStyle, width: '40%' }} />
    </div>
  );
}

// ── Status Badge component ────────────────────────────────────────────────
function StatusBadge({ status, theme }: { status: string; theme: 'light' | 'dark' }) {
  const s = badgeStyle(status, theme);
  const emoji = STAGE_EMOJIS[(status || '').toLowerCase()] || '📄';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 12,
      fontSize: 11, fontWeight: 600,
      background: s.bg, color: s.color,
    }}>
      {emoji} {status}
    </span>
  );
}

// ── Footer ────────────────────────────────────────────────────────────────
function DsFooter({ theme }: { theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = ds(theme);
  const { openExternal } = useMcpBridge();
  return (
    <div className={styles.mcpFooter} style={{
      background: theme === 'dark' ? '#0f0f2e' : '#f8f9fa',
      borderTop: `1px solid ${t.border}`,
      color: t.textWeak,
    }}>
      <span>✒️ <strong>MCP Widget</strong> · DocuSign eSignature</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ cursor: 'pointer', textDecoration: 'underline' }}
          onClick={() => openExternal('https://app.docusign.com')}>
          Open in DocuSign ↗
        </span>
        <span>⚓ GTC</span>
      </div>
    </div>
  );
}

// ── Pipeline bar ──────────────────────────────────────────────────────────
function PipelineBar({ envelopes, theme }: { envelopes: Envelope[]; theme: 'light' | 'dark' }) {
  const styles = useStyles();
  const t = ds(theme);

  const counts: Record<string, number> = {};
  envelopes.forEach(e => {
    const s = (e.status || 'unknown').toLowerCase();
    counts[s] = (counts[s] || 0) + 1;
  });

  return (
    <div className={styles.pipeline} style={{
      background: t.surface, border: `1px solid ${t.border}`,
    }}>
      {STAGES.map(s => {
        const bs = badgeStyle(s, theme);
        const active = (counts[s] || 0) > 0;
        return (
          <div key={s} className={styles.stage} style={{
            background: bs.bg, color: bs.color,
            opacity: active ? 1 : 0.5,
            boxShadow: active ? '0 2px 8px rgba(0,0,0,0.12)' : 'none',
            transform: active ? 'translateY(-1px)' : 'none',
          }}>
            <span className={styles.stageCount}>{counts[s] || 0}</span>
            <span className={styles.stageLabel}>{STAGE_EMOJIS[s]} {s}</span>
          </div>
        );
      })}
    </div>
  );
}

// ── Envelopes View ────────────────────────────────────────────────────────
function EnvelopesView({ items, theme }: {
  items: Envelope[];
  theme: 'light' | 'dark';
}) {
  const styles = useStyles();
  const t = ds(theme);

  const cellStyle: React.CSSProperties = {
    padding: '6px 10px', fontSize: 12, whiteSpace: 'nowrap',
    overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 200, verticalAlign: 'middle',
  };
  const headerCellStyle: React.CSSProperties = {
    fontWeight: 700, fontSize: 10, textTransform: 'uppercase',
    letterSpacing: '0.5px', padding: '6px 10px', color: t.textWeak,
  };

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <div className={styles.headerBar} style={{ background: headerGradient(theme) }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: 20 }}>✒️</span>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>DocuSign Envelopes</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: 10 }}>
            {items.length} envelope{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <ExpandButton />
      </div>

      <div style={{ padding: '12px 12px 0' }}>
        <PipelineBar envelopes={items} theme={theme} />
      </div>

      <Table size="small" style={{ borderCollapse: 'collapse' }}>
        <TableHeader>
          <TableRow style={{ background: t.headerBg }}>
            <TableHeaderCell style={headerCellStyle}>Status</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Subject</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>Sent</TableHeaderCell>
            <TableHeaderCell style={headerCellStyle}>ID</TableHeaderCell>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className={styles.empty}>
                <Text>📭 No envelopes found</Text>
              </TableCell>
            </TableRow>
          )}
          {items.map((env, idx) => (
            <TableRow key={env.envelopeId || idx} style={{
              borderBottom: idx === items.length - 1 ? 'none' : `1px solid ${t.border}`,
            }}>
              <TableCell style={cellStyle}>
                <StatusBadge status={env.status} theme={theme} />
              </TableCell>
              <TableCell style={{ ...cellStyle, maxWidth: 220 }} title={env.emailSubject}>
                {env.emailSubject || '(no subject)'}
              </TableCell>
              <TableCell style={{ ...cellStyle, fontSize: 12, color: t.textWeak }}>
                {formatDate(env.sentDateTime)}
              </TableCell>
              <TableCell style={{ ...cellStyle, fontFamily: 'monospace', fontSize: 11, color: t.textWeak }}>
                {shortId(env.envelopeId)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <DsFooter theme={theme} />
    </div>
  );
}

// ── Envelope Detail View ──────────────────────────────────────────────────
function EnvelopeDetailView({ detail, theme }: {
  detail: EnvelopeDetail;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles();
  const t = ds(theme);

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <div className={styles.headerBar} style={{ background: headerGradient(theme) }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: 20 }}>{detail.statusEmoji || '📄'}</span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>
              {detail.emailSubject || 'Envelope Details'}
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.8)' }}>
              Status: {detail.status} · {detail.signers.length} signer(s)
            </div>
          </div>
        </div>
        <ExpandButton />
      </div>

      <div className={styles.detailSection} style={{ background: t.surface, borderBottom: `1px solid ${t.border}` }}>
        <Text weight="semibold" size={300} style={{ display: 'block', marginBottom: 10, color: t.text }}>
          Signers
        </Text>
        {detail.signers.length === 0 && (
          <Text style={{ color: t.textWeak, fontSize: 13 }}>No signers</Text>
        )}
        {detail.signers.map((s, i) => (
          <div key={i} className={styles.signerRow} style={{
            borderBottom: i < detail.signers.length - 1 ? `1px solid ${t.border}` : 'none',
          }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13, color: t.text }}>{s.name}</div>
              <div style={{ fontSize: 12, color: t.textWeak }}>{s.email}</div>
            </div>
            <StatusBadge status={s.status} theme={theme} />
          </div>
        ))}
      </div>

      <div style={{ padding: '10px 16px', fontSize: 12, color: t.textWeak }}>
        Sent: {formatDateTime(detail.sentDateTime)} ·
        Completed: {formatDateTime(detail.completedDateTime)}
      </div>

      <DsFooter theme={theme} />
    </div>
  );
}

// ── Templates View ────────────────────────────────────────────────────────
function TemplatesView({ items, theme }: {
  items: Template[];
  theme: 'light' | 'dark';
}) {
  const styles = useStyles();
  const t = ds(theme);

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <div className={styles.headerBar} style={{ background: headerGradient(theme) }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: 20 }}>📋</span>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>DocuSign Templates</span>
          <Badge appearance="filled" size="small"
            style={{ background: 'rgba(255,255,255,0.2)', color: '#fff', borderRadius: 10 }}>
            {items.length} template{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>
        <ExpandButton />
      </div>

      <div style={{ padding: 12 }}>
        {items.length === 0 && (
          <div className={styles.empty} style={{ color: t.textWeak }}>📋 No templates found</div>
        )}
        {items.map((tpl, i) => (
          <div key={tpl.templateId || i} className={styles.templateCard} style={{
            background: t.surface, border: `1px solid ${t.border}`,
          }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: t.text }}>{tpl.name}</div>
            <div style={{ fontSize: 12, color: t.textWeak, marginTop: 4 }}>
              {tpl.description || 'No description'}
            </div>
            <div style={{ fontSize: 11, color: t.textWeak, marginTop: 4 }}>
              ID: {shortId(tpl.templateId)} · Folder: {tpl.folderName || '—'}
            </div>
          </div>
        ))}
      </div>

      <DsFooter theme={theme} />
    </div>
  );
}

// ── Send Envelope Form ────────────────────────────────────────────────────
function SendEnvelopeForm({ prefill, theme }: {
  prefill?: Record<string, string>;
  theme: 'light' | 'dark';
}) {
  const styles = useStyles();
  const t = ds(theme);
  const { callTool } = useMcpBridge();
  const toast = useToast();

  const [form, setForm] = useState({
    template_id: prefill?.template_id || '',
    recipient_name: prefill?.recipient_name || '',
    recipient_email: prefill?.recipient_email || '',
    subject: prefill?.subject || '',
    email_body: prefill?.email_body || 'Please sign this document.',
  });
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = form.recipient_name.trim() && form.recipient_email.trim();

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      await callTool('ds__send_envelope', {
        template_id: form.template_id || undefined,
        subject: form.subject || `Signature Request for ${form.recipient_name}`,
        signers: [{ name: form.recipient_name, email: form.recipient_email, role_name: 'Signer' }],
        email_body: form.email_body,
      });
      toast('✅ Envelope sent successfully!');
      setForm({ template_id: '', recipient_name: '', recipient_email: '', subject: '', email_body: 'Please sign this document.' });
    } catch (e: any) {
      toast(e.message || 'Failed to send envelope', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setForm({ template_id: '', recipient_name: '', recipient_email: '', subject: '', email_body: 'Please sign this document.' });
  };

  const formBg = theme === 'dark' ? '#1a1a40' : '#f8f6ff';

  return (
    <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
      <div className={styles.headerBar} style={{ background: headerGradient(theme) }}>
        <div className={styles.headerLeft}>
          <span style={{ fontSize: 20 }}>✨</span>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>Send Envelope</span>
        </div>
        <ExpandButton />
      </div>

      <div className={styles.formPanel} style={{
        background: formBg,
        borderColor: t.brand,
      }}>
        <div className={styles.formTitle} style={{ color: t.brand }}>
          📝 Fill in the details to send a new envelope
        </div>

        <div className={styles.formGrid}>
          <Field label="Template ID / Name" size="small">
            <Input size="small" placeholder="Optional"
              value={form.template_id}
              onChange={(_, d) => setForm(f => ({ ...f, template_id: d.value }))} />
          </Field>
          <Field label="Recipient Name *" size="small" required>
            <Input size="small" placeholder="Jane Doe"
              value={form.recipient_name}
              onChange={(_, d) => setForm(f => ({ ...f, recipient_name: d.value }))} />
          </Field>
          <Field label="Recipient Email *" size="small" required>
            <Input size="small" type="email" placeholder="jane@example.com"
              value={form.recipient_email}
              onChange={(_, d) => setForm(f => ({ ...f, recipient_email: d.value }))} />
          </Field>
          <Field label="Email Subject" size="small">
            <Input size="small" placeholder="Please sign this document"
              value={form.subject}
              onChange={(_, d) => setForm(f => ({ ...f, subject: d.value }))} />
          </Field>
        </div>

        <Field label="Email Body" size="small" style={{ marginBottom: 14 }}>
          <Textarea size="small" rows={3}
            value={form.email_body}
            onChange={(_, d) => setForm(f => ({ ...f, email_body: d.value }))} />
        </Field>

        <div className={styles.formActions}>
          <Button appearance="secondary" size="small" onClick={handleReset} disabled={submitting}
            style={{ borderRadius: 4, height: 32, padding: '0 16px', border: `1px solid ${t.border}` }}>
            Reset
          </Button>
          <Button appearance="primary" size="small" onClick={handleSubmit}
            disabled={submitting || !canSubmit}
            style={{
              background: t.brand, borderColor: t.brand, color: '#fff',
              borderRadius: 4, height: 32, padding: '0 16px', minWidth: 90,
            }}>
            {submitting ? <Spinner size="tiny" /> : '📤 Send'}
          </Button>
        </div>
      </div>

      <DsFooter theme={theme} />
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────
export function DocuSignApp() {
  const styles = useStyles();
  const data = useToolData<DsData>();
  const theme = useTheme();
  const t = ds(theme);

  const shellStyle: React.CSSProperties = { padding: 12, fontSize: 12 };

  // Loading state
  if (!data) {
    return (
      <div className={styles.shell} style={shellStyle}>
        <SkeletonLoader />
      </div>
    );
  }

  // Error state (if data has error-like shape)
  if ((data as any).error) {
    return (
      <div className={styles.shell} style={shellStyle}>
        <div className={styles.card} style={{ border: `1px solid ${t.border}` }}>
          <div className={styles.headerBar} style={{ background: headerGradient(theme) }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>⚠️ Error</span>
          </div>
          <div className={styles.errorBanner} style={{
            background: theme === 'dark' ? '#3c1a1a' : '#FEF1EE',
            color: theme === 'dark' ? '#fe9f9b' : t.danger,
            borderLeft: `3px solid ${t.danger}`,
          }}>
            {(data as any).message || 'An unknown error occurred.'}
          </div>
          <DsFooter theme={theme} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.shell} style={shellStyle}>
      {data.type === 'envelopes' && (
        <EnvelopesView items={data.data || []} theme={theme} />
      )}
      {data.type === 'envelope_detail' && (
        <EnvelopeDetailView detail={data.data} theme={theme} />
      )}
      {data.type === 'templates' && (
        <TemplatesView items={data.data || []} theme={theme} />
      )}
      {data.type === 'form' && data.entity === 'send_envelope' && (
        <SendEnvelopeForm prefill={data.prefill} theme={theme} />
      )}
    </div>
  );
}
