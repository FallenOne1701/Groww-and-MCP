export const NAV = [
  { href: "/", label: "Pulse", icon: "pulse" as const },
  { href: "/themes", label: "Themes", icon: "themes" as const },
  { href: "/evidence", label: "Evidence", icon: "evidence" as const },
  { href: "/actions", label: "Actions", icon: "actions" as const },
  { href: "/delivery", label: "Delivery", icon: "delivery" as const },
  { href: "/gates", label: "Gates", icon: "gates" as const },
  { href: "/history", label: "History", icon: "history" as const },
];

export const MOBILE_TABS = [
  { href: "/", label: "Pulse", icon: "pulse" as const },
  { href: "/themes", label: "Themes", icon: "themes" as const },
  { href: "/evidence", label: "Evidence", icon: "evidence" as const },
] as const;

export const PAGE_META: Record<
  string,
  { title: string; subtitle: string }
> = {
  "/": {
    title: "Pulse",
    subtitle: "One-page weekly brief for Product, Support, and Leadership",
  },
  "/themes": {
    title: "Themes",
    subtitle: "Five-theme vocabulary · ranked by ≤2★ severity, not volume",
  },
  "/evidence": {
    title: "Evidence",
    subtitle: "Verbatim Play Store wording · anonymous, no reviewer identities",
  },
  "/actions": {
    title: "Actions",
    subtitle: "Three next steps grounded in this week’s top themes",
  },
  "/delivery": {
    title: "Delivery",
    subtitle: "MCP-first Docs append and Gmail draft · never auto-send",
  },
  "/gates": {
    title: "Quality gates",
    subtitle: "Architecture §9 checks before a week is published",
  },
  "/history": {
    title: "History",
    subtitle: "Archive of weekly executive pulses · append-only living doc",
  },
};
