import { cn } from "@/lib/cn";

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={cn(
        "inline-block size-4 animate-spin rounded-full border-2 border-current border-t-transparent",
        className,
      )}
    />
  );
}

export function PageSpinner() {
  return (
    <div className="grid place-items-center py-24 text-slate-400">
      <Spinner className="size-6" />
    </div>
  );
}
