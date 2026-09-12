# Edge Cases: Groww Weekly Review Pulse

Corner scenarios derived from `architecture.md` and `implementation-plan.md`.  
Use this as a test matrix and runtime decision guide for Phases 1–5.

**Legend**

| Severity | Meaning |
|----------|---------|
| **Blocker** | Stop publish (Docs/Gmail); fix or degrade explicitly |
| **Degrade** | Continue with a defined fallback; log clearly |
| **Ignore** | Safe to skip / drop the record |

---

## 1. Ingestion & Data Window (Phase 1)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| I-01 | Raw export file missing or empty | Fail Phase 1 with clear error; do not invent reviews | Blocker |
| I-02 | Export has unsupported / unknown columns | Map known fields only; ignore extras; log unmapped columns | Degrade |
| I-03 | Missing `text` (or equivalent body) | Drop review from cleaned set | Ignore |
| I-04 | Missing `date` | Drop review (cannot apply 8–12 week window) | Ignore |
| I-05 | Unparseable date formats | Try common formats; if still invalid → drop + count in ingest report | Ignore |
| I-06 | Dates outside 8–12 week window | Exclude from cleaned set | Ignore |
| I-07 | Very few reviews in last **8** weeks | Auto-widen toward **12** weeks; log window used | Degrade |
| I-08 | Still insufficient after 12 weeks (e.g. &lt; N reviews) | Produce “insufficient signal” pulse path in Phase 2/5; skip or flag weak themes; **do not** fabricate quotes | Degrade |
| I-09 | Duplicate reviews (same text + date + rating) | Dedupe by hash of `(date, rating, text)`; keep one | Degrade |
| I-10 | Extremely large export (tens of thousands of rows) | Window filter first; optionally sample per theme later; avoid sending full dump to LLM/MCP | Degrade |
| I-11 | Non-English / mixed-language reviews | Keep if in window; theme with available text; do not translate quotes (verbatim rule) | Degrade |
| I-12 | Rating missing or out of 1–5 | Keep text for theming if present; set `rating` null; don’t use in severity ranking | Degrade |
| I-13 | Title-only review (empty body) | Treat title as `text` if body empty; else drop | Degrade |
| I-14 | App Store rows accidentally present in a mixed file | **Reject / filter out**; v1 is Play Store only (`source: "play"`) | Blocker* |
| I-15 | Export clearly from wrong app / package | Abort ingest; do not proceed to pulse | Blocker |
| I-16 | Timezone / date-only vs datetime mismatch | Normalize to date (UTC or local consistently); document choice | Degrade |

\*If rows can be filtered cleanly, treat leftover App Store rows as Ignore after filter; if entire file is App Store–only, Blocker.

---

## 2. Privacy & PII Scrub (Phases 1, 2, 5)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| P-01 | Username / reviewer name in export | Drop field; never copy into pulse, Doc, or email | Blocker if published |
| P-02 | Email in review body text | Redact in cleaned `text` (e.g. `[email]`) **or** skip that review for quoting; never publish raw email | Blocker if published |
| P-03 | Phone number in review body | Same as P-02 | Blocker if published |
| P-04 | Device / advertising ID fields | Drop before analysis | Blocker if retained downstream |
| P-05 | PII only discovered at pulse validation (regex) | **Refuse MCP publish**; rewrite/redact; keep local `pulse.md` marked failed | Blocker |
| P-06 | LLM echoes a username from context | Validator fails verbatim/PII gates; regenerate without identity fields in prompt context | Blocker |
| P-07 | Raw export path accidentally passed to Docs/Gmail tool | Tools must accept **pulse text only**; reject payloads that look like full review dumps | Blocker |
| P-08 | Partial scrub (name dropped, email left in text) | Treat as scrub failure; re-run scrub; do not cluster until clean | Blocker |

---

