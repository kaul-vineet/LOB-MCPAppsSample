export interface EmailStats {
  sent: number;
  delivered: number;
  opened: number;
  clicked: number;
  bounced: number;
  unsubscribed: number;
}

export interface Email {
  id: string;
  name: string;
  subject: string;
  status: string;
  stats: EmailStats;
}

export interface ContactList {
  id: string;
  name: string;
  type: 'MANUAL' | 'DYNAMIC';
  size: number;
}

export interface Contact {
  id: string;
  firstname: string;
  lastname: string;
  email: string;
  phone: string;
  company: string;
  lifecyclestage: string;
}

export interface CrmContact {
  id: string;
  firstname: string;
  lastname: string;
  email: string;
  phone: string;
  company: string;
  jobtitle: string;
  lifecyclestage: string;
}

export interface Company {
  id: string;
  name: string;
  domain: string;
  phone: string;
  city: string;
  industry: string;
}

export interface Deal {
  id: string;
  dealname: string;
  amount?: number;
  dealstage: string;
  closedate?: string;
  pipeline: string;
}

export interface Ticket {
  id: string;
  subject: string;
  status: string;
  priority: string;
  category?: string;
  description?: string;
}

export type HubSpotViewType = 'emails' | 'lists' | 'list_contacts' | 'form' | 'contacts' | 'companies' | 'deals' | 'tickets';

export interface HubSpotData {
  type: HubSpotViewType;
  total?: number;
  items?: (Email | ContactList | Contact | CrmContact | Company | Deal | Ticket)[];
  list_id?: string;
  list_name?: string;
  entity?: 'contact' | 'deal' | 'company' | 'ticket';
  prefill?: Record<string, string>;
}
