import React, { useState } from 'react';

import { useToolData, useMcpBridge, useTheme } from '../shared/McpBridge';
import { ExpandButton } from '../shared/ExpandButton';
import { McpFooter } from '../shared/McpFooter';
import { useToast } from '../shared/Toast';
import type { SapData, PurchaseOrder, BusinessPartner, Material } from './types';

/* ─── SAP Fiori Design Tokens ─────────────────────────────────────── */
const fioriLight = {
  shellColor: '#354A5F',
  brandColor: '#0070F2',
  bgColor: '#F7F7F7',
  surfaceColor: '#FFFFFF',
  listHeaderBg: '#F5F6F7',
  borderColor: '#E5E5E5',
  textColor: '#32363A',
  textSecondary: '#6A6D70',
  hoverBg: '#E8F0FE',
  positiveColor: '#107E3E',
  negativeColor: '#BB0000',
  criticalColor: '#E78C07',
  infoColor: '#0070F2',
  positiveBg: '#F1FDF6',
  negativeBg: '#FFF2F2',
  criticalBg: '#FFF8E6',
  infoBg: '#EBF5FF',
  inputBorder: '#89919A',
};

const fioriDark = {
  shellColor: '#1C2228',
  brandColor: '#0070F2',
  bgColor: '#1C2228',
  surfaceColor: '#29313A',
  listHeaderBg: '#29313A',
  borderColor: '#3B4754',
  textColor: '#EDEDED',
  textSecondary: '#A9B4BE',
  hoverBg: '#354050',
  positiveColor: '#5DC122',
  negativeColor: '#FF5E5E',
  criticalColor: '#F9A429',
  infoColor: '#4DB1FF',
  positiveBg: '#1E3323',
  negativeBg: '#3E1F1F',
  criticalBg: '#3E3117',
  infoBg: '#1D2F42',
  inputBorder: '#5B6B7A',
};

function useFioriTokens() {
  const theme = useTheme();
  return theme === 'dark' ? fioriDark : fioriLight;
}

/* ─── Global Fiori Styles (injected once) ─────────────────────────── */
const FIORI_STYLE_ID = 'sap-fiori-global';
function injectFioriGlobalStyles() {
  if (document.getElementById(FIORI_STYLE_ID)) return;
  const style = document.createElement('style');
  style.id = FIORI_STYLE_ID;
  style.textContent = `
    *, *::before, *::after {
      font-family: '72', 'Segoe UI', Arial, Helvetica, sans-serif !important;
    }
    input, button, select, textarea {
      font-family: '72', 'Segoe UI', Arial, Helvetica, sans-serif !important;
    }
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
  `;
  document.head.appendChild(style);
}

/* ─── Fiori Object Status Badge ───────────────────────────────────── */
type FioriSemantic = 'positive' | 'negative' | 'critical' | 'information' | 'neutral';

function FioriBadge({ label, semantic }: { label: string; semantic: FioriSemantic }) {
  const t = useFioriTokens();
  const colorMap: Record<FioriSemantic, { fg: string; bg: string }> = {
    positive: { fg: t.positiveColor, bg: t.positiveBg },
    negative: { fg: t.negativeColor, bg: t.negativeBg },
    critical: { fg: t.criticalColor, bg: t.criticalBg },
    information: { fg: t.infoColor, bg: t.infoBg },
    neutral: { fg: t.textSecondary, bg: t.listHeaderBg },
  };
  const c = colorMap[semantic];
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      fontSize: '12px',
      fontWeight: 600,
      lineHeight: '18px',
      borderRadius: '2px',
      color: c.fg,
      backgroundColor: c.bg,
    }}>
      {label}
    </span>
  );
}

