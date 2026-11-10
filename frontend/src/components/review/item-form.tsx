"use client";

import { useState } from "react";

import { FormError } from "@/components/auth/auth-card";
import { CATEGORY_LABELS } from "@/components/review/labels";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/fields";
import { Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Item, ItemCategory, ItemPayload } from "@/types/api";

const CATEGORY_OPTIONS = (Object.keys(CATEGORY_LABELS) as ItemCategory[]).map((value) => ({
  value,
  label: CATEGORY_LABELS[value],
}));

/** Used both to edit a suggested item and to add one by hand. */
export function ItemForm({
  item,
  currency,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  item?: Item;
  currency: string;
  submitLabel: string;
  onSubmit: (data: ItemPayload) => Promise<void>;
  onCancel: () => void;
}) {
  const [quantity, setQuantity] = useState(item ? String(Number(item.quantity)) : "1");
  const [price, setPrice] = useState(item?.unit_price ?? "");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const amount = Number(quantity) * Number(price);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    setPending(true);
    setError(null);
    try {
      await onSubmit({
        description: String(form.get("description")).trim(),
        category: form.get("category") as ItemCategory,
        quantity: quantity || "1",
        unit_price: price === "" ? null : price,
      });
    } catch (err) {
      setError(errorMessage(err));
      setPending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <FormError message={error} />
      <Input
        label="Description (shown on the invoice)"
        name="description"
        required
        maxLength={500}
        defaultValue={item?.description}
      />
      <div className="grid gap-4 sm:grid-cols-3">
        <Select
          label="Type"
          name="category"
          options={CATEGORY_OPTIONS}
          defaultValue={item?.category ?? "other"}
        />
        <Input
          label="Quantity"
          type="number"
          min="0.01"
          step="0.01"
          required
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
        <Input
          label={`Unit price (${currency})`}
          type="number"
          min="0"
          step="0.01"
          value={price}
          placeholder="Not set"
          onChange={(e) => setPrice(e.target.value)}
        />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-600">
          Amount:{" "}
          <span className="font-mono font-medium text-slate-900">
            {price !== "" && Number.isFinite(amount) ? formatMoney(amount, currency) : "—"}
          </span>
        </p>
        <div className="flex gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={pending}>
            {pending ? "Saving…" : submitLabel}
          </Button>
        </div>
      </div>
    </form>
  );
}
