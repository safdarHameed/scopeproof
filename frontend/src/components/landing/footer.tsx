import { Logo } from "@/components/ui/logo";

export function Footer() {
  return (
    <footer className="border-t border-slate-200">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:px-6">
        <Logo />
        <p>© 2026 ScopeProof. All rights reserved.</p>
      </div>
    </footer>
  );
}
