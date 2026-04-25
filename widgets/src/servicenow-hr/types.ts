export interface HRCase {
  sys_id: string;
  number: string;
  opened_for: string;
  hr_service?: string;
  subject: string;
  description?: string;
  state: string;
  priority: string;
  sys_created_on: string;
}

export interface HRService {
  sys_id: string;
  name: string;
  category: string;
  short_description: string;
}

export interface HRApproval {
  sys_id: string;
  approver: string;
  document: string;
  state: string;
  due_date: string;
}

export type HRData = {
  type: 'hr_cases' | 'hr_services' | 'hr_approvals' | 'form';
  entity?: 'hr_case';
  prefill?: Record<string, string>;
  fkSelections?: Record<string, { label: string; options: { id: string; name: string }[] }>;
  total?: number;
  items?: HRCase[] | HRService[] | HRApproval[];
  error?: boolean;
  message?: string;
};
