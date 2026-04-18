export interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  company: string;
  email: string;
  phone: string;
  status: string;
  lead_source: string;
}

export interface Opportunity {
  id: string;
  name: string;
  account_name: string;
  stage: string;
  amount: number | null;
  close_date: string;
  probability: number | null;
}

export interface SfListData {
  type: 'leads' | 'opportunities' | 'accounts' | 'contacts';
  total: number;
  items: (Lead | Opportunity)[];
  error?: boolean;
  message?: string;
  _createdId?: string;
}

export interface SfFormData {
  type: 'form';
  entity: 'lead' | 'account' | 'contact';
  prefill?: Record<string, string>;
}

export type SfData = SfListData | SfFormData;
