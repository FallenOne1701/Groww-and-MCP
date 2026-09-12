# Quote selection (Phase 2)

Pick **exactly 3** short, scannable **verbatim** snippets from the candidate review pool. These become “What Users Said” in the weekly pulse.

## Rules

1. Each quote must be a **contiguous substring** of some candidate’s `text` (or a truncated **prefix** of that text ending with `…` / `...`).
2. **Never invent or paraphrase** text and present it as a quote.
3. Prefer concrete failure modes: wrong OHLC/avg price, cannot sell, support no response, brokerage too high, crash after update.
4. Prefer `rating <= 2` evidence; still allow up to 3★ candidates if stronger.
5. Aim for diversity across the **top 3 themes** when possible (one quote per theme is ideal).
6. Keep each quote roughly **12–40 words**; if the review is longer, take a verbatim prefix and append `…`.
7. No usernames, emails, phones, or other PII (candidates are already scrubbed).
8. Return the source `review_id` with each quote.

## Output

Exactly 3 items: `{review_id, quote}`.
