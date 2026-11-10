"use client";

import { useState } from "react";

import { FormError } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { Select, Textarea } from "@/components/ui/fields";
import { Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import type { Project, ProjectPayload } from "@/types/api";

const CURRENCIES = [
  { value: "EUR", label: "EUR (€)" },
  { value: "USD", label: "USD ($)" },
  { value: "GBP", label: "GBP (£)" },
];

export function ProjectForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  initial?: Project;
  submitLabel: string;
  onSubmit: (data: ProjectPayload) => Promise<void>;
  onCancel?: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const value = (key: string) => String(form.get(key) ?? "").trim();
    setError(null);
    setPending(true);
    try {
      await onSubmit({
        name: value("name"),
        description: value("description") || null,
        currency: value("currency"),
        client_name: value("client_name"),
        client_email: value("client_email"),
        client_company: value("client_company") || null,
        client_address: value("client_address") || null,
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-8">
      <FormError message={error} />

      <fieldset className="space-y-4">
        <legend className="text-sm font-semibold text-slate-900">Project</legend>
        <Input
          label="Project name"
          name="name"
          required
          maxLength={200}
          defaultValue={initial?.name}
          placeholder="e.g. Online ordering website"
        />
        <div className="grid gap-4 sm:grid-cols-[1fr_10rem]">
          <Textarea
            label="Description (optional)"
            name="description"
            maxLength={5000}
            rows={2}
            defaultValue={initial?.description ?? ""}
          />
          <Select
            label="Currency"
            name="currency"
            options={CURRENCIES}
            defaultValue={initial?.currency ?? "EUR"}
          />
        </div>
      </fieldset>

      <fieldset className="space-y-4">
        <legend className="text-sm font-semibold text-slate-900">Client</legend>
        <p className="-mt-2 text-sm text-slate-500">The invoice is addressed and sent to this person.</p>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Contact name"
            name="client_name"
            required
            maxLength={200}
            defaultValue={initial?.client_name}
            autoComplete="off"
          />
          <Input
            label="Email"
            name="client_email"
            type="email"
            required
            defaultValue={initial?.client_email}
            autoComplete="off"
          />
        </div>
        <Input
          label="Company (optional)"
          name="client_company"
          maxLength={200}
          defaultValue={initial?.client_company ?? ""}
        />
        <Textarea
          label="Billing address (optional)"
          name="client_address"
          maxLength={1000}
          rows={2}
          defaultValue={initial?.client_address ?? ""}
        />
      </fieldset>

      <div className="flex justify-end gap-3">
        {onCancel && (
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={pending}>
          {pending ? "Saving…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
