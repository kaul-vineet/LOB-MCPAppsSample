import React, { useState, useCallback, useEffect, useRef } from 'react';

import { useToolData, useMcpBridge, useTheme } from '../shared/McpBridge';
import { ExpandButton } from '../shared/ExpandButton';
import { McpFooter } from '../shared/McpFooter';
import { useToast } from '../shared/Toast';
import type {
  SapData, PurchaseOrder, BusinessPartner, Material, MaterialDetail,
  PoLineItem, PoLineItemsResult, GoodsReceipt, GoodsReceiptsResult,
  BpPurchaseOrdersResult, MaterialPlantData, MaterialPlantDataResult,
  StockLevel, StockLevelsResult,
  SalesOrder, SalesOrderItem, SalesOrderItemsResult, Delivery, DeliveriesResult,
} from './types';

/* ─── SAP Fiori / Horizon Design Tokens ───────────────────────────────── */
const fioriLight = {
  brand:        '#0070F2',
  surface:      '#FFFFFF',
  bg:           '#F5F6F7',
  text:         '#32363A',
  textWeak:     '#6A6D70',
  border:       '#E5E5E5',
  headerBg:     '#FAFAFA',
  success:      '#107E3E',
  successBg:    '#F1FDF6',
  warning:      '#E9730C',
  warningBg:    '#FFF8E6',
  error:        '#BB0000',
  errorBg:      '#FFF2F2',
  info:         '#0070F2',
  infoBg:       '#EBF5FF',
  neutral:      '#6A6D70',
  neutralBg:    '#F5F6F7',
  hoverBg:      '#E8F0FE',
  inputBorder:  '#89919A',
  shellColor:   '#354A5F',
};

const fioriDark = {
  brand:        '#0070F2',
  surface:      '#1C2027',
  bg:           '#13161B',
  text:         '#F5F6F7',
  textWeak:     '#89919A',
  border:       '#354A5E',
  headerBg:     '#1C2027',
  success:      '#5DC122',
  successBg:    '#1E3323',
  warning:      '#F9A429',
  warningBg:    '#3E3117',
  error:        '#FF5E5E',
  errorBg:      '#3E1F1F',
  info:         '#4DB1FF',
  infoBg:       '#1D2F42',
  neutral:      '#89919A',
  neutralBg:    '#29313A',
  hoverBg:      '#354050',
  inputBorder:  '#5B6B7A',
  shellColor:   '#1C2228',
};

type FioriTokens = typeof fioriLight;

function useFioriTokens(): FioriTokens {
  const theme = useTheme();
  return theme === 'dark' ? fioriDark : fioriLight;
}

/* ─── Global Fiori Styles ─────────────────────────────────────────────── */
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
      0%   { background-position: 200% 0; }
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

/* ─── Badge ───────────────────────────────────────────────────────────── */
type BadgeSemantic = 'success' | 'error' | 'warning' | 'info' | 'neutral';

function Badge({ label, semantic = 'neutral' }: { label: string; semantic?: BadgeSemantic }) {
  const t = useFioriTokens();
  const map: Record<BadgeSemantic, { fg: string; bg: string }> = {
    success: { fg: t.success, bg: t.successBg },
    error:   { fg: t.error,   bg: t.errorBg   },
    warning: { fg: t.warning, bg: t.warningBg  },
    info:    { fg: t.info,    bg: t.infoBg     },
    neutral: { fg: t.neutral, bg: t.neutralBg  },
  };
  const c = map[semantic];
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px',
      fontSize: '11px', fontWeight: 600, lineHeight: '18px',
      borderRadius: '2px', color: c.fg, backgroundColor: c.bg,
      whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  );
}

/* ─── Mono text ───────────────────────────────────────────────────────── */
function Mono({ children }: { children: React.ReactNode }) {
  return (
    <span style={{ fontFamily: "'72 Mono','Cascadia Code','Consolas',monospace", fontSize: '13px' }}>
      {children}
    </span>
  );
}

/* ─── Shell Bar ───────────────────────────────────────────────────────── */
function ShellBar({ title }: { title: string }) {
  const t = useFioriTokens();
  return (
    <div style={{
      backgroundColor: t.shellColor, color: '#FFFFFF',
      padding: '0 16px', height: '44px',
      display: 'flex', alignItems: 'center', gap: '12px',
    }}>
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <rect width="20" height="20" rx="2" fill="#FFFFFF" fillOpacity="0.15"/>
        <text x="3" y="14" fill="#FFFFFF" fontSize="11" fontWeight="bold">S/4</text>
      </svg>
      <span style={{ fontSize: '14px', fontWeight: 600, letterSpacing: '0.2px', flex: 1 }}>{title}</span>
      <ExpandButton />
    </div>
  );
}

/* ─── Error Banner ────────────────────────────────────────────────────── */
function ErrorBanner({ message }: { message: string }) {
  const t = useFioriTokens();
  return (
    <div style={{
      borderLeft: `4px solid ${t.error}`, backgroundColor: t.errorBg,
      padding: '12px 16px', marginBottom: '16px',
      fontSize: '13px', color: t.text,
    }}>
      <strong style={{ color: t.error }}>Error: </strong>{message}
    </div>
  );
}

/* ─── Empty State ─────────────────────────────────────────────────────── */
function EmptyState({ label }: { label?: string }) {
  const t = useFioriTokens();
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '48px 16px', color: t.textWeak,
      gap: '8px',
    }}>
      <span style={{ fontSize: '32px' }}>📋</span>
      <span style={{ fontSize: '14px' }}>{label || 'No records found.'}</span>
    </div>
  );
}

/* ─── Filter Bar ──────────────────────────────────────────────────────── */
function FilterBar({ children }: { children: React.ReactNode }) {
  const t = useFioriTokens();
  return (
    <div style={{
      display: 'flex', gap: '12px', alignItems: 'flex-end',
      flexWrap: 'wrap',
      backgroundColor: t.headerBg,
      border: `1px solid ${t.border}`,
      borderBottom: 'none',
      padding: '12px 16px',
    }}>
      {children}
    </div>
  );
}

function FilterInput({
  label, value, onChange, placeholder,
}: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  const t = useFioriTokens();
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', minWidth: '160px' }}>
      <label style={{ fontSize: '11px', fontWeight: 600, color: t.textWeak, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
        {label}
      </label>
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          height: '30px', padding: '0 8px', fontSize: '13px',
          color: t.text, backgroundColor: t.surface,
          border: 'none',
          borderBottom: focused ? `2px solid ${t.brand}` : `1px solid ${t.inputBorder}`,
          outline: 'none',
        }}
      />
    </div>
  );
}

