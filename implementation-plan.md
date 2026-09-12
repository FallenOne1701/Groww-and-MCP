# Implementation Plan: Groww Weekly Review Pulse

Phase-wise plan derived from `problemStatement.md` and `architecture.md`.

**Goal:** Play Store reviews → themed weekly pulse (≤250 words) → Google Docs + Gmail draft via LangChain + MCP.

**Out of scope (v1 assignment):** Apple App Store reviews; custom Google OAuth/REST clients; auto-sending email (draft only).

**Ops add-on (after the assignment DoD):** Phase 6 weekly scheduler — every week download new Play reviews → classify → generate the pulse → **then** append it to the living Google Doc **and** email it. Place it **after Phase 5**, not before.

---

## Phase Map

```
Phase 0  Foundation & repo
    │
Phase 1  Play Store ingest + PII scrub
    │
Phase 2  LangChain analysis (themes → quotes → actions → pulse)
    │
Phase 3  MCP delivery (Docs + Gmail tools)
    │
Phase 4  LangGraph end-to-end orchestration
    │
Phase 5  Gates, hardening, demo readiness
    │
Phase 6  Weekly scheduler (fetch → classify → report → Doc + email)
```

| Phase | Focus | Primary outcome |
|-------|--------|-----------------|
| **0** | Setup | Runnable Python project + folder layout |
| **1** | Data | `data/cleaned/reviews.json` + `data/exports/play_store.csv` (8 weeks, EN, ≥8 words, no PII) |
| **2** | Intelligence | Local `output/pulse.md` from real Phase 1 corpus (data-driven ≤5 themes) |
| **3** | Integrations | Docs create + Gmail draft via MCP (manual tool test OK) |
| **4** | Agent | One command/graph run: data → pulse → Railway MCP Docs append + Gmail draft |
| **5** | Quality | Gates pass; demo checklist green |
| **6** | Schedule | Every week: download new reviews → classify → generate pulse → Google Doc **and** Gmail |

---

## Phase 0 — Foundation & Project Setup

**Objective:** Establish the codebase, dependencies, and conventions so later phases plug in cleanly.

### Tasks

1. Create repository layout per architecture:
   - `data/raw/`, `data/cleaned/`, `output/`, `src/`, `src/agent/`, `prompts/`
2. Add `requirements.txt` (minimum):
   - `langchain`, `langchain-core`, `langgraph`
   - LLM provider package used by the course/lab
   - MCP client / connector libs as provided by the environment
   - `pydantic`, plus CSV/JSON helpers as needed
3. Add `src/models.py` with Pydantic stubs:
   - `Review`, `Theme`, `PulseDraft` (themes ×3, quotes ×3, actions ×3, body, word_count)
4. Add `.gitignore` for `data/raw/`, secrets, `.env`, virtualenv
5. Document env vars needed later (LLM key, MCP config, draft recipient) in a short `README` or `.env.example` — **no secrets committed**

### Deliverables

- [x] Folder structure in place
- [x] Virtualenv + dependencies install cleanly
- [x] Pydantic models defined (even if unused yet)

### Exit criteria

- `pip install -r requirements.txt` succeeds
- Layout matches architecture §7

### Depends on

- Nothing

---

## Phase 1 — Play Store Ingestion & Privacy

**Objective:** Load public Groww Play Store reviews for the last 8–12 weeks and produce a cleaned, PII-free dataset.

### Tasks

1. **Obtain public export** for `com.nextbillion.groww` (CSV/JSON dump or course-provided export) → place under `data/raw/`
2. Implement `src/ingest.py`:
   - Parse export fields → `Review` schema (`source` always `"play"`)
   - Filter `date` to last **8–12 weeks** (default **8**)
   - Drop empty-text reviews; drop reviews with **&lt; 8 words**
   - Keep **English-only** review text (script checks + language detect)
   - Assign opaque local `id`s (do not use usernames as ids)
3. Implement `src/scrub.py`:
   - Drop/redact usernames, emails, phones, device IDs, and other PII fields
   - Keep only fields needed for analysis (`id`, `source`, `rating`, `title`, `text`, `date`, `language`)
4. Write `data/cleaned/reviews.json` and mirror CSV `data/exports/play_store.csv`
5. Add a small sanity script or CLI flag: print count, date min/max, rating histogram

### Deliverables

- [x] `data/cleaned/reviews.json`
- [x] `data/exports/play_store.csv` (filtered mirror)
- [x] Ingest + scrub modules with clear CLI or `main` entry
- [x] Confirmation log: N reviews in window, zero retained PII fields

