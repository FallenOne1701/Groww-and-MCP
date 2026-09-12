# Demo pack — Groww Weekly Review Pulse

Two-minute walkthrough for Product, Support, and Leadership. No cron; this is a **gated one-command run**.

## Artifacts to open

| Artifact | Path / link |
|----------|-------------|
| Sample pulse | [`output/pulse.md`](../output/pulse.md) |
| Theme stats | [`output/themes.json`](../output/themes.json) |
| Gate report | `output/gates.json` (written by `python -m src.agent.run_gates`) |
| Living Google Doc | https://docs.google.com/document/d/1AqN2ubfts7Ub6SWPfRj8pIp_rLiVv7xk7x9Klhoa3VY/edit |
| Gmail draft | Drafts folder — id `r-1350697756955077758` (created via `gmail_create_draft`, **not sent**) |
| Last graph summary | [`output/run.json`](../output/run.json) |
| File trace | `output/traces/latest.json` |

The Doc is append-only: each run adds a section titled with ISO week key `YYYY-Www`.

## 2-minute walkthrough

| Time | Audience | What to show |
|------|----------|----------------|
| 0:00–0:25 | **Leadership** | Open the Doc (or `pulse.md`). One page, ≤250 words, week ending date. Health check without raw reviews. |
| 0:25–0:55 | **Product / Growth** | **Top 3 themes** from a severity-aware rank (not 5★ volume). This corpus: app reliability, trading/orders, customer support. |
| 0:55–1:25 | **Support** | **What Users Said** — three verbatim Play Store snippets (ellipsis = truncated prefix, never paraphrased). Actions map 1:1 to those themes. |
| 1:25–2:00 | **All** | How it ships: one graph command → §9 gates → Docs append + Gmail **draft**. Failed gates or a quiet week **do not** publish. |

Talking points:

- Reviews are **Play Store only**, last **8–12 weeks**, English, PII-scrubbed.
- Clustering is capped at **5** fixed themes; the note shows the **top 3**.
- Delivery is **MCP-first** (Railway Docs append + Gmail draft). The agent never calls `gmail_send_email`.

## Commands (live or offline)

```bash
# Prove the problem-statement gates on current artifacts
python -m src.agent.run_gates --weeks 8

# Full graph, local stubs (safe for a conference-room demo)
python -m src.agent.graph --mode heuristic --weeks 8 --transport inprocess

# Analysis + gates only (no Docs/Gmail)
python -m src.agent.graph --mode heuristic --weeks 8 --skip-delivery

# Unit tests for gates + sparse / truncate / long-tail + weekly job
python -m unittest tests.test_gates tests.test_edges tests.test_weekly_job
```

Weekly unattended loop (Phase 6, not required for the assignment demo): `Docs/scheduler.md`.

Live Railway (needs `.env`: `MCP_API_KEY`, `PULSE_DOC_ID`, `PULSE_DRAFT_RECIPIENT`):

```bash
python -m src.agent.graph --mode heuristic --weeks 8
```

Then open the Doc URL in `output/delivery.json` and Gmail → Drafts.

## What “done” looks like on stage

1. `run_gates` prints `Architecture §9 gates: PASS`.
2. Pulse on screen has exactly 3 themes, 3 quotes, 3 actions, ≤250 words.
3. Doc has a dated `2026-Www` section; Gmail has a matching **draft** (unsent).

Known limitations: [limitations.md](limitations.md). Scheduler is Phase 6 and is **not** enabled.
