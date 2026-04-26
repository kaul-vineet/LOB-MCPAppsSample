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

export interface SalesOrder {
  sales_order: string;
  sold_to_party: string;
  order_date: string;
  net_value: number;
  currency: string;
  status: string;
}

/* ─── Child / grandchild data returned by expand callTool ─────────────── */
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

export interface GoodsReceipt {
  gr_document: string;
  posting_date: string;
  quantity: number;
  unit: string;
  delivery_note: string;
}

export interface GoodsReceiptsResult {
  type: 'goods_receipts';
  purchase_order: string;
  item_number: string;
  items: GoodsReceipt[];
}

export interface BpPurchaseOrdersResult {
  type: 'bp_purchase_orders';
  partner_id: string;
  items: PurchaseOrder[];
}

export interface MaterialPlantData {
  plant: string;
  mrp_type: string;
  lot_size: string;
  safety_stock: number;
  lead_time: number;
}

export interface MaterialPlantDataResult {
  type: 'material_plant_data';
  material_id: string;
  items: MaterialPlantData[];
}

export interface StockLevel {
  storage_location: string;
  unrestricted: number;
  quality_inspection: number;
  blocked: number;
  in_transit: number;
  unit: string;
}

export interface StockLevelsResult {
  type: 'stock_levels';
  material_id: string;
  plant: string;
  items: StockLevel[];
}

export interface SalesOrderItem {
  item_number: string;
  material: string;
  description: string;
  quantity: number;
  unit: string;
  net_price: number;
  currency: string;
}

export interface SalesOrderItemsResult {
  type: 'so_items';
  sales_order: string;
  items: SalesOrderItem[];
}

export interface Delivery {
  delivery: string;
  actual_gi_date: string;
  delivery_quantity: number;
  unit: string;
  delivery_status: string;
}

export interface DeliveriesResult {
  type: 'deliveries';
  sales_order: string;
  item_number: string;
  items: Delivery[];
}

export type SapDataType =
  | 'purchase_orders'
  | 'business_partners'
  | 'materials'
  | 'material_detail'
  | 'sales_orders';

export interface SapData {
  type: SapDataType;
  total?: number;
  sandbox?: boolean;
  items?: (PurchaseOrder | BusinessPartner | Material | SalesOrder)[];
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
