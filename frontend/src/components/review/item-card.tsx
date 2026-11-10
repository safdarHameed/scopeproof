"use client";

import {
  AlertTriangle,
  Ban,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDashed,
  Pencil,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import { EvidenceList } from "@/components/review/evidence-list";
import { ItemForm } from "@/components/review/item-form";
import { CATEGORY_LABELS, FLAG_LABELS } from "@/components/review/labels";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { cn } from "@/lib/cn";
import { errorMessage } from "@/lib/api";
import { formatMoney, formatQuantity } from "@/lib/format";
import type { DocumentMeta, Item, ItemPayload } from "@/types/api";

export function ItemCard({
  item,
  currency,
  documents,
  locked,
  onUpdate,
  onDelete,
  onOpenSource,
}: {
  item: Item;
  currency: string;
  documents: Map<string, DocumentMeta>;
  locked: boolean;
  onUpdate: (data: ItemPayload) => Promise<void>;
  onDelete: () => Promise<void>;
  onOpenSource: (documentId: string, quote: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [showEvidence, setShowEvidence] = useState(item.status === "pending");
  const [confirmFlags, setConfirmFlags] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const flagged = item.flags.length > 0;
  const excluded = item.status === "excluded";
  const approved = item.status === "approved";

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function approve() {
    if (flagged) setConfirmFlags(true);
    else run(() => onUpdate({ status: "approved" }));
  }

  const StatusIcon = approved ? CheckCircle2 : excluded ? Ban : flagged ? AlertTriangle : CircleDashed;

  return (
    <article
      className={cn(
        "rounded-2xl border bg-white shadow-sm transition",
        approved && "border-brand-100",
        excluded && "border-slate-200 bg-slate-50/70",
        !approved && !excluded && (flagged ? "border-amber-200" : "border-slate-200"),
      )}
    >
      <div className="flex gap-4 p-5">
        <StatusIcon
          className={cn(
            "mt-0.5 size-5 shrink-0",
            approved ? "text-brand-600" : excluded ? "text-slate-400" : flagged ? "text-amber-500" : "text-slate-400",
          )}
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
            <div className="min-w-0">
              <h3 className={cn("font-medium text-slate-900", excluded && "text-slate-500 line-through")}>
                {item.description}
              </h3>
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                <Badge>{CATEGORY_LABELS[item.category]}</Badge>
                {item.origin === "manual" && <Badge tone="blue">Added by you</Badge>}
                {item.edited && <Badge tone="blue">Edited</Badge>}
                {approved && <Badge tone="green">Approved</Badge>}
                {excluded && <Badge>Excluded</Badge>}
                {approved && item.flags_acknowledged && <Badge tone="amber">Approved despite flags</Badge>}
                {item.confidence !== null && item.origin === "analysis" && (
                  <span className="text-xs text-slate-500">
                    {Math.round(item.confidence * 100)}% confidence
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              {item.amount !== null ? (
                <p className={cn("font-mono text-lg font-semibold", excluded ? "text-slate-400" : "text-slate-900")}>
                  {formatMoney(item.amount, currency)}
                </p>
              ) : (
                <p className="text-sm font-medium text-amber-700">No price</p>
              )}
              {item.unit_price !== null && Number(item.quantity) !== 1 && (
                <p className="text-xs text-slate-500">
                  {formatQuantity(item.quantity)} × {formatMoney(item.unit_price, currency)}
                </p>
              )}
            </div>
          </div>

          {flagged && !excluded && (
            <ul className="mt-4 space-y-1.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {item.flags.map((flag) => (
                <li key={flag.code} className="flex gap-2">
                  <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
                  <span>
                    <span className="font-medium">{FLAG_LABELS[flag.code] ?? flag.code}:</span>{" "}
                    {flag.message}
                  </span>
                </li>
              ))}
            </ul>
          )}

          {item.rationale && <p className="mt-3 text-sm text-slate-600">{item.rationale}</p>}

          {editing ? (
            <div className="mt-4 rounded-xl border border-slate-200 p-4">
              <ItemForm
                item={item}
                currency={currency}
                submitLabel="Save"
                onCancel={() => setEditing(false)}
                onSubmit={async (data) => {
                  await onUpdate(data);
                  setEditing(false);
                }}
              />
            </div>
          ) : (
            <>
              {item.evidence.length > 0 && (
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={() => setShowEvidence((v) => !v)}
                    className="flex items-center gap-1 text-sm font-medium text-slate-700 hover:text-slate-900"
                    aria-expanded={showEvidence}
                  >
                    <ChevronDown className={cn("size-4 transition", !showEvidence && "-rotate-90")} />
                    Evidence ({item.evidence.length})
                  </button>
                  {showEvidence && (
                    <div className="mt-3">
                      <EvidenceList evidence={item.evidence} documents={documents} onOpen={onOpenSource} />
                    </div>
                  )}
                </div>
              )}

              {error && (
                <Alert kind="error" className="mt-4">
                  {error}
                </Alert>
              )}

              {!locked && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {item.status !== "approved" && (
                    <Button size="sm" onClick={approve} disabled={busy}>
                      <Check className="size-4" /> Approve
                    </Button>
                  )}
                  {item.status !== "excluded" && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => run(() => onUpdate({ status: "excluded" }))}
                      disabled={busy}
                    >
                      <Ban className="size-4" /> Exclude
                    </Button>
                  )}
                  {item.status !== "pending" && (
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => run(() => onUpdate({ status: "pending" }))}
                      disabled={busy}
                    >
                      <RotateCcw className="size-4" /> Undo decision
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => setEditing(true)} disabled={busy}>
                    <Pencil className="size-4" /> Edit
                  </Button>
                  {item.origin === "manual" && (
                    <Button size="sm" variant="ghost" onClick={() => run(onDelete)} disabled={busy}>
                      <Trash2 className="size-4" /> Delete
                    </Button>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <FlagConfirmDialog
        open={confirmFlags}
        item={item}
        onClose={() => setConfirmFlags(false)}
        onConfirm={() => {
          setConfirmFlags(false);
          run(() => onUpdate({ status: "approved", acknowledge_flags: true }));
        }}
      />
    </article>
  );
}

function FlagConfirmDialog({
  open,
  item,
  onClose,
  onConfirm,
}: {
  open: boolean;
  item: Item;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const [checked, setChecked] = useState(false);
  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Approve a flagged item?"
      description={`“${item.description}” has open issues. Only approve it if you have confirmation that isn't in the uploaded documents.`}
    >
      <ul className="space-y-1.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        {item.flags.map((f) => (
          <li key={f.code}>
            <span className="font-medium">{FLAG_LABELS[f.code] ?? f.code}:</span> {f.message}
          </li>
        ))}
      </ul>
      {item.unit_price === null && (
        <Alert kind="error" className="mt-4">
          Set a price with Edit before approving.
        </Alert>
      )}
      <label className="mt-4 flex items-start gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
          className="mt-0.5 size-4 rounded border-slate-300 accent-ink-950"
        />
        I&apos;ve checked these issues and want to bill this item anyway.
      </label>
      <div className="mt-6 flex justify-end gap-3">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={onConfirm} disabled={!checked || item.unit_price === null}>
          Approve anyway
        </Button>
      </div>
    </Dialog>
  );
}
