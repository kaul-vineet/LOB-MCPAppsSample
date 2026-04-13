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

export type HubSpotViewType = 'emails' | 'lists' | 'list_contacts';

export interface HubSpotData {
  type: HubSpotViewType;
  total?: number;
  items?: (Email | ContactList | Contact)[];
  list_id?: string;
  list_name?: string;
}
