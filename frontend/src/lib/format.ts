export function formatMoney(value: string | number | null | undefined, currency: string) {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  return new Intl.NumberFormat("en-IE", { style: "currency", currency }).format(n);
}

export function formatDate(value: string | null | undefined, withTime = false) {
  if (!value) return "—";
  // Date-only values ("2026-10-27") are calendar dates: don't shift them by timezone.
  const date = /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(`${value}T00:00:00`) : new Date(value);
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  }).format(date);
}

export function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function formatQuantity(value: string) {
  const n = Number(value);
  return Number.isInteger(n) ? String(n) : n.toFixed(2);
}

/** "Maya Chen <maya@x.com>" -> "Maya Chen" */
export function displayName(address: string | null | undefined) {
  if (!address) return null;
  const match = address.match(/^(.*?)\s*<[^>]+>$/);
  return (match?.[1] || address).replace(/^"|"$/g, "");
}

export function plural(n: number, word: string, pluralWord = `${word}s`) {
  return `${n} ${n === 1 ? word : pluralWord}`;
}
