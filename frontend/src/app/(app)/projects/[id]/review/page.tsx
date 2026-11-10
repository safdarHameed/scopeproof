"use client";

import { CheckCheck, FileSearch, Lock, Plus, ReceiptText, Sparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { DocumentViewer } from "@/components/documents/document-viewer";
import { useProject } from "@/components/projects/project-context";
import { ConfirmInvoiceDialog } from "@/components/review/confirm-invoice-dialog";
import { ItemCard } from "@/components/review/item-card";
import { ItemForm } from "@/components/review/item-form";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, EmptyState } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { PageSpinner, Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/cn";
import { documentsApi, errorMessage, reviewApi } from "@/lib/api";
import { formatDate, formatMoney, plural } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { Item, ItemPayload, ReviewState } from "@/types/api";

type Filter = "all" | "pending" | "approved" | "excluded";

export default function ReviewPage() {
  const { project, refreshProject } = useProject();
  const router = useRouter();
  const review = useResource(`review:${project.id}`, () => reviewApi.get(project.id));
  const docs = useResource(`docs:${project.id}`, () => documentsApi.list(project.id));
  const [filter, setFilter] = useState<Filter>("all");
  const [source, setSource] = useState<{ documentId: string; quote: string } | null>(null);
  const [adding, setAdding] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState<"analyze" | "approve" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const documents = useMemo(() => new Map((docs.data ?? []).map((d) => [d.id, d])), [docs.data]);
  const state = review.data;

  async function apply(next: ReviewState | Promise<ReviewState | null>) {
    const value = await next;
    if (value) review.setData(value);
    await refreshProject();
  }

  async function analyze() {
    setBusy("analyze");
    setError(null);
    try {
      await apply(reviewApi.analyze(project.id));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function approveClear() {
    setBusy("approve");
    setError(null);
    try {
      await apply(reviewApi.approveClear(project.id));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function updateItem(item: Item, data: ItemPayload) {
    await reviewApi.updateItem(project.id, item.id, data);
    await apply(review.reload());
  }

  async function deleteItem(item: Item) {
    await reviewApi.removeItem(project.id, item.id);
    await apply(review.reload());
  }

  if (review.loading || docs.loading) return <PageSpinner />;
  if (!state) return <Alert kind="error">{review.error}</Alert>;

  const items = state.items;
  const approved = items.filter((i) => i.status === "approved");
  const clearCount = items.filter(
    (i) => i.status === "pending" && i.flags.length === 0 && i.unit_price !== null,
  ).length;
  const counts: Record<Filter, number> = {
    all: items.length,
    pending: state.pending_count,
    approved: approved.length,
    excluded: items.filter((i) => i.status === "excluded").length,
  };
  const visible = filter === "all" ? items : items.filter((i) => i.status === filter);
  const canConfirm = !state.locked && state.pending_count === 0 && approved.length > 0;

  if (items.length === 0) {
    return (
      <>
        {error && <Alert kind="error" className="mb-6">{error}</Alert>}
        {state.analysis?.status === "completed" ? (
          <EmptyState
            icon={FileSearch}
            title="No billable work found"
            action={
              <>
                <Button variant="secondary" onClick={() => setAdding(true)}>
                  <Plus className="size-4" /> Add item by hand
                </Button>
                <ButtonLink href={`/projects/${project.id}`}>Back to documents</ButtonLink>
              </>
            }
          >
            The analysis of {plural(state.analysis.document_count, "document")} didn&apos;t find
            agreed work with a price. Add items by hand or upload more documents.
          </EmptyState>
        ) : (
          <EmptyState
            icon={Sparkles}
            title="Nothing to review yet"
            action={
              project.stats.document_count > 0 ? (
                <Button onClick={analyze} disabled={busy !== null}>
                  {busy === "analyze" ? <Spinner /> : <Sparkles className="size-4" />}
                  Analyze {plural(project.stats.document_count, "document")}
                </Button>
              ) : (
                <ButtonLink href={`/projects/${project.id}`}>Upload documents</ButtonLink>
              )
            }
          >
            Analyze the uploaded contract and emails to get suggested invoice items, each backed
            by quotes from your documents.
          </EmptyState>
        )}
        <AddItemDialog
          open={adding}
          onClose={() => setAdding(false)}
          currency={project.currency}
          onSubmit={async (data) => {
            await reviewApi.addItem(project.id, data);
            setAdding(false);
            await apply(review.reload());
          }}
        />
      </>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_19rem]">
      <div className="min-w-0">
        {state.locked && (
          <Alert
            kind="info"
            className="mb-6"
            title={`Invoice ${project.stats.invoice_number ?? ""} is ${project.stats.invoice_status}`}
            action={
              <Link href={`/projects/${project.id}/invoice`} className="font-medium underline">
                View invoice
              </Link>
            }
          >
            Items are locked while an invoice exists.
          </Alert>
        )}
        {error && <Alert kind="error" className="mb-6">{error}</Alert>}

        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-1 rounded-xl bg-slate-200/60 p-1" role="tablist">
            {(["all", "pending", "approved", "excluded"] as Filter[]).map((f) => (
              <button
                key={f}
                role="tab"
                aria-selected={filter === f}
                onClick={() => setFilter(f)}
                className={cn(
                  "rounded-lg px-3 py-1.5 text-sm font-medium transition",
                  filter === f ? "bg-white text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900",
                )}
              >
                {{ all: "All", pending: "To decide", approved: "Approved", excluded: "Excluded" }[f]}
                <span className="ml-1.5 text-xs text-slate-500">{counts[f]}</span>
              </button>
            ))}
          </div>
          {!state.locked && (
            <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <Plus className="size-4" /> Add item
            </Button>
          )}
        </div>

        <div className="space-y-4">
          {visible.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
              No items here.
            </p>
          ) : (
            visible.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
                currency={state.currency}
                documents={documents}
                locked={state.locked}
                onUpdate={(data) => updateItem(item, data)}
                onDelete={() => deleteItem(item)}
                onOpenSource={(documentId, quote) => setSource({ documentId, quote })}
              />
            ))
          )}
        </div>
      </div>

      <aside className="space-y-4 lg:sticky lg:top-6 lg:self-start">
        <Card className="p-5">
          <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">Invoice total</p>
          <p className="mt-1 font-mono text-3xl font-semibold text-slate-900">
            {formatMoney(state.approved_total, state.currency)}
          </p>
          <p className="mt-1 text-sm text-slate-600">from {plural(approved.length, "approved item")}</p>

          <dl className="mt-5 space-y-2 border-t border-slate-100 pt-4 text-sm">
            <Row label="To decide" value={state.pending_count} tone={state.pending_count ? "amber" : undefined} />
            <Row label="Flagged for review" value={state.flagged_count} tone={state.flagged_count ? "amber" : undefined} />
            <Row label="Excluded" value={counts.excluded} />
          </dl>

          {state.locked ? (
            <ButtonLink href={`/projects/${project.id}/invoice`} className="mt-5 w-full">
              <ReceiptText className="size-4" /> View invoice
            </ButtonLink>
          ) : (
            <>
              {clearCount > 0 && (
                <Button
                  variant="secondary"
                  className="mt-5 w-full"
                  onClick={approveClear}
                  disabled={busy !== null}
                >
                  {busy === "approve" ? <Spinner /> : <CheckCheck className="size-4" />}
                  Approve {plural(clearCount, "clear item")}
                </Button>
              )}
              <Button
                className="mt-3 w-full"
                disabled={!canConfirm}
                onClick={() => setConfirming(true)}
              >
                <Lock className="size-4" /> Confirm invoice draft
              </Button>
              {!canConfirm && (
                <p className="mt-2 text-xs text-slate-500">
                  {state.pending_count > 0
                    ? "Approve or exclude every item to continue."
                    : "Approve at least one item to continue."}
                </p>
              )}
            </>
          )}
        </Card>

        {state.analysis && (
          <div className="px-1 text-xs text-slate-500">
            <p>
              Analyzed {plural(state.analysis.document_count, "document")} on{" "}
              {formatDate(state.analysis.created_at, true)} ({state.analysis.engine} engine).
            </p>
            {state.analysis.engine === "placeholder" && (
              <p className="mt-1">
                The placeholder engine is a stand-in until the AI analysis is connected.
              </p>
            )}
          </div>
        )}
      </aside>

      <DocumentViewer
        projectId={project.id}
        documentId={source?.documentId ?? null}
        highlight={source?.quote}
        onClose={() => setSource(null)}
      />

      <AddItemDialog
        open={adding}
        onClose={() => setAdding(false)}
        currency={project.currency}
        onSubmit={async (data) => {
          await reviewApi.addItem(project.id, data);
          setAdding(false);
          await apply(review.reload());
        }}
      />

      <ConfirmInvoiceDialog
        open={confirming}
        onClose={() => setConfirming(false)}
        project={project}
        lineCount={approved.length}
        total={state.approved_total}
        onConfirmed={async () => {
          setConfirming(false);
          await refreshProject();
          router.push(`/projects/${project.id}/invoice`);
        }}
      />
    </div>
  );
}

function Row({ label, value, tone }: { label: string; value: number; tone?: "amber" }) {
  return (
    <div className="flex justify-between">
      <dt className="text-slate-600">{label}</dt>
      <dd className={cn("font-medium", tone === "amber" ? "text-amber-700" : "text-slate-900")}>
        {value}
      </dd>
    </div>
  );
}

function AddItemDialog({
  open,
  onClose,
  currency,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  currency: string;
  onSubmit: (data: ItemPayload) => Promise<void>;
}) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Add an invoice item"
      description="For billable work that isn't in the documents, like an expense. Items with a price are approved right away."
    >
      <ItemForm currency={currency} submitLabel="Add item" onCancel={onClose} onSubmit={onSubmit} />
    </Dialog>
  );
}
