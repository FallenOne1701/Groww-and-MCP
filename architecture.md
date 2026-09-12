# Architecture: Groww Weekly Review Pulse

## 1. Overview

This system turns public Groww **Google Play Store** reviews into a **scannable weekly pulse** and delivers it through **Google Docs** and a **Gmail draft**, using a **LangChain AI agent + MCP** integration pattern rather than custom Google OAuth/REST clients.

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌──────────────┐
│ Public      │     │ Ingest &         │     │ Theme, Summarize│     │ Deliver via  │
│ Play Store  │────▶│ Normalize        │────▶│ & Pulse Writer  │────▶│ MCP (Docs +  │
│ Exports     │     │ (8–12 weeks)     │     │ (LangChain)     │     │ Gmail)       │
└─────────────┘     └──────────────────┘     └─────────────────┘     └──────────────┘
```

**Primary product:** Groww (`com.nextbillion.groww`) on Google Play  
**Out of scope:** Apple App Store reviews  
**Primary surfaces:** Google Docs (stakeholder-readable note), Gmail (draft to self/alias)  
**Agent framework:** LangChain (orchestration, LLM chains/agents, tool calling into MCP)

---

## 2. Design Principles

| Principle | Implication |
|-----------|-------------|
| **Play Store only** | Ingest Google Play reviews for Groww only; App Store is deferred |
| **MCP-first delivery** | Docs and Gmail are invoked only through MCP tools; no bespoke Google API client as the primary path |
| **LangChain orchestration** | Use LangChain to build the agent: chains/graphs for theme → quote → actions → pulse, and tools for MCP delivery |
| **Public data only** | Reviews come from public Play Store exports / allowed public sources — no login-gated scraping or ToS-violating automation |
| **Privacy by default** | Strip PII before any artifact is written (Docs, email, local caches) |
| **Scannable output** | Pulse is one page, ≤250 words, fixed structure (3 themes / 3 quotes / 3 actions) |
| **Verbatim evidence** | Quotes are copied from review text; never invented or paraphrased as “quotes” |
| **Bounded clustering** | At most 5 themes; pulse highlights the top 3 |

---

## 3. High-Level Architecture

```
                    ┌─────────────────────────────────────────────────────────┐
                    │              Orchestration Layer (LangChain)             │
                    │   Agent / LCEL chains / LangGraph workflow + MCP tools   │
                    └────────────┬────────────────────────┬───────────────────┘
                                 │                        │
              ┌──────────────────▼──────────┐   ┌─────────▼──────────────────┐
              │     Review Pipeline         │   │     Delivery via MCP         │
              │  ┌───────────────────────┐  │   │  ┌────────────────────────┐  │
              │  │ 1. Import Play Store  │  │   │  │ Google Docs MCP Server │  │
              │  │ 2. Filter window      │  │   │  │  • create / update doc │  │
              │  │ 3. PII scrub          │  │   │  └───────────┬────────────┘  │
              │  │ 4. Theme cluster (≤5) │  │   │              │               │
              │  │ 5. Rank top 3         │  │   │  ┌───────────▼────────────┐  │
              │  │ 6. Select quotes      │  │   │  │ Gmail MCP Server       │  │
              │  │ 7. Propose actions    │  │   │  │  • create draft email  │  │
              │  │ 8. Compose pulse      │  │   │  └────────────────────────┘  │
              │  └───────────────────────┘  │   └──────────────────────────────┘
              └─────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Local Artifacts       │
                    │  • raw Play exports     │
                    │  • cleaned reviews      │
                    │  • themes.json          │
                    │  • pulse.md (optional)  │
                    └─────────────────────────┘
