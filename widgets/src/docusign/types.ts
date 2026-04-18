/* ── DocuSign structured-content data shapes ─────────────────────────────── */

/** Envelope row from ds__get_envelopes */
export interface Envelope {
  envelopeId: string;
  emailSubject: string;
  status: string;
  statusEmoji: string;
  sentDateTime: string;
  completedDateTime?: string;
  recipientCount?: number;
}

/** Signer within envelope detail */
export interface Signer {
  name: string;
  email: string;
  status: string;
  signedDateTime?: string;
  deliveredDateTime?: string;
}

/** Envelope detail from ds__get_envelope_details */
export interface EnvelopeDetail {
  envelopeId: string;
  emailSubject: string;
  status: string;
  statusEmoji: string;
  sentDateTime: string;
  completedDateTime?: string;
  signers: Signer[];
}

/** Template row from ds__get_templates */
export interface Template {
  templateId: string;
  name: string;
  description: string;
  lastModified: string;
  folderName: string;
}

/* ── Structured-content wrapper types ───────────────────────────────────── */

export interface DsEnvelopesData {
  type: 'envelopes';
  data: Envelope[];
}

export interface DsEnvelopeDetailData {
  type: 'envelope_detail';
  data: EnvelopeDetail;
}

export interface DsTemplatesData {
  type: 'templates';
  data: Template[];
}

export interface DsFormData {
  type: 'form';
  entity: 'send_envelope';
  prefill?: Record<string, string>;
}

export type DsData =
  | DsEnvelopesData
  | DsEnvelopeDetailData
  | DsTemplatesData
  | DsFormData;
