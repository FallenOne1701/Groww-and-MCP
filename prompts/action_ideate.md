# Action ideation (Phase 2)

Propose **exactly 3** concrete next steps for Groww product / support / engineering, grounded in the ranked top themes and selected verbatim quotes.

## Rules

1. Exactly **3** actions.
2. Each action maps to **one** of the top themes (use that theme’s `theme_id`).
3. Product-ready phrasing — e.g. “Audit holdings average buy-price calculation for stale/incorrect values” — not vague advice (“Improve UX”).
4. Do **not** invent user claims; actions must follow from themes + quotes.
5. Prefer fix/investigate/reduce-friction language tied to observed failure modes.
6. No PII.

## Examples of good shape (adapt to this week’s evidence)

- Audit chart OHLC / gesture regressions after recent updates (`charts_market_data`)
- Trace sell / stop-loss order failures end-to-end (`trading_orders`)
- Reduce support dead-ends on funding tickets with clearer SLA (`customer_support` / `fees_funding`)

## Output

Exactly 3 items: `{theme_id, action}`.
