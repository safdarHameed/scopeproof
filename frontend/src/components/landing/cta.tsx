import { ArrowRight } from "lucide-react";

import { ButtonLink } from "@/components/ui/button";

export function Cta() {
  return (
    <section className="py-24">
      <div className="mx-auto max-w-4xl px-4 text-center sm:px-6">
        <h2 className="text-3xl font-semibold tracking-tight text-balance text-slate-900 sm:text-4xl">
          Stop leaving approved work off your invoices
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-lg text-slate-600">
          Set up your first project in minutes. Bring a contract and the conversations that
          followed it.
        </p>
        <div className="mt-8 flex justify-center">
          <ButtonLink href="/register" size="lg">
            Create your account <ArrowRight className="size-4" />
          </ButtonLink>
        </div>
      </div>
    </section>
  );
}
