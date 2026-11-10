// Decimal values arrive from the API as strings (e.g. "600.00") to avoid float rounding.
export type Money = string;

export interface ProjectStats {
  document_count: number;
  item_count: number;
  pending_count: number;
  flagged_count: number;
  approved_total: number;
  invoice_status: InvoiceStatus | null;
  invoice_number: string | null;
}

export interface Project {
  id: string;
  name: string;
  description: string | null;
  currency: string;
  client_name: string;
  client_email: string;
  client_company: string | null;
  client_address: string | null;
  created_at: string;
  updated_at: string;
  stats: ProjectStats;
}

export interface ProjectPayload {
  name: string;
  description?: string | null;
  currency: string;
  client_name: string;
  client_email: string;
  client_company?: string | null;
  client_address?: string | null;
}

export type DocumentKind = "contract" | "email" | "note";

export interface DocumentMeta {
  id: string;
  filename: string;
  source_path: string;
  kind: DocumentKind;
  content_type: string;
  size_bytes: number;
  status: "processed" | "failed";
  error: string | null;
  title: string | null;
  author: string | null;
  recipients: string | null;
  sent_at: string | null;
  word_count: number;
  created_at: string;
}

export interface DocumentDetail extends DocumentMeta {
  message_id: string | null;
  in_reply_to: string | null;
  text: string;
}

export interface UploadResult {
  documents: DocumentMeta[];
  skipped: { filename: string; reason: string }[];
}

export type ItemStatus = "pending" | "approved" | "excluded";
export type ItemCategory = "milestone" | "extra" | "fixed" | "hourly" | "expense" | "other";

export interface Flag {
  code: string;
  message: string;
}

export interface Evidence {
  id: string;
  document_id: string | null;
  role: string;
  quote: string;
  location: string | null;
  verified: boolean;
}

export interface Item {
  id: string;
  origin: "analysis" | "manual";
  category: ItemCategory;
  description: string;
  rationale: string | null;
  quantity: Money;
  unit_price: Money | null;
  amount: Money | null;
  status: ItemStatus;
  flags: Flag[];
  flags_acknowledged: boolean;
  confidence: number | null;
  edited: boolean;
  position: number;
  evidence: Evidence[];
  created_at: string;
  updated_at: string;
}

export interface ItemPayload {
  description?: string;
  category?: ItemCategory;
  rationale?: string | null;
  quantity?: string;
  unit_price?: string | null;
  status?: ItemStatus;
  acknowledge_flags?: boolean;
}

export interface AnalysisRun {
  id: string;
  engine: string;
  status: "running" | "completed" | "failed";
  document_count: number;
  item_count: number;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface ReviewState {
  analysis: AnalysisRun | null;
  items: Item[];
  approved_total: Money;
  pending_count: number;
  flagged_count: number;
  locked: boolean;
  currency: string;
}

export type InvoiceStatus = "confirmed" | "sent" | "paid" | "cancelled" | "refunded";

export interface InvoiceLine {
  id: string;
  item_id: string | null;
  description: string;
  quantity: Money;
  unit_price: Money;
  amount: Money;
  evidence_count: number;
}

export interface Invoice {
  id: string;
  project_id: string;
  number: string;
  status: InvoiceStatus;
  currency: string;
  total: Money;
  issue_date: string;
  due_date: string;
  note: string | null;
  client_name: string;
  client_email: string;
  client_company: string | null;
  provider: string | null;
  provider_invoice_id: string | null;
  provider_status: string | null;
  payment_url: string | null;
  sent_at: string | null;
  paid_at: string | null;
  last_synced_at: string | null;
  created_at: string;
  lines: InvoiceLine[];
}

export interface InvoiceState {
  invoice: Invoice | null;
  history: Invoice[];
  provider: string;
  provider_label: string;
}
