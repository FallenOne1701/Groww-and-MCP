# Deployment: Railway MCP + Vercel Next.js frontend

The **MCP server is already live on Railway.** This note is how to ship a **production-quality stakeholder UI** on Vercel — rebuilt from the Google Stitch export in [`stitch_groww_weekly_review_pulse/`](stitch_groww_weekly_review_pulse/) — without moving Docs/Gmail onto Vercel or leaking secrets into the browser.

**Stack decision:** **Next.js (App Router) + React + TypeScript + Tailwind** on Vercel. Stitch exported static HTML; that folder is the **visual contract**, not the deployable app. Do not host `code.html` as production.

---

## What is already deployed

| Piece | Host | Status |
|-------|------|--------|
| MCP server ([FallenOne1701/MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1)) | **Railway** | Live |
| Python agent (ingest → LangGraph → weekly job) | **Local / Task Scheduler** | Phases 0–6 in this repo |
| Stakeholder UI | **Vercel** | Design ready in `stitch_groww_weekly_review_pulse/` — implement as `web/` |

### Railway MCP (do not redeploy unless it breaks)

| | Value |
|--|--|
| Public base | `https://mcp-server-1-production.up.railway.app` |
| MCP (Streamable HTTP) | `https://mcp-server-1-production.up.railway.app/mcp` |
| Health | `https://mcp-server-1-production.up.railway.app/health` |
| Auth | `Authorization: Bearer <MCP_API_KEY>` |
| Public TLS | `:443` only — do **not** append Railway’s internal `:8080` |

Google OAuth stays **on Railway**. This repo and the Vercel app only need the Bearer key (and only on a **server**, never in client JS).

Remote tools the pulse uses:

| Tool | Role |
|------|------|
| `google_docs_append_content` | Append a `YYYY-Www` section to `PULSE_DOC_ID` |
| `gmail_create_draft` | Draft to `PULSE_DRAFT_RECIPIENT` (assignment default) |
| `gmail_send_email` | Phase 6 opt-in only — keep off for the demo |

MCP runbook: [`Docs/mcp-runbook.md`](Docs/mcp-runbook.md). Design prompts: [`Docs/stitch-prompt.md`](Docs/stitch-prompt.md).

---

## Target topology

```
  Browser (Vercel)
        │  HTTPS  (no MCP_API_KEY)
        ▼
  Next.js on Vercel  ← React UI rebuilt from Stitch
   • App Router pages (Pulse, Themes, Evidence, …)
   • shared chrome (sidebar + header)
   • Route Handlers (BFF) — short requests only
        │
        ├─ read last pulse JSON / Doc URL
        └─ (optional) POST /run → Pulse API on Railway or a webhook
                    │
                    ▼
           Python agent (local or Railway worker)
                    │  MCP HTTP + Bearer
                    ▼
           Railway MCP-Server-1
                    ├─ Google Docs
                    └─ Gmail draft
```

**Hard split**

| Must stay off Vercel | Why |
|----------------------|-----|
| Full `weekly_job` / LangGraph E2E | Fetch + 1k+ reviews exceeds serverless time/memory; no durable `data/` disk |
| Browser → Railway `/mcp` | Would expose `MCP_API_KEY` and is the wrong protocol for a UI |
| Google OAuth / Docs REST in the Next app | Assignment is MCP-first; OAuth already lives on Railway |
| Shipping `stitch_groww_weekly_review_pulse/code.html` as the site | CDN Tailwind, no routing, hardcoded sample data, no BFF |

Vercel is the **read / trigger UI**. Railway MCP is the **only** Docs + Gmail path. The Python agent remains the **only** caller of MCP tools.

---

## Frontend source of truth (Stitch)

The Google Stitch project lives in this repo. Use it as the pixel and token reference; then **rebuild** it as a Next.js app.

| File | Role |
|------|------|
| [`stitch_groww_weekly_review_pulse/DESIGN.md`](stitch_groww_weekly_review_pulse/DESIGN.md) | Tokens, type scale, chrome, components, motion of the design system |
| [`stitch_groww_weekly_review_pulse/code.html`](stitch_groww_weekly_review_pulse/code.html) | High-fidelity History screen + shared sidebar/header (Tailwind + Inter + Material Symbols) |
| [`Docs/stitch-prompt.md`](Docs/stitch-prompt.md) | Full IA (9 screens), sample copy, and Next.js route map |

