import { ArrowRight, ShieldCheck } from "lucide-react";

import { ButtonLink } from "@/components/ui/button";
import { InvoicePreview } from "./invoice-preview";

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,var(--color-brand-50),transparent_60%)]" />
      <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 pt-16 pb-20 sm:px-6 lg:grid-cols-2 lg:pt-24 lg:pb-28">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-1 text-xs font-medium text-brand-700 ring-1 ring-brand-100">
            <ShieldCheck className="size-3.5" />
            Every line item backed by evidence
          </span>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight text-balance text-slate-900 sm:text-5xl lg:text-6xl">
            Invoice exactly what was agreed. Nothing more, nothing missed.
          </h1>
          <p className="mt-6 max-w-xl text-lg text-pretty text-slate-600">
            ScopeProof reads your contracts, client conversations and work logs, then drafts
            invoices where every charge links back to its source. If a price is unclear or
            contradicted, it flags the item for review instead of guessing.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink href="/register" size="lg">
              Start free <ArrowRight className="size-4" />
            </ButtonLink>
            <ButtonLink href="#how-it-works" variant="secondary" size="lg">
              See how it works
            </ButtonLink>
          </div>
          <p className="mt-6 text-sm text-slate-500">
            For freelancers, agencies, contractors and any business that bills against a contract.
          </p>
        </div>
        <InvoicePreview />
      </div>
    </section>
  );
}
