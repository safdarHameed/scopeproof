export function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="mx-auto max-w-2xl text-center">
      <p className="text-sm font-semibold text-brand-600">{eyebrow}</p>
      <h2 className="mt-2 text-3xl font-semibold tracking-tight text-balance text-slate-900 sm:text-4xl">
        {title}
      </h2>
      {description && <p className="mt-4 text-lg text-pretty text-slate-600">{description}</p>}
    </div>
  );
}