**Do not**

- Open `code.html` in a static host and call it the product
- Copy Stitch’s CDN Tailwind (`cdn.tailwindcss.com`) into production
- Keep Stitch’s Material 3 token dump (`surface-container-low`, `on-tertiary-fixed`, …) as the runtime theme. Prefer the **Groww fintech tokens** in `DESIGN.md` § Colors (`#00B386`, `#0B0D12`, `#F6F7F9`, `#44475B`)
- Invent extra nav, a chat widget, or a “Send email” button

**Do**

- Extract **shared chrome** first (dark 240px sidebar, 64px header, week chip, MCP pill, Gates chip, Open Doc / View draft)
- Rebuild every Stitch screen as a typed React route
- Bind real `run.json` / `themes.json` / `gates.json` / `delivery.json` / `pulse.md` through a BFF
- Keep Stitch’s sample W37 copy only as a **fallback / Storybook fixture**, never as the only data path

---

## Recommended stack (quality bar)

Use **Next.js**, not a bare Vite SPA, so secrets stay on the server and Vercel is a first-class host.

| Layer | Choice | Why |
|-------|--------|-----|
| Framework | **Next.js 15 App Router** (React 19) | File routes match Stitch IA; Route Handlers are the BFF; Vercel preset |
| Language | **TypeScript** strict | Pulse JSON is a contract (`week_key`, gates, themes) |
| Styling | **Tailwind CSS** (installed, not CDN) + CSS variables from `DESIGN.md` | Stitch already thinks in Tailwind utilities |
| Fonts | `next/font/google` → **Inter** (100–900) | Matches Stitch; no render-blocking Google Fonts `<link>` |
| Icons | **Material Symbols Outlined** (self-hosted or `material-symbols` package) | Same icon set as `code.html` |
| Data | Server Components + `app/api/pulse` BFF | Browser never sees `PULSE_API_SECRET` / MCP keys |
| Quality | ESLint + Prettier, `next/image` unused for photos (there are none), WCAG AA | Leadership-ready, privacy-first |

A Vite + React SPA is acceptable only if you still put a tiny BFF in front of secrets. Prefer Next.js so one Vercel project covers UI + `/api/*`.

### Quality rules

1. **Rebuild, don’t wrap.** Components (`Sidebar`, `TopBar`, `StatusChip`, `KpiCard`, `QuoteCard`, `ThemeRow`, `GateRow`) — not one giant HTML string.
2. **One layout, many pages.** `app/(app)/layout.tsx` owns sidebar + header. Screens only own the main canvas.
3. **Empty / fail / loading.** Insufficient-signal (Stitch screen 8), MCP-down chip, and skeleton KPI cards are first-class, not afterthoughts.
4. **Privacy.** Never render reviewer names, emails, phones, device IDs, or `recipient` from `delivery.json`. Show `draft_id` truncated; mask any address as “self / alias”.
5. **No secrets in the client bundle.** No `NEXT_PUBLIC_MCP_API_KEY`. MCP health may be fetched from the public `/health` URL or via `/api/health`.
6. **Accessibility.** Mint focus ring (`0 0 0 2px #D1F2E8` + `#00B386` border). PASS/FAIL is text + icon, not color alone. `tabular-nums` on ratings and counts.
7. **Responsive.** Desktop: 240px rail. Tablet: 64px icon rail. Mobile: bottom tabs Pulse / Themes / Evidence / More (Gates + History + Actions + Delivery in overflow). Sticky “Open Doc” above the tab bar.
8. **No “Run weekly job” on Home.** If present at all, it is a secondary control on Delivery that hits Pulse API `POST /api/run` (202), never the LangGraph import.

---

## App layout (`web/`)

Keep the Python tree as-is. Vercel **Root Directory** = `web`.

