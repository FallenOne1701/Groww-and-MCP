import { formatCount } from "@/lib/format";

const COLORS = [
  "bg-danger",
  "bg-[#f08080]",
  "bg-warning",
  "bg-[#7dcea0]",
  "bg-accent",
];

export function RatingBar({
  counts,
}: {
  counts: [number, number, number, number, number];
}) {
  const total = counts.reduce((sum, n) => sum + n, 0) || 1;

  return (
    <div>
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
        This week at a glance
      </p>
      <div className="flex h-3 overflow-hidden rounded-full bg-canvas">
        {counts.map((count, index) => (
          <div
            key={index}
            className={`${COLORS[index]} h-full`}
            style={{ width: `${(count / total) * 100}%` }}
            title={`${index + 1}★ ${count}`}
          />
        ))}
      </div>
      <div className="mt-2 grid grid-cols-5 gap-1 text-center text-[11px] font-medium text-muted tabular">
        {counts.map((count, index) => (
          <div key={index}>
            <p className="text-ink">{formatCount(count)}</p>
            <p>{index + 1}★</p>
          </div>
        ))}
      </div>
    </div>
  );
}