### Exit criteria

| Check | Pass |
|-------|------|
| Source | Play Store only |
| Window | Dates within ~8–12 weeks of run date |
| Privacy | No usernames/emails/device IDs in cleaned file |
| Schema | Matches architecture `Review` |
| Quality | English only; ≥8 words per review |

### Depends on

- Phase 0

### Notes / risks

- If volume is low at 8 weeks, widen toward 12 before failing the phase
- Do **not** scrape behind logins or violate Play Store ToS

### Phase 1 corpus snapshot (input to Phase 2)

Source of truth for analysis: `data/exports/play_store.csv` (same rows as `data/cleaned/reviews.json`).

| Metric | Value |
|--------|-------|
| Reviews | **1226** |
| App | Groww (`com.nextbillion.groww`) |
| Window | **2026-07-21 → 2026-09-08** (~8 weeks) |
| Language | `en` only |
| Word length | min 8 · median ~17 · avg ~26 · max ~102 |
| Ratings | 1★ **473** · 2★ 77 · 3★ 105 · 4★ 99 · 5★ **472** |
| Low-severity share | **~45%** rated ≤2★ (polarized corpus) |

Keyword probe on this CSV (non-exclusive; guides label set — not final LLM labels):

| Probe theme | Approx hits | Of which ≤2★ |
|-------------|-------------|----------------|
| Trading / orders (buy, sell, stop-loss, IPO, F&O…) | ~364 | ~183 |
| App bugs / not working / update | ~149 | ~99 |
| Customer support | ~149 | ~119 |
| Charges / brokerage / fees | ~84 | ~56 |
| Payments / UPI / deposit | ~70 | ~31 |
| Mutual funds / SIP | ~67 | ~25 |
| Statements / portfolio / holdings | ~46 | ~23 |
| Withdrawals | ~28 | ~21 |
| KYC / verification | ~17 | ~14 |
| Onboarding / signup | ~8 | ~4 |
| No keyword match | ~530 | — |

**Implication:** classic architecture starters (onboarding / KYC / withdrawals) are **low-volume** here. Phase 2 must use a **data-driven ≤5 theme vocabulary** centered on trading, reliability, support, and fees — not the generic five alone.

---

## Phase 2 — LangChain Analysis & Pulse Composition

**Objective:** Build LLM chains that turn the **Phase 1 Groww corpus** (`data/exports/play_store.csv` / `data/cleaned/reviews.json`) into a compliant one-page weekly pulse **locally** (no MCP yet).

### Analysis layer — grounded in Phase 1 data

```
play_store.csv (1226 EN reviews)
        │
        ▼
┌───────────────────┐
│ 1. Load + sample  │  full set or stratified by rating/theme candidate
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 2. Theme label    │  fixed ≤5 labels (data-driven set below)
│    (LangChain)    │  one primary theme per review
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 3. Aggregate      │  Theme[] with counts, avg_rating, sample_ids
│    + rank top 3   │  rank = volume × severity (≤2★ weight)
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 4. Quote select   │  3 verbatim snippets from top themes
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 5. Actions        │  3 concrete next steps tied to top themes
└─────────┬─────────┘
          ▼
┌───────────────────┐
│ 6. Compose pulse  │  ≤250 words → output/themes.json + output/pulse.md
│    + validate     │
└───────────────────┘
```

#### Fixed theme vocabulary (v1) — replace architecture defaults for this corpus

Use **exactly these five** as the LLM label set (cap ≤5). Map long-tail into the closest bucket or `app_reliability` / `trading_orders` rather than inventing a 6th label.

| Theme ID | Label (pulse-facing) | Why (from Phase 1 probe + samples) |
|----------|----------------------|-------------------------------------|
| `trading_orders` | Trading & order execution | Highest hit volume; sell/buy failures, stop-loss, auto square-off, IPO mandate/status, F&O |
| `charts_market_data` | Charts & market / holdings data | Strong 1★ complaints: wrong OHLC, chart UX regressions, misleading avg buy price, stale yields |
| `customer_support` | Customer support | High ≤2★ density; call centre loops, tickets, “no response” |
| `app_reliability` | App reliability & updates | Crashes, lag, “not working”, update regressions, missing controls |
| `fees_funding` | Fees, brokerage & funding | Brokerage/F&O charges + UPI/deposit/withdraw friction (merge thin payments/withdrawals) |

