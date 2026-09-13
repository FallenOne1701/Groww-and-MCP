import type { PulsePayload } from "@/lib/types";
import { CopyPulseButton } from "./CopyPulseButton";
import { QuoteCard } from "./QuoteCard";

export function PulseArticle({ pulse }: { pulse: PulsePayload }) {
  const top = pulse.themes.filter((theme) => pulse.top_3.includes(theme.id));

  return (
    <article className="rounded-xl border border-hairline bg-surface p-6 shadow-[0_1px_3px_rgba(0,0,0,0.04)] lg:p-8">
      <div className="mx-auto max-w-[680px]">
        <h2 className="text-[28px] font-bold leading-9 tracking-tight text-ink lg:text-[30px]">
          {pulse.title}
        </h2>
        <p className="mt-2 text-[13px] text-muted">
          {pulse.review_count.toLocaleString("en-IN")} English Play reviews ·{" "}
          {pulse.window_label}
        </p>

        <section className="mt-8">
          <h3 className="text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
            Top Themes
          </h3>
          <ol className="mt-3 space-y-2 text-[15px] leading-6 text-body">
            {top.map((theme, index) => (
              <li key={theme.id}>
                <span className="font-semibold text-ink tabular">
                  {index + 1}. {theme.label}
                </span>{" "}
                ({theme.review_count} reviews, avg {theme.avg_rating.toFixed(2)})
              </li>
            ))}
          </ol>
        </section>

        <section className="mt-8">
          <h3 className="text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
            What Users Said
          </h3>
          <div className="mt-3 space-y-3">
            {pulse.quotes.map((quote) => (
              <QuoteCard key={quote.text} quote={quote} />
            ))}
          </div>
        </section>

        <section className="mt-8">
          <h3 className="text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">
            Action Ideas
          </h3>
          <ol className="mt-3 space-y-3">
            {pulse.actions.map((action) => (
              <li key={action.id} className="flex gap-3 text-[15px] leading-6 text-body">
                <span className="font-semibold text-accent tabular">{action.id}</span>
                <span>{action.body}</span>
              </li>
            ))}
          </ol>
        </section>

        <footer className="mt-8 flex flex-wrap gap-2 border-t border-hairline pt-5">
          {pulse.delivery.doc_url ? (
            <a
              href={pulse.delivery.doc_url}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white hover:bg-accent-hover"
            >
              Open living Google Doc
            </a>
          ) : null}
          <CopyPulseButton markdown={pulse.pulse_markdown} />
        </footer>
      </div>
    </article>
  );
}
