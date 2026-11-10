import { BadgeCheck } from "lucide-react";

import { Badge, type Tone } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatDate, formatMoney, formatQuantity } from "@/lib/format";
import type { Invoice, InvoiceStatus } from "@/types/api";
import type { User } from "@/types/auth";

export const INVOICE_STATUS: Record<InvoiceStatus, { label: string; tone: Tone }> = {
  confirmed: { label: "Ready to send", tone: "violet" },
  sent: { label: "Awaiting payment", tone: "blue" },
  paid: { label: "Paid", tone: "green" },
  cancelled: { label: "Cancelled", tone: "slate" },
  refunded: { label: "Refunded", tone: "slate" },
};

/** Printable-looking rendering of an invoice. */
export function InvoiceDocument({ invoice, sender }: { invoice: Invoice; sender: User | null }) {
  const status = INVOICE_STATUS[invoice.status];
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-6 py-5 sm:px-8">
        <div>
          <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">Invoice</p>
          <p className="mt-0.5 font-mono text-xl font-semibold text-slate-900">{invoice.number}</p>
        </div>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>

      <div className="grid gap-6 px-6 py-6 text-sm sm:grid-cols-3 sm:px-8">
        <div>
          <p className="text-xs font-medium text-slate-500">From</p>
          <p className="mt-1 font-medium text-slate-900">
            {sender?.company_name || sender?.full_name || sender?.email}
          </p>
          {sender?.company_name && sender.full_name && <p className="text-slate-600">{sender.full_name}</p>}
          <p className="text-slate-600">{sender?.email}</p>
        </div>
        <div>
          <p className="text-xs font-medium text-slate-500">Bill to</p>
          <p className="mt-1 font-medium text-slate-900">{invoice.client_company || invoice.client_name}</p>
          {invoice.client_company && <p className="text-slate-600">{invoice.client_name}</p>}
          <p className="text-slate-600">{invoice.client_email}</p>
        </div>
        <div className="space-y-1">
          <DateRow label="Issued" value={formatDate(invoice.issue_date)} />
          <DateRow label="Due" value={formatDate(invoice.due_date)} />
          {invoice.paid_at && <DateRow label="Paid" value={formatDate(invoice.paid_at)} />}
        </div>
      </div>

      <div className="overflow-x-auto px-6 sm:px-8">
        <table className="w-full min-w-[32rem] text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs text-slate-500">
              <th className="py-2 font-medium">Description</th>
              <th className="py-2 text-right font-medium">Qty</th>
              <th className="py-2 text-right font-medium">Unit price</th>
              <th className="py-2 text-right font-medium">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {invoice.lines.map((line) => (
              <tr key={line.id}>
                <td className="py-3 pr-4">
                  <p className="text-slate-900">{line.description}</p>
                  {line.evidence_count > 0 && (
                    <p className="mt-0.5 flex items-center gap-1 text-xs text-brand-700">
                      <BadgeCheck className="size-3.5" />
                      Backed by {line.evidence_count} verified {line.evidence_count === 1 ? "quote" : "quotes"}
                    </p>
                  )}
                </td>
                <td className="py-3 text-right text-slate-600">{formatQuantity(line.quantity)}</td>
                <td className="py-3 text-right font-mono text-slate-600">
                  {formatMoney(line.unit_price, invoice.currency)}
                </td>
                <td className="py-3 text-right font-mono text-slate-900">
                  {formatMoney(line.amount, invoice.currency)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-2 flex items-center justify-between bg-slate-50 px-6 py-4 sm:px-8">
        <p className="text-sm font-medium text-slate-600">Total due</p>
        <p className="font-mono text-2xl font-semibold text-slate-900">
          {formatMoney(invoice.total, invoice.currency)}
        </p>
      </div>

      {invoice.note && (
        <div className="border-t border-slate-100 px-6 py-4 text-sm text-slate-600 sm:px-8">
          <p className="text-xs font-medium text-slate-500">Note</p>
          <p className="mt-1 whitespace-pre-wrap">{invoice.note}</p>
        </div>
      )}
    </Card>
  );
}

function DateRow({ label, value }: { label: string; value: string }) {
  return (
    <p className="flex justify-between gap-4 sm:justify-start">
      <span className="w-14 text-xs font-medium text-slate-500">{label}</span>
      <span className="text-slate-900">{value}</span>
    </p>
  );
}
