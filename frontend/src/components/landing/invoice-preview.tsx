import { AlertTriangle, CheckCircle2, FileText, MessageSquare } from "lucide-react";

const items = [
  {
    label: "Phase 1: Site preparation & foundation",
    amount: "$18,500.00",
    source: "Contract §4.1, Milestone 1",
    icon: FileText,
    status: "verified" as const,
  },
  {
    label: "Change order #2: Additional drainage line",
    amount: "$2,350.00",
    source: "Email from client, Mar 12: \"Approved, go ahead\"",
    icon: MessageSquare,
    status: "verified" as const,
  },
  {
    label: "Upgraded window fittings",
    amount: "Needs review",
    source: "Requested on Mar 18, but no price was ever confirmed",
    icon: AlertTriangle,
    status: "flagged" as const,
  },
];

export function InvoicePreview() {
  return (
    <div className="relative mx-auto w-full max-w-lg">
      <div className="absolute -inset-4 -z-10 rounded-3xl bg-gradient-to-tr from-brand-100 via-white to-sky-100 blur-2xl" />
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div>
            <p className="text-xs font-medium tracking-wide text-slate-500 uppercase">Draft invoice</p>
            <p className="font-semibold text-slate-900">Riverside Residence: Phase 1</p>
          </div>
          <span className="shrink-0 whitespace-nowrap rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 ring-1 ring-amber-200">
            1 item to review
          </span>
        </div>

        <ul className="divide-y divide-slate-100">
          {items.map((item) => {
            const flagged = item.status === "flagged";
            return (
              <li key={item.label} className={flagged ? "bg-amber-50/50 px-5 py-4" : "px-5 py-4"}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex gap-3">
                    {flagged ? (
                      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-500" />
                    ) : (
                      <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-brand-600" />
                    )}
                    <div>
                      <p className="text-sm font-medium text-slate-900">{item.label}</p>
                      <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
                        <item.icon className="size-3.5 shrink-0" />
                        {item.source}
                      </p>
                    </div>
                  </div>
                  <p
                    className={
                      flagged
                        ? "shrink-0 text-sm font-medium text-amber-700"
                        : "shrink-0 font-mono text-sm text-slate-900"
                    }
                  >
                    {item.amount}
                  </p>
                </div>
              </li>
            );
          })}
        </ul>

        <div className="flex items-center justify-between bg-slate-50 px-5 py-4">
          <p className="text-sm text-slate-500">Verified subtotal</p>
          <p className="font-mono text-lg font-semibold text-slate-900">$20,850.00</p>
        </div>
      </div>
    </div>
  );
}
