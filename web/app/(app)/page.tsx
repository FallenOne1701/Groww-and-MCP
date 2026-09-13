import { EmptyPulse } from "@/components/pulse/EmptyPulse";
import { GateChecklist } from "@/components/gates/GateChecklist";
import { KpiStrip } from "@/components/pulse/KpiStrip";
import { PulseArticle } from "@/components/pulse/PulseArticle";
import { RatingBar } from "@/components/pulse/RatingBar";
import { truncateDraftId } from "@/lib/format";
import { getPulse } from "@/lib/pulse";

export default async function PulseHome({
  searchParams,
}: {
  searchParams: Promise<{ signal?: string }>;
}) {
  const params = await searchParams;
  const pulse = await getPulse(params.signal === "empty");

  return (
    <div className="space-y-6">
      <KpiStrip pulse={pulse} />
      <div className="grid gap-6 xl:grid-cols-12">
        <div className="xl:col-span-8">
          {pulse.insufficient_signal ? (
            <EmptyPulse weekKey={pulse.week_key} />
          ) : (
            <PulseArticle pulse={pulse} />
          )}
        </div>
        <aside className="space-y-4 xl:col-span-4">
          <div className="rounded-xl border border-hairline bg-surface p-5 shadow-[0_1px_3px_rgba(0,0,0,0.04)]">
            <RatingBar counts={pulse.rating_histogram} />
          </div>
          <GateChecklist pulse={pulse} compact />
          <div className="rounded-xl border border-hairline bg-surface p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
              Delivery
            </p>
            <p className="mt-2 text-[13px] text-body">
              Google Doc {pulse.delivery.doc_url ? "link ready" : "not attached"}
            </p>
            <p className="mt-1 font-mono text-[12px] text-muted">
              {truncateDraftId(pulse.delivery.draft_id)}
            </p>
            <span className="mt-3 inline-flex rounded-full bg-warning-soft px-2 py-0.5 text-[11px] font-semibold text-warning">
              Not sent
            </span>
          </div>
          <p className="text-[12px] text-muted">
            Next run: Monday 08:00 IST · weekly scheduler
          </p>
        </aside>
      </div>
    </div>
  );
}
