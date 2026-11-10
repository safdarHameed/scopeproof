"use client";

import { AlertTriangle, BadgeCheck, ExternalLink } from "lucide-react";

import { DocumentIcon } from "@/components/documents/document-icon";
import { ROLE_LABELS, ROLE_TONES } from "@/components/review/labels";
import { Badge } from "@/components/ui/badge";
import { displayName, formatDate } from "@/lib/format";
import type { DocumentMeta, Evidence } from "@/types/api";

export function EvidenceList({
  evidence,
  documents,
  onOpen,
}: {
  evidence: Evidence[];
  documents: Map<string, DocumentMeta>;
  onOpen: (documentId: string, quote: string) => void;
}) {
  if (evidence.length === 0) {
    return <p className="text-sm text-slate-500">No supporting quotes. Added by hand.</p>;
  }
  return (
    <ol className="space-y-2.5">
      {evidence.map((ev) => {
        const doc = ev.document_id ? documents.get(ev.document_id) : undefined;
        return (
          <li key={ev.id} className="rounded-xl border border-slate-200 bg-slate-50/60 p-3">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <Badge tone={ROLE_TONES[ev.role] ?? "slate"}>{ROLE_LABELS[ev.role] ?? ev.role}</Badge>
              {doc ? (
                <span className="flex min-w-0 items-center gap-1.5">
                  <DocumentIcon kind={doc.kind} className="size-3.5 shrink-0" />
                  <span className="truncate">
                    {doc.kind === "email"
                      ? `${displayName(doc.author)}, ${formatDate(doc.sent_at)}`
                      : doc.title || doc.filename}
                    {ev.location && ` · ${ev.location}`}
                  </span>
                </span>
              ) : (
                <span>Source document not found</span>
              )}
              <span className="ml-auto flex items-center gap-1">
                {ev.verified ? (
                  <span className="flex items-center gap-1 text-brand-700" title="Quote found word for word in the document">
                    <BadgeCheck className="size-3.5" /> Verified quote
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-amber-700">
                    <AlertTriangle className="size-3.5" /> Not found in documents
                  </span>
                )}
              </span>
            </div>
            <blockquote className="mt-2 border-l-2 border-slate-300 pl-3 text-sm text-slate-800">
              &ldquo;{ev.quote}&rdquo;
            </blockquote>
            {ev.document_id && doc && (
              <button
                type="button"
                onClick={() => onOpen(ev.document_id!, ev.quote)}
                className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-brand-700 hover:underline"
              >
                Show in {doc.kind === "email" ? "email" : "document"}
                <ExternalLink className="size-3" />
              </button>
            )}
          </li>
        );
      })}
    </ol>
  );
}