**Do not** force onboarding / KYC / statements as primary themes unless a later re-probe shows volume; treat rare KYC/onboarding mentions as secondary evidence under `customer_support` or `app_reliability` when labeling.

#### Ranking rule (top 3 for pulse)

Given polarization (~45% ≤2★ and many 5★), **do not rank by volume alone**:

1. Primary sort: count of reviews with `rating <= 2` in the theme  
2. Tie-break: total `review_count`  
3. Tie-break: lower `avg_rating`  
4. Stable sort by theme `id`

Expected top-3 candidates from the probe (to validate after LLM labeling): **trading_orders**, **customer_support**, **app_reliability** and/or **charts_market_data**.

#### Scale & cost controls (1226 rows)

- Batch label reviews (e.g. 20–40 texts per LLM call) with structured output → `{review_id, theme_id}`  
- Optional: keyword pre-hint in the prompt (not hard assign) to stabilize labels  
- For quote selection, **candidate pool** = reviews in top-3 themes with `rating <= 3` and word count ≥ 12 (scannable evidence); LLM picks 3 verbatim substrings  
- Never send usernames (already scrubbed); send `id`, `rating`, `text` only  

#### Quote & action guidance from this corpus

- Prefer quotes that name a concrete failure mode (chart OHLC wrong, cannot sell, support no response, brokerage too high) — already abundant in ≤2★ samples  
- Truncate long reviews with ellipsis; keep **verbatim prefix** only  
- Actions should be product-ready, e.g. audit holdings avg-price calc; fix chart gesture/OHLC regression; reduce support dead-ends on funding SLA — each mapped to one top theme  

### Tasks

1. **Prompts** under `prompts/`:
   - `theme_cluster.md` — assign each review to **one** of the five Phase-1-derived theme IDs above; forbid extra theme invention; ≤5 hard cap
   - `quote_select.md` — pick **3 verbatim** snippets from candidate pool; forbid invention/paraphrase-as-quote
   - `action_ideate.md` — **3** actions grounded in ranked themes + selected quotes
   - `pulse_compose.md` — top **3** themes, **3** quotes, **3** actions, **≤250 words**, fixed pulse structure
2. Implement `src/agent/chains.py` (analysis layer):
   - Loader: read `data/cleaned/reviews.json` (preferred) or `data/exports/play_store.csv`
   - Theme labeling chain → structured assignments → aggregate `Theme[]` (cap 5)
   - Rank top 3 with **severity-aware** rule above
   - Quote selection chain (hybrid: retrieve candidates → LLM pick) + **verbatim** validation
   - Action ideation chain grounded in top themes
   - Pulse compose chain → `PulseDraft` + markdown body
3. Persist intermediates:
   - `output/themes.json` (all ≤5 themes + counts + sample_ids)
   - `output/pulse.md`
4. Add validators:
   - `len(themes) <= 5` and theme ids ⊆ fixed vocabulary
   - pulse has exactly 3 themes / 3 quotes / 3 actions
   - word count ≤ 250
   - each quote is a substring of some review `text` (or allowed truncated prefix)
   - simple PII regex scan on pulse body (email/phone patterns)
   - all source reviews in run have `source == "play"` and `language == "en"`

### Deliverables

- [x] Working chains callable from a script (e.g. `python -m src.agent.run_pulse`)
- [x] `output/themes.json` and `output/pulse.md` produced from the Phase 1 CSV/JSON corpus
- [x] Validation passes on the real **1226**-review cleaned dataset

### Exit criteria

| Check | Pass |
|-------|------|
| Input | Uses Phase 1 cleaned Groww Play reviews (EN, ≥8 words, 8-week window) |
| Themes | ≤5 total from fixed data-driven set; pulse shows top 3 |
| Ranking | Top 3 reflect severity-aware ranking (not 5★ fluff alone) |
| Quotes | 3; verbatim; anonymous |
| Actions | 3; tied to themes |
| Length | ≤250 words |
| Privacy | Pulse has no PII |

### Depends on

- Phase 1 (cleaned reviews + `data/exports/play_store.csv`)
- Phase 0 (models, deps, LLM config)

### Phase 2 completion snapshot

| Item | Value |
|------|-------|
| Command | `python -m src.agent.run_pulse` (`--mode auto\|llm\|heuristic`) |
| Corpus | 1226 EN Play reviews |
| Top 3 (heuristic run) | `app_reliability`, `trading_orders`, `customer_support` |
| Artifacts | `output/themes.json`, `output/pulse.md` |
| Gates | ≤5 fixed themes · 3/3/3 · ≤250 words · verbatim quotes · Play/EN only |

