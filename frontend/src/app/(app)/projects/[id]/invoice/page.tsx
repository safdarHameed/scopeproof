"use client";

import { Lock, ReceiptText } from "lucide-react";
import { useCallback, useState } from "react";

import { InvoiceDocument, INVOICE_STATUS } from "@/components/invoice/invoice-document";
import { PaymentPanel } from "@/components/invoice/payment-panel";
import { useProject } from "@/components/projects/project-context";
import { ConfirmInvoiceDialog } from "@/components/review/confirm-invoice-dialog";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card, EmptyState } from "@/components/ui/card";
import { PageSpinner } from "@/components/ui/spinner";
import { invoiceApi, reviewApi } from "@/lib/api";
import { formatDate, formatMoney, plural } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import { useAuth } from "@/providers/auth-provider";
import type { InvoiceState } from "@/types/api";

export default function InvoicePage() {
  const { project, refreshProject } = useProject();
  const { user } = useAuth();
  const invoice = useResource(`invoice:${project.id}`, () => invoiceApi.get(project.id));
  const review = useResource(`review:${project.id}`, () => reviewApi.get(project.id));
  const [confirming, setConfirming] = useState(false);

  const { setData: setInvoice, reload: reloadInvoice } = invoice;
  const { reload: reloadReview } = review;

  const handleChange = useCallback(
    async (next: InvoiceState) => {
      setInvoice((prev) => {
        // Only refresh the rest of the page when something actually changed.
        if (prev?.invoice?.status !== next.invoice?.status || !!prev?.invoice !== !!next.invoice) {
          void refreshProject();
          void reloadReview();
        }
        return next;
      });
    },
    [setInvoice, refreshProject, reloadReview],
  );

  if (invoice.loading || review.loading) return <PageSpinner />;
  if (!invoice.data) return <Alert kind="error">{invoice.error}</Alert>;

  const state = invoice.data;
  const history = state.history;

  if (!state.invoice) {
    const r = review.data;
    const approved = r?.items.filter((i) => i.status === "approved") ?? [];
    const ready = r && r.pending_count === 0 && approved.length > 0;
    return (
      <div className="space-y-8">
        {!r || r.items.length === 0 ? (
          <EmptyState
            icon={ReceiptText}
            title="No invoice yet"
            action={<ButtonLink href={`/projects/${project.id}/review`}>Go to review</ButtonLink>}
          >
            Analyze your documents and approve the items you want to bill first.
          </EmptyState>
        ) : (
          <Card className="mx-auto max-w-2xl p-6 sm:p-8">
            <h2 className="text-lg font-semibold text-slate-900">Invoice draft</h2>
            <p className="mt-1 text-sm text-slate-600">
              {ready
                ? "Everything is reviewed. Confirm the draft to lock it, then send it."
                : `${plural(r.pending_count, "item")} still ${r.pending_count === 1 ? "needs" : "need"} a decision before you can confirm.`}
            </p>
            <ul className="mt-6 divide-y divide-slate-100 border-y border-slate-100">
              {approved.map((item) => (
                <li key={item.id} className="flex justify-between gap-4 py-3 text-sm">
                  <span className="text-slate-900">{item.description}</span>
                  <span className="font-mono text-slate-900">
                    {formatMoney(item.amount, project.currency)}
                  </span>
                </li>
              ))}
              {approved.length === 0 && (
                <li className="py-3 text-sm text-slate-500">No approved items yet.</li>
              )}
            </ul>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-sm text-slate-600">Total</span>
              <span className="font-mono text-xl font-semibold text-slate-900">
                {formatMoney(r.approved_total, project.currency)}
              </span>
            </div>
            <div className="mt-6 flex flex-wrap justify-end gap-3">
              <ButtonLink href={`/projects/${project.id}/review`} variant="secondary">
                Back to review
              </ButtonLink>
              <Button disabled={!ready} onClick={() => setConfirming(true)}>
                <Lock className="size-4" /> Confirm invoice draft
              </Button>
            </div>
            <ConfirmInvoiceDialog
              open={confirming}
              onClose={() => setConfirming(false)}
              project={project}
              lineCount={approved.length}
              total={r.approved_total}
              onConfirmed={async () => {
                setConfirming(false);
                await Promise.all([reloadInvoice(), reloadReview(), refreshProject()]);
              }}
            />
          </Card>
        )}
        <History history={history} />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {state.provider === "placeholder" && (
        <Alert kind="info" title="Payments not connected">
          PayPal isn&apos;t connected yet. Sending marks the invoice as sent, but no payment link
          is created and the status won&apos;t change to paid.
        </Alert>
      )}
      <div className="grid gap-8 lg:grid-cols-[1fr_20rem]">
        <InvoiceDocument invoice={state.invoice} sender={user} />
        <aside className="lg:sticky lg:top-6 lg:self-start">
          <PaymentPanel state={state} projectId={project.id} onChange={handleChange} />
        </aside>
      </div>
      <History history={history} />
    </div>
  );
}

function History({ history }: { history: InvoiceState["history"] }) {
  if (history.length === 0) return null;
  return (
    <section>
      <h2 className="mb-3 text-sm font-semibold text-slate-900">Earlier invoices</h2>
      <Card className="divide-y divide-slate-100">
        {history.map((inv) => (
          <div key={inv.id} className="flex flex-wrap items-center gap-3 px-5 py-3 text-sm">
            <span className="font-mono text-slate-900">{inv.number}</span>
            <Badge tone={INVOICE_STATUS[inv.status].tone}>{INVOICE_STATUS[inv.status].label}</Badge>
            <span className="text-slate-500">{formatDate(inv.created_at)}</span>
            <span className="ml-auto font-mono text-slate-700">
              {formatMoney(inv.total, inv.currency)}
            </span>
          </div>
        ))}
      </Card>
    </section>
  );
}
