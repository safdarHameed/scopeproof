import { Logo } from "@/components/ui/logo";

export default function AuthLayout({ children }: LayoutProps<"/">) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <header className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6">
        <Logo />
      </header>
      <main className="flex flex-1 items-start justify-center px-4 pt-8 pb-16 sm:pt-16">
        {children}
      </main>
    </div>
  );
}
