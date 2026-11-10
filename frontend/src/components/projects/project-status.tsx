import { Badge, type Tone } from "@/components/ui/badge";
import type { Project } from "@/types/api";

/** One-line summary of where a project is in the upload → review → invoice flow. */
export function projectStatus(project: Project): { label: string; tone: Tone } {
  const s = project.stats;
  if (s.invoice_status === "paid") return { label: "Paid", tone: "green" };
  if (s.invoice_status === "sent") return { label: "Awaiting payment", tone: "blue" };
  if (s.invoice_status === "refunded") return { label: "Refunded", tone: "slate" };
  if (s.invoice_status === "confirmed") return { label: "Invoice ready to send", tone: "violet" };
  if (s.document_count === 0) return { label: "No documents", tone: "slate" };
  if (s.item_count === 0) return { label: "Ready to analyze", tone: "slate" };
  if (s.flagged_count > 0) return { label: `${s.flagged_count} flagged`, tone: "amber" };
  if (s.pending_count > 0) return { label: `${s.pending_count} to review`, tone: "amber" };
  return { label: "Ready to invoice", tone: "green" };
}

export function ProjectStatusBadge({ project }: { project: Project }) {
  const { label, tone } = projectStatus(project);
  return <Badge tone={tone}>{label}</Badge>;
}