/* ─── Fiori Button ────────────────────────────────────────────────── */
function FioriButton({ children, emphasis = 'secondary', icon, onClick, disabled, title, style: extraStyle }: {
  children?: React.ReactNode;
  emphasis?: 'primary' | 'secondary' | 'ghost';
  icon?: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  title?: string;
  style?: React.CSSProperties;
}) {
  const t = useFioriTokens();
  const [hovered, setHovered] = useState(false);
  const base: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    height: '28px',
    padding: children ? '0 12px' : '0 6px',
    fontSize: '13px',
    fontWeight: 600,
    borderRadius: '2px',
    cursor: disabled ? 'default' : 'pointer',
    border: 'none',
    opacity: disabled ? 0.5 : 1,
    transition: 'background-color 0.15s, border-color 0.15s',
    ...extraStyle,
  };

  const styles: Record<string, React.CSSProperties> = {
    primary: {
      ...base,
      backgroundColor: hovered && !disabled ? '#0062D1' : t.brandColor,
      color: '#FFFFFF',
    },
    secondary: {
      ...base,
      backgroundColor: hovered && !disabled ? t.hoverBg : 'transparent',
      color: t.brandColor,
      border: `1px solid ${t.brandColor}`,
    },
    ghost: {
      ...base,
      backgroundColor: hovered && !disabled ? t.hoverBg : 'transparent',
      color: t.brandColor,
    },
  };

  return (
    <button
      style={styles[emphasis]}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      title={title}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {icon}{children}
    </button>
  );
}

/* ─── Fiori Input (bottom-border style) ───────────────────────────── */
function FioriInput({ label, value, onChange }: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const t = useFioriTokens();
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <label style={{ fontSize: '12px', fontWeight: 600, color: t.textSecondary, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
        {label}
      </label>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          height: '32px',
          padding: '0 8px',
          fontSize: '14px',
          color: t.textColor,
          backgroundColor: 'transparent',
          border: 'none',
          borderBottom: focused ? `2px solid ${t.brandColor}` : `1px solid ${t.inputBorder}`,
          outline: 'none',
          transition: 'border-bottom 0.15s',
        }}
      />
    </div>
  );
}

/* ─── Fiori Shell Bar ─────────────────────────────────────────────── */
function FioriShellBar({ title }: {
  title: string;
}) {
  const t = useFioriTokens();
  return (
    <div style={{
      backgroundColor: t.shellColor,
      color: '#FFFFFF',
      padding: '0 16px',
      height: '44px',
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      marginBottom: '16px',
    }}>
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><rect width="20" height="20" rx="2" fill="#FFFFFF" fillOpacity="0.15"/><text x="3" y="14" fill="#FFFFFF" fontSize="11" fontWeight="bold">S/4</text></svg>
      <span style={{ fontSize: '14px', fontWeight: 600, letterSpacing: '0.2px', flex: 1 }}>{title}</span>
      <ExpandButton />
    </div>
  );
}

/* ─── Fiori MessageStrip (sandbox banner) ─────────────────────────── */
function FioriMessageStrip({ children }: { children: React.ReactNode }) {
  const t = useFioriTokens();
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 16px',
      backgroundColor: t.surfaceColor,
      borderLeft: '4px solid #F0AB00',
      marginBottom: '16px',
      fontSize: '13px',
      color: t.textColor,
    }}>
      <span style={{ fontSize: '16px' }}>⚠️</span>
      <span>{children}</span>
    </div>
  );
}

/* ─── Badge semantic helpers ──────────────────────────────────────── */
function statusSemantic(deleted: boolean): FioriSemantic {
  return deleted ? 'negative' : 'positive';
}
function statusLabel(deleted: boolean) {
  return deleted ? 'Deleted' : 'Active';
}
function categorySemantic(cat: string): FioriSemantic {
  return cat === '2' ? 'information' : 'positive';
}
function categoryLabel(cat: string) {
  return cat === '2' ? 'Person' : 'Organization';
}
function typeSemantic(t: string): FioriSemantic {
  if (t === 'FERT') return 'information';
  if (t === 'HALB') return 'positive';
  return 'neutral';
}

