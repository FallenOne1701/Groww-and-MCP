import { getPulse } from "@/lib/pulse";

export default async function ActionsPage() {
  const pulse = await getPulse();

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {pulse.actions.map((action) => (
        <article
          key={action.id}
          className="rounded-xl border border-hairline bg-surface p-6 shadow-[0_1px_3px_rgba(0,0,0,0.04)]"
        >
          <p className="text-3xl font-bold text-accent tabular">{action.id}</p>
          <span className="mt-3 inline-flex rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-semibold text-accent">
            {action.theme_label}
          </span>
          <p className="mt-4 text-[15px] leading-6 text-ink">{action.body}</p>
          <p className="mt-4 text-[12px] text-muted">
            Grounded in: “{action.grounded_in}”
          </p>
          <span className="mt-5 inline-flex rounded-full border border-hairline px-2 py-0.5 text-[11px] font-semibold text-body">
            {action.owner}
          </span>
        </article>
      ))}
    </div>
  );
}
