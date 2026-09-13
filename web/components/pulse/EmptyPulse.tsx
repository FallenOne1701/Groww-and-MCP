import Link from "next/link";

export function EmptyPulse({ weekKey }: { weekKey: string }) {
  return (
    <article className="rounded-xl border border-hairline bg-surface p-6 shadow-[0_1px_3px_rgba(0,0,0,0.04)] lg:p-8">
      <div className="mb-4 rounded-xl border border-danger/20 bg-danger-soft px-4 py-3 text-sm text-danger">
        Gates did not pass · Google Doc and Gmail were not updated.
      </div>
      <h2 className="text-[28px] font-bold tracking-tight text-ink">
        Insufficient signal — week {weekKey}
      </h2>
      <p className="mt-3 max-w-[640px] text-[15px] leading-6 text-body">
        Not enough English Play reviews in the 8-week window. The pipeline widened
        toward 12 weeks and still sat below the publish threshold.
      </p>
      <div className="mt-8 grid gap-3">
        {["Top Themes", "What Users Said", "Action Ideas"].map((label) => (
          <div
            key={label}
            className="rounded-xl border border-dashed border-hairline bg-canvas px-4 py-6 text-sm text-muted"
          >
            {label} — placeholder until the week clears gates
          </div>
        ))}
      </div>
      <Link
        href="/"
        className="mt-6 inline-flex rounded-lg border border-hairline px-3 py-2 text-xs font-semibold text-ink hover:bg-canvas"
      >
        Read last good pulse (2026-W37)
      </Link>
    </article>
  );
}
