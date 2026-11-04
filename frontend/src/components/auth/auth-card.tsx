import Link from "next/link";

export function AuthCard({
  title,
  subtitle,
  footer,
  children,
}: {
  title: string;
  subtitle: string;
  footer: { text: string; linkLabel: string; href: string };
  children: React.ReactNode;
}) {
  return (
    <div className="w-full max-w-md">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
        <p className="mt-1.5 text-sm text-slate-600">{subtitle}</p>
        <div className="mt-8">{children}</div>
      </div>
      <p className="mt-6 text-center text-sm text-slate-600">
        {footer.text}{" "}
        <Link href={footer.href} className="font-medium text-brand-700 hover:text-brand-600">
          {footer.linkLabel}
        </Link>
      </p>
    </div>
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">
      {message}
    </p>
  );
}