### Recommended approach (v1)

1. **LLM labeling** over the **fixed 5-label set in this section** (architecture option 1, vocabulary updated from real data).  
2. Keyword pre-bucket only as a hint / eval baseline — not the sole assigner (~530 rows unmatched by simple keywords).  
3. Add embeddings later only if label quality is weak or unstable across runs.

### Notes / risks

- Polarized ratings: a volume-only top-3 may over-weight generic 5★ praise — keep severity weighting  
- Charts vs trading can overlap; instruct the model: **data/display accuracy → `charts_market_data`**, **order lifecycle → `trading_orders`**  
- Mutual-fund/SIP mentions (~67) are secondary; fold into `fees_funding` or `trading_orders` unless they dominate a weekly slice  

---

## Phase 3 — MCP Delivery (Google Docs & Gmail)

**Objective:** Publish the pulse and create a draft email **only through MCP**, wrapped as LangChain tools.

### Production MCP (chosen)

| Item | Value |
|------|-------|
| Server repo | [FallenOne1701/MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1) |
| Deploy | Railway Streamable HTTP |
| Public host | `https://mcp-server-1-production.up.railway.app` |
| MCP URL | `https://mcp-server-1-production.up.railway.app/mcp` |
| Health | `/health` |
| Container PORT | `8080` (internal; public TLS is :443 — do not append `:8080`) |
| Auth | `Authorization: Bearer <MCP_API_KEY>` (Google OAuth stays on the server) |

**Remote tools used by the agent:**

| Tool | Use |
|------|-----|
| `google_docs_append_content` | Append pulse to existing Doc (`document_id` + `content`) |
| `gmail_create_draft` | Create draft (`to: string[]`, `subject`, `body`) — **never send** |
| `gmail_send_email` | **Out of scope** — agent must not call |

**Docs constraint:** MCP-Server-1 cannot create a new Google Doc. Operator creates one Doc once; set `PULSE_DOC_ID`. Weekly runs **append** a titled section (week key in heading).

### Tasks

1. Point agent at Railway MCP (`MCP_TRANSPORT=http`, `MCP_URL`, `MCP_API_KEY`)
2. Implement `src/agent/tools_mcp.py` + `mcp_bridge.py`:
   - `create_or_update_pulse_doc(title, body) → {doc_id, url}` (maps to append)
   - `create_pulse_draft(to, subject, body) → {draft_id}` (`to` array on the wire)
3. Wire tools as LangChain `BaseTool`s calling the MCP client/bridge
4. Manual smoke test **outside** the full graph:
   - Append sample `pulse.md` to `PULSE_DOC_ID`
   - Create a Gmail **draft** to self/alias (full note or summary + Doc link)
5. Confirm: no direct Google REST client in app code for the happy path
6. Keep `MCP_TRANSPORT=inprocess` stubs for offline demos

### Deliverables

- [x] MCP tool wrappers in repo
- [x] Railway HTTP bridge + Bearer auth + real tool schemas
- [x] Docs append path via `PULSE_DOC_ID`
- [x] Gmail draft via `gmail_create_draft` (not send)
- [x] Short runbook notes (`Docs/mcp-runbook.md`)
- [x] Live smoke on Railway (`output/delivery.json` has real Doc id + Gmail `draft_id`)

### Exit criteria

| Check | Pass |
|-------|------|
| Docs | Pulse visible in Google Docs via MCP append |
| Gmail | Draft exists for self/alias via MCP |
| Integration style | MCP-first; no bespoke Google API primary path |
| Safety | Agent never calls `gmail_send_email` |

### Depends on

- Phase 2 (real pulse content preferred; fixture pulse OK for first MCP test)
- Healthy Railway MCP + Google OAuth configured on the server

### Failure handling (build now, use in Phase 4–5)

- If MCP auth missing: keep `output/pulse.md` and fail delivery with a clear message
- If Doc OK but draft fails: allow retry of Gmail-only step with Doc URL
- If Railway 502/unreachable: clear error + optional `inprocess` stub fallback

### Phase 3 completion snapshot

| Item | Value |
|------|-------|
| Command | `python -m src.agent.run_delivery` |
| Tools | `create_or_update_pulse_doc`, `create_pulse_draft` (LangChain `StructuredTool`s) |
| Production MCP | Railway `MCP-Server-1` → `google_docs_append_content` + `gmail_create_draft` |
| Offline MCP | In-process stubs (`MCP_TRANSPORT=inprocess`) |
| Required env | `MCP_API_KEY`, `PULSE_DOC_ID`, `PULSE_DRAFT_RECIPIENT` |
| Artifacts | `output/delivery.json` (+ stub files under `output/mcp/` when inprocess) |
| Runbook | `Docs/mcp-runbook.md` |

