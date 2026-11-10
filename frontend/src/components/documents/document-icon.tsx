import { FileSignature, FileText, Mail } from "lucide-react";

import type { DocumentKind } from "@/types/api";

export const KIND_LABELS: Record<DocumentKind, string> = {
  contract: "Contract",
  email: "Email",
  note: "Other document",
};

export function DocumentIcon({ kind, className }: { kind: DocumentKind; className?: string }) {
  const Icon = kind === "email" ? Mail : kind === "contract" ? FileSignature : FileText;
  return <Icon className={className} />;
}
