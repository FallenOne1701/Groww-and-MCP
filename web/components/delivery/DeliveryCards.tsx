import { truncateDraftId } from "@/lib/format";
import type { PulsePayload } from "@/lib/types";

const STEPS = [
  "Fetch reviews",
  "Classify ≤5 themes",
  "Compose pulse",
  "Validate gates",
  "Append Doc",
  "Create Gmail draft",
];

export function DeliveryCards({ pulse }: { pulse: PulsePayload }) {
  const skipped = pulse.delivery.delivery_skipped || pulse.insufficient_signal;

  return (
    <div className="space-y-6">
      {skipped ? (
        <div className="rounded-xl border border-danger/20 bg-danger-soft px-4 py-3 text-sm text-danger">
          Local pulse.md kept · delivery skipped
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <article className="rounded-xl border border-hairline bg-surface p-6 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
            Google Docs
          </p>
          <h3 className="mt-2 text-[15px] font-semibold text-ink">
            {skipped
              ? "Doc not updated this week"
              : `Appended section ${pulse.week_key} to living pulse doc`}
          </h3>
          {pulse.delivery.doc_url && !skipped ? (
            <a
              href={pulse.delivery.doc_url}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white hover:bg-accent-hover"
            >
              Open Doc
            </a>
          ) : null}
          <p className="mt-4 text-[12px] text-muted">
            MCP tool: google_docs_append_content (append only, no new-doc create)
          </p>
        </article>

        <article className="rounded-xl border border-hairline bg-surface p-6 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
            Gmail
          </p>
          <h3 className="mt-2 text-[15px] font-semibold text-ink">
            {pulse.delivery.draft_id && !skipped
              ? "Draft created · not sent"
              : "No draft this week"}
          </h3>
          <p className="mt-2 text-[13px] text-body">
            Subject: Groww Weekly Review Pulse — {pulse.week_key}
          </p>
          <p className="mt-1 text-[13px] text-body">Recipient: self / alias</p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-warning-soft px-2 py-0.5 text-[11px] font-semibold text-warning">
              Not sent
            </span>
            <span className="font-mono text-[12px] text-muted">
              {truncateDraftId(pulse.delivery.draft_id)}
            </span>
          </div>
          <p className="mt-4 text-[12px] text-muted">
            MCP tool: gmail_create_draft · agent never calls gmail_send_email
          </p>
        </article>

        <article className="rounded-xl border border-hairline bg-surface p-6 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
            MCP health
          </p>
          <h3
            className={`mt-2 text-[15px] font-semibold ${
              pulse.mcp.ok ? "text-accent" : "text-danger"
            }`}
          >
            {pulse.mcp.ok ? "Railway MCP healthy" : "Railway MCP down"}
          </h3>
          <p className="mt-2 text-[13px] text-body">{pulse.mcp.label}</p>
          <p className="mt-4 text-[12px] text-muted">
            Public /health only. API keys and Bearer tokens never render here.
          </p>
        </article>
      </div>

      <section className="rounded-xl border border-hairline bg-surface p-6">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
          Pipeline
        </h3>
        <ol className="mt-4 space-y-3">
          {STEPS.map((step, index) => (
            <li key={step} className="flex items-center gap-3 text-[13px] text-body">
              <span className="flex size-6 items-center justify-center rounded-full bg-accent-soft text-[11px] font-semibold text-accent tabular">
                {index + 1}
              </span>
              {step}
            </li>
          ))}
        </ol>
        <p className="mt-6 text-[12px] text-muted">
          Run is handled by Monday 08:00 IST scheduler — this UI does not execute
          the weekly job.
        </p>
      </section>
    </div>
  );
}
