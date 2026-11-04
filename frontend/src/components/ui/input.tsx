import { useId } from "react";

import { cn } from "@/lib/cn";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function Input({ label, hint, className, id, ...props }: InputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <div className="space-y-1.5">
      <label htmlFor={inputId} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={inputId}
        className={cn(
          "block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900",
          "placeholder:text-slate-400 focus:border-brand-600 focus:ring-2 focus:ring-brand-100 focus:outline-none",
          className,
        )}
        {...props}
      />
      {hint && <p className="text-xs text-slate-500">{hint}</p>}
    </div>
  );
}
