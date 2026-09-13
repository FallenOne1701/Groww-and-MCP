type IconName =
  | "pulse"
  | "themes"
  | "evidence"
  | "actions"
  | "delivery"
  | "gates"
  | "history"
  | "check"
  | "shield"
  | "calendar"
  | "external"
  | "mail"
  | "more"
  | "doc"
  | "close"
  | "dot";

const PATHS: Record<IconName, string> = {
  pulse:
    "M4 14c2-6 4-9 6-9s3 5 5 5 3-8 5-8 2 6 4 12",
  themes:
    "M4 7h7v7H4zM13 4h7v7h-7zM13 13h7v7h-7zM4 16h7v4H4z",
  evidence: "M7 4h10v16H7zM10 8h4M10 12h4M10 16h3",
  actions: "M9 12.5 11 14.5 16 9.5M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z",
  delivery: "M4 8h10l6 4-6 4H4l3-4z",
  gates: "M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z",
  history:
    "M12 8v5l3 2M4.5 12a7.5 7.5 0 1 0 2-5M4.5 5v4h4",
  check: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM8.5 12.5 11 15l4.5-5",
  shield: "M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z",
  calendar: "M7 4v2M17 4v2M5 8h14M6 6h12a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z",
  external: "M10 6h8v8M18 6l-9 9M7 8H6v10h10v-1",
  mail: "M4 7h16v10H4zM4 7l8 6 8-6",
  more: "M6 12h.01M12 12h.01M18 12h.01",
  doc: "M8 4h6l4 4v12H8zM14 4v4h4",
  close: "M7 7l10 10M17 7 7 17",
  dot: "M12 12m-4 0a4 4 0 1 0 8 0 4 4 0 1 0-8 0",
};

export function Icon({
  name,
  filled = false,
  className = "",
}: {
  name: IconName;
  filled?: boolean;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={`size-[18px] shrink-0 ${className}`}
      fill={filled && name === "dot" ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={PATHS[name]} fill={filled && name !== "dot" ? "currentColor" : undefined} />
    </svg>
  );
}
