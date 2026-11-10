import type { Tone } from "@/components/ui/badge";
import type { ItemCategory, ItemStatus } from "@/types/api";

export const CATEGORY_LABELS: Record<ItemCategory, string> = {
  milestone: "Milestone",
  extra: "Extra",
  fixed: "Fixed fee",
  hourly: "Hourly",
  expense: "Expense",
  other: "Other",
};

export const ROLE_LABELS: Record<string, string> = {
  contract_term: "Contract term",
  request: "Request",
  price: "Price quoted",
  approval: "Approval",
  completion: "Delivery",
  acceptance: "Acceptance",
  other: "Context",
};

export const ROLE_TONES: Record<string, Tone> = {
  contract_term: "violet",
  request: "slate",
  price: "blue",
  approval: "green",
  completion: "slate",
  acceptance: "green",
  other: "slate",
};

export const FLAG_LABELS: Record<string, string> = {
  missing_approval: "Missing approval",
  conflicting_price: "Conflicting prices",
  unclear_price: "Unclear price",
  not_ready: "Not ready to invoice",
  low_confidence: "Low confidence",
  unsupported: "No verified source",
};

export const STATUS_LABELS: Record<ItemStatus, string> = {
  pending: "Needs decision",
  approved: "Approved",
  excluded: "Excluded",
};
