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

export interface ChangeRequest {
  sys_id: string;
  number: string;
  short_description: string;
  state: string;
  priority: string;
  risk: string;
  category: string;
  assigned_to?: string;
  sys_created_on: string;
}

export interface Problem {
  sys_id: string;
  number: string;
  short_description: string;
  state: string;
  priority: string;
  assigned_to?: string;
  sys_created_on: string;
}

export interface KnowledgeArticle {
  sys_id: string;
  number: string;
  short_description: string;
  category: string;
  author: string;
  updated_on: string;
  state: string;
}

export interface CatalogItem {
  sys_id: string;
  name: string;
  short_description: string;
  category: string;
  price: string;
}

export interface SnowApproval {
  sys_id: string;
  approver: string;
  document: string;
  state: string;
  due_date: string;
  created_on: string;
}

export interface SnowData {
  type:
    | 'incidents'
    | 'requests'
    | 'request_items'
    | 'form'
    | 'change_requests'
    | 'problems'
    | 'knowledge_articles'
    | 'service_catalog'
    | 'approvals';
  entity?: 'incident' | 'request';
  prefill?: Record<string, string>;
  total?: number;
  incidents?: Incident[];
  requests?: ServiceRequest[];
  items?: any[];
  error?: boolean;
  message?: string;
  _createdId?: string;
}