```

### Layers

| Layer | Responsibility |
|-------|----------------|
| **Ingestion** | Load public **Play Store** review exports; keep last 8–12 weeks; normalize fields |
| **Privacy** | Remove usernames, emails, device IDs, and other identifiers |
| **Analysis** | Cluster into ≤5 themes; rank; pick quotes; suggest actions (LangChain LLM steps) |
| **Composition** | Produce the one-page weekly pulse (≤250 words) |
| **Delivery** | Publish Doc + create Gmail draft exclusively via MCP (exposed as LangChain tools) |
| **Orchestration** | **LangChain** agent/graph that sequences steps and calls MCP tools |

---

## 4. Component Detail

### 4.1 Review Ingestion Module

**Purpose:** Obtain and normalize Groww **Google Play Store** reviews for the analysis window.

**Scope:** Play Store only. **Apple App Store reviews are out of scope** for this project.

**Sources (allowed):**
- Public Play Store review **exports** or dumps the environment already provides
- Manually downloaded public Play Store CSVs/JSON (no authenticated scraping)

**App focus:**
- Package / app id: `com.nextbillion.groww`
- Store listing: https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN
- Locale reference: `en_IN` (and any other locales present in the Play export)

**Canonical review schema (normalized):**

```text
Review {
  id           : string          // opaque local id (not store username)
  source       : "play"          // Play Store only in v1
  rating       : number          // e.g. 1–5
  title        : string | null
  text         : string          // review body
  date         : ISO-8601 date
  language     : string | null
}
```

**Window filter:** Keep reviews with `date` in the last **8–12 weeks** relative to run date.

**Outputs:**
- `data/raw/` — untouched Play Store exports (optional archive)
- `data/cleaned/reviews.json` — normalized, windowed, PII-scrubbed records

---

### 4.2 PII Scrubber

**Purpose:** Enforce the privacy constraint before theming or publishing.

**Strip / redact:**
- Usernames / reviewer display names
- Email addresses
- Phone numbers
- Device IDs / advertising IDs
- Any other personally identifiable fields from the export

**Policy:**
- Quotes in the pulse use **anonymous** snippets (review text only)
- Downstream Docs and Gmail payloads must never reintroduce scrubbed fields
- Prefer dropping fields over masking when the field is not needed for analysis

---

### 4.3 Theme Clustering Module

**Purpose:** Group cleaned reviews into a small, product-relevant theme set.

**Hard limit:** ≤ **5** themes total.

**Suggested Groww-oriented theme vocabulary (adapt to data):**

| Theme ID | Example focus |
|----------|----------------|
| `onboarding` | Sign-up, first-time UX, account creation |
| `kyc` | KYC / verification friction |
| `payments` | Deposits, UPI, payment failures |
| `statements` | Reports, tax, portfolio statements |
| `withdrawals` | Payouts, bank transfer delays |
| *(other)* | App performance, trading UX, mutual funds, IPO — only if volume justifies replacing one of the above |

**Approach options (implementation may use one or a mix via LangChain):**
1. **LLM labeling** — LangChain structured-output chain assigns each review to one primary theme from a fixed label set
2. **Embedding + clustering** — Cluster texts (optionally with LangChain embeddings), then name clusters (still cap at 5)
3. **Hybrid** — Keyword/rule pre-bucket, then LLM refinement chain

**Theme record:**

```text
Theme {
  id           : string
  label        : string
  review_count : number
  avg_rating   : number | null
  summary      : string          // short internal summary (not the pulse yet)
  sample_ids   : string[]        // pointers into cleaned reviews
}
```

**Ranking for pulse:** Sort themes by volume (and optionally severity via low ratings); select **Top 3** for the written note.

---

### 4.4 Quote Selector

**Purpose:** Attach real evidence to the pulse.

**Rules:**
- Exactly **3** quotes in the final pulse (may draw from top themes)
- **Verbatim** from review `text` (or title+text if short); no paraphrasing presented as a quote
- Prefer short, scannable snippets (trim with ellipsis only if needed for length)
- No usernames or other PII in the quote line
- Prefer quotes that clearly illustrate a top theme

---

### 4.5 Action Ideation Module

**Purpose:** Produce **3 concrete next steps** grounded in the top themes.

**Guidelines:**
- Each action maps to at least one top theme
- Prefer product/support-ready phrasing (“Investigate KYC drop-off after OTP…”) over vague advice
- Do not invent user claims; actions follow from observed themes/quotes

---

### 4.6 Pulse Composer

**Purpose:** Generate the stakeholder-facing one-page note.

**Structure (fixed):**

```text
# Groww Weekly Review Pulse — {Week Ending YYYY-MM-DD}

## Top Themes
1. …
2. …
3. …

## What Users Said
1. “…”
2. “…”
3. “…”

## Action Ideas
1. …
2. …
3. …
```

**Constraints:**
- Scannable; **≤250 words** where applicable
- Top **3** themes only in the published note
- **3** quotes, **3** actions
- No PII

**Optional local artifact:** `output/pulse.md` (source of truth before MCP publish)

---

### 4.7 Delivery Layer (MCP)

**Purpose:** Publish and notify without custom Google API code.

#### Google Docs MCP

| Capability | Use in this project |
|------------|---------------------|
| Create document | New weekly pulse doc per run (or dated title) |
| Update document | Overwrite/append if reusing a living “latest pulse” doc |
| Return link / id | Include in Gmail draft as pointer |

#### Gmail MCP

| Capability | Use in this project |
|------------|---------------------|
| Create draft | Draft to self or configured alias |
| Body | Full pulse text **or** short summary + Docs link |
| Subject | e.g. `Groww Weekly Review Pulse — {date}` |

**Auth model:** Handled by MCP server / host environment (OAuth tokens, connector login). The **LangChain agent** only **calls MCP tools** (wrapped as LangChain tools).

```
LangChain agent/graph  ──tool──▶  Docs MCP  ──▶  Google Docs
LangChain agent/graph  ──tool──▶  Gmail MCP ──▶  Gmail Drafts
```

---

## 5. End-to-End Data Flow

```
1. LOAD
   Public Play Store export files → raw reviews

