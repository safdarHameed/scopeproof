import { FileSearch, ListChecks, Send, Upload } from "lucide-react";

import { SectionHeading } from "./section-heading";

const steps = [
  {
    icon: Upload,
    title: "Upload the paper trail",
    body: "Add the contract, change orders, client emails or chat exports, and work logs for a project.",
  },
  {
    icon: FileSearch,
    title: "Extract what was agreed",
    body: "ScopeProof finds the prices, milestones, rates and approved extras, and keeps a citation for each one.",
  },
  {
    icon: ListChecks,
    title: "Review the draft",
    body: "Verified items are ready to go. Unclear or conflicting ones are flagged with the evidence side by side.",
  },
  {
    icon: Send,
    title: "Send and get paid",
    body: "Approve the invoice and send it through PayPal. Your client can see exactly what each charge is for.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-16 bg-slate-50 py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          eyebrow="How it works"
          title="From signed contract to paid invoice"
          description="Four steps, and you approve every one."
        />
        <ol className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, i) => (
            <li key={step.title} className="rounded-2xl border border-slate-200 bg-white p-6">
              <div className="flex items-center justify-between">
                <span className="grid size-10 place-items-center rounded-lg bg-brand-50 text-brand-700">
                  <step.icon className="size-5" />
                </span>
                <span className="font-mono text-sm text-slate-400">0{i + 1}</span>
              </div>
              <h3 className="mt-5 font-semibold text-slate-900">{step.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
