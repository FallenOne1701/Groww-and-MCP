export type ThemeId =
  | "app_reliability"
  | "trading_orders"
  | "customer_support"
  | "fees_funding"
  | "charts_market_data";

export type Theme = {
  id: ThemeId;
  label: string;
  review_count: number;
  avg_rating: number;
  low_star_count: number;
};

export type GateRow = {
  name: string;
  ok: boolean;
  detail: string;
};

export type Quote = {
  theme_id: ThemeId;
  theme_label: string;
  stars: 1 | 2;
  text: string;
};

export type ActionItem = {
  id: string;
  theme_id: ThemeId;
  theme_label: string;
  owner: "Product" | "Engineering" | "Support";
  body: string;
  grounded_in: string;
};

export type Snippet = {
  id: string;
  theme_id: ThemeId;
  theme_label: string;
  stars: number;
  date: string;
  text: string;
};

export type HistoryWeek = {
  week_key: string;
  week_ending: string;
  top_theme: string | null;
  word_count: number | null;
  gates_ok: boolean | null;
  loaded: boolean;
};

export type PulsePayload = {
  week_key: string;
  week_ending: string;
  title: string;
  review_count: number;
  word_count: number;
  word_limit: 250;
  validation_ok: boolean;
  insufficient_signal: boolean;
  window_widened: boolean;
  window_label: string;
  top_3: ThemeId[];
  pulse_markdown: string;
  themes: Theme[];
  rating_histogram: [number, number, number, number, number];
  quotes: Quote[];
  actions: ActionItem[];
  snippets: Snippet[];
  history: HistoryWeek[];
  gates: {
    ok: boolean;
    gates: Record<string, GateRow>;
  };
  delivery: {
    doc_url: string | null;
    draft_id: string | null;
    sent_id: null;
    delivery_skipped: boolean;
  };
  mcp: { ok: boolean; label: "mcp-server-1 · Railway" };
};