2. NORMALIZE + WINDOW
   Map fields → Review schema
   Filter date ∈ [now − 12 weeks, now] (target 8–12 weeks)

3. SCRUB
   Drop/redact PII → cleaned reviews

4. CLUSTER
   Assign themes (≤5) → theme stats + sample review ids

5. SELECT
   Top 3 themes
   3 verbatim quotes
   3 action ideas

6. COMPOSE
   Pulse markdown/text ≤250 words

7. PUBLISH (MCP)
   Docs MCP: create/update pulse document → doc URL/id

8. NOTIFY (MCP)
   Gmail MCP: create draft (body and/or link) → draft id
```

**Idempotency suggestion:** Use a run id / week key (`YYYY-Www`) so re-runs update the same Doc title or produce clearly versioned artifacts.

---

## 6. Orchestration Model (LangChain)

**LangChain is the recommended framework** for building this AI agent: it fits multi-step LLM workflows (theme → quotes → actions → pulse) and tool calling into Docs/Gmail MCP servers.

### Why LangChain fits

| Need | LangChain capability |
|------|----------------------|
| Multi-step pulse pipeline | LCEL chains or **LangGraph** stateful graph (deterministic stages) |
| Theme / quote / action LLM calls | Chat models + structured output (Pydantic / JSON schema) |
| Docs & Gmail delivery | Tools wrapping MCP client calls (`create_doc`, `create_draft`) |
| Prompts & constraints | Prompt templates encoding ≤5 themes, 3 quotes, ≤250 words, no PII |
| Local data access | Tools or RunnableLambdas for load/scrub/filter over `reviews.json` |

### Preferred: LangChain agent / LangGraph workflow

```
                    ┌──────────────────────────────────────┐
                    │         LangChain / LangGraph        │
                    │  nodes: load → scrub → theme →       │
                    │  rank → quotes → actions → compose → │
                    │  publish_doc → draft_email           │
                    └───────────┬──────────────┬───────────┘
                                │              │
                         LLM (theme/pulse)   MCP tools
                                             (Docs, Gmail)
```

Sequence owned by the LangChain graph/agent:

1. Load Play Store cleaned reviews (8–12 week window)  
2. Scrub PII (deterministic Python step inside the graph)  
3. Cluster / label ≤5 themes (LLM structured output)  
4. Rank top 3; select 3 verbatim quotes; propose 3 actions  
5. Compose pulse (≤250 words)  
6. Call **Docs MCP** tool → document URL/id  
7. Call **Gmail MCP** tool → draft to self/alias  

### Stack sketch

| Piece | Choice |
|-------|--------|
| Language | Python |
| Core | `langchain`, `langchain-core`, `langgraph` (recommended for fixed pipeline) |
| LLM provider | Any LangChain chat model the course/lab supports |
| Structured outputs | Pydantic models for `Theme`, `PulseDraft` |
| MCP | MCP Python client or host-provided bridge → wrap as LangChain `BaseTool`s |
| Deterministic I/O | Plain Python modules (`ingest`, `scrub`) invoked as graph nodes |

### Alternative: Thin script + LangChain for LLM steps only

```
Python pipeline (Play ingest, scrub, I/O)
        │
        ▼
LangChain chains (theme, quote pick, actions, prose)
        │
        ▼
