import type { PulsePayload } from "@/lib/types";

const ORDER = [
  "window",
  "theme_count",
  "quotes",
  "actions",
  "length",
  "privacy",
  "source",
];

export function GateChecklist({
  pulse,
  compact = false,
}: {
  pulse: PulsePayload;
  compact?: boolean;
}) {
  const rows = ORDER.map((key) => pulse.gates.gates[key]).filter(Boolean);

  return (
    <div>
      {!compact ? (
        <div
          className={`mb-6 rounded-xl px-5 py-4 text-lg font-bold tracking-tight ${
            pulse.gates.ok
              ? "bg-accent-soft text-accent"
              : "bg-danger-soft text-danger"
          }`}
        >
          {pulse.gates.ok ? "PASS — all seven gates green" : "FAIL — week not published"}
        </div>
      ) : (
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.04em] text-muted">
          Gates
        </p>
      )}
      <ul className="divide-y divide-hairline rounded-xl border border-hairline bg-surface">
        {rows.map((row) => (
          <li key={row.name} className="flex items-start gap-3 px-4 py-3.5">
            <span
              className={`mt-0.5 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                row.ok ? "bg-accent-soft text-accent" : "bg-danger-soft text-danger"
              }`}
            >
              {row.ok ? "PASS" : "FAIL"}
            </span>
            <div>
              <p className="text-[13px] font-semibold text-ink">{row.name}</p>
              <p className="text-[12px] text-muted">{row.detail}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
