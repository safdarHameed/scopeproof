"use client";

import { AlertCircle, Download, Eye, Sparkles, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { DocumentIcon, KIND_LABELS } from "@/components/documents/document-icon";
import { DocumentViewer } from "@/components/documents/document-viewer";
import { UploadSummary, Uploader } from "@/components/documents/uploader";
import { useProject } from "@/components/projects/project-context";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import { documentsApi, errorMessage, reviewApi } from "@/lib/api";
import { displayName, formatDate, plural } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { DocumentKind, DocumentMeta, UploadResult } from "@/types/api";

const GROUPS: { kind: DocumentKind; title: string; empty: string }[] = [
  { kind: "contract", title: "Contract", empty: "No contract yet. Upload the signed agreement." },
  { kind: "email", title: "Client conversation", empty: "No emails yet." },
  { kind: "note", title: "Other documents", empty: "" },
];

export default function DocumentsPage() {
  const { project, refreshProject } = useProject();
  const router = useRouter();
  const docs = useResource(`docs:${project.id}`, () => documentsApi.list(project.id));
  const [viewing, setViewing] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [confirmReanalyze, setConfirmReanalyze] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpload, setLastUpload] = useState<UploadResult | null>(null);

  const documents = docs.data ?? [];
  const readable = documents.filter((d) => d.status === "processed");
  const locked = project.stats.invoice_status !== null;
  const hasItems = project.stats.item_count > 0;

  async function refreshAll() {
    await Promise.all([docs.reload(), refreshProject()]);
  }

  async function onUploaded(result: UploadResult) {
    setLastUpload(result);
    await refreshAll();
  }

  async function analyze() {
    setConfirmReanalyze(false);
    setAnalyzing(true);
    setError(null);
    try {
      await reviewApi.analyze(project.id);
      await refreshProject();
      router.push(`/projects/${project.id}/review`);
    } catch (err) {
      setError(errorMessage(err));
      setAnalyzing(false);
    }
  }

  async function changeKind(doc: DocumentMeta, kind: DocumentKind) {
    try {
      const updated = await documentsApi.setKind(project.id, doc.id, kind);
      docs.setData(documents.map((d) => (d.id === doc.id ? updated : d)));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(doc: DocumentMeta) {
    try {
      await documentsApi.remove(project.id, doc.id);
      await refreshAll();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (docs.loading) return <PageSpinner />;

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_20rem]">
      <div className="min-w-0 space-y-8">
        {error && <Alert kind="error">{error}</Alert>}
        {docs.error && <Alert kind="error">{docs.error}</Alert>}
        {lastUpload && <UploadSummary result={lastUpload} />}

        {documents.length === 0 ? (
          <Uploader projectId={project.id} onUploaded={onUploaded} />
        ) : (
          GROUPS.map((group) => {
            const inGroup = documents.filter((d) => d.kind === group.kind);
            if (inGroup.length === 0 && !group.empty) return null;
            return (
              <section key={group.kind}>
                <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
                  {group.title}
                  <span className="font-normal text-slate-500">{inGroup.length || ""}</span>
                </h2>
                {inGroup.length === 0 ? (
                  <p className="rounded-xl border border-dashed border-slate-300 px-4 py-3 text-sm text-slate-500">
                    {group.empty}
                  </p>
                ) : (
                  <Card className="divide-y divide-slate-100 overflow-hidden">
                    {inGroup.map((doc) => (
                      <DocumentRow
                        key={doc.id}
                        doc={doc}
                        onView={() => setViewing(doc.id)}
                        onDownload={() => documentsApi.download(project.id, doc)}
                        onKindChange={(kind) => changeKind(doc, kind)}
                        onDelete={() => remove(doc)}
                      />
                    ))}
                  </Card>
                )}
              </section>
            );
          })
        )}
      </div>

      <aside className="space-y-6 lg:sticky lg:top-6 lg:self-start">
        <Card className="p-5">
          <h2 className="font-semibold text-slate-900">Find what&apos;s billable</h2>
          <p className="mt-1 text-sm text-slate-600">
            ScopeProof reads every document and suggests invoice items for agreed work, with the
            quotes that back them up. Unclear or unapproved work gets flagged.
          </p>
          <dl className="mt-4 space-y-1 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Readable documents</dt>
              <dd className="font-medium text-slate-900">{readable.length}</dd>
            </div>
            {documents.length > readable.length && (
              <div className="flex justify-between text-red-700">
                <dt>Couldn&apos;t be read</dt>
                <dd className="font-medium">{documents.length - readable.length}</dd>
              </div>
            )}
          </dl>
          {locked ? (
            <Alert kind="info" className="mt-4">
              An invoice exists for this project, so analysis is locked.
            </Alert>
          ) : (
            <Button
              className="mt-5 w-full"
              disabled={readable.length === 0 || analyzing}
              onClick={() => (hasItems ? setConfirmReanalyze(true) : analyze())}
            >
              {analyzing ? <Spinner /> : <Sparkles className="size-4" />}
              {analyzing ? "Analyzing…" : hasItems ? "Analyze again" : "Analyze documents"}
            </Button>
          )}
        </Card>

        {documents.length > 0 && (
          <div>
            <h2 className="mb-3 text-sm font-semibold text-slate-900">Add more files</h2>
            <Uploader projectId={project.id} onUploaded={onUploaded} compact />
          </div>
        )}
      </aside>

      <DocumentViewer
        projectId={project.id}
        documentId={viewing}
        onClose={() => setViewing(null)}
      />

      <Dialog
        open={confirmReanalyze}
        onClose={() => setConfirmReanalyze(false)}
        title="Analyze again?"
        description="The current suggestions, including your edits and decisions on them, will be replaced. Items you added by hand are kept."
      >
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setConfirmReanalyze(false)}>
            Cancel
          </Button>
          <Button onClick={analyze}>Replace suggestions</Button>
        </div>
      </Dialog>
    </div>
  );
}

function DocumentRow({
  doc,
  onView,
  onDownload,
  onKindChange,
  onDelete,
}: {
  doc: DocumentMeta;
  onView: () => void;
  onDownload: () => void;
  onKindChange: (kind: DocumentKind) => void;
  onDelete: () => void;
}) {
  const failed = doc.status === "failed";
  const from = displayName(doc.author);
  const to = displayName(doc.recipients?.split(",")[0]);
  return (
    <div className="flex items-center gap-3 px-4 py-3 hover:bg-slate-50">
      <span
        className={
          failed
            ? "grid size-9 shrink-0 place-items-center rounded-lg bg-red-50 text-red-600"
            : "grid size-9 shrink-0 place-items-center rounded-lg bg-slate-100 text-slate-600"
        }
      >
        {failed ? <AlertCircle className="size-4" /> : <DocumentIcon kind={doc.kind} className="size-4" />}
      </span>
      <button type="button" onClick={onView} className="min-w-0 flex-1 text-left">
        <p className="truncate text-sm font-medium text-slate-900">{doc.title || doc.filename}</p>
        <p className="truncate text-xs text-slate-500">
          {failed ? (
            <span className="text-red-700">{doc.error}</span>
          ) : doc.kind === "email" ? (
            <>
              {from}
              {to && ` → ${to}`} · {formatDate(doc.sent_at, true)}
            </>
          ) : (
            <>
              {doc.filename} · {plural(doc.word_count, "word")}
            </>
          )}
        </p>
      </button>
      <select
        aria-label="Document type"
        value={doc.kind}
        onChange={(e) => onKindChange(e.target.value as DocumentKind)}
        className="hidden h-8 rounded-lg border border-slate-200 bg-white px-2 text-xs text-slate-700 sm:block"
      >
        {(Object.keys(KIND_LABELS) as DocumentKind[]).map((k) => (
          <option key={k} value={k}>
            {KIND_LABELS[k]}
          </option>
        ))}
      </select>
      <div className="flex shrink-0">
        <IconButton label="View text" onClick={onView} icon={Eye} />
        <IconButton label="Download original" onClick={onDownload} icon={Download} />
        <IconButton label="Delete" onClick={onDelete} icon={Trash2} />
      </div>
    </div>
  );
}

function IconButton({
  label,
  onClick,
  icon: Icon,
}: {
  label: string;
  onClick: () => void;
  icon: typeof Eye;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
    >
      <Icon className="size-4" />
    </button>
  );
}

