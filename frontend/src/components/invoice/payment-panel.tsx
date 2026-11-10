"use client";

import {
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  RefreshCw,
  RotateCcw,
  Send,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/cn";
import { errorMessage, invoiceApi } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import type { InvoiceState } from "@/types/api";

const POLL_MS = 15_000;

type Action = "send" | "refresh" | "cancel" | "reopen";

export function PaymentPanel({
  state,
  projectId,
  onChange,
}: {
  state: InvoiceState;
  projectId: string;
  onChange: (next: InvoiceState) => void | Promise<void>;
}) {
  const invoice = state.invoice!;
  const [busy, setBusy] = useState<Action | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<"send" | "cancel" | null>(null);
  const [copied, setCopied] = useState(false);

  async function run(action: Action) {
    setConfirm(null);
    setBusy(action);
    setError(null);
    try {
      const call = {
        send: invoiceApi.send,
        refresh: invoiceApi.refresh,
        cancel: invoiceApi.cancel,
        reopen: invoiceApi.reopen,
      }[action];
      await onChange(await call(projectId));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  // Keep checking the payment status while the client hasn't paid yet.
  useEffect(() => {
    if (invoice.status !== "sent") return;
    const timer = setInterval(async () => {
      try {
        await onChange(await invoiceApi.refresh(projectId));
      } catch {
        /* the manual refresh button shows errors */
      }
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [invoice.status, projectId, onChange]);

  async function copyLink() {
    if (!invoice.payment_url) return;
    await navigator.clipboard.writeText(invoice.payment_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="space-y-4">
      <Card className="p-5">
        {invoice.status === "confirmed" && (
          <>
            <h2 className="font-semibold text-slate-900">Send to {invoice.client_name}</h2>
            <p className="mt-1 text-sm text-slate-600">
              Creates the invoice with <span className="font-medium">{state.provider_label}</span>{" "}
              and emails {invoice.client_email} a payment link.
            </p>
            <Button className="mt-5 w-full" onClick={() => setConfirm("send")} disabled={busy !== null}>
              {busy === "send" ? <Spinner /> : <Send className="size-4" />} Send invoice
            </Button>
            <Button
              variant="ghost"
              className="mt-2 w-full"
              onClick={() => run("reopen")}
              disabled={busy !== null}
            >
              {busy === "reopen" ? <Spinner /> : <RotateCcw className="size-4" />} Reopen to edit items
            </Button>
          </>
        )}

        {invoice.status === "sent" && (
          <>
            <h2 className="font-semibold text-slate-900">Waiting for payment</h2>
            <p className="mt-1 text-sm text-slate-600">
              Sent on {formatDate(invoice.sent_at, true)}. The status updates automatically.
            </p>
            {invoice.payment_url && (
              <div className="mt-4">
                <p className="text-xs font-medium text-slate-500">Payment link</p>
                <div className="mt-1 flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 py-1 pr-1 pl-3">
                  <span className="min-w-0 flex-1 truncate font-mono text-xs text-slate-700">
                    {invoice.payment_url}
                  </span>
                  <button
                    type="button"
                    onClick={copyLink}
                    className="rounded-md p-1.5 text-slate-500 hover:bg-white hover:text-slate-900"
                    aria-label="Copy payment link"
                  >
                    {copied ? <Check className="size-4 text-brand-600" /> : <Copy className="size-4" />}
                  </button>
                  <a
                    href={invoice.payment_url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-md p-1.5 text-slate-500 hover:bg-white hover:text-slate-900"
                    aria-label="Open payment link"
                  >
                    <ExternalLink className="size-4" />
                  </a>
                </div>
              </div>
            )}
            <Button
              variant="secondary"
              className="mt-5 w-full"
              onClick={() => run("refresh")}
              disabled={busy !== null}
            >
              {busy === "refresh" ? <Spinner /> : <RefreshCw className="size-4" />} Refresh status
            </Button>
            <Button
              variant="ghost"
              className="mt-2 w-full text-red-700 hover:bg-red-50 hover:text-red-800"
              onClick={() => setConfirm("cancel")}
              disabled={busy !== null}
            >
              <XCircle className="size-4" /> Cancel invoice
            </Button>
          </>
        )}

        {invoice.status === "paid" && (
          <div className="text-center">
            <CheckCircle2 className="mx-auto size-10 text-brand-600" />
            <h2 className="mt-3 font-semibold text-slate-900">Paid</h2>
            <p className="mt-1 text-sm text-slate-600">
              {formatMoney(invoice.total, invoice.currency)} received on {formatDate(invoice.paid_at, true)}.
            </p>
          </div>
        )}

        {invoice.status === "refunded" && (
          <p className="text-sm text-slate-600">This invoice was refunded.</p>
        )}

        {error && (
          <Alert kind="error" className="mt-4">
            {error}
          </Alert>
        )}
      </Card>

      <Card className="p-5">
        <h3 className="text-sm font-semibold text-slate-900">Timeline</h3>
        <ol className="mt-4 space-y-4">
          <TimelineStep done label="Draft confirmed" date={invoice.created_at} />
          <TimelineStep done={!!invoice.sent_at} label="Sent to client" date={invoice.sent_at} />
          <TimelineStep done={!!invoice.paid_at} label="Paid" date={invoice.paid_at} last />
        </ol>
        {invoice.provider && (
          <dl className="mt-5 space-y-1 border-t border-slate-100 pt-4 text-xs text-slate-500">
            <div className="flex justify-between gap-2">
              <dt>Provider status</dt>
              <dd className="font-mono text-slate-700">{invoice.provider_status ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>Provider ID</dt>
              <dd className="truncate font-mono text-slate-700">{invoice.provider_invoice_id}</dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>Last checked</dt>
              <dd className="text-slate-700">{formatDate(invoice.last_synced_at, true)}</dd>
            </div>
          </dl>
        )}
      </Card>

      <Dialog
        open={confirm === "send"}
        onClose={() => setConfirm(null)}
        title={`Send ${invoice.number}?`}
        description={`${invoice.client_name} (${invoice.client_email}) will receive an invoice for ${formatMoney(invoice.total, invoice.currency)} through ${state.provider_label}. You can't edit it after sending.`}
      >
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setConfirm(null)}>
            Not yet
          </Button>
          <Button onClick={() => run("send")}>
            <Send className="size-4" /> Send invoice
          </Button>
        </div>
      </Dialog>

      <Dialog
        open={confirm === "cancel"}
        onClose={() => setConfirm(null)}
        title={`Cancel ${invoice.number}?`}
        description="The payment link stops working and the items unlock so you can create a new invoice."
      >
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setConfirm(null)}>
            Keep it
          </Button>
          <Button className="bg-red-600 hover:bg-red-700" onClick={() => run("cancel")}>
            Cancel invoice
          </Button>
        </div>
      </Dialog>
    </div>
  );
}

function TimelineStep({
  done,
  label,
  date,
  last,
}: {
  done: boolean;
  label: string;
  date: string | null;
  last?: boolean;
}) {
  return (
    <li className="relative flex gap-3">
      {!last && (
        <span
          className={cn("absolute top-6 left-[9px] h-[calc(100%-0.5rem)] w-px", done ? "bg-brand-500" : "bg-slate-200")}
        />
      )}
      <span
        className={cn(
          "relative grid size-5 shrink-0 place-items-center rounded-full",
          done ? "bg-brand-600 text-white" : "border-2 border-slate-200 bg-white",
        )}
      >
        {done && <Check className="size-3" />}
      </span>
      <div className="-mt-0.5">
        <p className={cn("text-sm", done ? "font-medium text-slate-900" : "text-slate-500")}>{label}</p>
        {date && <p className="text-xs text-slate-500">{formatDate(date, true)}</p>}
      </div>
    </li>
  );
}