```text
web/                              # Next.js App Router — Vercel project root
  app/
    layout.tsx                    # Inter, CSS variables, html/body
    (gate)/login/page.tsx         # Stitch access gate (shared password)
    (app)/
      layout.tsx                  # Sidebar + TopBar chrome
      page.tsx                    # Pulse Home
      themes/page.tsx
      evidence/page.tsx
      actions/page.tsx
      delivery/page.tsx
      gates/page.tsx
      history/page.tsx
    api/pulse/route.ts            # BFF: last run + themes + pulse body
    api/health/route.ts           # proxy Railway /health (no API key)
    api/run/route.ts              # optional: forward 202 to Pulse API
  components/
    chrome/Sidebar.tsx
    chrome/TopBar.tsx
    chrome/MobileTabBar.tsx
    pulse/KpiStrip.tsx
    pulse/PulseArticle.tsx
    pulse/QuoteCard.tsx
    pulse/RatingBar.tsx
    themes/ThemeTable.tsx
    delivery/DeliveryCards.tsx
    gates/GateChecklist.tsx
  lib/
    tokens.ts                     # DESIGN.md colors / radius / type
    pulse.ts                      # typed fetch of /api/pulse
    types.ts                      # PulsePayload, Theme, Gate, Delivery
  public/
  .env.example
  tailwind.config.ts
```

### Stitch screen → route

| Stitch screen | Route | Primary data |
|---------------|-------|----------------|
| Access gate | `/login` (middleware or `(gate)` group) | Shared password cookie — **no Google SSO** |
| Pulse Home | `/` | `run.json` + `pulse.md` + MCP health |
| Themes | `/themes` | `themes.json` (all 5) + `top_3` |
| Evidence | `/evidence` | 3 pulse quotes + anonymous snippets (id, stars, theme, date, text) |
| Actions | `/actions` | 3 actions mapped to top themes |
| Delivery | `/delivery` | `delivery.json` + MCP `/health` |
| Quality gates | `/gates` | `gates.json` / `run.gates` |
| History | `/history` | week list; older weeks may be “snapshot not loaded” |
| Insufficient signal | `/` empty variant | `insufficient_signal: true` — hide Doc/Gmail CTAs |

### What each screen must show

**Pulse Home (fold on 1440px)**

- Week key (`YYYY-Www`) and week ending
- KPI strip: reviews in window, low-star share, pulse length (`word_count` / 250), delivery (Doc appended · draft ready)
- Pulse article: Top Themes · What Users Said · Action Ideas (≤250 words)
- Rating distribution 1★–5★, gate mini-list, delivery card, “Monday 08:00 IST” next run
- Primary: Open living Google Doc. Secondary: Copy pulse. No Send email.

**Themes** — all five vocabulary themes; top 3 as ranked cards (severity = ≤2★ first, not volume); remaining two as “Also clustered”.

**Evidence** — featured 3 verbatim quotes, then 6–8 anonymous cards. Persistent bar: “No usernames, emails, or device IDs.”

**Actions** — three numbered cards (`01` / `02` / `03` in mint), each tagged to a top theme. Not a Kanban.

**Delivery** — Docs append, Gmail **draft / not sent**, MCP health. Timeline: Fetch → Classify → Compose → Gates → Doc → Draft. Never render an API key.

**Gates** — seven rows from `run.gates`: window, theme_count, quotes, actions, length, privacy, source. Large PASS/FAIL banner.

**History** — current week + earlier rows; do not invent full fake pulses for missing weeks.

---

## Design tokens (lock these)

Copy into `web` as CSS variables / Tailwind theme. Source: `DESIGN.md` (Groww layer), not the YAML Material dump at the top of that file.

| Token | Value | Use |
|-------|--------|-----|
| Canvas | `#F6F7F9` | Page wash |
| Surface | `#FFFFFF` | Cards, header |
| Sidebar | `#0B0D12` | 240px rail |
| Sidebar text | `#E8EAED` | Nav labels |
| Text | `#1E222B` / `#44475B` | Headings / body |
| Muted | `#7C7E8C` | Meta, overlines |
| Accent | `#00B386` | CTA, success, selected nav |
| Accent hover | `#009E76` | Primary button hover |
| Accent soft | `#E6F7F2` | Chips, selected row |
| Border | `#F0F0F2` | Hairline |
| Danger | `#E05656` + `#FDE8E8` | ≤2★, MCP down, failed gates |
| Warning | `#D97706` + `#FEF3C7` | Sparse week, draft not sent |
| Radius | 12px cards, 8px controls, 999px chips | |
| Shadow | `0 1px 3px rgba(0,0,0,0.04)` | Almost flat |
| Type | Inter — headlines 600/700, body 400, `label-sm` uppercase 11px / 0.04em | |
| Grid | 8px; page padding 24–32px; card padding 16–24px | |