## 3. Theme Clustering (Phase 2)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| T-01 | LLM returns **&gt;5** themes | Hard-cap: merge lowest-volume into `other` until ≤5 | Degrade |
| T-02 | LLM returns **0** themes | Retry once; else insufficient-signal pulse | Degrade |
| T-03 | All reviews map to one theme | Valid; top 3 list may repeat structure with secondary themes from long-tail or note “dominant theme” + 2 weaker ones if counts allow; if truly only one theme, state top 1 clearly and still supply 3 quotes/actions from that theme where possible | Degrade |
| T-04 | Fewer than 3 themes with any volume | Pulse lists available themes (1–2); still require 3 quotes/actions from available evidence; note limited theme diversity | Degrade |
| T-05 | Tie between themes for “top 3” | Break ties by lower `avg_rating` (severity), then stable label sort | Degrade |
| T-06 | Theme labels don’t match Groww vocabulary | Allow data-driven labels; still ≤5; prefer mapping to onboarding/KYC/payments/statements/withdrawals when close | Degrade |
| T-07 | Review fits multiple themes | Assign **one primary** theme only (v1) | Ignore secondary |
| T-08 | Nonsense / spam / one-word reviews (“nice”, “bad”) | Bucket as `other` or exclude from quote pool; don’t let spam dominate top themes if volume is thin | Degrade |
| T-09 | Conflicting ratings vs text (5★ but angry text) | Theme on **text**; optionally flag for quote preference toward text-aligned severity | Degrade |
| T-10 | Embedding cluster count unstable run-to-run | Prefer fixed label set (LLM labeling) for v1; pin seed if embeddings used | Degrade |

---

## 4. Quotes (Phase 2, validators)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| Q-01 | LLM invents / paraphrases a “quote” | Verbatim check fails; regenerate or replace from source substring | Blocker |
| Q-02 | Quote longer than scannable / blows word budget | Truncate with ellipsis; **verbatim prefix** only | Degrade |
| Q-03 | Fewer than 3 usable reviews with text | Use all available unique snippets; if &lt;3, mark pulse incomplete and **block publish** (or explicitly label “limited quotes” only if product accepts — default **Blocker** for MCP) | Blocker |
| Q-04 | Same quote selected three times | Enforce uniqueness; pick next-best verbatim snippets | Degrade |
| Q-05 | Best quote contains PII | Redact or skip; pick alternate verbatim snippet | Degrade / Blocker if no alternate |
| Q-06 | Quote from review outside top themes | Prefer top-theme quotes; allow one cross-theme only if needed to reach 3 | Degrade |
| Q-07 | Unicode / emoji / Devanagari in quote | Keep verbatim; ensure Docs/Gmail MCP UTF-8 safe | Degrade |
| Q-08 | Quote is entire long review | Prefer shorter contiguous snippet that still matches theme; still substring of source | Degrade |

---

## 5. Actions & Pulse Composition (Phase 2)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| A-01 | Actions not grounded in themes | Reject; regenerate with theme ids required in structured output | Blocker |
| A-02 | Vague actions (“improve UX”) | Prompt/retry for concrete product/support steps | Degrade |
| A-03 | Pulse **&gt;250 words** | Trim compose step / regenerate with hard limit; validator blocks publish until ≤250 | Blocker |
| A-04 | Missing section (themes / quotes / actions) | Validator fails; do not publish | Blocker |
| A-05 | Wrong counts (≠3 themes in note, ≠3 quotes, ≠3 actions) | Fail gate; retry compose | Blocker |
| A-06 | Week ending date wrong / missing | Derive from run date or max review date; set consistently in title | Degrade |
| A-07 | Insufficient-data mode | Fixed template: state low volume, window used, any real themes/quotes available; **no invented quotes**; may block Gmail/Docs or publish with explicit “low confidence” banner — choose one policy and stick to it (recommended: publish Doc with banner, still allow draft) | Degrade |
| A-08 | Markdown breaks Docs MCP (tables, raw HTML) | Prefer simple headings + numbered lists per architecture template | Degrade |

---

## 6. MCP Delivery — Docs & Gmail (Phases 3–4)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| M-01 | MCP auth missing / expired | Keep `output/pulse.md`; fail delivery with runbook message; do not crash silently | Blocker (delivery) |
| M-02 | Docs MCP down; Gmail up | Skip Doc; optional draft with **full pulse body** only; log Doc failure | Degrade |
| M-03 | Docs OK; Gmail draft fails | Keep Doc URL; retry Gmail-only with link + short summary | Degrade |
| M-04 | Both MCP servers fail | Local pulse remains source of truth; run status = failed delivery | Blocker (delivery) |
| M-05 | Doc create timeout / partial write | Retry once; else fail Doc node; don’t claim success | Degrade |
| M-06 | Duplicate weekly run (same `YYYY-Www`) | Update existing “latest” doc **or** create versioned title; avoid confusing duplicates — pick one strategy | Degrade |
| M-07 | Invalid / missing draft recipient | Fail Gmail node; require `--recipient` or env default | Blocker (email) |
| M-08 | Email body too large for provider | Send summary + Doc link instead of full note | Degrade |
| M-09 | MCP tool returns success without id/url | Treat as failure; do not mark Definition of Done | Blocker |
| M-10 | Accidental **send** vs draft | v1 must use **draft-only** APIs; never call send | Blocker if send used |
| M-11 | Wrong Google account connected in MCP host | Detect via smoke test; document reconnect steps | Blocker until fixed |
| M-12 | Rate limit from MCP / Google | Backoff + retry; preserve local artifacts | Degrade |

