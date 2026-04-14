export interface Incident {
  sys_id: string;
  number: string;
  short_description: string;
  description: string;
  state: string;
  priority: string;
  assigned_to: string;
  sys_created_on: string;
}

export interface ServiceRequest {
  sys_id: string;
  number: string;
  short_description: string;
  request_state: string;
  priority: string;
  approval: string;
  sys_created_on: string;
}

export interface RequestItem {
  sys_id: string;
  number?: string;
  short_description: string;
  quantity: number;
  stage: string;
  price: string;
  cat_item: string;
  state?: string;
}

export interface SnowData {
  type: 'incidents' | 'requests' | 'request_items';
  total?: number;
  incidents?: Incident[];
  requests?: ServiceRequest[];
  items?: RequestItem[];
  error?: boolean;
  message?: string;
  _createdId?: string;
}
