"use client";

import { formatShortDate } from "@/lib/format";
import type { PulsePayload, ThemeId } from "@/lib/types";
import { QuoteCard } from "@/components/pulse/QuoteCard";
import { useMemo, useState } from "react";

export function EvidenceBoard({
  pulse,
  initialTheme,
}: {
  pulse: PulsePayload;
  initialTheme?: ThemeId | "top3";
}) {
  const [filter, setFilter] = useState<ThemeId | "top3" | "all">(
    initialTheme ?? "all",
  );

  const chips: Array<{ id: ThemeId | "top3" | "all"; label: string }> = [
    { id: "all", label: "All themes" },
    { id: "top3", label: "Top 3 only" },
    ...pulse.themes.map((theme) => ({ id: theme.id, label: theme.label })),
  ];

  const snippets = useMemo(() => {
    return pulse.snippets.filter((snippet) => {
      if (filter === "all") return true;
      if (filter === "top3") return pulse.top_3.includes(snippet.theme_id);
      return snippet.theme_id === filter;
    });
  }, [filter, pulse]);

  const quotes = useMemo(() => {
    return pulse.quotes.filter((quote) => {
      if (filter === "all" || filter === "top3") return true;
      return quote.theme_id === filter;
    });
  }, [filter, pulse.quotes]);

  return (
    <div className="space-y-6">
      <div className="sticky top-16 z-20 -mx-1 rounded-xl border border-hairline bg-surface px-4 py-3 text-[13px] text-body shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
        No usernames, emails, or device IDs. Public Play Store text only.
      </div>
      <p className="rounded-xl border border-accent/20 bg-accent-soft px-4 py-3 text-[13px] text-body">
        Quotes are verbatim Play Store text. Ellipsis means a truncated prefix,
        never a paraphrase.
      </p>
      <div className="flex flex-wrap gap-2">
        {chips.map((chip) => {
          const active = filter === chip.id;
          return (
            <button
              key={chip.id}
              type="button"
              onClick={() => setFilter(chip.id)}
              className={`rounded-full px-3 py-1.5 text-[12px] font-semibold ${
                active
                  ? "bg-accent text-white"
                  : "border border-hairline bg-surface text-body hover:bg-canvas"
              }`}
            >
              {chip.label}
            </button>
          );
        })}
      </div>
      <section>
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
          Featured pulse quotes
        </h2>
        <div className="mt-3 grid gap-3 lg:grid-cols-3">
          {quotes.map((quote) => (
            <QuoteCard key={quote.text} quote={quote} />
          ))}
        </div>
      </section>
      <section>
        <h2 className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
          Anonymous snippets
        </h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {snippets.map((snippet) => (
            <article
              key={snippet.id}
              className="rounded-xl border border-hairline border-l-[3px] border-l-danger bg-surface p-4"
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-danger-soft px-2 py-0.5 text-[11px] font-semibold text-danger tabular">
                  {snippet.stars}★
                </span>
                <span className="rounded-full bg-canvas px-2 py-0.5 text-[11px] font-semibold text-muted">
                  {snippet.theme_label}
                </span>
                <span className="text-[11px] text-muted">
                  {formatShortDate(snippet.date)}
                </span>
                <span className="ml-auto rounded-full border border-hairline bg-canvas px-2 py-0.5 font-mono text-[11px] text-muted">
                  {snippet.id.slice(0, 12)}…
                </span>
              </div>
              <p className="text-[13px] leading-5 text-ink">{snippet.text}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