Icons: Material Symbols at 18px, weight 400, `FILL` 1 only on the active nav item (as in `code.html`).

---

## Environment variables

### Vercel — public (safe in the browser)

Prefix **`NEXT_PUBLIC_`**. These are baked into the client bundle.

| Variable | Example | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_PULSE_DOC_URL` | `https://docs.google.com/document/d/<PULSE_DOC_ID>/edit` | Open living Doc |
| `NEXT_PUBLIC_MCP_HEALTH_URL` | `https://mcp-server-1-production.up.railway.app/health` | Status chip |
| `NEXT_PUBLIC_PRODUCT_NAME` | `Groww` | Header wordmark caption |

### Vercel — server-only (Route Handlers)

**Never** prefix these with `NEXT_PUBLIC_`. Never commit them.

| Variable | Use |
|----------|-----|
| `PULSE_API_URL` | Optional backend that returns `run.json` / `pulse.md` |
| `PULSE_API_SECRET` | Shared secret if the Pulse API requires `Authorization` |
| `PULSE_SITE_PASSWORD` | Optional access-gate password (httpOnly cookie) |

### Do **not** put these on Vercel

| Variable | Lives where |
|----------|-------------|
| `MCP_API_KEY` | Railway MCP + the **Python runner** `.env` only |
| `GROQ_API_KEY` / `GOOGLE_API_KEY` | Python runner only |
| `PULSE_DRAFT_RECIPIENT` | Python runner / MCP path — UI must not display the raw address |
| Google refresh tokens | Railway MCP service variables |

If a Vercel Route Handler ever needed to call MCP (not recommended), that key would still be server-only — and the function still must not run the full weekly fetch.

### Python runner (unchanged)

Keep using repo `.env` / `.env.example` on the machine (or Railway worker) that runs:

```bash
python -m src.agent.weekly_job --once --mode heuristic
```

Required for live Doc + Gmail: `MCP_TRANSPORT=http`, `MCP_URL`, `MCP_API_KEY`, `PULSE_DOC_ID`, `PULSE_DRAFT_RECIPIENT`.

---

## Scaffold and implement

From the repo root (do not generate the app *inside* the Stitch folder):

```bash
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir=false --import-alias "@/*"
```

Then:

1. Port tokens from `DESIGN.md` into `tailwind.config.ts` / `app/globals.css`.
2. Split `code.html` into `Sidebar` + `TopBar` (ignore the History-only `<main>` until `/history`).
3. Add the remaining routes from the table above; keep chrome identical.
4. Implement `GET /api/pulse` to return a single typed payload (see below).
5. Replace hardcoded W37 strings with that payload; keep W37 as a fixture for local UI work.
6. Add `/login` if the pulse should not be world-readable.

`web/.env.example` should list only `NEXT_PUBLIC_*` and server `PULSE_*` vars — never MCP or LLM keys.

---

## Deploy the frontend on Vercel

