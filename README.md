# Groww Weekly Review Pulse

Turn public **Google Play Store** reviews for Groww (`com.nextbillion.groww`) into a scannable weekly pulse, then deliver it via **Google Docs** and a **Gmail draft** using **LangChain + MCP**.

See `problemStatement.md`, `architecture.md`, and `implementation-plan.md` for full context.

## Status

| Phase | Status |
|-------|--------|
| **0** Foundation | Done |
| **1** Ingest + PII scrub | Done |
| **2** LangChain analysis | Done (local `output/pulse.md`) |
| **3** MCP delivery | Done (Docs + Gmail draft via MCP tools) |
| **4** LangGraph E2E | Done (`python -m src.agent.graph`; live Railway graph still open) |
| **5** Gates, hardening, demo | Done (`python -m src.agent.run_gates`; see `Docs/demo.md`) |
| **6** Weekly scheduler | Done (`python -m src.agent.weekly_job --once`; see `Docs/scheduler.md`) |

## Setup

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

Edit `.env` with your LLM key and (later) draft recipient / MCP settings. **Do not commit `.env`.**

## Phase 1 — Ingest & scrub

Public Play Store reviews → window filter (8–12 weeks) → PII scrub → `data/cleaned/reviews.json`.

```bash
# Fetch public reviews into data/raw/, then clean (recommended first run)
python -m src.ingest --fetch --weeks 8

# Or place your own Play Console CSV / JSON under data/raw/ and run:
python -m src.ingest --weeks 8

# Sanity report only (existing cleaned file)
python -m src.ingest --sanity-only
```

| Module | Role |
|--------|------|
| `src/ingest.py` | Parse CSV/JSON, opaque ids, date window, min-words + English filter, CLI |
| `src/scrub.py` | Drop identity fields; redact email/phone/device ids in text |

`--fetch` uses `google-play-scraper` against **publicly listed** reviews (no login). You can instead drop a Play Console export CSV/JSON into `data/raw/`.

## Environment variables

Documented in [`.env.example`](.env.example):

| Variable | When needed | Purpose |
|----------|-------------|---------|
| `GROQ_API_KEY` | Phase 2+ | Groq API key for LangChain |
| `GROQ_MODEL` | Optional | Default `openai/gpt-oss-120b` |
| `GROQ_RPM` / `GROQ_TPM` | Optional | Rate limits (default 30 / 8000) |
| `GROQ_BATCH_SIZE` | Optional | Theme-label batch size (default 8) |
| `GROQ_MAX_LLM_LABEL` | Optional | Max ambiguous reviews sent to Groq (default 40) |
| `GROQ_HEURISTIC_MIN_SCORE` | Optional | Keyword hits to skip Groq (default 1) |
| `PULSE_DRAFT_RECIPIENT` | Phase 3+ | Gmail draft To: address |
| `PULSE_DOC_ID` | Phase 3+ (Railway) | Existing Google Doc id for `google_docs_append_content` |
| `MCP_TRANSPORT` | Phase 3+ | `http` (Railway default) / `inprocess` (stubs) / `stdio` / `config` |
| `MCP_URL` | Phase 3+ | Default `https://mcp-server-1-production.up.railway.app/mcp` |
| `MCP_API_KEY` | Phase 3+ (http) | Bearer token matching Railway `MCP_API_KEY` |
| `MCP_DOCS_CREATE_TOOL` | Optional | Default `google_docs_append_content` |
| `MCP_GMAIL_DRAFT_TOOL` | Optional | Default `gmail_create_draft` (graph never sends) |
| `PULSE_EMAIL_SEND` | Phase 6 opt-in | `true` → `gmail_send_email` (default off) |
| `PULSE_SCHEDULE_HOUR` | Phase 6 | Default `8` (Monday 08:00 IST) |
| `MCP_CONFIG` | Optional | Path to `mcp.json` |
| `REVIEW_WINDOW_WEEKS` | Phase 1+ | Default `8` (range 8–12) |
| `APP_PACKAGE_ID` | Phase 1+ | Default `com.nextbillion.groww` |

## Repo layout

```text
data/raw/          Play Store exports (gitignored contents)
data/cleaned/      reviews.json (normalized, scrubbed)
data/exports/      play_store.csv (filtered mirror)
output/            themes.json, pulse.md
src/models.py      Pydantic schemas
src/ingest.py      Phase 1 ingest CLI
src/scrub.py       Phase 1 PII scrub
src/agent/         Phase 2–6 chains, MCP tools, LangGraph, gates, weekly job
src/mcp_servers/   Docs + Gmail MCP servers (stubs; swap for real MCP)
prompts/           theme / quote / action / pulse prompts
tests/             Gate, edge-case, and weekly-job unit tests
scripts/           Task Scheduler register + weekly_job.cmd
mcp.json.example   Docs/Gmail MCP server config template
Docs/mcp-runbook.md  Auth + smoke-test notes
Docs/demo.md       2-minute stakeholder walkthrough
Docs/scheduler.md  Phase 6 Monday 08:00 IST job
Docs/limitations.md  Known v1 limits (App Store deferred, draft-only, …)
Deployment.md      Railway MCP (live) + Vercel frontend contract
```

## Phase 2 — Analysis & pulse (local)

Cleaned Play reviews → fixed ≤5 themes → top 3 (severity-aware) → 3 quotes → 3 actions → `output/pulse.md`.

```bash
# Auto: dual LLM if keys set, else keyword heuristic
python -m src.agent.run_pulse

# Low-token LLM run (recommended): 200 stratified reviews, ≤40 Groq theme calls
python -m src.agent.run_pulse --mode llm --limit 200

# Force heuristic (no API) or tune Groq budget
python -m src.agent.run_pulse --mode heuristic
python -m src.agent.run_pulse --mode llm --max-llm-label 24 --batch-size 8
```

