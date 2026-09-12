# MCP Delivery Runbook (Phase 3–4)

Groww Weekly Review Pulse publishes to **Google Docs** and creates a **Gmail draft** only through **MCP tools**. App code never uses a bespoke Google OAuth + REST client as the primary path.

**Production MCP:** [FallenOne1701/MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1) on Railway.

| | Value |
|--|--|
| Public base | `https://mcp-server-1-production.up.railway.app` |
| MCP endpoint | `https://mcp-server-1-production.up.railway.app/mcp` |
| Health | `https://mcp-server-1-production.up.railway.app/health` |
| Container PORT | `8080` (Railway internal — **do not** put `:8080` on the public URL) |
| Auth | `Authorization: Bearer <MCP_API_KEY>` |

Google OAuth tokens stay **inside** the Railway server. This agent only needs `MCP_API_KEY`.

## Tools used by the agent

| Role | MCP tool | Notes |
|------|----------|--------|
| Docs | `google_docs_append_content` | Appends to an **existing** Doc (`PULSE_DOC_ID`). No create-doc tool on MCP-Server-1. |
| Gmail | `gmail_create_draft` | `to` is a **string array**. Draft only — never sent. |
| — | `gmail_send_email` | **Not used** (external side effect; out of scope). |

Agent wrappers (LangChain):

- `create_or_update_pulse_doc(title, body)` → appends `# title` + body to `PULSE_DOC_ID` → `{doc_id, url}`
- `create_pulse_draft(to, subject, body)` → `{draft_id}`

## One-time setup

1. Confirm Railway is healthy:
   ```bash
   python -m src.agent.run_delivery --health
   ```
2. Set in `.env` (see `.env.example`):
   - `MCP_TRANSPORT=http`
   - `MCP_URL=https://mcp-server-1-production.up.railway.app/mcp`
   - `MCP_API_KEY=` (same as Railway → Variables → `MCP_API_KEY`)
   - `PULSE_DOC_ID=` (create a Doc in Drive; copy id from the URL)
   - `PULSE_DRAFT_RECIPIENT=` your address / alias
3. List remote tools (needs API key + healthy deploy):
   ```bash
   python -m src.agent.run_delivery --list-remote-tools
   ```
   Expect: `gmail_create_draft`, `gmail_send_email`, `google_docs_append_content`.

## Smoke test

```bash
# After Phase 2 pulse exists
python -m src.agent.run_delivery

# Docs only / Gmail-only retry
python -m src.agent.run_delivery --docs-only
python -m src.agent.run_delivery --gmail-only --doc-url "https://docs.google.com/document/d/<PULSE_DOC_ID>/edit"

# Offline stubs (no Railway)
python -m src.agent.run_delivery --transport inprocess
```

Success writes `output/delivery.json` with `doc_id`, `doc_url`, `draft_id`.

## Phase 4 — full graph

```bash
# Live Railway (default MCP_TRANSPORT=http)
python -m src.agent.graph --mode heuristic --weeks 8 --recipient you@example.com

# Offline stubs
python -m src.agent.graph --mode heuristic --weeks 8 --transport inprocess
```

Doc section title / email subject use ISO week key `YYYY-Www` (append another section on re-run). Validation failure **or** an insufficient-signal week skips MCP. Local pulse stays at `output/pulse.md`.

## Phase 5 — gates before publish

```bash
python -m src.agent.run_gates --weeks 8
```

Architecture §9 must be green (window, ≤5 themes, 3 verbatim quotes, 3 actions, ≤250 words, privacy, Play-only) before Docs/Gmail. Demo path: `Docs/demo.md`. Limits: `Docs/limitations.md`.

## Phase 6 — weekly schedule

Unattended **fetch → classify → pulse → Doc append + Gmail**. Monday 08:00 IST.

```bash
python -m src.agent.weekly_job --once --mode heuristic
```

Idempotent skip when `output/run.json` already has this `week_key` + `doc_id` + `draft_id`. Overlap lock: `output/weekly_job.lock`. Default email remains a **draft**; `--send-email` is opt-in.

Full trigger / Task Scheduler / cron notes: [`Docs/scheduler.md`](scheduler.md).

## Failure handling

| Case | Behavior |
|------|----------|
| MCP_API_KEY missing / 401 | `McpAuthMissingError`; keep `output/pulse.md` |
| Railway 502 / down | Clear unreachable error; fallback `MCP_TRANSPORT=inprocess` for local stubs |
| `PULSE_DOC_ID` missing | Auth/config error before Docs append |
| Doc OK, draft fails | Error includes Doc URL; retry `--gmail-only --doc-url` |
| No recipient | Require `PULSE_DRAFT_RECIPIENT` or `--to` (stub default only for `inprocess`) |

## Env vars

See `.env.example`: `MCP_TRANSPORT`, `MCP_URL`, `MCP_API_KEY`, `PULSE_DOC_ID`, `PULSE_DRAFT_RECIPIENT`, `MCP_DOCS_CREATE_TOOL`, `MCP_GMAIL_DRAFT_TOOL`.

## Local stubs (optional)

| Role | Stub server | Tool |
|------|-------------|------|
| Docs | `python -m src.mcp_servers.docs_server` | `create_or_update_document` |
| Gmail | `python -m src.mcp_servers.gmail_server` | `create_draft` |

`MCP_TRANSPORT=inprocess` — no Google login, artifacts under `output/mcp/`.
