"use client";

import { Download, X } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";

import { DocumentIcon, KIND_LABELS } from "@/components/documents/document-icon";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PageSpinner } from "@/components/ui/spinner";
import { documentsApi } from "@/lib/api";
import { formatBytes, formatDate } from "@/lib/format";
import { useResource } from "@/lib/use-resource";

/** Side panel that shows a document's extracted text, optionally highlighting a quote. */
export function DocumentViewer({
  projectId,
  documentId,
  highlight,
  onClose,
}: {
  projectId: string;
  documentId: string | null;
  highlight?: string | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!documentId) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [documentId, onClose]);

  if (!documentId) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true">
      <button
        type="button"
        aria-label="Close document"
        className="absolute inset-0 bg-slate-900/30 backdrop-blur-[1px]"
        onClick={onClose}
      />
      <div className="relative flex h-full w-full max-w-2xl flex-col bg-white shadow-2xl">
        <ViewerBody
          key={`${documentId}:${highlight ?? ""}`}
          projectId={projectId}
          documentId={documentId}
          highlight={highlight ?? null}
          onClose={onClose}
        />
      </div>
    </div>
  );
}

function ViewerBody({
  projectId,
  documentId,
  highlight,
  onClose,
}: {
  projectId: string;
  documentId: string;
  highlight: string | null;
  onClose: () => void;
}) {
  const { data: doc, error, loading } = useResource(`doc:${documentId}`, () =>
    documentsApi.get(projectId, documentId),
  );
  const markRef = useRef<HTMLElement>(null);

  const parts = useMemo(() => (doc ? splitOnQuote(doc.text, highlight) : null), [doc, highlight]);

  useEffect(() => {
    markRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [parts]);

  return (
    <>
      <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-6 py-4">
        <div className="min-w-0">
          {doc && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <DocumentIcon kind={doc.kind} className="size-3.5" />
              {KIND_LABELS[doc.kind]} · {doc.source_path}
            </div>
          )}
          <h2 className="mt-1 truncate text-lg font-semibold text-slate-900">
            {doc ? doc.title || doc.filename : "Loading…"}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          aria-label="Close"
        >
          <X className="size-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {loading ? (
          <PageSpinner />
        ) : !doc ? (
          <Alert kind="error">{error}</Alert>
        ) : (
          <>
            <dl className="grid grid-cols-[6rem_1fr] gap-x-4 gap-y-1.5 text-sm">
              {doc.author && <Meta label="From">{doc.author}</Meta>}
              {doc.recipients && <Meta label="To">{doc.recipients}</Meta>}
              {doc.sent_at && <Meta label="Date">{formatDate(doc.sent_at, true)}</Meta>}
              <Meta label="File">
                {doc.filename} · {formatBytes(doc.size_bytes)}
              </Meta>
            </dl>

            {highlight && parts && !parts.match && (
              <Alert kind="warning" className="mt-4">
                The quoted passage couldn&apos;t be located exactly in this document.
              </Alert>
            )}
            {doc.status === "failed" && (
              <Alert kind="error" className="mt-4" title="Text couldn't be extracted">
                {doc.error}
              </Alert>
            )}

            <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-5 font-mono text-[13px] leading-relaxed whitespace-pre-wrap text-slate-800">
              {parts?.match ? (
                <>
                  {parts.before}
                  <mark ref={markRef} className="rounded bg-amber-200 px-0.5 text-slate-900">
                    {parts.match}
                  </mark>
                  {parts.after}
                </>
              ) : (
                doc.text || <span className="text-slate-400">No text</span>
              )}
            </div>
          </>
        )}
      </div>

      {doc && (
        <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-6 py-3">
          <Badge>{doc.word_count} words</Badge>
          <Button variant="secondary" size="sm" onClick={() => documentsApi.download(projectId, doc)}>
            <Download className="size-4" /> Original file
          </Button>
        </div>
      )}
    </>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <dt className="text-slate-500">{label}</dt>
      <dd className="min-w-0 break-words text-slate-900">{children}</dd>
    </>
  );
}

/** Finds the quote in the text, tolerant of whitespace and letter case differences. */
function splitOnQuote(text: string, quote: string | null) {
  if (!quote) return { before: text, match: null, after: "" };
  const words = quote.trim().split(/\s+/).map(escapeRegExp);
  if (words.length === 0) return { before: text, match: null, after: "" };
  const found = new RegExp(words.join("\\s+"), "i").exec(text);
  if (!found) return { before: text, match: null, after: "" };
  return {
    before: text.slice(0, found.index),
    match: found[0],
    after: text.slice(found.index + found[0].length),
  };
}

function escapeRegExp(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
