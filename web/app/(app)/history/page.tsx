import { formatWeekEnding } from "@/lib/format";
import { getPulse } from "@/lib/pulse";
import Link from "next/link";
import { Icon } from "@/components/chrome/Icon";

export default async function HistoryPage({
  searchParams,
}: {
  searchParams: Promise<{ week?: string }>;
}) {
  const pulse = await getPulse();
  const { week } = await searchParams;
  const selected = week ?? pulse.week_key;
  const row = pulse.history.find((item) => item.week_key === selected);
  const loaded = row?.loaded ?? selected === pulse.week_key;

  return (
    <div className="space-y-6">
      <div className="overflow-hidden rounded-xl border border-hairline bg-surface">
        <table className="w-full text-left text-[13px]">
          <thead>
            <tr className="border-b border-hairline text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
              <th className="px-4 py-3">Week</th>
              <th className="px-4 py-3">Ending</th>
              <th className="px-4 py-3">Top theme</th>
              <th className="px-4 py-3">Words</th>
              <th className="px-4 py-3">Gates</th>
            </tr>
          </thead>
          <tbody>
            {pulse.history.map((item) => {
              const active = item.week_key === selected;
              return (
                <tr
                  key={item.week_key}
                  className={`border-b border-hairline last:border-0 ${
                    active ? "bg-accent-soft" : "hover:bg-canvas"
                  }`}
                >
                  <td className="px-4 py-3.5">
                    <Link
                      href={`/history?week=${item.week_key}`}
                      className="font-semibold text-ink"
                    >
                      {item.week_key}
                      {item.week_key === pulse.week_key ? (
                        <span className="ml-2 text-[11px] font-semibold text-accent">
                          current
                        </span>
                      ) : null}
                    </Link>
                  </td>
                  <td className="px-4 py-3.5 text-body">
                    {formatWeekEnding(item.week_ending)}
                  </td>
                  <td className="px-4 py-3.5 text-body">
                    {item.top_theme ?? "sample / not loaded"}
                  </td>
                  <td className="px-4 py-3.5 tabular text-body">
                    {item.word_count ?? "—"}
                  </td>
                  <td className="px-4 py-3.5">
                    {item.gates_ok == null ? (
                      <span className="rounded-full bg-canvas px-2 py-0.5 text-[11px] font-semibold text-muted">
                        n/a
                      </span>
                    ) : (
                      <span
                        className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                          item.gates_ok
                            ? "bg-accent-soft text-accent"
                            : "bg-danger-soft text-danger"
                        }`}
                      >
                        {item.gates_ok ? "PASS" : "FAIL"}
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {!loaded ? (
        <div className="flex flex-col items-center rounded-xl border border-dashed border-hairline bg-surface px-6 py-16 text-center">
          <span className="flex size-12 items-center justify-center rounded-xl bg-accent-soft text-accent">
            <Icon name="doc" className="size-6" />
          </span>
          <h2 className="mt-4 text-lg font-semibold text-ink">
            No snapshot in this demo
          </h2>
          <p className="mt-2 max-w-md text-[13px] text-muted">
            {selected} is marked sample / not loaded. Only {pulse.week_key} has a
            full pulse in this first ship.
          </p>
          <Link
            href="/history"
            className="mt-5 rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white hover:bg-accent-hover"
          >
            Back to {pulse.week_key}
          </Link>
        </div>
      ) : (
        <p className="text-[13px] text-muted">
          Living Doc section for {pulse.week_key} is the current pulse. Open the
          Google Doc from the header to read the append-only archive.
        </p>
      )}
    </div>
  );
}
