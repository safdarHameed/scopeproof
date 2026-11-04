import { Briefcase, Building2, HardHat, Laptop } from "lucide-react";


const industries = [
  {
    icon: Laptop,
    title: "Freelancers",
    body: "Fixed-price gigs, hourly retainers and the \"one small extra feature\" requests.",
  },
  {
    icon: Briefcase,
    title: "Agencies & studios",
    body: "Multi-phase projects with several stakeholders and a long trail of change requests.",
  },
  {
    icon: HardHat,
    title: "Construction & trades",
    body: "Milestone payments, change orders and variations agreed on site or by email.",
  },
  {
    icon: Building2,
    title: "Professional services",
    body: "Consultancies and service firms billing against SOWs, rate cards and approved hours.",
  },
];

export function Industries() {
  return (
    <section id="industries" className="scroll-mt-16 bg-ink-950 py-24 text-white">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold text-brand-500">Who it&apos;s for</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
            Any business that bills against an agreement
          </h2>
          <p className="mt-4 text-lg text-slate-300">
            Whether it&apos;s a two-page freelance contract or a building project with dozens of
            change orders, ScopeProof works the same way.
          </p>
        </div>
        <div className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {industries.map((i) => (
            <div key={i.title} className="rounded-2xl bg-ink-900 p-6 ring-1 ring-white/10">
              <i.icon className="size-6 text-brand-500" />
              <h3 className="mt-4 font-semibold">{i.title}</h3>
              <p className="mt-2 text-sm text-slate-400">{i.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
