"use client";

import { ButtonLink } from "@/components/ui/button";
import { Logo } from "@/components/ui/logo";
import { useAuth } from "@/providers/auth-provider";

const links = [
  { href: "#how-it-works", label: "How it works" },
  { href: "#features", label: "Features" },
  { href: "#industries", label: "Who it's for" },
];

export function Navbar() {
  const { status } = useAuth();
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Logo />
        <div className="hidden items-center gap-8 text-sm text-slate-600 md:flex">
          {links.map((l) => (
            <a key={l.href} href={l.href} className="transition-colors hover:text-slate-900">
              {l.label}
            </a>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {status === "authenticated" ? (
            <ButtonLink href="/dashboard" size="sm">
              Dashboard
            </ButtonLink>
          ) : (
            <>
              <ButtonLink href="/login" variant="ghost" size="sm">
                Log in
              </ButtonLink>
              <ButtonLink href="/register" size="sm">
                Get started
              </ButtonLink>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