---

## Phase 4 — End-to-End LangGraph Orchestration

**Objective:** One orchestrated run: cleaned data → analysis → Docs (MCP) → Gmail draft (MCP).

**Status:** **Implemented.** `src/agent/graph.py` is the single weekly command. Heuristic + stub MCP E2E is proven on the Phase 1 corpus. Live Railway through the **graph** is the only open checkbox (Phase 3 `run_delivery` already published a real Doc + Gmail draft).

### Tasks

1. Implement `src/agent/graph.py` (LangGraph) with nodes:
   ```
   load → scrub → theme → rank → quotes → actions → compose
        → validate → [publish_doc → draft_email | END]
   ```
   Conditional edges: empty load → END; validation fail or `--skip-delivery` → END (no MCP).
2. Thread state includes: reviews, themes, quotes, actions, pulse text, week_key, title, doc_url, draft_id, errors
3. CLI: `python -m src.agent.graph --weeks 8 --recipient you@example.com`
   - Also: `--mode auto|llm|heuristic`, `--transport`, `--skip-delivery`, `--email-mode`, `--print-graph`
4. Week key / run id (`YYYY-Www`) in Doc **section heading** + email subject (append-only Doc; re-runs add another dated section)
5. Stop before publish if validation fails (do not push bad content to Docs/email)
6. Delivery nodes call the same Phase 3 wrappers (`create_or_update_pulse_doc`, `create_pulse_draft`) — deterministic function calls, not ReAct tool-picking. Never `gmail_send_email`.

### Deliverables

- [x] Single-command (or single-graph) weekly run
- [x] Successful E2E on real Play reviews (heuristic + stub MCP)
- [x] Logged artifacts: themes, pulse, doc URL, draft id
- [ ] Successful E2E against live Railway MCP via the graph  
      (`python -m src.agent.graph --mode heuristic --weeks 8`; Phase 3 live smoke already green)

### Exit criteria

Matches architecture **Definition of Done**:

1. Cleaned Play Store reviews (8–12 weeks) exist — **yes** (1226 EN Play, 8-week window)  
2. ≤5 themes; top 3 selected via LangChain — **yes** (fixed vocab + severity rank; `--mode llm` when keys set)  
3. Pulse in **Google Docs** via Docs MCP (`google_docs_append_content`) — **stub graph yes**; live graph pending (Phase 3 live append already done)  
4. **Gmail draft** via Gmail MCP (`gmail_create_draft`) — **stub graph yes**; live graph pending (Phase 3 live draft already done)  
5. Privacy + verbatim quote constraints hold — **yes** (`validate` node; fail skips MCP)

### Depends on

- Phases 1–3 (Railway credentials optional for `--transport inprocess` / `--skip-delivery`)

### Failure handling (wired in the graph)

- Validation fail → no Docs/Gmail; local invalid pulse is not published
- MCP auth / Railway 502 → keep `output/pulse.md`; clear error; optional `--transport inprocess`
- Doc OK, draft fails → continue; error includes Gmail-only retry hint with Doc URL
- Missing recipient → required on HTTP; stub default only for `inprocess`

### Phase 4 completion snapshot

| Item | Value |
|------|-------|
| Command | `python -m src.agent.graph --mode heuristic --weeks 8` |
| Graph | `load → scrub → theme → rank → quotes → actions → compose → validate → publish_doc → draft_email` |
| Routing | Empty corpus or failed validate / `--skip-delivery` → END (no MCP) |
| Week key | `YYYY-Www` in Doc section title + email subject (append, not overwrite) |
| Gate | `validate_all` before MCP (3/3/3, ≤250 words, verbatim quotes, Play/EN, PII scan) |
| MCP | Same as Phase 3 (`http` → Railway append + draft; `inprocess` stubs) |
| Artifacts | `output/themes.json`, `output/pulse.md`, `output/run.json`, `output/delivery.json` |
| E2E (done) | Heuristic + stub MCP · 1226 reviews · top 3 `app_reliability`, `trading_orders`, `customer_support` · 204 words · week `2026-W37` |
| E2E (open) | Same graph against live Railway (`MCP_TRANSPORT=http`) |

---