**Theme labeling is hybrid:** keyword-confident reviews skip Groq; only ambiguous
ones (capped by `GROQ_MAX_LLM_LABEL`, default 40) are batched. Quotes / actions /
pulse still use Gemini in `--mode llm`.

LLM: **Groq** `openai/gpt-oss-120b` (throttled for ~30 RPM / 8K TPM).

| Artifact | Path |
|----------|------|
| Themes | `output/themes.json` |
| Pulse | `output/pulse.md` |

Prompts live under `prompts/` (`theme_cluster`, `quote_select`, `action_ideate`, `pulse_compose`).

### LLM smoke test

```bash
# Ping Groq + Gemini (tiny structured calls)
python -m src.agent.run_llm_smoke

# One provider only
python -m src.agent.run_llm_smoke --provider groq
python -m src.agent.run_llm_smoke --provider gemini

# Mini end-to-end LLM pulse on N reviews (writes output/llm_smoke/)
python -m src.agent.run_llm_smoke --sample 12 --batch-size 4

# Full corpus with hybrid Groq cap (still ≤40 theme API calls by default)
python -m src.agent.run_pulse --mode llm --batch-size 8
```

Needs `GROQ_API_KEY` + `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) in `.env`. Default Gemini model: `gemini-3.6-flash`.

## Phase 3 — MCP delivery (Docs + Gmail)

Publish `output/pulse.md` via **[MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1)** on Railway (Streamable HTTP), or local stubs.

```bash
# Health check (no API key)
python -m src.agent.run_delivery --health

# Production Railway (needs MCP_API_KEY + PULSE_DOC_ID + PULSE_DRAFT_RECIPIENT)
python -m src.agent.run_delivery

# Docs only / Gmail-only retry
python -m src.agent.run_delivery --docs-only
python -m src.agent.run_delivery --gmail-only --doc-url "https://docs.google.com/document/d/<PULSE_DOC_ID>/edit"

# List wrappers / remote tools
python -m src.agent.run_delivery --list-tools
python -m src.agent.run_delivery --list-remote-tools

# Offline stubs
python -m src.agent.run_delivery --transport inprocess
```

| Module | Role |
|--------|------|
| `src/agent/tools_mcp.py` | `create_or_update_pulse_doc`, `create_pulse_draft`, LangChain tools |
| `src/agent/mcp_bridge.py` | Railway HTTP + Bearer auth / stubs / stdio |
| Remote tools | `google_docs_append_content`, `gmail_create_draft` (never `gmail_send_email`) |
| `Docs/mcp-runbook.md` | Auth, `PULSE_DOC_ID`, failure handling |

Artifacts: `output/delivery.json` (stubs also write under `output/mcp/`).

## Phase 4 — LangGraph end-to-end

One graph run: load → scrub → theme → rank → quotes → actions → compose → validate → Railway Docs append → Gmail draft.

```bash
# Full E2E against Railway MCP (default MCP_TRANSPORT=http)
python -m src.agent.graph --mode heuristic --weeks 8 --recipient you@example.com

# Offline stubs (no Railway)
python -m src.agent.graph --mode heuristic --weeks 8 --transport inprocess

# Analysis + validate only (no MCP)
python -m src.agent.graph --mode heuristic --skip-delivery

# Show node order
python -m src.agent.graph --print-graph
```

| Module | Role |
|--------|------|
| `src/agent/graph.py` | LangGraph state, nodes, CLI |
| Week key | `YYYY-Www` in Doc section title + email subject |

Validation failure **stops before** Docs/Gmail. Artifacts: `output/themes.json`, `output/pulse.md`, `output/run.json`, `output/delivery.json`.

## Phase 5 — Quality gates, hardening, demo

Architecture §9 gates (window, ≤5 themes, verbatim quotes, 3 actions, ≤250 words, privacy, Play-only) run in the graph **and** as a standalone script. Sparse weeks widen 8→12 and write a structured insufficient-signal pulse (MCP skipped). Long quotes keep a verbatim prefix + ellipsis; unknown theme ids merge into the fixed five.

```bash
# Check current artifacts against §9
python -m src.agent.run_gates --weeks 8

# Graph with gates + local file trace (output/traces/)
python -m src.agent.graph --mode heuristic --weeks 8 --skip-delivery

# Edge-case + gate + weekly-job unit tests
python -m unittest tests.test_gates tests.test_edges tests.test_weekly_job
```

| Module | Role |
|--------|------|
| `src/agent/validators.py` | Named §9 gates + `evaluate_gates` |
| `src/agent/run_gates.py` | CLI → `output/gates.json` |
| `src/agent/edges.py` | Sparse widen, quote truncate, long-tail merge |
| `src/agent/trace.py` | `output/traces/latest.json` (LangSmith optional) |

Demo pack: [`Docs/demo.md`](Docs/demo.md) (sample pulse, Doc link, Gmail draft note, 2-minute walkthrough). Limitations: [`Docs/limitations.md`](Docs/limitations.md).

## Phase 6 — Weekly scheduler

Every Monday 08:00 IST: fetch public Play reviews → classify → pulse → append `PULSE_DOC_ID` → Gmail draft. Failed gates skip Doc and email. Same-week retries are idempotent.

```bash
# Run now (Task Scheduler / cron entrypoint)
python -m src.agent.weekly_job --once --mode heuristic

# Offline stubs
python -m src.agent.weekly_job --once --mode heuristic --transport inprocess

# Next fire time
python -m src.agent.weekly_job --print-schedule
```

Windows: `powershell -File .\scripts\register-weekly-task.ps1` (set the PC timezone to IST). Notes: [`Docs/scheduler.md`](Docs/scheduler.md).
