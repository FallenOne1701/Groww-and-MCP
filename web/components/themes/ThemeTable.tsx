import { formatCount, lowStarShare } from "@/lib/format";
import type { PulsePayload, Theme } from "@/lib/types";
import Link from "next/link";

function ThemeRow({
  theme,
  total,
  rank,
  featured,
}: {
  theme: Theme;
  total: number;
  rank: number | null;
  featured: boolean;
}) {
  const share = lowStarShare(theme.review_count, total);
  const severity = lowStarShare(theme.low_star_count, theme.review_count);
  const rest = 100 - severity;

  return (
    <Link
      href={`/evidence?theme=${theme.id}`}
      className={`block rounded-xl border border-hairline bg-surface p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:bg-canvas ${
        featured ? "" : "opacity-90"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          {rank ? (
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-accent">
              Rank #{rank}
            </p>
          ) : (
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
              Also clustered
            </p>
          )}
          <h3 className="mt-1 text-[15px] font-semibold text-ink">{theme.label}</h3>
        </div>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-right text-[13px] tabular sm:grid-cols-4">
          <Stat label="Reviews" value={formatCount(theme.review_count)} />
          <Stat label="Avg rating" value={theme.avg_rating.toFixed(2)} />
          <Stat label="≤2★" value={formatCount(theme.low_star_count)} danger />
          <Stat label="Share" value={`${share}%`} />
        </div>
      </div>
      <div className="mt-4 flex h-2 overflow-hidden rounded-full bg-canvas">
        <div className="bg-danger" style={{ width: `${severity}%` }} />
        <div className="bg-sidebar-muted/40" style={{ width: `${rest}%` }} />
      </div>
    </Link>
  );
}

function Stat({
  label,
  value,
  danger,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
        {label}
      </p>
      <p className={`font-semibold ${danger ? "text-danger" : "text-ink"}`}>{value}</p>
    </div>
  );
}

export function ThemeTable({ pulse }: { pulse: PulsePayload }) {
  const featured = pulse.top_3
    .map((id) => pulse.themes.find((theme) => theme.id === id))
    .filter((theme): theme is Theme => Boolean(theme));
  const rest = pulse.themes.filter((theme) => !pulse.top_3.includes(theme.id));

  return (
    <div className="space-y-4">
      <p className="rounded-xl border border-accent/20 bg-accent-soft px-4 py-3 text-[13px] text-body">
        Top 3 are severity-ranked (≤2★ first), not by raw volume. App reliability is
        #1 because it has the most low-star reviews, even though its average is
        higher than Support.
      </p>
      <p className="text-[11px] font-semibold text-muted">
        <span className="mr-3 inline-flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-danger" /> rose = ≤2★ severity
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-2 rounded-full bg-sidebar-muted/40" /> slate = other
          ratings
        </span>
      </p>
      <div className="space-y-3">
        {featured.map((theme, index) => (
          <ThemeRow
            key={theme.id}
            theme={theme}
            total={pulse.review_count}
            rank={index + 1}
            featured
          />
        ))}
      </div>
      <h3 className="pt-2 text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
        Also clustered (not in pulse)
      </h3>
      <div className="grid gap-3 md:grid-cols-2">
        {rest.map((theme) => (
          <ThemeRow
            key={theme.id}
            theme={theme}
            total={pulse.review_count}
            rank={null}
            featured={false}
          />
        ))}
      </div>
    </div>
  );
}
