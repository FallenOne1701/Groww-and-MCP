import type { Quote } from "@/lib/types";

export function QuoteCard({ quote }: { quote: Quote }) {
  return (
    <figure className="rounded-xl border border-hairline border-l-[3px] border-l-accent bg-surface p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-semibold text-accent">
          {quote.theme_label}
        </span>
        <span className="rounded-full bg-danger-soft px-2 py-0.5 text-[11px] font-semibold text-danger">
          {quote.stars}★
        </span>
        <span className="text-[11px] font-semibold text-muted">
          verbatim · anonymous
        </span>
      </div>
      <blockquote className="text-[13px] leading-5 text-ink">
        “{quote.text}”
      </blockquote>
    </figure>
  );
}
