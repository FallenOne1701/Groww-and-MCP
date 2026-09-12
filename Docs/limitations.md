# Known limitations (v1)

Assignment non-goals and operational caveats. None of these block the Phase 5 Definition of Done.

## Deferred / out of scope

| Item | Status |
|------|--------|
| **Apple App Store reviews** | Deferred. `source` is Play-only (`play`). No App Store ingest. |
| **Custom Google OAuth / REST clients** | Not the primary path. Docs + Gmail go through MCP tools only. |
| **Auto-send email** | Assignment path is draft-only. Phase 6 may call `gmail_send_email` only with `--send-email` / `PULSE_EMAIL_SEND` (off by default). The graph never sends. |
| **Full review dump in Docs/email** | Pulse only (≤250 words). Raw rows stay local. |
| **Weekly scheduler** | Phase 6 (`python -m src.agent.weekly_job --once`). See `Docs/scheduler.md`. |

## Product / data

- **Public Play listing only.** `--fetch` uses publicly listed reviews. No login-gated scrape, no Play Console private replies as input.
- **English-only, ≥8 words.** Short or non-English reviews are dropped at ingest. Hinglish can still appear inside `language=en` rows; quote selection prefers scannable English.
- **Fixed 5-theme vocabulary.** Long-tail labels (KYC, onboarding, statements, …) merge into the closest bucket — usually `app_reliability` or `customer_support`. A sixth theme is never invented.
- **Heuristic vs LLM.** `--mode heuristic` is keyword-based and deterministic. `--mode llm` needs Groq + Gemini keys and is budget-capped; labels can drift slightly across runs.
- **Polarized ratings.** ~45% of the Phase 1 corpus is ≤2★. Ranking is severity-aware so generic 5★ praise does not dominate the top 3.

## Delivery

- **MCP-Server-1 cannot create a Google Doc.** Operator creates one living Doc; set `PULSE_DOC_ID`. Weekly runs **append** a `YYYY-Www` section.
- **Re-runs.** Phase 6 skips Doc + email when `output/run.json` already has this `week_key` with both `doc_id` and `draft_id`. The Phase 4 graph alone still appends on every publish.
- **Railway 502 / missing `MCP_API_KEY`.** Local `output/pulse.md` is kept; delivery fails with a clear error. Use `--transport inprocess` for an offline stub.
- **Doc OK, draft fails.** Retry `python -m src.agent.run_delivery --gmail-only --doc-url …`.

## Quiet weeks (Phase 5 contract)

If the preferred window has fewer than 30 cleaned reviews, the graph **widens toward 12 weeks**. If it is still sparse:

- A structured **insufficient-signal** pulse is written locally (same headings).
- MCP publish is **skipped** unless `--allow-sparse-delivery`.
- Quotes stay verbatim prefixes; they are never invented.

## Privacy

- Scrubber drops usernames and redacts email / phone / device-like ids in review text.
- Gates scan the pulse (and theme summaries) for leftover patterns. Operator addresses in `.env` / Gmail `To:` are expected and are not treated as reviewer PII.
- Do not commit `.env` or raw exports that still contain identity fields.

## Tracing

- Every graph run writes `output/traces/<week_key>_<utc>.json` and `output/traces/latest.json`.
- LangSmith is optional (`LANGCHAIN_TRACING_V2` + `LANGCHAIN_API_KEY`) and is not required for the demo.
