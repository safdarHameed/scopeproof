import { AlertTriangle, GitCompare, Link2, Lock, Receipt, Scale } from "lucide-react";

import { SectionHeading } from "./section-heading";

const features = [
  {
    icon: Link2,
    title: "Evidence-linked line items",
    body: "Every charge cites the clause, message or log entry it came from. One click shows you the original.",
  },
  {
    icon: AlertTriangle,
    title: "Flags instead of guesses",
    body: "If there's no approved price, ScopeProof asks you rather than making one up.",
  },
  {
    icon: GitCompare,
    title: "Conflict detection",
    body: "When the contract says one thing and a later email says another, both versions are shown side by side so you can decide.",
  },
  {
    icon: Scale,
    title: "Scope-creep tracking",
    body: "Extra requests are logged as they come in, so approved changes get billed and unapproved ones don't slip through.",
  },
  {
    icon: Receipt,
    title: "PayPal invoicing",
    body: "Turn an approved draft into a PayPal invoice your client can pay online.",
  },
  {
    icon: Lock,
    title: "Your documents stay private",
    body: "Your project files are only used to draft your invoices and are never shared.",
  },
];

export function Features() {
  return (
    <section id="features" className="scroll-mt-16 py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          eyebrow="Features"
          title="Billing you can defend, line by line"
          description="Disputes start when nobody can point to what was agreed. ScopeProof keeps that record for you."
        />
        <div className="mt-16 grid gap-x-10 gap-y-12 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div key={f.title}>
              <f.icon className="size-6 text-brand-600" />
              <h3 className="mt-4 font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{f.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