## Phase 5 — Quality Gates, Hardening & Demo

**Objective:** Make the system reliable for a demo/review and prove all problem-statement success criteria.

### Tasks

1. Encode architecture §9 gates as automated checks (script or graph node):
   - Window, theme count, quote verbatim, action count, length, privacy, Play-only source
2. Edge cases:
   - Sparse data → widen window / explicit “insufficient signal” pulse (still structured)
   - Over-long quotes → truncate with ellipsis, keep verbatim prefix
   - Theme long-tail → merge into ≤5
3. Optional: LangSmith (or simple file logs) for one traced successful run
4. Demo pack:
   - Sample `output/pulse.md`
   - Link to Docs + screenshot/note of Gmail draft
   - 2-minute walkthrough of phases for stakeholders (Product / Support / Leadership)
5. Final pass against problem-statement checklist (below)

**Do not** enable a weekly cron/Task Scheduler job in this phase. Unattended publish needs Phase 5 gates (and sparse-week behavior) first — see Phase 6.

### Deliverables

- [x] Gate script or validated graph node
- [x] Documented demo path
- [x] Known limitations listed (e.g. App Store deferred)

### Exit criteria

All success criteria in the problem statement are checked off (see Master Checklist).

### Depends on

- Phase 4

### Phase 5 completion snapshot

| Item | Value |
|------|-------|
| Command | `python -m src.agent.run_gates --weeks 8` |
| Graph | Same Phase 4 graph; `validate` now runs named §9 gates; sparse weeks skip MCP |
| Edge cases | Widen 8→12; insufficient-signal pulse (structured); verbatim truncate; long-tail → ≤5 |
| Trace | `output/traces/<week_key>_<utc>.json` + `latest.json` (LangSmith optional) |
| Demo | `Docs/demo.md` · sample `output/pulse.md` · living Doc + Gmail draft note |
| Limits | `Docs/limitations.md` (App Store deferred, draft-only, no scheduler yet) |
| Tests | `python -m unittest tests.test_gates tests.test_edges` |

---

## Phase 6 — Weekly Scheduler (fetch → classify → report → Doc + email)

**Placement: after Phase 5, not before.** Architecture §12 lists “scheduled weekly run” as extensibility. The assignment DoD ends at a correct graph (Phase 4) plus gates/demo (Phase 5). This phase is the **unattended weekly operating loop**: new reviews in, classified pulse out, then **both** delivery surfaces.

| If scheduled *before* Phase 5 | If scheduled *after* Phase 5 |
|-------------------------------|------------------------------|
| Auto-publishes even when gates/edge cases are unfinished | Failed validate / sparse week / PII leak **skips** Doc + email |
| Quiet weeks have no “insufficient signal” contract yet | Phase 5 sparse-week handling is in place |
| Demo/review still blocked on quality, not on cron | Schedule is optional once the pulse is trusted |

### Weekly operating loop (strict order)

Do **not** email or append to the Doc until a validated pulse exists for that week.

```
Monday 08:00 IST  (PULSE_SCHEDULE_WEEKDAY / PULSE_SCHEDULE_HOUR)
        │
        ▼
┌──────────────────────────────────────────┐
│ 1. DOWNLOAD new Play reviews             │
│    python -m src.ingest --fetch --weeks 8│
│    Public listing only → window + scrub  │
│    → data/cleaned/reviews.json           │
│    → data/exports/play_store.csv         │
│    Rolling 8-week window: last week’s    │
│    new reviews appear; older ones drop.  │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│ 2. CLASSIFY                              │
│    Fixed ≤5 themes · one label / review  │
│    Severity-aware rank → top 3           │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│ 3. GENERATE REPORT                       │
│    3 verbatim quotes · 3 actions         │
│    Pulse ≤250 words → output/pulse.md    │
│    Gates (Phase 5) must pass             │
└──────────────────┬───────────────────────┘
                   ▼  only if validation_ok
        ┌──────────┴──────────┐
        ▼                     ▼
┌─────────────────┐   ┌─────────────────────┐
│ 4a. GOOGLE DOC  │   │ 4b. EMAIL           │
│ Append section  │   │ Gmail to recipient  │
│ YYYY-Www onto   │   │ Subject = week key  │
│ PULSE_DOC_ID    │   │ Body = pulse or     │
│                 │   │ summary + Doc link  │
└─────────────────┘   └─────────────────────┘
```

