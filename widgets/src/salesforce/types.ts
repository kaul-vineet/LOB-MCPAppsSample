// ── Salesforce Entity Types ───────────────────────────────────────────────

export interface Account {
  id: string;
  Name: string;
  Industry?: string;
  Phone?: string;
  Website?: string;
  BillingCity?: string;
  Type?: string;
  NumberOfEmployees?: number | null;
}

export interface Lead {
  id: string;
  FirstName?: string;
  LastName: string;
  Company: string;
  Email?: string;
  Phone?: string;
  Status: string;
  LeadSource?: string;
  // legacy snake_case aliases (kept for backward compat)
  first_name?: string;
  last_name?: string;
  company?: string;
  email?: string;
  phone?: string;
  status?: string;
  lead_source?: string;
}

export interface Contact {
  id: string;
  FirstName?: string;
  LastName: string;
  Email?: string;
  Phone?: string;
  Title?: string;
  AccountId?: string;
  account_name?: string;
}

export interface Opportunity {
  id: string;
  Name: string;
  AccountId?: string;
  account_name?: string;
  StageName: string;
  Amount?: number | null;
  CloseDate?: string;
  Probability?: number | null;
  // legacy snake_case aliases
  name?: string;
  stage?: string;
  amount?: number | null;
  close_date?: string;
  probability?: number | null;
}

export interface Case {
  id: string;
  CaseNumber?: string;
  Subject: string;
  Status: string;
  Priority: string;
  AccountId?: string;
  account_name?: string;
  CreatedDate?: string;
}

export interface Task {
  id: string;
  Subject: string;
  Status: string;
  Priority: string;
  ActivityDate?: string;
  WhoId?: string;
  WhatId?: string;
}

export interface Campaign {
  id: string;
  Name: string;
  Status: string;
  Type?: string;
  StartDate?: string;
  EndDate?: string;
  NumberOfLeads?: number | null;
}

export interface CaseComment {
  id: string;
  Body: string;
  CreatedDate?: string;
  created_by_name?: string;
}

// ── Approval ──────────────────────────────────────────────────────────────
export interface Approval {
  id: string;
  target_name?: string;
  Status?: string;
  CreatedDate?: string;
}

// ── List data ─────────────────────────────────────────────────────────────
export interface SfListData {
  type: 'accounts' | 'leads' | 'contacts' | 'opportunities' | 'cases' | 'tasks' | 'campaigns' | 'approvals';
  total?: number;
  items: any[];
  error?: boolean;
  message?: string;
  _createdId?: string;
}

// ── Form data ─────────────────────────────────────────────────────────────
export interface SfFormData {
  type: 'form';
  entity: 'account' | 'lead' | 'contact' | 'opportunity' | 'case' | 'task' | 'campaign';
  prefill?: Record<string, string>;
}

// ── Dashboard data ────────────────────────────────────────────────────────
export interface SalesDashboardData {
  type: 'sales_dashboard';
  pipeline_by_stage: { stage: string; count: number; amount: number }[];
  closed_won_this_month: number;
  closed_lost_this_month: number;
  top_accounts: { id: string; name: string; amount: number }[];
}

export interface SupportDashboardData {
  type: 'support_dashboard';
  by_status: { status: string; count: number }[];
  by_priority: { priority: string; count: number }[];
  opened_this_month: number;
  total_open: number;
}

// ── Lead Convert result ────────────────────────────────────────────────────
export interface LeadConvertData {
  type: 'lead_convert';
  leadId: string;
  accountId: string;
  contactId: string;
  opportunityId?: string;
}

// ── Error data ────────────────────────────────────────────────────────────
export interface SfErrorData {
  error: true;
  message: string;
  type?: string;
}

// ── Detail views (legacy) ─────────────────────────────────────────────────
export interface LeadDetail {
  id: string;
  first_name: string;
  last_name: string;
  company: string;
  email: string;
  phone: string;
  status: string;
  lead_source: string;
  title?: string;
  website?: string;
  description?: string;
  annual_revenue?: number | null;
  number_of_employees?: number | null;
  created_date?: string;
}

export interface CaseDetail {
  id: string;
  case_number: string;
  subject: string;
  status: string;
  priority: string;
  origin?: string;
  type?: string;
  account_name?: string;
  description?: string;
  comments?: string;
  created_date?: string;
  closed_date?: string;
}

export interface TaskDetail {
  id: string;
  subject: string;
  status: string;
  priority: string;
  activity_date?: string;
  description?: string;
  who_id?: string;
  what_id?: string;
  created_date?: string;
}

export interface SfDetailData {
  type: 'lead_detail' | 'case_detail' | 'task_detail';
  record: LeadDetail | CaseDetail | TaskDetail;
}

// ── Union type ────────────────────────────────────────────────────────────
export type SfData =
  | SfListData
  | SfFormData
  | SalesDashboardData
  | SupportDashboardData
  | LeadConvertData
  | SfDetailData
  | SfErrorData;
