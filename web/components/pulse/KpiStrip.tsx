import { formatCount } from "@/lib/format";
import type { PulsePayload } from "@/lib/types";

export function KpiStrip({ pulse }: { pulse: PulsePayload }) {
  const low =
    pulse.rating_histogram[0] + pulse.rating_histogram[1];
  const share = Math.round((low / pulse.review_count) * 100);
  const delivery = pulse.delivery.delivery_skipped
    ? "Local only"
    : "Doc appended · Draft ready";

  const items = [
    { label: "Reviews in window", value: formatCount(pulse.review_count) },
    { label: "Low-star share", value: `${share}% ≤2★` },
    {
      label: "Pulse length",
      value: `${pulse.word_count} / ${pulse.word_limit}`,
    },
    { label: "Delivery", value: delivery },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {items.map((item) => (
        <article
          key={item.label}
          className="rounded-xl border border-hairline bg-surface p-4 shadow-[0_1px_3px_rgba(0,0,0,0.04)]"
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
            {item.label}
          </p>
          <p className="mt-2 text-xl font-semibold tracking-tight text-ink tabular">
            {item.value}
          </p>
        </article>
      ))}
    </div>
  );
}