**Both 4a and 4b run after step 3.** Order on the wire: append Doc first (so the email can include `doc_url`), then create the Gmail message. If Docs fails, still email the **full pulse** (no link). If email fails after a successful Doc, keep the Doc URL and retry Gmail-only.

**Email vs assignment DoD:** the course checklist is satisfied by a **Gmail draft** (`gmail_create_draft`). For this weekly ops job the report must still **land in Gmail and in the living Doc**. Default remains draft (operator hits Send). Optional `--send-email` / `PULSE_EMAIL_SEND=true` may call `gmail_send_email` so the recipient’s inbox gets it unattended — **off by default**; do not enable for the assignment demo unless stakeholders ask.

### What “new reviews” means each week

| Rule | Behavior |
|------|----------|
| Source | Same public Groww Play listing (`com.nextbillion.groww`); `--fetch` only |
| Window | Last **8 weeks** from run date (widen toward 12 only if sparse, Phase 5) |
| Incremental | Re-fetch + re-window. Reviews newer than last run enter the corpus; reviews older than the window drop |
| Privacy | Scrub before classify; no usernames in artifacts |
| No fetch | Job fails closed (do not classify last week’s stale file as if it were fresh) |

### Tasks

1. Add `src/agent/weekly_job.py` / `python -m src.agent.weekly_job`:
   - **A. Download:** `ingest --fetch --weeks 8` (refresh cleaned JSON + export CSV)
   - **B. Classify + report:** Phase 4 graph (`theme → rank → quotes → actions → compose → validate`)
   - **C. Deliver (only after gates pass):**
     1. Google Doc — `google_docs_append_content` on `PULSE_DOC_ID` (heading `YYYY-Www`)
     2. Email — `gmail_create_draft` to `PULSE_DRAFT_RECIPIENT` (subject includes week key; body = full pulse or summary + Doc link)
   - Exit non-zero if fetch, validate, Doc, or email fails (scheduler must surface it)
2. CLI flags: `--once` (run now), `--skip-fetch` (debug only), `--skip-delivery`, `--send-email` (opt-in inbox send), `--mode`, `--weeks`, `--transport`
3. **Idempotency:** skip Doc + email if `output/run.json` already has this `week_key` with `validation_ok` and both `doc_id` + `draft_id` (no duplicate append / duplicate mail on retry)
4. **Overlap lock:** `output/weekly_job.lock` — refuse a second run while one is in progress
5. Host the schedule (Windows-first):
   - **Windows Task Scheduler** — weekly Monday 08:00 IST →  
     `.venv\Scripts\python.exe -m src.agent.weekly_job --once`
   - cron / systemd timer on Linux (`0 8 * * 1` in `Asia/Kolkata`)
   - Optional GitHub Actions `schedule` only if secrets live in Actions; prefer a machine that already has `.env`
6. Document trigger, timezone (IST), and Doc + email steps in `Docs/scheduler.md` (link from `Docs/mcp-runbook.md`)
7. Secrets stay on the runner only (`.env`: LLM keys, `MCP_API_KEY`, `PULSE_DOC_ID`, `PULSE_DRAFT_RECIPIENT`). Do not commit raw fetches or PII.

### Deliverables

- [x] `weekly_job` that chains **download → classify → generate report → Doc append + email**
- [x] One documented schedule (Task Scheduler or cron) + `--once` dry-run notes
- [x] Skip/lock so retries do not double-append the Doc or double-email
- [x] Proof: one `--once` (or scheduled) run that pulled a fresher window, wrote a new `YYYY-Www` Doc section, **and** created the Gmail message

### Exit criteria

| Check | Pass |
|-------|------|
| Download | Fresh Play reviews in `data/cleaned/reviews.json` (8–12 weeks, EN, scrubbed) |
| Classify | ≤5 fixed themes; top 3 ranked |
| Report | `output/pulse.md` (3 quotes, 3 actions, ≤250 words, gates green) |
| Google Doc | New `YYYY-Www` section on `PULSE_DOC_ID` via MCP append |
| Email | Gmail message to `PULSE_DRAFT_RECIPIENT` (draft by default; inbox only if `--send-email`) |
| Safety | Gate fail → **no** Doc and **no** email; no overlapping runs |

### Depends on

- Phase 5 (gates + sparse-week behavior)
- Phase 4 graph + Phase 1 `--fetch`
- Healthy Railway MCP for live Doc + Gmail (or `--transport inprocess` for a local-only schedule)

### Phase 6 completion snapshot

