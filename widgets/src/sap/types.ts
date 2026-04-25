export interface PurchaseOrder {
  purchase_order: string;
  supplier: string;
  purchasing_org: string;
  order_date: string;
  deletion_code: boolean;
}

export interface BusinessPartner {
  id: string;
  name: string;
  category: string;
  organization: string;
}

export interface Material {
  product: string;
  product_type: string;
  product_group: string;
  base_unit: string;
}

export interface MaterialDetail extends Material {
  gross_weight: number;
  net_weight: number;
  weight_unit: string;
  division: string;
  product_description: string;
}

/* ─── Child data returned by expand callTool ── */
export interface PoLineItem {
  item_number: string;
  material: string;
  description: string;
  quantity: number;
  unit: string;
  net_price: number;
  currency: string;
  delivery_date: string;
}

export interface PoLineItemsResult {
  type: 'po_line_items';
  purchase_order: string;
  items: PoLineItem[];
}

export interface BpPurchaseOrdersResult {
  type: 'bp_purchase_orders';
  partner_id: string;
  items: PurchaseOrder[];
}

export type SapDataType =
  | 'purchase_orders'
  | 'business_partners'
  | 'materials'
  | 'material_detail';

export interface SapData {
  type: SapDataType;
  total?: number;
  sandbox?: boolean;
  items?: (PurchaseOrder | BusinessPartner | Material)[];
  // material_detail fields (flat)
  product?: string;
  product_type?: string;
  product_group?: string;
  base_unit?: string;
  gross_weight?: number;
  net_weight?: number;
  weight_unit?: string;
  division?: string;
  product_description?: string;
}
