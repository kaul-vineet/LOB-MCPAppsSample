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

export type SapDataType = 'purchase_orders' | 'business_partners' | 'materials' | 'material_detail';

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
