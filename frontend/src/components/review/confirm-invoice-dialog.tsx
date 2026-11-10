"use client";

import { useState } from "react";

import { FormError } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/fields";
import { Input } from "@/components/ui/input";
import { errorMessage, invoiceApi } from "@/lib/api";
import { formatMoney, plural } from "@/lib/format";
import type { Project } from "@/types/api";

function isoDate(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function ConfirmInvoiceDialog({
  open,
  onClose,
  project,
  lineCount,
  total,
  onConfirmed,
}: {
  open: boolean;
  onClose: () => void;
  project: Project;
  lineCount: number;
  total: string;
  onConfirmed: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const today = new Date();
  const defaultDue = new Date(today.getTime() + 14 * 24 * 3600 * 1000);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setPending(true);
    setError(null);
    try {
      await invoiceApi.confirm(project.id, {
        due_date: String(form.get("due_date")) || null,
        note: String(form.get("note")).trim() || null,
      });
      onConfirmed();
    } catch (err) {
      setError(errorMessage(err));
      setPending(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title="Confirm invoice draft"
      description={
        <>
          {plural(lineCount, "approved item")} for{" "}
          <span className="font-medium text-slate-900">{formatMoney(total, project.currency)}</span>,
          addressed to {project.client_name} ({project.client_email}). Items are locked once
          confirmed; you can reopen the draft until it&apos;s sent.
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <FormError message={error} />
        <Input
          label="Due date"
          name="due_date"
          type="date"
          min={isoDate(today)}
          defaultValue={isoDate(defaultDue)}
          required
        />
        <Textarea
          label="Note to client (optional)"
          name="note"
          maxLength={2000}
          rows={3}
          placeholder="Thanks for the great collaboration!"
        />
        <div className="flex justify-end gap-3 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={pending}>
            {pending ? "Confirming…" : "Confirm invoice"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
