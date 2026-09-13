import { formatWeekEnding } from "@/lib/format";
import type { PulsePayload } from "@/lib/types";
import { Icon } from "./Icon";
import { PAGE_META } from "./nav";

export function TopBar({
  pathname,
  pulse,
}: {
  pathname: string;
  pulse: PulsePayload;
}) {
  const meta = PAGE_META[pathname] ?? PAGE_META["/"];
  const hideCtas = pulse.insufficient_signal || !pulse.validation_ok;
  const weekLabel = `${pulse.week_key} · Week ending ${formatWeekEnding(pulse.week_ending)}`;

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-hairline bg-surface px-4 lg:px-6">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-lg font-semibold tracking-tight text-ink">
            {meta.title}
          </h1>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-canvas px-2 py-0.5 text-[11px] font-semibold text-body">
            <Icon name="calendar" className="size-3.5 text-muted" />
            {weekLabel}
          </span>
        </div>
        <p className="hidden text-[11px] font-semibold text-muted sm:block">
          {meta.subtitle}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2 sm:gap-3">
        <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-muted">
          <span
            className={`size-2 rounded-full ${pulse.mcp.ok ? "bg-accent" : "bg-danger"}`}
            aria-hidden
          />
          <span className="sr-only">
            MCP {pulse.mcp.ok ? "healthy" : "down"}
          </span>
        </span>
        <span
          className={`hidden rounded-full px-2 py-0.5 text-[11px] font-semibold sm:inline ${
            pulse.gates.ok
              ? "bg-accent-soft text-accent"
              : "bg-danger-soft text-danger"
          }`}
        >
          Gates {pulse.gates.ok ? "PASS" : "FAIL"}
        </span>
        {!hideCtas && pulse.delivery.doc_url ? (
          <a
            href={pulse.delivery.doc_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white shadow-[0_1px_2px_rgba(0,0,0,0.05)] hover:bg-accent-hover"
          >
            <Icon name="external" className="size-3.5 text-white" />
            <span className="hidden sm:inline">Open Google Doc</span>
            <span className="sm:hidden">Doc</span>
          </a>
        ) : null}
        {!hideCtas ? (
          <span className="hidden items-center gap-1.5 rounded-lg border border-hairline bg-surface px-3 py-2 text-xs font-semibold text-ink md:inline-flex">
            <Icon name="mail" className="size-3.5" />
            View Gmail draft
          </span>
        ) : null}
      </div>
    </header>
  );
}