LangChain tools → MCP (Docs, Gmail)
```

Either layout is valid; **delivery must remain MCP-first**, and **reviews remain Play Store only**.

---

## 7. Suggested Repository Layout

```text
/
├── problemStatement.md          # Product / assignment context
├── architecture.md              # This document
├── Statement.txt                # Original brief
├── data/
│   ├── raw/                     # Public Play Store exports (gitignored if large)
│   └── cleaned/
│       └── reviews.json
├── output/
│   ├── themes.json
│   └── pulse.md
├── src/
│   ├── ingest.py                # Play Store export → normalized Review
│   ├── scrub.py
│   ├── agent/                   # LangChain / LangGraph
│   │   ├── graph.py             # pipeline graph
│   │   ├── chains.py            # theme / quotes / actions / compose
│   │   └── tools_mcp.py         # Docs + Gmail MCP as LangChain tools
│   └── models.py                # Pydantic schemas
├── prompts/
│   ├── theme_cluster.md
│   ├── quote_select.md
│   └── pulse_compose.md
└── requirements.txt             # langchain, langgraph, mcp client, etc.
```

Boundaries above should stay intact even if package names shift.

---

## 8. MCP Integration Contract

### Inputs the agent prepares before MCP calls

| Artifact | Consumed by |
|----------|-------------|
| Pulse title | Docs + Gmail subject |
| Pulse body (plain or markdown→plain) | Docs content; optional Gmail body |
| Docs URL/id (after create) | Gmail body pointer |
| Recipient | Self or alias for Gmail draft |

### Explicit non-goals

- Implementing Google OAuth clients in app code  
- Hand-rolling Docs/Gmail REST wrappers as the primary path  
- Auto-**sending** email (draft creation is enough unless extended later)

---

## 9. Quality & Compliance Gates

Run these checks before MCP publish:

| Gate | Pass condition |
|------|----------------|
| Window | Reviews restricted to ~8–12 weeks |
| Theme count | ≤5 themes produced; pulse shows top 3 |
| Quotes | Exactly 3; each matches source review text |
| Actions | Exactly 3; each tied to observed themes |
| Length | Pulse scannable / ≤250 words |
| Privacy | No usernames, emails, device IDs in pulse, Doc, or email |
| Source | Play Store public exports only; no App Store; no login-gated scrape |

---

## 10. Failure Modes & Mitigations

| Failure | Mitigation |
|---------|------------|
| Empty/short export in window | Widen window toward 12 weeks; report insufficient data in pulse |
| Theme explosion | Hard-cap labels at 5; merge long-tail into “Other” then rebalance |
| Quote too long | Truncate with ellipsis; keep verbatim prefix |
| MCP auth missing | Fail delivery with clear runbook step; keep local `pulse.md` |
| Doc create succeeds, draft fails | Retry Gmail only; include Doc link in retry payload |
| PII leaked in export fields | Scrub before cluster; refuse to publish if scrubber flags remain |

---

## 11. Security & Privacy Architecture

```
Export (may contain PII)
        │
        ▼
   Scrubber (mandatory)
        │
        ▼
Cleaned store ──▶ Analysis ──▶ Pulse ──▶ MCP (Docs / Gmail)
```

- Treat raw exports as **sensitive**; do not paste raw rows into Docs/email  
- Prefer local cleaned JSON as the only analysis input  
- MCP receives **composed pulse text** (+ metadata), not full review dumps

---

## 12. Extensibility (Non-Blocking)

Optional later enhancements that do not change the core architecture:

- **App Store reviews** (explicitly deferred in v1) — extend `source` and merge pipelines later  
- Trend vs prior week comparison section (keep under word budget)  
- Scheduled weekly run (cron / LangGraph job) calling the same pipeline  
- “Living” Google Doc updated in place vs one doc per week  
- LangSmith tracing for prompt/eval of theme and pulse quality  

---

## 13. Definition of Done (Architecture View)

A run is complete when:

1. Cleaned **Play Store** reviews for the last 8–12 weeks exist (no App Store)  
2. ≤5 themes computed; top 3 selected (via LangChain LLM steps)  
3. Pulse document exists in **Google Docs** via **Docs MCP**  
4. **Gmail draft** exists via **Gmail MCP**, containing the note or a clear link  
5. All privacy and verbatim-quote constraints hold  

---

## 14. Summary Diagram (Logical)

```
 Public Groww Play Store reviews (export)
            │
            ▼
     Ingest + 8–12w filter
            │
            ▼
        PII scrub
            │
            ▼
   ┌─ LangChain / LangGraph ─────────────────┐
   │  Cluster ≤5 themes → Top 3              │
   │       ├──▶ 3 verbatim quotes            │
   │       └──▶ 3 action ideas               │
   │  Weekly pulse (≤250 words)              │
   └──────────────┬──────────────────────────┘
                  │
           ┌──────┴──────┐
           ▼             ▼
     Docs MCP        Gmail MCP
     (publish)       (draft to self)
     via LangChain tools
```

This architecture keeps analysis local and controllable, uses **LangChain** for the agent pipeline, scopes data to **Play Store only**, and keeps Google delivery aligned with the **MCP-first** requirement in the problem statement.