function FilterSelect({
  label, value, onChange, options,
}: { label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[] }) {
  const t = useFioriTokens();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', minWidth: '140px' }}>
      <label style={{ fontSize: '11px', fontWeight: 600, color: t.textWeak, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
        {label}
      </label>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          height: '30px', padding: '0 8px', fontSize: '13px',
          color: t.text, backgroundColor: t.surface,
          border: `1px solid ${t.inputBorder}`, borderRadius: '2px',
          outline: 'none', cursor: 'pointer',
        }}
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

function FilterToggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  const t = useFioriTokens();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', justifyContent: 'flex-end', paddingBottom: '2px' }}>
      <label style={{ fontSize: '11px', fontWeight: 600, color: t.textWeak, textTransform: 'uppercase', letterSpacing: '0.3px' }}>
        &nbsp;
      </label>
      <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '13px', color: t.text }}>
        <input
          type="checkbox"
          checked={checked}
          onChange={e => onChange(e.target.checked)}
          style={{ width: '14px', height: '14px', cursor: 'pointer', accentColor: t.brand }}
        />
        {label}
      </label>
    </div>
  );
}

/* ─── Fiori Table ─────────────────────────────────────────────────────── */
function Table({ columns, children }: {
  columns: { label: string; width?: number | string }[];
  children: React.ReactNode;
}) {
  const t = useFioriTokens();
  return (
    <div style={{ border: `1px solid ${t.border}`, overflow: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '500px' }}>
        <thead>
          <tr style={{ backgroundColor: t.headerBg }}>
            {columns.map((col, i) => (
              <th key={i} style={{
                padding: '10px 14px', textAlign: 'left', fontSize: '11px',
                fontWeight: 600, color: t.textWeak,
                textTransform: 'uppercase', letterSpacing: '0.4px',
                borderBottom: `1px solid ${t.border}`,
                whiteSpace: 'nowrap',
                ...(col.width !== undefined ? { width: col.width } : {}),
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

function TableRow({ children, expandable }: { children: React.ReactNode; expandable?: boolean }) {
  const t = useFioriTokens();
  const [hovered, setHovered] = useState(false);
  return (
    <tr
      style={{
        backgroundColor: hovered ? t.hoverBg : t.surface,
        borderBottom: `1px solid ${t.border}`,
        transition: 'background-color 0.1s',
        cursor: expandable ? 'pointer' : 'default',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {children}
    </tr>
  );
}

function TD({ children, style }: { children?: React.ReactNode; style?: React.CSSProperties }) {
  const t = useFioriTokens();
  return (
    <td style={{ padding: '9px 14px', fontSize: '13px', color: t.text, verticalAlign: 'middle', ...style }}>
      {children}
    </td>
  );
}

/* ─── Expand toggle button ────────────────────────────────────────────── */
function ExpandToggle({ expanded, onClick, loading }: { expanded: boolean; onClick: () => void; loading?: boolean }) {
  const t = useFioriTokens();
  return (
    <button
      onClick={onClick}
      title={expanded ? 'Collapse' : 'Expand'}
      style={{
        background: 'none', border: 'none', cursor: 'pointer',
        padding: '2px 4px', borderRadius: '2px',
        color: t.brand, fontSize: '12px', fontWeight: 700,
        transition: 'background 0.1s',
      }}
    >
      {loading ? '⌛' : expanded ? '▼' : '▶'}
    </button>
  );
}

/* ─── Sub-table container ─────────────────────────────────────────────── */
function SubRow({ colSpan, children }: { colSpan: number; children: React.ReactNode }) {
  const t = useFioriTokens();
  return (
    <tr style={{ borderBottom: `1px solid ${t.border}` }}>
      <td colSpan={colSpan} style={{ padding: 0, backgroundColor: t.bg }}>
        <div style={{ borderTop: `2px solid ${t.brand}`, padding: '12px 16px 16px 40px' }}>
          {children}
        </div>
      </td>
    </tr>
  );
}

/* ─── Sub-table skeleton ──────────────────────────────────────────────── */
function SubSkeleton() {
  const t = useFioriTokens();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '8px 0' }}>
      {[0,1,2].map(i => (
        <div key={i} style={{ display: 'flex', gap: '16px' }}>
          {['50px','90px','160px','50px','40px'].map((w, j) => (
            <div key={j} className="skel" style={{ width: w, height: '12px' }} />
          ))}
        </div>
      ))}
    </div>
  );
}

/* ─── Shimmer skeleton (list) ─────────────────────────────────────────── */
function SkeletonTable({ cols = 4 }: { cols?: number }) {
  const t = useFioriTokens();
  const widths = ['60%','45%','30%','50%','40%'];
  return (
    <div style={{ border: `1px solid ${t.border}`, overflow: 'hidden' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ backgroundColor: t.headerBg }}>
            {Array.from({ length: cols }).map((_, i) => (
              <th key={i} style={{ padding: '10px 14px', borderBottom: `1px solid ${t.border}` }}>
                <div className="skel" style={{ width: '55%', height: '10px' }} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[0,1,2,3,4].map(ri => (
            <tr key={ri} style={{ backgroundColor: t.surface, borderBottom: `1px solid ${t.border}` }}>
              {Array.from({ length: cols }).map((_, ci) => (
                <td key={ci} style={{ padding: '9px 14px' }}>
                  <div className="skel" style={{ width: widths[ci % widths.length] }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ─── Section header ──────────────────────────────────────────────────── */
function SectionHeader({ title, count }: { title: string; count?: number }) {
  const t = useFioriTokens();
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '12px' }}>
      <span style={{ fontSize: '15px', fontWeight: 600, color: t.text }}>{title}</span>
      {count !== undefined && (
        <span style={{ fontSize: '12px', color: t.textWeak }}>({count})</span>
      )}
    </div>
  );
}

/* ─── Badge helpers ───────────────────────────────────────────────────── */
function statusBadge(deleted: boolean) {
  return <Badge label={deleted ? 'Deleted' : 'Active'} semantic={deleted ? 'error' : 'success'} />;
}

function categoryBadge(cat: string) {
  const label = cat === '1' ? 'Vendor' : cat === '2' ? 'Customer' : 'Both';
  const semantic: BadgeSemantic = cat === '2' ? 'info' : cat === '3' ? 'warning' : 'success';
  return <Badge label={label} semantic={semantic} />;
}

function typeBadge(pt: string) {
  const semantic: BadgeSemantic =
    pt === 'FERT' ? 'info' : pt === 'HALB' ? 'success' : pt === 'ROH' ? 'neutral' : 'neutral';
  return <Badge label={pt} semantic={semantic} />;
}

/* ═══════════════════════════════════════════════════════════════════════
   PURCHASE ORDERS VIEW
   ══════════════════════════════════════════════════════════════════════ */
function PurchaseOrdersView({
  items, callTool, toast,
}: {
  items: PurchaseOrder[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}) {
  const t = useFioriTokens();

  /* Filters */
  const [supplier, setSupplier]   = useState('');
  const [org, setOrg]             = useState('');
  const [dateFrom, setDateFrom]   = useState('');
  const [dateTo, setDateTo]       = useState('');
  const [showDeleted, setShowDeleted] = useState(true);

  /* Expand state — level 1 (PO → line items) */
  const [expanded, setExpanded]   = useState<Record<string, boolean>>({});
  const [loading, setLoading]     = useState<Record<string, boolean>>({});
  const [lineItems, setLineItems] = useState<Record<string, PoLineItem[]>>({});

  /* Expand state — level 2 (line item → goods receipts) */
  const [expandedLI, setExpandedLI]       = useState<Record<string, boolean>>({});
  const [loadingLI, setLoadingLI]         = useState<Record<string, boolean>>({});
  const [goodsReceipts, setGoodsReceipts] = useState<Record<string, GoodsReceipt[]>>({});

  /* Unique orgs for dropdown */
  const orgs = Array.from(new Set(items.map(p => p.purchasing_org).filter(Boolean)));
  const orgOptions = [{ value: '', label: '— All Orgs —' }, ...orgs.map(o => ({ value: o, label: o }))];

  const filtered = items.filter(po => {
    if (supplier && !po.supplier.toLowerCase().includes(supplier.toLowerCase())) return false;
    if (org && po.purchasing_org !== org) return false;
    if (dateFrom && po.order_date < dateFrom) return false;
    if (dateTo && po.order_date > dateTo) return false;
    if (!showDeleted && po.deletion_code) return false;
    return true;
  });

  const toggleExpand = useCallback(async (po: PurchaseOrder) => {
    const key = po.purchase_order;
    const isOpen = expanded[key];
    setExpanded(prev => ({ ...prev, [key]: !isOpen }));
    if (!isOpen && !lineItems[key]) {
      setLoading(prev => ({ ...prev, [key]: true }));
      try {
        const result: PoLineItemsResult = await callTool('sap__get_po_line_items', { purchase_order: key });
        setLineItems(prev => ({ ...prev, [key]: result?.items || [] }));
      } catch (e: any) {
        toast(e.message || 'Failed to load line items', 'error');
        setExpanded(prev => ({ ...prev, [key]: false }));
      } finally {
        setLoading(prev => ({ ...prev, [key]: false }));
      }
    }
  }, [expanded, lineItems, callTool, toast]);

  const toggleLI = useCallback(async (poKey: string, li: PoLineItem) => {
    const key = `${poKey}/${li.item_number}`;
    const isOpen = expandedLI[key];
    setExpandedLI(prev => ({ ...prev, [key]: !isOpen }));
    if (!isOpen && !goodsReceipts[key]) {
      setLoadingLI(prev => ({ ...prev, [key]: true }));
      try {
        const result: GoodsReceiptsResult = await callTool('sap__get_goods_receipts', { purchase_order: poKey, item_number: li.item_number });
        setGoodsReceipts(prev => ({ ...prev, [key]: result?.items || [] }));
      } catch (e: any) {
        toast(e.message || 'Failed to load goods receipts', 'error');
        setExpandedLI(prev => ({ ...prev, [key]: false }));
      } finally {
        setLoadingLI(prev => ({ ...prev, [key]: false }));
      }
    }
  }, [expandedLI, goodsReceipts, callTool, toast]);

  const cols = [
    { label: '', width: 32 },
    { label: 'PO Number', width: 130 },
    { label: 'Supplier' },
    { label: 'Purch. Org', width: 100 },
    { label: 'Order Date', width: 110 },
    { label: 'Status', width: 90 },
  ];

  const lineItemCols = [
    { label: '', width: 32 },
    { label: 'Item#', width: 60 },
    { label: 'Material', width: 100 },
    { label: 'Description' },
    { label: 'Qty', width: 60 },
    { label: 'Unit', width: 50 },
    { label: 'Net Price', width: 80 },
    { label: 'Currency', width: 70 },
    { label: 'Delivery Date', width: 110 },
  ];

  const grCols = [
    { label: 'GR Document', width: 130 },
    { label: 'Posting Date', width: 110 },
    { label: 'Qty', width: 70 },
    { label: 'Unit', width: 50 },
    { label: 'Delivery Note' },
  ];

  return (
    <>
      <SectionHeader title="Purchase Orders" count={filtered.length} />

      <FilterBar>
        <FilterInput label="Supplier" value={supplier} onChange={setSupplier} placeholder="Search…" />
        <FilterSelect label="Purchasing Org" value={org} onChange={setOrg} options={orgOptions} />
        <FilterInput label="Order Date From" value={dateFrom} onChange={setDateFrom} placeholder="YYYY-MM-DD" />
        <FilterInput label="Order Date To" value={dateTo} onChange={setDateTo} placeholder="YYYY-MM-DD" />
        <FilterToggle label="Show Deleted" checked={showDeleted} onChange={setShowDeleted} />
      </FilterBar>

      {filtered.length === 0
        ? <EmptyState label="No purchase orders match the current filters." />
        : (
          <Table columns={cols}>
            {filtered.map(po => (
              <React.Fragment key={po.purchase_order}>
                <TableRow expandable>
                  <TD>
                    <ExpandToggle
                      expanded={!!expanded[po.purchase_order]}
                      loading={!!loading[po.purchase_order]}
                      onClick={() => toggleExpand(po)}
                    />
                  </TD>
                  <TD><Mono>{po.purchase_order}</Mono></TD>
                  <TD>{po.supplier}</TD>
                  <TD style={{ color: t.textWeak }}>{po.purchasing_org}</TD>
                  <TD style={{ color: t.textWeak }}>{po.order_date}</TD>
                  <TD>{statusBadge(po.deletion_code)}</TD>
                </TableRow>

                {expanded[po.purchase_order] && (
                  <SubRow colSpan={cols.length}>
                    {loading[po.purchase_order]
                      ? <SubSkeleton />
                      : lineItems[po.purchase_order]?.length === 0
                        ? <EmptyState label="No line items." />
                        : (
                          <>
                            <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                              PO Line Items — {po.purchase_order}
                            </div>
                            <Table columns={lineItemCols}>
                              {(lineItems[po.purchase_order] || []).map(li => {
                                const liKey = `${po.purchase_order}/${li.item_number}`;
                                return (
                                  <React.Fragment key={li.item_number}>
                                    <TableRow expandable>
                                      <TD>
                                        <ExpandToggle
                                          expanded={!!expandedLI[liKey]}
                                          loading={!!loadingLI[liKey]}
                                          onClick={() => toggleLI(po.purchase_order, li)}
                                        />
                                      </TD>
                                      <TD><Mono>{li.item_number}</Mono></TD>
                                      <TD><Mono>{li.material}</Mono></TD>
                                      <TD>{li.description}</TD>
                                      <TD style={{ textAlign: 'right' }}>{li.quantity}</TD>
                                      <TD style={{ color: t.textWeak }}>{li.unit}</TD>
                                      <TD style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                                        {typeof li.net_price === 'number' ? li.net_price.toFixed(2) : li.net_price}
                                      </TD>
                                      <TD style={{ color: t.textWeak }}>{li.currency}</TD>
                                      <TD style={{ color: t.textWeak }}>{li.delivery_date}</TD>
                                    </TableRow>
                                    {expandedLI[liKey] && (
                                      <SubRow colSpan={lineItemCols.length}>
                                        {loadingLI[liKey]
                                          ? <SubSkeleton />
                                          : goodsReceipts[liKey]?.length === 0
                                            ? <EmptyState label="No goods receipts." />
                                            : (
                                              <>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                                                  Goods Receipts — Item {li.item_number}
                                                </div>
                                                <Table columns={grCols}>
                                                  {(goodsReceipts[liKey] || []).map(gr => (
                                                    <TableRow key={gr.gr_document}>
                                                      <TD><Mono>{gr.gr_document}</Mono></TD>
                                                      <TD style={{ color: t.textWeak }}>{gr.posting_date}</TD>
                                                      <TD style={{ textAlign: 'right' }}>{gr.quantity}</TD>
                                                      <TD style={{ color: t.textWeak }}>{gr.unit}</TD>
                                                      <TD style={{ color: t.textWeak }}>{gr.delivery_note}</TD>
                                                    </TableRow>
                                                  ))}
                                                </Table>
                                              </>
                                            )
                                        }
                                      </SubRow>
                                    )}
                                  </React.Fragment>
                                );
                              })}
                            </Table>
                          </>
                        )
                    }
                  </SubRow>
                )}
              </React.Fragment>
            ))}
          </Table>
        )
      }
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   BUSINESS PARTNERS VIEW
   ══════════════════════════════════════════════════════════════════════ */
function BusinessPartnersView({
  items, callTool, toast,
}: {
  items: BusinessPartner[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}) {
  const t = useFioriTokens();

  /* Filters */
  const [name, setName]     = useState('');
  const [category, setCategory] = useState('');

  /* Expand state — level 1 (BP → POs) */
  const [expanded, setExpanded]   = useState<Record<string, boolean>>({});
  const [loading, setLoading]     = useState<Record<string, boolean>>({});
  const [bpPos, setBpPos]         = useState<Record<string, PurchaseOrder[]>>({});

  /* Expand state — level 2 (PO → line items) */
  const [expandedPO, setExpandedPO]     = useState<Record<string, boolean>>({});
  const [loadingPO, setLoadingPO]       = useState<Record<string, boolean>>({});
  const [poLineItems, setPoLineItems]   = useState<Record<string, PoLineItem[]>>({});

  const catOptions = [
    { value: '', label: '— All Categories —' },
    { value: '1', label: 'Vendor' },
    { value: '2', label: 'Customer' },
    { value: '3', label: 'Both' },
  ];

  const filtered = items.filter(bp => {
    if (name && !bp.name.toLowerCase().includes(name.toLowerCase())) return false;
    if (category && bp.category !== category) return false;
    return true;
  });

  const toggleExpand = useCallback(async (bp: BusinessPartner) => {
    const key = bp.id;
    const isOpen = expanded[key];
    setExpanded(prev => ({ ...prev, [key]: !isOpen }));
    if (!isOpen && !bpPos[key]) {
      setLoading(prev => ({ ...prev, [key]: true }));
      try {
        const result: BpPurchaseOrdersResult = await callTool('sap__get_bp_purchase_orders', { partner_id: key });
        setBpPos(prev => ({ ...prev, [key]: result?.items || [] }));
      } catch (e: any) {
        toast(e.message || 'Failed to load purchase orders', 'error');
        setExpanded(prev => ({ ...prev, [key]: false }));
      } finally {
        setLoading(prev => ({ ...prev, [key]: false }));
      }
    }
  }, [expanded, bpPos, callTool, toast]);

  const togglePO = useCallback(async (bpKey: string, po: PurchaseOrder) => {
    const key = `${bpKey}/${po.purchase_order}`;
    const isOpen = expandedPO[key];
    setExpandedPO(prev => ({ ...prev, [key]: !isOpen }));
    if (!isOpen && !poLineItems[key]) {
      setLoadingPO(prev => ({ ...prev, [key]: true }));
      try {
        const result: PoLineItemsResult = await callTool('sap__get_po_line_items', { purchase_order: po.purchase_order });
        setPoLineItems(prev => ({ ...prev, [key]: result?.items || [] }));
      } catch (e: any) {
        toast(e.message || 'Failed to load line items', 'error');
        setExpandedPO(prev => ({ ...prev, [key]: false }));
      } finally {
        setLoadingPO(prev => ({ ...prev, [key]: false }));
      }
    }
  }, [expandedPO, poLineItems, callTool, toast]);

  const cols = [
    { label: '', width: 32 },
    { label: 'BP ID', width: 100 },
    { label: 'Name' },
    { label: 'Category', width: 110 },
    { label: 'Organization' },
  ];

  const poCols = [
    { label: '', width: 32 },
    { label: 'PO Number', width: 130 },
    { label: 'Supplier' },
    { label: 'Purch. Org', width: 100 },
    { label: 'Order Date', width: 110 },
    { label: 'Status', width: 90 },
  ];

  const bpLineItemCols = [
    { label: 'Item#', width: 60 },
    { label: 'Material', width: 100 },
    { label: 'Description' },
    { label: 'Qty', width: 60 },
    { label: 'Unit', width: 50 },
    { label: 'Net Price', width: 80 },
    { label: 'Currency', width: 70 },
    { label: 'Delivery Date', width: 110 },
  ];

  return (
    <>
      <SectionHeader title="Business Partners" count={filtered.length} />

      <FilterBar>
        <FilterInput label="Name" value={name} onChange={setName} placeholder="Search…" />
        <FilterSelect label="Category" value={category} onChange={setCategory} options={catOptions} />
      </FilterBar>

      {filtered.length === 0
        ? <EmptyState label="No business partners match the current filters." />
        : (
          <Table columns={cols}>
            {filtered.map(bp => (
              <React.Fragment key={bp.id}>
                <TableRow expandable>
                  <TD>
                    <ExpandToggle
                      expanded={!!expanded[bp.id]}
                      loading={!!loading[bp.id]}
                      onClick={() => toggleExpand(bp)}
                    />
                  </TD>
                  <TD><Mono>{bp.id}</Mono></TD>
                  <TD>{bp.name}</TD>
                  <TD>{categoryBadge(bp.category)}</TD>
                  <TD style={{ color: t.textWeak }}>{bp.organization}</TD>
                </TableRow>

                {expanded[bp.id] && (
                  <SubRow colSpan={cols.length}>
                    {loading[bp.id]
                      ? <SubSkeleton />
                      : bpPos[bp.id]?.length === 0
                        ? <EmptyState label="No purchase orders for this partner." />
                        : (
                          <>
                            <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                              Purchase Orders — {bp.name}
                            </div>
                            <Table columns={poCols}>
                              {(bpPos[bp.id] || []).map(po => {
                                const poKey = `${bp.id}/${po.purchase_order}`;
                                return (
                                  <React.Fragment key={po.purchase_order}>
                                    <TableRow expandable>
                                      <TD>
                                        <ExpandToggle
                                          expanded={!!expandedPO[poKey]}
                                          loading={!!loadingPO[poKey]}
                                          onClick={() => togglePO(bp.id, po)}
                                        />
                                      </TD>
                                      <TD><Mono>{po.purchase_order}</Mono></TD>
                                      <TD>{po.supplier}</TD>
                                      <TD style={{ color: t.textWeak }}>{po.purchasing_org}</TD>
                                      <TD style={{ color: t.textWeak }}>{po.order_date}</TD>
                                      <TD>{statusBadge(po.deletion_code)}</TD>
                                    </TableRow>
                                    {expandedPO[poKey] && (
                                      <SubRow colSpan={poCols.length}>
                                        {loadingPO[poKey]
                                          ? <SubSkeleton />
                                          : poLineItems[poKey]?.length === 0
                                            ? <EmptyState label="No line items." />
                                            : (
                                              <>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                                                  Line Items — PO {po.purchase_order}
                                                </div>
                                                <Table columns={bpLineItemCols}>
                                                  {(poLineItems[poKey] || []).map(li => (
                                                    <TableRow key={li.item_number}>
                                                      <TD><Mono>{li.item_number}</Mono></TD>
                                                      <TD><Mono>{li.material}</Mono></TD>
                                                      <TD>{li.description}</TD>
                                                      <TD style={{ textAlign: 'right' }}>{li.quantity}</TD>
                                                      <TD style={{ color: t.textWeak }}>{li.unit}</TD>
                                                      <TD style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                                                        {typeof li.net_price === 'number' ? li.net_price.toFixed(2) : li.net_price}
                                                      </TD>
                                                      <TD style={{ color: t.textWeak }}>{li.currency}</TD>
                                                      <TD style={{ color: t.textWeak }}>{li.delivery_date}</TD>
                                                    </TableRow>
                                                  ))}
                                                </Table>
                                              </>
                                            )
                                        }
                                      </SubRow>
                                    )}
                                  </React.Fragment>
                                );
                              })}
                            </Table>
                          </>
                        )
                    }
                  </SubRow>
                )}
              </React.Fragment>
            ))}
          </Table>
        )
      }
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   MATERIALS VIEW
   ══════════════════════════════════════════════════════════════════════ */
function MaterialsView({
  items, callTool, toast,
}: {
  items: Material[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}) {
  const t = useFioriTokens();

  /* Filters */
  const [product, setProduct]     = useState('');
  const [pType, setPType]         = useState('');
  const [pGroup, setPGroup]       = useState('');

  /* Expand state — level 1 (material → plant data) */
  const [expanded, setExpanded]     = useState<Record<string, boolean>>({});
  const [loading, setLoading]       = useState<Record<string, boolean>>({});
  const [plantData, setPlantData]   = useState<Record<string, MaterialPlantData[]>>({});

  /* Expand state — level 2 (plant → stock levels) */
  const [expandedPlant, setExpandedPlant]   = useState<Record<string, boolean>>({});
  const [loadingPlant, setLoadingPlant]     = useState<Record<string, boolean>>({});
  const [stockLevels, setStockLevels]       = useState<Record<string, StockLevel[]>>({});

  const typeOptions = [
    { value: '', label: '— All Types —' },
    ...Array.from(new Set(items.map(m => m.product_type).filter(Boolean))).map(v => ({ value: v, label: v })),
  ];
  const groupOptions = [
    { value: '', label: '— All Groups —' },
    ...Array.from(new Set(items.map(m => m.product_group).filter(Boolean))).map(v => ({ value: v, label: v })),
  ];

  const filtered = items.filter(m => {
    if (product && !m.product.toLowerCase().includes(product.toLowerCase())) return false;
    if (pType && m.product_type !== pType) return false;
    if (pGroup && m.product_group !== pGroup) return false;
    return true;
  });

  const toggleExpand = useCallback(async (m: Material) => {
    const key = m.product;
    const isOpen = expanded[key];
    setExpanded(prev => ({ ...prev, [key]: !isOpen }));
    if (!isOpen && !plantData[key]) {
      setLoading(prev => ({ ...prev, [key]: true }));
      try {
        const result: MaterialPlantDataResult = await callTool('sap__get_material_plant_data', { material_id: key });
        setPlantData(prev => ({ ...prev, [key]: result?.items || [] }));
      } catch (e: any) {
        toast(e.message || 'Failed to load plant data', 'error');
        setExpanded(prev => ({ ...prev, [key]: false }));
      } finally {
        setLoading(prev => ({ ...prev, [key]: false }));
      }
    }
  }, [expanded, plantData, callTool, toast]);

  const togglePlant = useCallback(async (materialKey: string, pd: MaterialPlantData) => {
    const key = `${materialKey}/${pd.plant}`;
    const isOpen = expandedPlant[key];
    setExpandedPlant(prev => ({ ...prev, [key]: !isOpen }));
    if (!isOpen && !stockLevels[key]) {
      setLoadingPlant(prev => ({ ...prev, [key]: true }));
      try {
        const result: StockLevelsResult = await callTool('sap__get_stock_levels', { material_id: materialKey, plant: pd.plant });
        setStockLevels(prev => ({ ...prev, [key]: result?.items || [] }));
      } catch (e: any) {
        toast(e.message || 'Failed to load stock levels', 'error');
        setExpandedPlant(prev => ({ ...prev, [key]: false }));
      } finally {
        setLoadingPlant(prev => ({ ...prev, [key]: false }));
      }
    }
  }, [expandedPlant, stockLevels, callTool, toast]);

  const cols = [
    { label: '', width: 32 },
    { label: 'Material#', width: 120 },
    { label: 'Description' },
    { label: 'Type', width: 80 },
    { label: 'Group', width: 80 },
    { label: 'Base Unit', width: 80 },
  ];

  const plantCols = [
    { label: '', width: 32 },
    { label: 'Plant', width: 80 },
    { label: 'MRP Type', width: 80 },
    { label: 'Lot Size', width: 80 },
    { label: 'Safety Stock', width: 110 },
    { label: 'Lead Time', width: 90 },
  ];

  const stockCols = [
    { label: 'Storage Loc.', width: 110 },
    { label: 'Unrestricted', width: 100 },
    { label: 'QI', width: 70 },
    { label: 'Blocked', width: 70 },
    { label: 'In Transit', width: 90 },
    { label: 'Unit', width: 50 },
  ];

  return (
    <>
      <SectionHeader title="Materials" count={filtered.length} />

      <FilterBar>
        <FilterInput label="Material#" value={product} onChange={setProduct} placeholder="Search…" />
        <FilterSelect label="Product Type" value={pType} onChange={setPType} options={typeOptions} />
        <FilterSelect label="Product Group" value={pGroup} onChange={setPGroup} options={groupOptions} />
      </FilterBar>

      {filtered.length === 0
        ? <EmptyState label="No materials match the current filters." />
        : (
          <Table columns={cols}>
            {filtered.map(m => (
              <React.Fragment key={m.product}>
                <TableRow expandable>
                  <TD>
                    <ExpandToggle
                      expanded={!!expanded[m.product]}
                      loading={!!loading[m.product]}
                      onClick={() => toggleExpand(m)}
                    />
                  </TD>
                  <TD><Mono>{m.product}</Mono></TD>
                  <TD style={{ color: t.textWeak }}>—</TD>
                  <TD>{typeBadge(m.product_type)}</TD>
                  <TD style={{ color: t.textWeak }}>{m.product_group}</TD>
                  <TD style={{ color: t.textWeak }}>{m.base_unit}</TD>
                </TableRow>

                {expanded[m.product] && (
                  <SubRow colSpan={cols.length}>
                    {loading[m.product]
                      ? <SubSkeleton />
                      : (plantData[m.product] || []).length === 0
                        ? <EmptyState label="No plant data available." />
                        : (
                          <>
                            <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                              Plant Data — {m.product}
                            </div>
                            <Table columns={plantCols}>
                              {(plantData[m.product] || []).map(pd => {
                                const plantKey = `${m.product}/${pd.plant}`;
                                return (
                                  <React.Fragment key={pd.plant}>
                                    <TableRow expandable>
                                      <TD>
                                        <ExpandToggle
                                          expanded={!!expandedPlant[plantKey]}
                                          loading={!!loadingPlant[plantKey]}
                                          onClick={() => togglePlant(m.product, pd)}
                                        />
                                      </TD>
                                      <TD><Mono>{pd.plant}</Mono></TD>
                                      <TD style={{ color: t.textWeak }}>{pd.mrp_type}</TD>
                                      <TD style={{ color: t.textWeak }}>{pd.lot_size}</TD>
                                      <TD style={{ textAlign: 'right' }}>{pd.safety_stock}</TD>
                                      <TD style={{ textAlign: 'right' }}>{pd.lead_time}d</TD>
                                    </TableRow>
                                    {expandedPlant[plantKey] && (
                                      <SubRow colSpan={plantCols.length}>
                                        {loadingPlant[plantKey]
                                          ? <SubSkeleton />
                                          : (stockLevels[plantKey] || []).length === 0
                                            ? <EmptyState label="No stock data." />
                                            : (
                                              <>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                                                  Stock Levels — Plant {pd.plant}
                                                </div>
                                                <Table columns={stockCols}>
                                                  {(stockLevels[plantKey] || []).map(sl => (
                                                    <TableRow key={sl.storage_location}>
                                                      <TD><Mono>{sl.storage_location}</Mono></TD>
                                                      <TD style={{ textAlign: 'right' }}>{sl.unrestricted}</TD>
                                                      <TD style={{ textAlign: 'right' }}>{sl.quality_inspection}</TD>
                                                      <TD style={{ textAlign: 'right' }}>{sl.blocked}</TD>
                                                      <TD style={{ textAlign: 'right' }}>{sl.in_transit}</TD>
                                                      <TD style={{ color: t.textWeak }}>{sl.unit}</TD>
                                                    </TableRow>
                                                  ))}
                                                </Table>
                                              </>
                                            )
                                        }
                                      </SubRow>
                                    )}
                                  </React.Fragment>
                                );
                              })}
                            </Table>
                          </>
                        )
                    }
                  </SubRow>
                )}
              </React.Fragment>
            ))}
          </Table>
        )
      }
    </>
  );
}

/* ─── Material Detail Panel (2-col grid, no edit) ─────────────────────── */
function MaterialDetailPanel({ detail }: { detail: MaterialDetail }) {
  const t = useFioriTokens();

  const fields = [
    { label: 'Description',  value: detail.product_description },
    { label: 'Type',         value: typeBadge(detail.product_type) },
    { label: 'Group',        value: detail.product_group },
    { label: 'Base Unit',    value: detail.base_unit },
    { label: 'Gross Weight', value: detail.gross_weight != null ? `${detail.gross_weight} ${detail.weight_unit}` : '—' },
    { label: 'Net Weight',   value: detail.net_weight   != null ? `${detail.net_weight} ${detail.weight_unit}`   : '—' },
    { label: 'Weight Unit',  value: detail.weight_unit },
    { label: 'Division',     value: detail.division },
  ];

  return (
    <div>
      <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
        Material Detail — {detail.product}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0', border: `1px solid ${t.border}` }}>
        {fields.map((f, i) => (
          <div key={f.label} style={{
            display: 'flex', padding: '8px 14px',
            borderBottom: i < fields.length - 2 ? `1px solid ${t.border}` : 'none',
            ...(i % 2 === 0 ? { borderRight: `1px solid ${t.border}` } : {}),
          }}>
            <div style={{
              fontSize: '11px', fontWeight: 600, color: t.textWeak,
              textTransform: 'uppercase', letterSpacing: '0.3px',
              minWidth: '110px',
            }}>
              {f.label}
            </div>
            <div style={{ fontSize: '13px', color: t.text }}>{f.value ?? '—'}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   MATERIAL DETAIL VIEW  (top-level data.type === "material_detail")
   ══════════════════════════════════════════════════════════════════════ */
function MaterialDetailView({ data }: { data: SapData }) {
  const t = useFioriTokens();
  const detail: MaterialDetail = {
    product:             data.product ?? '',
    product_type:        data.product_type ?? '',
    product_group:       data.product_group ?? '',
    base_unit:           data.base_unit ?? '',
    gross_weight:        data.gross_weight ?? 0,
    net_weight:          data.net_weight ?? 0,
    weight_unit:         data.weight_unit ?? '',
    division:            data.division ?? '',
    product_description: data.product_description ?? '',
  };

  return (
    <>
      {/* Object Page Header */}
      <div style={{
        backgroundColor: t.surface, border: `1px solid ${t.border}`, marginBottom: '16px',
      }}>
        <div style={{ padding: '16px', borderBottom: `1px solid ${t.border}` }}>
          <div style={{ fontSize: '17px', fontWeight: 600, color: t.text, marginBottom: '16px' }}>
            Material — {detail.product}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '16px' }}>
            {[
              { label: 'Product',    value: <Mono>{detail.product}</Mono> },
              { label: 'Type',       value: typeBadge(detail.product_type) },
              { label: 'Group',      value: detail.product_group },
              { label: 'Base Unit',  value: detail.base_unit },
            ].map(f => (
              <div key={f.label}>
                <div style={{ fontSize: '11px', fontWeight: 600, color: t.textWeak, textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '4px' }}>
                  {f.label}
                </div>
                <div style={{ fontSize: '13px', color: t.text }}>{f.value}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ padding: '16px' }}>
          <div style={{ fontSize: '13px', fontWeight: 600, color: t.text, marginBottom: '12px' }}>Details</div>
          <MaterialDetailPanel detail={detail} />
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   SALES ORDERS VIEW
   ══════════════════════════════════════════════════════════════════════ */
function SalesOrdersView({
  items, callTool, toast,
}: {
  items: SalesOrder[];
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  toast: (msg: string, type?: 'success' | 'error' | 'info') => void;
}) {
  const t = useFioriTokens();

  const [soldTo, setSoldTo]       = useState('');
  const [currency, setCurrency]   = useState('');
  const [status, setStatus]       = useState('');
  const [dateFrom, setDateFrom]   = useState('');
  const [dateTo, setDateTo]       = useState('');

  /* Expand state — level 1 (SO → items) */
  const [expanded, setExpanded]   = useState<Record<string, boolean>>({});
  const [loading, setLoading]     = useState<Record<string, boolean>>({});
  const [soItems, setSoItems]     = useState<Record<string, SalesOrderItem[]>>({});

  /* Expand state — level 2 (item → deliveries) */
  const [expandedItem, setExpandedItem] = useState<Record<string, boolean>>({});
  const [loadingItem, setLoadingItem]   = useState<Record<string, boolean>>({});
  const [deliveries, setDeliveries]     = useState<Record<string, Delivery[]>>({});

  const currencies = Array.from(new Set(items.map(s => s.currency).filter(Boolean)));
  const currencyOptions = [{ value: '', label: '— All —' }, ...currencies.map(c => ({ value: c, label: c }))];
  const statuses = Array.from(new Set(items.map(s => s.status).filter(Boolean)));
  const statusOptions = [{ value: '', label: '— All Statuses —' }, ...statuses.map(s => ({ value: s, label: s }))];

  const filtered = items.filter(so => {
    if (soldTo && !so.sold_to_party.toLowerCase().includes(soldTo.toLowerCase())) return false;
    if (currency && so.currency !== currency) return false;
    if (status && so.status !== status) return false;
    if (dateFrom && so.order_date < dateFrom) return false;
    if (dateTo && so.order_date > dateTo) return false;
    return true;
  });

  const toggleSO = useCallback(async (so: SalesOrder) => {
    const key = so.sales_order;
    const isOpen = expanded[key];
    setExpanded(prev => ({ ...prev, [key]: !isOpen }));
    if (!isOpen && !soItems[key]) {
      setLoading(prev => ({ ...prev, [key]: true }));
      try {
        const result: SalesOrderItemsResult = await callTool('sap__get_so_items', { sales_order: key });
        setSoItems(prev => ({ ...prev, [key]: result?.items || [] }));
      } catch (e: any) {
        toast(e.message || 'Failed to load SO items', 'error');
        setExpanded(prev => ({ ...prev, [key]: false }));
      } finally {
        setLoading(prev => ({ ...prev, [key]: false }));
      }
    }
  }, [expanded, soItems, callTool, toast]);

  const toggleItem = useCallback(async (soKey: string, item: SalesOrderItem) => {
    const key = `${soKey}/${item.item_number}`;
    const isOpen = expandedItem[key];
    setExpandedItem(prev => ({ ...prev, [key]: !isOpen }));
    if (!isOpen && !deliveries[key]) {
      setLoadingItem(prev => ({ ...prev, [key]: true }));
      try {
        const result: DeliveriesResult = await callTool('sap__get_deliveries', { sales_order: soKey, item_number: item.item_number });
        setDeliveries(prev => ({ ...prev, [key]: result?.items || [] }));
      } catch (e: any) {
        toast(e.message || 'Failed to load deliveries', 'error');
        setExpandedItem(prev => ({ ...prev, [key]: false }));
      } finally {
        setLoadingItem(prev => ({ ...prev, [key]: false }));
      }
    }
  }, [expandedItem, deliveries, callTool, toast]);

  function soStatusBadge(s: string) {
    const semantic: BadgeSemantic =
      s === 'Completed' || s === 'Delivered' ? 'success' :
      s === 'Open' ? 'info' : 'neutral';
    return <Badge label={s} semantic={semantic} />;
  }

  const cols = [
    { label: '', width: 32 },
    { label: 'Sales Order', width: 130 },
    { label: 'Sold-to Party' },
    { label: 'Order Date', width: 110 },
    { label: 'Net Value', width: 100 },
    { label: 'Currency', width: 80 },
    { label: 'Status', width: 110 },
  ];

  const itemCols = [
    { label: '', width: 32 },
    { label: 'Item#', width: 70 },
    { label: 'Material', width: 100 },
    { label: 'Description' },
    { label: 'Qty', width: 60 },
    { label: 'Unit', width: 50 },
    { label: 'Net Price', width: 90 },
    { label: 'Currency', width: 70 },
  ];

  const deliveryCols = [
    { label: 'Delivery', width: 120 },
    { label: 'GI Date', width: 110 },
    { label: 'Qty', width: 70 },
    { label: 'Unit', width: 50 },
    { label: 'Status' },
  ];

  return (
    <>
      <SectionHeader title="Sales Orders" count={filtered.length} />

      <FilterBar>
        <FilterInput label="Sold-to Party" value={soldTo} onChange={setSoldTo} placeholder="Search…" />
        <FilterSelect label="Currency" value={currency} onChange={setCurrency} options={currencyOptions} />
        <FilterSelect label="Status" value={status} onChange={setStatus} options={statusOptions} />
        <FilterInput label="Date From" value={dateFrom} onChange={setDateFrom} placeholder="YYYY-MM-DD" />
        <FilterInput label="Date To" value={dateTo} onChange={setDateTo} placeholder="YYYY-MM-DD" />
      </FilterBar>

      {filtered.length === 0
        ? <EmptyState label="No sales orders match the current filters." />
        : (
          <Table columns={cols}>
            {filtered.map(so => (
              <React.Fragment key={so.sales_order}>
                <TableRow expandable>
                  <TD>
                    <ExpandToggle
                      expanded={!!expanded[so.sales_order]}
                      loading={!!loading[so.sales_order]}
                      onClick={() => toggleSO(so)}
                    />
                  </TD>
                  <TD><Mono>{so.sales_order}</Mono></TD>
                  <TD>{so.sold_to_party}</TD>
                  <TD style={{ color: t.textWeak }}>{so.order_date}</TD>
                  <TD style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                    {typeof so.net_value === 'number' ? so.net_value.toFixed(2) : so.net_value}
                  </TD>
                  <TD style={{ color: t.textWeak }}>{so.currency}</TD>
                  <TD>{soStatusBadge(so.status)}</TD>
                </TableRow>

                {expanded[so.sales_order] && (
                  <SubRow colSpan={cols.length}>
                    {loading[so.sales_order]
                      ? <SubSkeleton />
                      : (soItems[so.sales_order] || []).length === 0
                        ? <EmptyState label="No items for this sales order." />
                        : (
                          <>
                            <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                              SO Items — {so.sales_order}
                            </div>
                            <Table columns={itemCols}>
                              {(soItems[so.sales_order] || []).map(item => {
                                const itemKey = `${so.sales_order}/${item.item_number}`;
                                return (
                                  <React.Fragment key={item.item_number}>
                                    <TableRow expandable>
                                      <TD>
                                        <ExpandToggle
                                          expanded={!!expandedItem[itemKey]}
                                          loading={!!loadingItem[itemKey]}
                                          onClick={() => toggleItem(so.sales_order, item)}
                                        />
                                      </TD>
                                      <TD><Mono>{item.item_number}</Mono></TD>
                                      <TD><Mono>{item.material}</Mono></TD>
                                      <TD>{item.description}</TD>
                                      <TD style={{ textAlign: 'right' }}>{item.quantity}</TD>
                                      <TD style={{ color: t.textWeak }}>{item.unit}</TD>
                                      <TD style={{ textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                                        {typeof item.net_price === 'number' ? item.net_price.toFixed(2) : item.net_price}
                                      </TD>
                                      <TD style={{ color: t.textWeak }}>{item.currency}</TD>
                                    </TableRow>
                                    {expandedItem[itemKey] && (
                                      <SubRow colSpan={itemCols.length}>
                                        {loadingItem[itemKey]
                                          ? <SubSkeleton />
                                          : (deliveries[itemKey] || []).length === 0
                                            ? <EmptyState label="No deliveries." />
                                            : (
                                              <>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: t.textWeak, marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.3px' }}>
                                                  Deliveries — Item {item.item_number}
                                                </div>
                                                <Table columns={deliveryCols}>
                                                  {(deliveries[itemKey] || []).map(d => (
                                                    <TableRow key={d.delivery}>
                                                      <TD><Mono>{d.delivery}</Mono></TD>
                                                      <TD style={{ color: t.textWeak }}>{d.actual_gi_date}</TD>
                                                      <TD style={{ textAlign: 'right' }}>{d.delivery_quantity}</TD>
                                                      <TD style={{ color: t.textWeak }}>{d.unit}</TD>
                                                      <TD>
                                                        <Badge
                                                          label={d.delivery_status}
                                                          semantic={d.delivery_status === 'Delivered' ? 'success' : d.delivery_status === 'In Transit' ? 'warning' : 'neutral'}
                                                        />
                                                      </TD>
                                                    </TableRow>
                                                  ))}
                                                </Table>
                                              </>
                                            )
                                        }
                                      </SubRow>
                                    )}
                                  </React.Fragment>
                                );
                              })}
                            </Table>
                          </>
                        )
                    }
                  </SubRow>
                )}
              </React.Fragment>
            ))}
          </Table>
        )
      }
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   MAIN APP
   ══════════════════════════════════════════════════════════════════════ */
export function SapApp() {
  injectFioriGlobalStyles();
  const t = useFioriTokens();
  const data = useToolData<SapData>();
  const { callTool } = useMcpBridge();
  const toast = useToast();

  const shellStyle: React.CSSProperties = {
    maxWidth: '1120px', margin: '0 auto',
    backgroundColor: t.bg, fontSize: '13px', minHeight: '200px',
  };
  const contentStyle: React.CSSProperties = { padding: '16px' };

  /* ── Loading (no data yet) ── */
  if (!data) {
    return (
      <div style={shellStyle}>
        <ShellBar title="SAP S/4HANA" />
        <div style={contentStyle}>
          <div className="skel" style={{ width: '200px', height: '16px', marginBottom: '16px' }} />
          <SkeletonTable cols={5} />
        </div>
      </div>
    );
  }

  /* ── Error ── */
  if ((data as any).error) {
    return (
      <div style={shellStyle}>
        <ShellBar title="SAP S/4HANA" />
        <div style={contentStyle}>
          <ErrorBanner message={(data as any).message || 'An unknown error occurred.'} />
        </div>
      </div>
    );
  }

  /* ── Shell bar title ── */
  const titleMap: Record<string, string> = {
    purchase_orders:  'SAP S/4HANA — Purchase Orders',
    business_partners:'SAP S/4HANA — Business Partners',
    materials:        'SAP S/4HANA — Materials',
    sales_orders:     'SAP S/4HANA — Sales Orders',
    material_detail:  `SAP S/4HANA — Material ${data.product || ''}`,
  };
  const shellTitle = titleMap[data.type] || 'SAP S/4HANA';

  /* ── Footer ── */
  const footer = (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '8px 0', marginTop: '16px',
      borderTop: `1px solid ${t.border}`,
      fontSize: '11px', color: t.textWeak,
    }}>
      <span>⚡ <strong>MCP Widget</strong> · SAP S/4HANA</span>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
        <a
          href="https://www.sap.com"
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: t.brand, textDecoration: 'underline', cursor: 'pointer' }}
        >
          Open in SAP ↗
        </a>
        <span>⚓ GTC</span>
      </div>
    </div>
  );

  /* ── material_detail (top-level) ── */
  if (data.type === 'material_detail') {
    return (
      <div style={shellStyle}>
        <ShellBar title={shellTitle} />
        <div style={contentStyle}>
          <MaterialDetailView data={data} />
          {footer}
        </div>
      </div>
    );
  }

  /* ── List views ── */
  return (
    <div style={shellStyle}>
      <ShellBar title={shellTitle} />
      <div style={contentStyle}>
        {data.type === 'purchase_orders' && (
          <PurchaseOrdersView
            items={(data.items || []) as PurchaseOrder[]}
            callTool={callTool}
            toast={toast}
          />
        )}
        {data.type === 'business_partners' && (
          <BusinessPartnersView
            items={(data.items || []) as BusinessPartner[]}
            callTool={callTool}
            toast={toast}
          />
        )}
        {data.type === 'materials' && (
          <MaterialsView
            items={(data.items || []) as Material[]}
            callTool={callTool}
            toast={toast}
          />
        )}
        {data.type === 'sales_orders' && (
          <SalesOrdersView
            items={(data.items || []) as SalesOrder[]}
            callTool={callTool}
            toast={toast}
          />
        )}
        {footer}
      </div>
    </div>
  );
}