/* ─── Fiori Table ─────────────────────────────────────────────────── */
function FioriTable({ columns, children }: {
  columns: { label: string; width?: number }[];
  children: React.ReactNode;
}) {
  const t = useFioriTokens();
  return (
    <div style={{ border: `1px solid ${t.borderColor}`, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ backgroundColor: t.listHeaderBg }}>
            {columns.map((col, i) => (
              <th key={i} style={{
                padding: '12px 16px',
                textAlign: 'left',
                fontSize: '12px',
                fontWeight: 600,
                color: t.textSecondary,
                textTransform: 'uppercase',
                letterSpacing: '0.4px',
                borderBottom: `1px solid ${t.borderColor}`,
                ...(col.width ? { width: col.width } : {}),
              }}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function FioriTableRow({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) {
  const t = useFioriTokens();
  const [hovered, setHovered] = useState(false);
  return (
    <tr
      style={{
        backgroundColor: hovered ? t.hoverBg : t.surfaceColor,
        borderBottom: `1px solid ${t.borderColor}`,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'background-color 0.12s',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onClick}
    >
      {children}
    </tr>
  );
}

function FioriTableCell({ children, style }: { children?: React.ReactNode; style?: React.CSSProperties }) {
  const t = useFioriTokens();
  return (
    <td style={{ padding: '10px 16px', fontSize: '13px', color: t.textColor, verticalAlign: 'middle', ...style }}>
      {children}
    </td>
  );
}

/* ─── Mono text for IDs ───────────────────────────────────────────── */
function MonoText({ children }: { children: React.ReactNode }) {
  return <span style={{ fontFamily: "'72 Mono', 'Cascadia Code', 'Consolas', monospace", fontSize: '13px' }}>{children}</span>;
}

// ─── Purchase Orders View ────────────────────────────────────────────
function PurchaseOrdersView({ items, sandbox, callTool, toast }: {
  items: PurchaseOrder[];
  sandbox?: boolean;
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}) {
  const t = useFioriTokens();
  const [editingPo, setEditingPo] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [formData, setFormData] = useState({ supplier: '', purchasing_org: '', order_type: 'NB' });
  const [saving, setSaving] = useState(false);

  const openEdit = (po: PurchaseOrder) => {
    setCreating(false);
    setEditingPo(po.purchase_order);
    setFormData({ supplier: po.supplier, purchasing_org: po.purchasing_org, order_type: 'NB' });
  };

  const openCreate = () => {
    setEditingPo(null);
    setCreating(true);
    setFormData({ supplier: '', purchasing_org: '', order_type: 'NB' });
  };

  const cancel = () => { setEditingPo(null); setCreating(false); };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (creating) {
        await callTool('create_purchase_order', {
          supplier: formData.supplier,
          purchasing_org: formData.purchasing_org,
          order_type: formData.order_type,
        });
        toast('Purchase order created');
      } else {
        await callTool('update_purchase_order', {
          purchase_order: editingPo,
          supplier: formData.supplier,
          purchasing_org: formData.purchasing_org,
          order_type: formData.order_type,
        });
        toast(`PO ${editingPo} updated`);
      }
      cancel();
    } catch (e: any) {
      toast(e.message || 'Operation failed', 'error');
    } finally {
      setSaving(false);
    }
  };

  const renderEditPanel = (title: string) => (
    <tr>
      <td colSpan={6} style={{ padding: 0 }}>
        <div style={{
          backgroundColor: t.listHeaderBg,
          borderTop: `2px solid ${t.brandColor}`,
          padding: '16px 16px',
        }}>
          <div style={{ fontSize: '14px', fontWeight: 600, color: t.textColor, marginBottom: '16px' }}>
            ✏️ {title}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <FioriInput label="Supplier" value={formData.supplier} onChange={v => setFormData(f => ({ ...f, supplier: v }))} />
            <FioriInput label="Purchasing Org" value={formData.purchasing_org} onChange={v => setFormData(f => ({ ...f, purchasing_org: v }))} />
            <FioriInput label="Order Type" value={formData.order_type} onChange={v => setFormData(f => ({ ...f, order_type: v }))} />
          </div>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <FioriButton emphasis="secondary" onClick={cancel} disabled={saving}>Cancel</FioriButton>
            <FioriButton emphasis="primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </FioriButton>
          </div>
        </div>
      </td>
    </tr>
  );

  const columns = [
    { label: 'PO Number' },
    { label: 'Supplier' },
    { label: 'Purch. Org' },
    { label: 'Order Date' },
    { label: 'Status' },
    { label: 'Actions', width: 70 },
  ];

  return (
    <>
      {sandbox && (
        <FioriMessageStrip>
          Sandbox Environment — Data resets nightly. Changes will not persist to production.
        </FioriMessageStrip>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <span style={{ fontSize: '16px', fontWeight: 600, color: t.textColor }}>Purchase Orders</span>
        <FioriButton emphasis="primary" icon={<span style={{ fontSize: '14px' }}>＋</span>} onClick={openCreate}>
          New PO
        </FioriButton>
      </div>

      <FioriTable columns={columns}>
        {creating && renderEditPanel('New Purchase Order')}
        {items.map((po) => (
          <React.Fragment key={po.purchase_order}>
            <FioriTableRow>
              <FioriTableCell><MonoText>{po.purchase_order}</MonoText></FioriTableCell>
              <FioriTableCell>{po.supplier}</FioriTableCell>
              <FioriTableCell>{po.purchasing_org}</FioriTableCell>
              <FioriTableCell>{po.order_date}</FioriTableCell>
              <FioriTableCell>
                <FioriBadge label={statusLabel(po.deletion_code)} semantic={statusSemantic(po.deletion_code)} />
              </FioriTableCell>
              <FioriTableCell>
                <FioriButton emphasis="ghost" title="Edit" onClick={() => openEdit(po)}>
                  <span style={{ fontSize: '14px' }}>✎</span>
                </FioriButton>
              </FioriTableCell>
            </FioriTableRow>
            {editingPo === po.purchase_order && renderEditPanel(`Edit Purchase Order ${po.purchase_order}`)}
          </React.Fragment>
        ))}
      </FioriTable>
    </>
  );
}

// ─── Business Partners View ──────────────────────────────────────────
function BusinessPartnersView({ items }: { items: BusinessPartner[] }) {
  const t = useFioriTokens();

  const columns = [
    { label: 'Partner ID' },
    { label: 'Name' },
    { label: 'Category' },
    { label: 'Organization' },
  ];

  return (
    <>
      <div style={{ marginBottom: '16px' }}>
        <span style={{ fontSize: '16px', fontWeight: 600, color: t.textColor }}>Business Partners</span>
      </div>

      <FioriTable columns={columns}>
        {items.map((bp) => (
          <FioriTableRow key={bp.id}>
            <FioriTableCell><MonoText>{bp.id}</MonoText></FioriTableCell>
            <FioriTableCell>{bp.name}</FioriTableCell>
            <FioriTableCell>
              <FioriBadge label={categoryLabel(bp.category)} semantic={categorySemantic(bp.category)} />
            </FioriTableCell>
            <FioriTableCell>{bp.organization}</FioriTableCell>
          </FioriTableRow>
        ))}
      </FioriTable>
    </>
  );
}

// ─── Materials View ──────────────────────────────────────────────────
function MaterialsView({ items, onViewDetail }: {
  items: Material[];
  onViewDetail: (product: string) => void;
}) {
  const t = useFioriTokens();

  const columns = [
    { label: 'Product' },
    { label: 'Type' },
    { label: 'Group' },
    { label: 'Base Unit' },
    { label: '', width: 120 },
  ];

  return (
    <>
      <div style={{ marginBottom: '16px' }}>
        <span style={{ fontSize: '16px', fontWeight: 600, color: t.textColor }}>Materials</span>
      </div>

      <FioriTable columns={columns}>
        {items.map((m) => (
          <FioriTableRow key={m.product}>
            <FioriTableCell><MonoText>{m.product}</MonoText></FioriTableCell>
            <FioriTableCell>
              <FioriBadge label={m.product_type} semantic={typeSemantic(m.product_type)} />
            </FioriTableCell>
            <FioriTableCell>{m.product_group}</FioriTableCell>
            <FioriTableCell>{m.base_unit}</FioriTableCell>
            <FioriTableCell>
              <button
                onClick={() => onViewDetail(m.product)}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                  color: t.brandColor, fontWeight: 600, fontSize: '12px',
                }}
              >
                View Detail →
              </button>
            </FioriTableCell>
          </FioriTableRow>
        ))}
      </FioriTable>
    </>
  );
}

// ─── Material Detail View (SAP Object Page) ─────────────────────────
function MaterialDetailView({ data, onBack }: { data: SapData; onBack: () => void }) {
  const t = useFioriTokens();

  const headerFields = [
    { label: 'Product', value: data.product },
    { label: 'Type', value: data.product_type ? <FioriBadge label={data.product_type} semantic={typeSemantic(data.product_type)} /> : '—' },
    { label: 'Group', value: data.product_group },
    { label: 'Base Unit', value: data.base_unit },
  ];

  const detailFields = [
    { label: 'Gross Weight', value: `${data.gross_weight} ${data.weight_unit || ''}` },
    { label: 'Net Weight', value: `${data.net_weight} ${data.weight_unit || ''}` },
    { label: 'Division', value: data.division },
    { label: 'Description', value: data.product_description },
  ];

  return (
    <>
      {/* Breadcrumb */}
      <div style={{ marginBottom: '16px' }}>
        <FioriButton emphasis="ghost" onClick={onBack}>
          <span style={{ fontSize: '14px' }}>←</span> Back to Materials
        </FioriButton>
      </div>

      {/* Object Page Header */}
      <div style={{
        backgroundColor: t.surfaceColor,
        border: `1px solid ${t.borderColor}`,
        marginBottom: '16px',
      }}>
        <div style={{
          padding: '16px',
          borderBottom: `1px solid ${t.borderColor}`,
        }}>
          <div style={{ fontSize: '18px', fontWeight: 600, color: t.textColor, marginBottom: '16px' }}>
            Material — {data.product}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '16px' }}>
            {headerFields.map(f => (
              <div key={f.label}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: t.textSecondary, textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '4px' }}>
                  {f.label}
                </div>
                <div style={{ fontSize: '14px', color: t.textColor }}>{f.value ?? '—'}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Detail Section */}
        <div style={{ padding: '16px' }}>
          <div style={{ fontSize: '14px', fontWeight: 600, color: t.textColor, marginBottom: '16px' }}>
            Details
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0' }}>
            {detailFields.map(f => (
              <div key={f.label} style={{
                display: 'flex',
                padding: '12px 16px',
                borderBottom: `1px solid ${t.borderColor}`,
              }}>
                <div style={{
                  fontWeight: 600, color: t.textSecondary, minWidth: '130px',
                  fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.3px',
                }}>
                  {f.label}
                </div>
                <div style={{ fontSize: '14px', color: t.textColor }}>{f.value ?? '—'}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

/* ─── Skeleton Loading Shimmer ─────────────────────────────────────── */
function SkeletonTable() {
  const t = useFioriTokens();
  const widths = [
    ['60%', '45%', '30%', '50%'],
    ['40%', '55%', '25%', '35%'],
    ['70%', '35%', '40%', '55%'],
    ['50%', '50%', '35%', '45%'],
    ['55%', '40%', '30%', '40%'],
  ];
  return (
    <div style={{ border: `1px solid ${t.borderColor}`, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ backgroundColor: t.listHeaderBg }}>
            {['', '', '', ''].map((_, i) => (
              <th key={i} style={{ padding: '12px 16px', borderBottom: `1px solid ${t.borderColor}` }}>
                <div className="skel" style={{ width: '60%', height: '10px' }} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {widths.map((row, ri) => (
            <tr key={ri} style={{ backgroundColor: t.surfaceColor, borderBottom: `1px solid ${t.borderColor}` }}>
              {row.map((w, ci) => (
                <td key={ci} style={{ padding: '10px 16px' }}>
                  <div className="skel" style={{ width: w }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Main App ────────────────────────────────────────────────────────
export function SapApp() {
  injectFioriGlobalStyles();
  const t = useFioriTokens();
  const data = useToolData<SapData>();
  const { callTool } = useMcpBridge();
  const toast = useToast();
  const [detailData, setDetailData] = useState<SapData | null>(null);

  const handleViewDetail = useCallback(async (product: string) => {
    try {
      const result = await callTool('get_material_details', { material_id: product });
      if (result) {
        setDetailData(result);
      }
    } catch (e: any) {
      toast(e.message || 'Failed to load detail', 'error');
    }
  }, [callTool, toast]);

  const handleBackFromDetail = useCallback(() => {
    setDetailData(null);
  }, []);

  const shellStyle: React.CSSProperties = {
    maxWidth: '1120px',
    margin: '0 auto',
    backgroundColor: t.bgColor,
    fontSize: '13px',
  };

  const contentStyle: React.CSSProperties = {
    padding: '16px',
  };

  // Loading state
  if (!data) {
    return (
      <div style={shellStyle}>
        <FioriShellBar title="SAP S/4HANA" />
        <div style={contentStyle}>
          <div style={{ marginBottom: '16px' }}>
            <div className="skel" style={{ width: '180px', height: '18px', marginBottom: '16px' }} />
          </div>
          <SkeletonTable />
        </div>
      </div>
    );
  }

  // Determine shell bar title based on data type
  const titleMap: Record<string, string> = {
    purchase_orders: 'SAP S/4HANA — Purchase Orders',
    business_partners: 'SAP S/4HANA — Business Partners',
    materials: 'SAP S/4HANA — Materials',
    material_detail: `SAP S/4HANA — Material ${data.product || ''}`,
  };
  const shellTitle = detailData?.type === 'material_detail'
    ? `SAP S/4HANA — Material ${detailData.product || ''}`
    : titleMap[data.type] || 'SAP S/4HANA';

  // Material detail view (from callTool response)
  if (detailData && detailData.type === 'material_detail') {
    return (
      <div style={shellStyle}>
        <FioriShellBar title={shellTitle} />
        <div style={contentStyle}>
          <MaterialDetailView data={detailData} onBack={handleBackFromDetail} />
          <McpFooter label="SAP S/4HANA" />
        </div>
      </div>
    );
  }

  // Initial data-driven view from tool result
  if (data.type === 'material_detail') {
    return (
      <div style={shellStyle}>
        <FioriShellBar title={shellTitle} />
        <div style={contentStyle}>
          <MaterialDetailView data={data} onBack={handleBackFromDetail} />
          <McpFooter label="SAP S/4HANA" />
        </div>
      </div>
    );
  }

  return (
    <div style={shellStyle}>
      <FioriShellBar title={shellTitle} />
      <div style={contentStyle}>
        {data.type === 'purchase_orders' && (
          <PurchaseOrdersView
            items={(data.items || []) as PurchaseOrder[]}
            sandbox={data.sandbox}
            callTool={callTool}
            toast={toast}
          />
        )}

        {data.type === 'business_partners' && (
          <BusinessPartnersView items={(data.items || []) as BusinessPartner[]} />
        )}

        {data.type === 'materials' && (
          <MaterialsView
            items={(data.items || []) as Material[]}
            onViewDetail={handleViewDetail}
          />
        )}

        <McpFooter label="SAP S/4HANA" />
      </div>
    </div>
  );
}

