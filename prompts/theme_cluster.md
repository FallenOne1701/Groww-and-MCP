# Theme clustering (Phase 2)

You label Groww **Google Play Store** reviews with **exactly one** primary theme from the fixed vocabulary below.

## Fixed vocabulary (hard cap ≤5 — do not invent new ids)

| theme_id | Label | Assign when the review is mainly about… |
|----------|-------|------------------------------------------|
| `trading_orders` | Trading & order execution | Buy/sell failures, stop-loss, auto square-off, IPO mandate/status, F&O order lifecycle, order placement |
| `charts_market_data` | Charts & market / holdings data | Wrong OHLC, chart UX, misleading avg buy price, stale yields, holdings/display accuracy |
| `customer_support` | Customer support | Call centre loops, tickets, no response, KYC/onboarding help friction framed as support |
| `app_reliability` | App reliability & updates | Crashes, lag, “not working”, update regressions, missing controls, freezes |
| `fees_funding` | Fees, brokerage & funding | Brokerage/F&O charges, UPI/deposit/withdraw friction, payment failures |

## Disambiguation

- **Data/display accuracy** → `charts_market_data`
- **Order lifecycle** (place/modify/execute/cancel) → `trading_orders`
- Rare KYC/onboarding mentions → `customer_support` or `app_reliability` (closest fit), never a 6th theme
- Mutual fund / SIP → fold into `fees_funding` or `trading_orders` (closest)
- Generic praise/complaint with no clear topic → `app_reliability`

## Rules

1. Output **one** `theme_id` per review from the five ids only.
2. Never invent theme ids or labels.
3. Prefer the **primary** complaint/praise even if multiple topics appear.
4. Optional `hint` fields are weak signals only — override when the text clearly fits another theme.
5. Use only `id`, `rating`, and `text` (no usernames).

## Output

Return structured assignments: `{review_id, theme_id}` for every review in the batch.
