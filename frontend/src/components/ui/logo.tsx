import Link from "next/link";

export function Logo({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="flex items-center gap-2 font-semibold tracking-tight text-slate-900">
      <span className="grid size-8 place-items-center rounded-lg bg-ink-950 text-white">
        <svg viewBox="0 0 24 24" className="size-4.5" fill="none" stroke="currentColor" strokeWidth={2.2}>
          <path d="M7 3h7l5 5v13H7z" strokeLinejoin="round" />
          <path d="m10 14 2 2 4-4" strokeLinecap="round" strokeLinejoin="round" className="text-brand-500" stroke="currentColor" />
        </svg>
      </span>
      ScopeProof
    </Link>
  );
}