1. Implement the Next.js app under `web/` as above.
2. Push the repo to GitHub (or connect the existing remote).
3. [vercel.com](https://vercel.com) → **Add New Project** → import the repo.
4. **Root Directory:** `web`.
5. Framework preset: **Next.js**. Build: `next build`. Output: default.
6. **Settings → Environment Variables** — add the `NEXT_PUBLIC_*` (and optional `PULSE_API_*`) values. Redeploy after changes.
7. Production URL: `https://<project>.vercel.app`.

CLI (from `web/` after `npm i -g vercel`):

```bash
npx vercel          # preview
npx vercel --prod   # production
```

### Local frontend

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`. Optionally open `stitch_groww_weekly_review_pulse/code.html` in a browser **side-by-side** to check chrome parity.

`NEXT_PUBLIC_*` in `.env.local` match Vercel. Do not copy `MCP_API_KEY` into `.env.local` unless you are deliberately writing a server-only experiment.

---

## How the UI gets pulse data

The agent already writes:

| Artifact | Path | UI use |
|----------|------|--------|
| Pulse | `output/pulse.md` | Home article (3 themes / 3 quotes / 3 actions) |
| Themes | `output/themes.json` | Themes + Evidence filters |
| Last run | `output/run.json` | Week meta, `top_3`, `validation_ok`, `doc_url`, `draft_id`, nested `gates` |
| Gates | `output/gates.json` | Gates screen |
| Delivery | `output/delivery.json` | Delivery cards (`draft_id`, `doc_url`, `sent_id`) |

Vercel has **no access** to that disk. Pick one feed:

| Option | How | When to use |
|--------|-----|-------------|
| **A. Pulse API** | Small FastAPI/Flask on Railway (or a Route Handler that `fetch`es it) returns the latest JSON | Best for a live dashboard |
| **B. Commit-free gist / blob** | Weekly job uploads `run.json` + `pulse.md` to a private store; Vercel fetches it | No extra Railway service |
| **C. Static snapshot** | Copy last artifacts into `web/public/pulse/` at build time, or commit a fixture | Demo / first Vercel ship; stale after Monday |

Option A sketch (Railway service, **not** the MCP container):

```text
GET  /health          → { ok, mcp: <railway /health> }
GET  /api/pulse       → PulsePayload (below)
POST /api/run         → 202 Accepted (enqueue weekly_job; do not block 60s+)
```

Protect `POST /api/run` with `PULSE_API_SECRET`. The Vercel BFF forwards the secret; the browser never sees `MCP_API_KEY`.

### `PulsePayload` (BFF response)

Shape the Route Handler around fields the Stitch screens already assume. Strip `recipient` and local disk paths before JSON leaves the server.

```ts
type PulsePayload = {
  week_key: string;            // "2026-W37"
  week_ending: string;         // "2026-09-08"
  title: string;
  review_count: number;
  word_count: number;
  word_limit: 250;
  validation_ok: boolean;
  insufficient_signal: boolean;
  window_widened: boolean;
  top_3: string[];             // theme ids
  pulse_markdown: string;      // from pulse.md
  themes: Array<{
    id: string;
    label: string;
    review_count: number;
    avg_rating: number;
    low_star_count: number;    // parse from theme.summary or compute in API
  }>;
  gates: { ok: boolean; gates: Record<string, { name: string; ok: boolean; detail: string }> };
  delivery: {
    doc_url: string | null;
    draft_id: string | null;   // truncate in the UI
    sent_id: null;             // assignment default
    delivery_skipped: boolean;
  };
  mcp: { ok: boolean; label: "mcp-server-1 · Railway" };
};
```

---

## CORS and auth

- Railway `/health` is public — the Vercel client may call it directly.
- Railway `/mcp` must **not** be called from the browser. No CORS opening for `/mcp`.
- If you add a Pulse API, allow only the Vercel origin:

  `https://<project>.vercel.app` and `http://localhost:3000`.

- Stitch access gate: shared password (httpOnly cookie) or Clerk. **No “Sign in with Google”** on this surface — Docs and Gmail stay on MCP. The assignment Doc is already in Drive; the site can stay behind a simple gate.

---

## Timeouts (do not ignore)

| Surface | Typical limit | Fits |
|---------|---------------|------|
| Vercel Hobby function | ~10s | Health + “get last pulse” |
| Vercel Pro function | up to ~60s–300s | Still **not** a full Play fetch + 1314-review graph |
| Railway MCP | Long-lived HTTP | Docs append + Gmail draft |
| Windows Task Scheduler / cron | Minutes | `weekly_job --once` |

Monday 08:00 IST schedule stays on the **runner** ([`Docs/scheduler.md`](Docs/scheduler.md)), not on a Vercel cron that executes the graph.

Vercel Cron can **poke** `POST /api/run` on a Pulse API if you later host the worker on Railway. It must not `import` this repo’s graph inside `app/api`.

---

## Health checks

```bash
# MCP (no API key)
curl https://mcp-server-1-production.up.railway.app/health

# From this repo
python -m src.agent.run_delivery --health
```

After the Next app exists:

```bash
curl https://<project>.vercel.app/api/health
curl https://<project>.vercel.app/api/pulse
```

Expect MCP `ok` and the sidebar / header status chip green before a stakeholder demo.

---

## Deploy checklist

### Railway MCP (already done)

- [x] `https://mcp-server-1-production.up.railway.app/health` returns ok
- [x] `MCP_API_KEY` set on Railway and in the **Python** `.env`
- [x] `PULSE_DOC_ID` + `PULSE_DRAFT_RECIPIENT` on the runner
- [x] Agent uses `MCP_TRANSPORT=http` (not `inprocess`) for live Doc/Gmail

### Stitch → Next.js (when `web/` exists)

- [ ] Next app in `web/`; Vercel Root Directory = `web`
- [ ] Tokens and chrome match `stitch_groww_weekly_review_pulse/DESIGN.md` (side-by-side with `code.html`)
- [ ] Routes: `/` `/themes` `/evidence` `/actions` `/delivery` `/gates` `/history` (+ `/login` if gated)
- [ ] Tailwind is a real dependency (no `cdn.tailwindcss.com`)
- [ ] Inter via `next/font`; no reviewer avatars or invented quotes
- [ ] `NEXT_PUBLIC_PULSE_DOC_URL` and `NEXT_PUBLIC_MCP_HEALTH_URL` set
- [ ] No `MCP_API_KEY` / LLM keys in Vercel **or** `NEXT_PUBLIC_*`
- [ ] Production preview loads pulse (or Stitch empty state) + Doc link
- [ ] `/health` chip matches Railway
- [ ] Gmail is draft-only; no Send button
- [ ] Weekly job still runs on the scheduler / Pulse API worker, not in a Vercel function

### Secrets hygiene

- [ ] `.env` and `web/.env.local` gitignored
- [ ] Rotate `MCP_API_KEY` if it was ever committed or pasted into a client bundle

---

## Failure handling

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Vercel UI “MCP down” | Railway sleep / 502 | Check `/health`; retry. Agent already keeps local `output/pulse.md` |
| Doc link 404 | Wrong `PULSE_DOC_ID` | Copy id from `docs.google.com/document/d/<id>/edit` |
| “Run” button 504 | Graph ran on Vercel | Move job to Railway worker / local `--once` |
| Gmail draft missing | Runner MCP error | See `output/delivery.json`; retry Gmail-only per mcp-runbook |
| Key leaked in page source | Used `NEXT_PUBLIC_MCP_API_KEY` | Remove var, rotate Railway key, redeploy |
| UI looks like a generic SaaS purple dashboard | Tokens ignored | Re-apply `DESIGN.md` Groww mint / obsidian sidebar |
| Production is a single static HTML page | Deployed the Stitch folder | Point Vercel at `web/` (Next.js), not `stitch_groww_weekly_review_pulse/` |

---

## Out of scope for Vercel

- Replacing Railway MCP
- Calling Google Docs / Gmail REST from Next.js
- Hosting `data/raw/` Play dumps on Vercel
- Auto-sending email from the frontend (`gmail_send_email` stays opt-in on the Python job)
- Deploying `stitch_groww_weekly_review_pulse/` as the production origin
- Consumer Groww trading / MF / IPO screens, App Store ingest, or a review-scraper console

---

## Related docs

| Doc | Topic |
|-----|--------|
| [`stitch_groww_weekly_review_pulse/DESIGN.md`](stitch_groww_weekly_review_pulse/DESIGN.md) | Tokens, chrome, components |
| [`stitch_groww_weekly_review_pulse/code.html`](stitch_groww_weekly_review_pulse/code.html) | Visual reference (History + shared nav) |
| [`Docs/stitch-prompt.md`](Docs/stitch-prompt.md) | Stitch prompts, 9-screen IA, handoff |
| [`Docs/mcp-runbook.md`](Docs/mcp-runbook.md) | Railway MCP auth, tools, smoke tests |
| [`Docs/scheduler.md`](Docs/scheduler.md) | Monday 08:00 IST weekly job |
| [`Docs/demo.md`](Docs/demo.md) | Stakeholder walkthrough |
| [`.env.example`](.env.example) | Python runner variables |