---

## 7. LangChain / LangGraph Orchestration (Phase 4)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| O-01 | LLM API timeout / 429 | Retry with backoff; if exhausted, stop before publish | Degrade → Blocker |
| O-02 | Structured output parse failure | Retry with stricter schema; fail node after N attempts | Degrade |
| O-03 | Graph node fails mid-run after Doc created | Persist state (`doc_url`); allow resume from `draft_email` | Degrade |
| O-04 | Validation fails after compose | **Do not** call Docs/Gmail tools | Blocker |
| O-05 | Stale `reviews.json` (old run) | Require explicit window relative to **run now**; warn if cleaned file older than X days | Degrade |
| O-06 | Concurrent two runs same week | File locks or week-key upsert; last writer wins with logged warning | Degrade |
| O-07 | Prompt injection in review text (“ignore instructions…”) | Treat reviews as untrusted data; system prompt forbids following review instructions; quotes remain data-only | Degrade |

---

## 8. Compliance & Scope Guards

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| C-01 | Request to scrape behind Play login | Refuse; public exports only | Blocker |
| C-02 | Pressure to add App Store in v1 | Out of scope; defer per architecture extensibility | Ignore (scope) |
| C-03 | Custom Google OAuth client proposed as primary path | Reject; MCP-first only | Blocker (design) |
| C-04 | Publishing full cleaned JSON to Docs “for transparency” | Refuse; pulse only (≤250 words) | Blocker |
| C-05 | Leadership wants &gt;5 themes in the note | Cluster may have ≤5; **note highlights top 3 only** | Ignore (scope) |

---

## 9. Decision Tree (Runtime)

```
Ingest Play export
    │
    ├─ empty / wrong app ──────────────────────▶ STOP
    ├─ App Store rows ─────────────────────────▶ filter out (Play only)
    ├─ &lt;8w sparse ─────────────────────────────▶ widen to 12w
    └─ still sparse ───────────────────────────▶ insufficient-signal mode
    │
Scrub PII
    │
    └─ PII remains ────────────────────────────▶ STOP (no cluster/publish)
    │
Theme ≤5 → Top 3 → Quotes ×3 → Actions ×3 → Compose ≤250w
    │
    ├─ verbatim / count / length / PII fail ───▶ retry compose; else STOP publish
    └─ gates pass
            │
        Docs MCP
            ├─ fail ─▶ keep pulse.md; try Gmail with full body (optional)
            └─ ok ──▶ Gmail draft (body or link)
                    ├─ fail ─▶ retry Gmail-only with Doc URL
                    └─ ok ──▶ DONE
```

---

## 10. Minimum Test Fixtures (Phase 5)

Build small fixtures under `data/` or `tests/fixtures/` to cover:

| Fixture | Covers |
|---------|--------|
| `empty.csv` | I-01 |
| `sparse_8w.json` | I-07, I-08, A-07 |
| `with_pii.json` | P-02, P-05 |
| `spam_heavy.json` | T-08 |
| `multi_theme_overflow.json` | T-01 |
| `long_reviews.json` | Q-02, Q-08 |
| `mixed_play_appstore.json` | I-14 |
| `golden_clean.json` | Happy path E2E |

For each fixture: assert severity outcome (Blocker / Degrade) and that MCP publish is skipped when gates fail.

---

## 11. Mapping to Implementation Phases

| Phase | Edge-case IDs to implement/handle |
|-------|-----------------------------------|
| **1** | I-01–I-16, P-01–P-04, P-08 |
| **2** | T-*, Q-*, A-*, P-05–P-06 |
| **3** | M-01–M-12, P-07, C-03–C-04 |
| **4** | O-01–O-07, M-03 resume path |
| **5** | Full matrix + fixtures; C-* policy confirmation |

---

## 12. Non-Edge (Happy Path) Reminder

When none of the above fire:

1. Play Store reviews in 8–12 week window, scrubbed  
2. ≤5 themes, top 3 in note  
3. 3 verbatim anonymous quotes, 3 grounded actions, ≤250 words  
4. Google Doc via Docs MCP + Gmail **draft** via Gmail MCP  
5. No PII in any artifact  

That remains the Definition of Done; every edge case above either preserves this contract or fails closed without silent corruption.
