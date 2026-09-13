export function formatWeekEnding(iso: string): string {
  const date = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function formatShortDate(iso: string): string {
  const date = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat("en-IN").format(value);
}

export function truncateDraftId(id: string | null): string {
  if (!id) return "—";
  if (id.length <= 14) return id;
  return `${id.slice(0, 12)}…`;
}

export function lowStarShare(low: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((low / total) * 100);
}

export function productName(): string {
  return process.env.NEXT_PUBLIC_PRODUCT_NAME ?? "Groww";
}
