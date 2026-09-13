import type { PulsePayload } from "./types";

const PULSE_MARKDOWN = `# Groww Weekly Review Pulse — Week Ending 2026-09-08

## Top Themes
1. App reliability & updates (588 reviews, avg 3.44)
2. Trading & order execution (361 reviews, avg 2.922)
3. Customer support (105 reviews, avg 1.629)

## What Users Said
1. “The app is super buggy at times, with painstakingly slow loading times for the market data, and this sometimes happen during the peak trading hours. When you reach out to support they keep saying same thing…”
2. “ale fraud h ye. I placed order of buy however they sell my all quantity without placing any sell order. very serious and fraud activity done by groww.”
3. “please don't download this app , because they have worst support system. my experience: I called their support team for email changing problem due to its locked for some reason,they told it's may take 2/3 working…”

## Action Ideas
1. Prioritize crash / freeze / post-update regressions from ≤2★ reviews and add release smoke checks for core screens.
2. Trace sell / stop-loss / square-off failures end-to-end and ship regression tests for the top order-lifecycle breakages.
3. Reduce support dead-ends: publish ticket SLAs and route funding / trading escalations to a faster path.
`;

export const W37_FIXTURE: PulsePayload = {
  week_key: "2026-W37",
  week_ending: "2026-09-08",
  title: "Groww Weekly Review Pulse — Week Ending 2026-09-08",
  review_count: 1226,
  word_count: 204,
  word_limit: 250,
  validation_ok: true,
  insufficient_signal: false,
  window_widened: false,
  window_label: "21 Jul 2026 → 8 Sep 2026",
  top_3: ["app_reliability", "trading_orders", "customer_support"],
  pulse_markdown: PULSE_MARKDOWN,
  themes: [
    {
      id: "app_reliability",
      label: "App reliability & updates",
      review_count: 588,
      avg_rating: 3.44,
      low_star_count: 202,
    },
    {
      id: "trading_orders",
      label: "Trading & order execution",
      review_count: 361,
      avg_rating: 2.92,
      low_star_count: 166,
    },
    {
      id: "customer_support",
      label: "Customer support",
      review_count: 105,
      avg_rating: 1.63,
      low_star_count: 88,
    },
    {
      id: "fees_funding",
      label: "Fees, brokerage & funding",
      review_count: 138,
      avg_rating: 2.65,
      low_star_count: 75,
    },
    {
      id: "charts_market_data",
      label: "Charts & market / holdings data",
      review_count: 34,
      avg_rating: 2.47,
      low_star_count: 19,
    },
  ],
  rating_histogram: [473, 77, 105, 99, 472],
  quotes: [
    {
      theme_id: "app_reliability",
      theme_label: "App reliability & updates",
      stars: 1,
      text: "The app is super buggy at times, with painstakingly slow loading times for the market data, and this sometimes happen during the peak trading hours. When you reach out to support they keep saying same thing…",
    },
    {
      theme_id: "trading_orders",
      theme_label: "Trading & order execution",
      stars: 1,
      text: "ale fraud h ye. I placed order of buy however they sell my all quantity without placing any sell order. very serious and fraud activity done by groww.",
    },
    {
      theme_id: "customer_support",
      theme_label: "Customer support",
      stars: 1,
      text: "please don't download this app , because they have worst support system. my experience: I called their support team for email changing problem due to its locked for some reason,they told it's may take 2/3 working…",
    },
  ],
  actions: [
    {
      id: "01",
      theme_id: "app_reliability",
      theme_label: "App reliability & updates",
      owner: "Engineering",
      body: "Prioritize crash / freeze / post-update regressions from ≤2★ reviews and add release smoke checks for core screens.",
      grounded_in:
        "The app is super buggy at times, with painstakingly slow loading times…",
    },
    {
      id: "02",
      theme_id: "trading_orders",
      theme_label: "Trading & order execution",
      owner: "Product",
      body: "Trace sell / stop-loss / square-off failures end-to-end and ship regression tests for the top order-lifecycle breakages.",
      grounded_in:
        "I placed order of buy however they sell my all quantity without placing any sell order.",
    },
    {
      id: "03",
      theme_id: "customer_support",
      theme_label: "Customer support",
      owner: "Support",
      body: "Reduce support dead-ends: publish ticket SLAs and route funding / trading escalations to a faster path.",
      grounded_in:
        "please don't download this app , because they have worst support system.",
    },
  ],
  snippets: [
    {
      id: "play-00aa3519ed7153a3",
      theme_id: "app_reliability",
      theme_label: "App reliability & updates",
      stars: 1,
      date: "2026-08-17",
      text: "ye aap bhot slow chal rha tha mera loss ho gya ess app ki bjha se.",
    },
    {
      id: "play-04eca2b9e3d6c3a4",
      theme_id: "customer_support",
      theme_label: "Customer support",
      stars: 1,
      date: "2026-08-16",
      text: "kyc process takes longer than usual time, now sent closure request before 2days,again on waiting, no reply of msg,mail and when call, IVR keeps you on waiting and after5 minutes call ends…",
    },
    {
      id: "play-000f53979763356e",
      theme_id: "trading_orders",
      theme_label: "Trading & order execution",
      stars: 1,
      date: "2026-08-07",
      text: "pathetic customer service. I exit one trade today at 3:05 PM that trade is showing again in buy order even though not initiated by me seems to be an system error and amount got debited for the same. no reply from support",
    },
    {
      id: "play-0731d72dd75c840f",
      theme_id: "charts_market_data",
      theme_label: "Charts & market / holdings data",
      stars: 1,
      date: "2026-08-28",
      text: "Hi Team, Recently I see some issues on groww app. when I open any chart , it's automatically changed as full screen and hide the back button, so always it auto selects the groww chart option. please rectify it.",
    },
    {
      id: "play-014a15376f9c43ba",
      theme_id: "fees_funding",
      theme_label: "Fees, brokerage & funding",
      stars: 1,
      date: "2026-07-22",
      text: "broker charges very high isse acha Angel one hai or Motilal hai",
    },
    {
      id: "play-0cc886dfc666a402",
      theme_id: "customer_support",
      theme_label: "Customer support",
      stars: 1,
      date: "2026-08-31",
      text: "I have been a groww customer for the last 5 years. Since last month I have been trying to update my e-mail id but due to reasons unknown it has failed number of times. Everytime I tried changing the email id it shows…",
    },
    {
      id: "play-02b01bbd4f0ebe3f",
      theme_id: "fees_funding",
      theme_label: "Fees, brokerage & funding",
      stars: 1,
      date: "2026-08-05",
      text: "Aware Hidden charges, very high commission. in a equity trading 10-20rs for each buying. if you are planning to invest daily you will be charged 7000INR annually for single stock…",
    },
    {
      id: "play-0c52171a5233255d",
      theme_id: "charts_market_data",
      theme_label: "Charts & market / holdings data",
      stars: 1,
      date: "2026-08-26",
      text: "Already mail at team groww but still not showing charts in my holding, please fix this asap",
    },
  ],
  history: [
    {
      week_key: "2026-W37",
      week_ending: "2026-09-08",
      top_theme: "App reliability & updates",
      word_count: 204,
      gates_ok: true,
      loaded: true,
    },
    {
      week_key: "2026-W36",
      week_ending: "2026-09-01",
      top_theme: null,
      word_count: null,
      gates_ok: null,
      loaded: false,
    },
    {
      week_key: "2026-W35",
      week_ending: "2026-08-25",
      top_theme: null,
      word_count: null,
      gates_ok: null,
      loaded: false,
    },
  ],
  gates: {
    ok: true,
    gates: {
      window: {
        name: "Window",
        ok: true,
        detail: "2026-07-21 → 2026-09-08 (1,226 reviews)",
      },
      theme_count: {
        name: "Theme count",
        ok: true,
        detail: "5 clustered; pulse shows top 3",
      },
      quotes: {
        name: "Quotes",
        ok: true,
        detail: "3; verbatim checked against corpus",
      },
      actions: {
        name: "Actions",
        ok: true,
        detail: "3; each tied to a top theme",
      },
      length: {
        name: "Length",
        ok: true,
        detail: "204 words (limit 250)",
      },
      privacy: {
        name: "Privacy",
        ok: true,
        detail: "no usernames / emails / phones / device IDs",
      },
      source: {
        name: "Source",
        ok: true,
        detail: "Play Store only; language = en",
      },
    },
  },
  delivery: {
    doc_url: null,
    draft_id: "draft_4186da579bc8",
    sent_id: null,
    delivery_skipped: false,
  },
  mcp: { ok: true, label: "mcp-server-1 · Railway" },
};
