# Weekly scheduler (Phase 6)

Unattended loop: **download new Play reviews → classify → generate the pulse → append the living Google Doc → create the Gmail message**. Gates from Phase 5 still apply — a failed validate, PII leak, or insufficient-signal week **skips Doc and email**.

Cadence: **Monday 08:00 IST** (`PULSE_SCHEDULE_WEEKDAY=0`, `PULSE_SCHEDULE_HOUR=8`).

## Command

```bash
# Production / Task Scheduler entrypoint
python -m src.agent.weekly_job --once

# Safer unattended analysis (no Groq/Gemini quota)
python -m src.agent.weekly_job --once --mode heuristic

# Offline stubs (no Railway)
python -m src.agent.weekly_job --once --mode heuristic --transport inprocess

# Debug: skip the Play download (do not put this on the schedule)
python -m src.agent.weekly_job --once --skip-fetch --transport inprocess

# Show next Monday 08:00 IST slot
python -m src.agent.weekly_job --print-schedule
```

Default email is a **Gmail draft** (`gmail_create_draft`). Inbox send is opt-in:

```bash
python -m src.agent.weekly_job --once --send-email
# or PULSE_EMAIL_SEND=true
```

Do **not** enable `--send-email` for the assignment demo unless stakeholders ask.

## Sequence (strict)

1. **Overlap lock** — `output/weekly_job.lock`. A second run while one is in progress exits `4`.
2. **Download** — `ingest --fetch --weeks 8` (public Groww listing only). Writes `data/cleaned/reviews.json` + `data/exports/play_store.csv`. Fetch failure **fails closed** (does not classify last week’s file).
3. **Classify + report** — Phase 4 graph (`theme → rank → quotes → actions → compose → validate`). Local `output/themes.json` + `output/pulse.md`.
4. **Deliver only if `validation_ok`**
   1. Google Doc — append a `YYYY-Www` section on `PULSE_DOC_ID`
   2. Gmail — draft to `PULSE_DRAFT_RECIPIENT` (subject includes the week key; body = summary + Doc link, or full pulse if Docs failed)

If Docs fails, the job still emails the **full pulse**. If email fails after a successful Doc, `output/run.json` keeps `doc_id` so the next retry is **Gmail-only**.

## Idempotency

Skip Doc + email when `output/run.json` already has this `week_key` with `validation_ok` **and** both `doc_id` + `draft_id`. Same-week retries must not double-append the living Doc.

## `--once` dry-run (local)

From the repo root, with `.venv` active:

```bash
# No Play download, no Railway — proves lock + classify + stub Doc/Gmail
python -m src.agent.weekly_job --once --skip-fetch --mode heuristic --transport inprocess

# Fresh public fetch + stub delivery (needs network; several minutes)
python -m src.agent.weekly_job --once --mode heuristic --transport inprocess
```

Expect `output/weekly_job.json`, refreshed `run.json` / `delivery.json` with stub `doc_id` + `draft_id`, and exit `0`.

Live Railway (needs `.env`: `MCP_API_KEY`, `PULSE_DOC_ID`, `PULSE_DRAFT_RECIPIENT`):

```bash
python -m src.agent.weekly_job --once --mode heuristic --transport http
```

Then open the Doc URL in `output/delivery.json` and Gmail → Drafts.

## Windows Task Scheduler

The runner machine must already have this repo, `.venv`, and a filled `.env`. Secrets stay on the machine — do not commit them.

**Option A — register script (current user, no admin):**

```powershell
cd "<repo>"
powershell -ExecutionPolicy Bypass -File .\scripts\register-weekly-task.ps1
```

That creates task `GrowwWeeklyReviewPulse`:

| | |
|--|--|
| Trigger | Weekly, Monday 08:00 (machine local time — set Windows to **India Standard Time**) |
| Action | `.venv\Scripts\python.exe -m src.agent.weekly_job --once --mode heuristic` |
| Start in | repo root |

Inspect / run once / remove:

```powershell
Get-ScheduledTask -TaskName GrowwWeeklyReviewPulse
Start-ScheduledTask -TaskName GrowwWeeklyReviewPulse
Unregister-ScheduledTask -TaskName GrowwWeeklyReviewPulse -Confirm:$false
```

**Option B — Task Scheduler UI**

1. Create Basic Task → Weekly → Monday → 08:00.
2. Start a program:  
   Program: `<repo>\.venv\Scripts\python.exe`  
   Arguments: `-m src.agent.weekly_job --once --mode heuristic`  
   Start in: `<repo>`
3. Settings → “Run task as soon as possible after a scheduled start is missed”.

`scripts\weekly_job.cmd` is a thin wrapper if you prefer a `.cmd` action.

## Linux cron / systemd

```cron
# /etc/cron.d/groww-pulse  or crontab  (tz Asia/Kolkata)
CRON_TZ=Asia/Kolkata
0 8 * * 1  cd /path/to/repo && .venv/bin/python -m src.agent.weekly_job --once --mode heuristic >> /var/log/groww-pulse.log 2>&1
```

## GitHub Actions (optional)

Only if repo secrets include `MCP_API_KEY`, `PULSE_DOC_ID`, `PULSE_DRAFT_RECIPIENT`, and LLM keys. Prefer a machine that already has `.env` — Actions logs can leak artifacts.

## Env vars (runner only)

See `.env.example`. Required for live Doc + Gmail:

- `MCP_API_KEY`, `MCP_URL`, `MCP_TRANSPORT=http`
- `PULSE_DOC_ID`, `PULSE_DRAFT_RECIPIENT`

Optional schedule knobs: `PULSE_SCHEDULE_WEEKDAY`, `PULSE_SCHEDULE_HOUR`, `PULSE_SCHEDULE_MINUTE`, `PULSE_WEEKLY_MODE`, `PULSE_EMAIL_SEND`.

Do not commit raw Play fetches or `.env`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | OK (including idempotent skip / sparse week with MCP skipped) |
| 1 | Fetch / ingest failed (fail closed) |
| 2 | Validation / gates failed — no Doc, no email |
| 3 | Doc or Gmail failed (local `pulse.md` kept) |
| 4 | Overlap lock — another job is running |
| 5 | Interrupted wait / usage |

MCP auth / Railway notes: [mcp-runbook.md](mcp-runbook.md).