| Item | Value |
|------|-------|
| Command | `python -m src.agent.weekly_job --once` |
| Cadence | Weekly · Monday 08:00 IST |
| Sequence | fetch → classify → pulse → **Docs append** → **Gmail** |
| Week key | `YYYY-Www` in Doc heading + email subject |
| Default email | `gmail_create_draft` (assignment-safe) |
| Opt-in send | `--send-email` / `PULSE_EMAIL_SEND` → `gmail_send_email` |
| Lock / skip | `output/weekly_job.lock` · skip if `run.json` already has this `week_key` + `doc_id` + `draft_id` |
| Schedule | `scripts/register-weekly-task.ps1` · `Docs/scheduler.md` |
| Artifacts | refreshed `reviews.json` + `themes.json` + `pulse.md` + `run.json` + `delivery.json` + `weekly_job.json` |
| Proof (`--once`, inprocess) | Fresh fetch **1314** EN Play reviews (was 1226); window through **2026-09-11**; week `2026-W37`; stub `doc_id` + `draft_id` in `output/phase6_proof/` |

### Notes / risks

- `--fetch` uses the public Play listing only (same ToS as Phase 1). No login-gated scrape.
- MCP-Server-1 **appends**; a same-week rerun without the skip check creates a duplicate Doc section and a second email.
- LLM quota: prefer `--mode heuristic` or the hybrid Groq cap for unattended runs unless you have budget headroom.
- This phase is **not** required for the problem-statement checklist (that closes at Phase 5).

---

## Master Checklist (maps to problem statement)

Track across phases; all must be done by end of Phase 5. Phase 6 is ops and is **not** on this list.

- [x] Play Store reviews imported for last 8–12 weeks (public exports only; no App Store) — *Phase 1*
- [x] Reviews clustered into ≤5 themes — *Phase 2*
- [x] One-page weekly pulse (≤250 words) with top 3 themes, 3 quotes, 3 action ideas — *Phase 2*
- [x] Pulse published to Google Docs via MCP — *Phase 3* (Railway `google_docs_append_content`; stubs for offline)
- [x] Draft email created in Gmail via MCP (self / alias) — *Phase 3* (Railway `gmail_create_draft`; never send)
- [x] No PII in any artifact — *Phases 1–5* (`run_gates` privacy + scrub; fail skips MCP)
- [x] No invented quotes; all quotes verbatim from reviews — *Phases 2–5* (verbatim gate; truncate keeps prefix)

---

## Suggested Timeline (flexible)

| Phase | Relative effort | Can parallelize? |
|-------|-----------------|------------------|
| 0 | 0.5 day | — |
| 1 | 1–2 days | After 0 |
| 2 | 2–3 days | Needs 1 |
| 3 | 1–2 days | Can start MCP auth/setup in parallel with late Phase 2 |
| 4 | 1–2 days | Needs 2 + 3 |
| 5 | 1 day | Needs 4 |
| 6 | 0.5–1 day | Needs 5 (do not start unattended jobs earlier) |

**Critical path:** `0 → 1 → 2 → 4 → 5` with **3** overlapping late 2. **Then** `6` if you want hands-off weekly pulses.

---

## Workstream Ownership (if splitting)

| Workstream | Phases | Notes |
|------------|--------|-------|
| Data | 0–1 | Deterministic Python; no LLM required |
| Agent / LLM | 2, 4 | LangChain / LangGraph + prompts |
| Integrations | 3–4 | MCP Docs + Gmail tools only |
| QA / Demo | 5 | Gates + stakeholder walkthrough |
| Ops | 6 | Weekly download → classify → report → Google Doc + Gmail |

---

## Explicit Non-Goals (do not schedule in v1)

- Apple App Store ingestion  
- Hand-rolled Google OAuth + REST as primary Docs/Gmail path  
- Auto-**send** of the weekly email (draft is enough)  
- Full review dump pasted into Docs/email (pulse only)

---

## Phase Completion Sign-off Template

Use at the end of each phase:

```text
Phase: __
Date: __
Artifacts: __
Exit criteria met? Y/N
Blockers for next phase: __
```

---

## Quick Reference — Pulse Contract

Every completed Phase 2+ run must produce:

```text
# Groww Weekly Review Pulse — {Week Ending YYYY-MM-DD}

## Top Themes
1. …
2. …
3. …

## What Users Said
1. “…”   # verbatim
2. “…”
3. “…”

## Action Ideas
1. …
2. …
3. …
```

Constraints: ≤250 words · ≤5 themes clustered · top 3 in note · no PII · Play Store only · Docs + Gmail draft via MCP.
