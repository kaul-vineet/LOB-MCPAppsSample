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

export interface SfData {
  type: 'leads' | 'opportunities';
  total: number;
  items: (Lead | Opportunity)[];
  error?: boolean;
  message?: string;
  _createdId?: string;
}
