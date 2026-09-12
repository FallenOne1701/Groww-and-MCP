# Google Stitch prompt — Groww Weekly Review Pulse (frontend)

Use this at [stitch.withgoogle.com](https://stitch.withgoogle.com) to design the stakeholder web UI. The backend already exists (LangGraph + MCP → Google Docs + Gmail). Stitch is only for **screens, layout, and visual system**. We will implement later as **Next.js on Vercel** (`web/`).

---

## How to use Stitch

1. Create a new project. Set **medium = Web** (desktop dashboard, not a mobile app).
2. Target canvas: **1440 × 1024** desktop, then generate a **390 × 844** mobile set from the same system.
3. Paste **Prompt A** first. Generate the full screen set.
4. After the first good screen, open **Edit Theme**, lock colors / fonts / radius from the token table below. That writes a `DESIGN.md` Stitch will reuse.
5. Paste **Prompts B–H** one at a time (one or two changes per message). Always say: *copy the exact sidebar, header, and status chips from the Pulse Home screen*.
6. Export HTML/CSS or screenshots when the set looks right. Do **not** ask Stitch to invent Google OAuth, MCP keys, or a review-scraper UI.

---

## Design tokens (lock these in Theme / DESIGN.md)

Inspired by Groww’s public product language — clean Indian fintech, not a generic SaaS purple dashboard.

| Token | Value | Use |
|-------|--------|-----|
| Background | `#FFFFFF` | Page canvas |
| Page wash | `#F6F7F9` | Main content well behind cards |
| Surface / card | `#FFFFFF` | Cards, drawers |
| Text primary | `#44475B` | Headings, body |
| Text muted | `#7C7E8C` | Meta, timestamps, helper copy |
| Accent / Groww green | `#00B386` | Primary CTA, positive chips, links, selected nav |
| Accent soft | `#E5F8F2` | Green pill backgrounds, selected row |
| Border | `#F0F0F2` | Hairline dividers, card stroke |
| Warning | `#F5A524` | Sparse week / widened window |
| Danger | `#E11D48` | Failed gates, MCP down |
| Success | `#00B386` | Gates pass, draft created, MCP healthy |
| Info | `#3B82F6` | Doc / Gmail delivery chips |
| Rating 1–2 | `#E11D48` | Severity bars |
| Rating 3 | `#F5A524` | Neutral |
| Rating 4–5 | `#00B386` | Positive |
| Sidebar | `#0B0D12` | Dark left rail (high contrast, like Groww dark surfaces) |
| Sidebar text | `#E8EAED` | Nav labels |
| Sidebar muted | `#8B8F9A` | Section labels |
| Radius | `12px` cards, `8px` buttons, `999px` chips | Soft, not bubbly |
| Shadow | `0 1px 2px rgba(68,71,91,0.06)` | Almost flat |
| Type | **Inter** (or Plus Jakarta Sans if Inter unavailable). Headings 600, body 400. No serif, no display script. |
| Spacing | 8px grid. Page padding 32px. Card padding 20–24px. Gap 16px. |

**Vibe adjectives:** calm, scannable, trustworthy, dense-but-airy, India-fintech, leadership-ready. Think Groww web + an internal ops console. Not neon, not glassmorphism, not illustration-heavy, not “AI chatbot” purple.

**Do not use:** stock crypto candlestick heroes, random avatars, usernames, emails, phone numbers, device IDs, or invented user quotes.

---

## Prompt A — paste this first (full product + screen set)

```
Design a desktop web application (1440px wide) called “Groww Weekly Review Pulse”.

PRODUCT
This is an internal stakeholder dashboard for Groww (India’s investing app — stocks, mutual funds, IPO). It is NOT the consumer Groww app and NOT a trading terminal. It turns public Google Play Store reviews for package com.nextbillion.groww into a one-page weekly pulse that Product, Support, and Leadership can scan in minutes.

The backend already exists. This UI only READS the latest pulse and shows delivery status. Do not design login-to-Play-Store, scraping consoles, API-key forms, or Google OAuth screens.

What the product does each week:
1. Import last 8–12 weeks of public Play Store reviews (English, PII-scrubbed).
2. Cluster into at most 5 fixed themes.
3. Rank a top 3 by severity (low-star volume first, not 5-star praise).
4. Write a ≤250 word pulse: top 3 themes, 3 verbatim quotes, 3 action ideas.
5. Append that pulse to a living Google Doc via MCP.
6. Create a Gmail DRAFT (never auto-send) to a configured alias.

FIXED THEME VOCABULARY (exactly these five — never invent a sixth):
1. Trading & order execution
2. Charts & market / holdings data
3. Customer support
4. App reliability & updates
5. Fees, brokerage & funding

AUDIENCE
- Leadership: one-page health check, no raw review dump
- Product / Growth: prioritize fixes from real signals
- Support: align messaging with what users actually said

PLATFORM
Responsive web dashboard. Desktop-first with a persistent left sidebar. Also generate a compact mobile layout (stacked, bottom tabs) that keeps the same visual language.

INFORMATION ARCHITECTURE — generate ALL of these screens in one set:
1. Pulse Home (default)
2. Themes
3. Evidence (quotes + anonymous review snippets)
4. Actions
5. Delivery
6. Quality gates
7. History
8. Empty / insufficient-signal state (variant of Pulse Home)
9. Simple access gate (shared-password screen — no social login)

GLOBAL CHROME (identical on every authenticated screen)
Left sidebar (dark #0B0D12):
- Wordmark: lowercase “groww” in white + a small mint square mark, then a thin caption “Weekly Review Pulse”
- Nav items with simple line icons: Pulse, Themes, Evidence, Actions, Delivery, Gates, History
- Footer of sidebar: MCP status pill (green “MCP healthy” or red “MCP down”) and “Play Store only · no PII”
Top header (white, 64px, hairline bottom border #F0F0F2):
- Page title + one-line subtitle
- Week switcher chip: “2026-W37 · Week ending 8 Sep 2026”
- Right cluster: circular MCP health dot, “Gates PASS” green chip, primary button “Open Google Doc” (mint fill), secondary ghost button “View Gmail draft”
No user avatar photos. If you need an operator mark, use initials “DT” in a mint-outline circle.

VISUAL SYSTEM
Light, calm Indian-fintech. White canvas, cool gray wash #F6F7F9, Groww mint #00B386 for CTAs and success, slate text #44475B, muted #7C7E8C, hairline borders #F0F0F2. Cards 12px radius, almost flat. Inter / geometric sans. 8px spacing grid. No purple gradients, no 3D illustrations, no stock-photo people, no crypto charts as decoration.

REALISTIC SAMPLE DATA (use exactly — do not invent different quotes)

Header meta:
- Week 2026-W37 · ending 8 Sep 2026
- 1,226 English Play reviews · window 21 Jul 2026 → 8 Sep 2026
- Polarized ratings: 473 ones, 77 twos, 105 threes, 99 fours, 472 fives (~45% ≤2★)
- Pulse 204 words / 250 limit
- Gates: PASS
- Source: Google Play only · language en · PII scrubbed
- Living Doc appended · Gmail draft created (unsent)

KPI strip (4 compact cards):
1. Reviews in window — 1,226
2. Low-star share — 45% ≤2★
3. Pulse length — 204 / 250 words
4. Delivery — Doc appended · Draft ready

Top 3 theme cards (ranked by severity, not volume):
1. App reliability & updates — 588 reviews · avg 3.44 · 202 rated ≤2★ · rank #1
2. Trading & order execution — 361 reviews · avg 2.92 · 166 rated ≤2★ · rank #2
3. Customer support — 105 reviews · avg 1.63 · 88 rated ≤2★ · rank #3 (worst average — show a danger-tinted severity bar)

Also show the two non-top themes as quieter secondary chips (not the hero):
- Fees, brokerage & funding — 138 · avg 2.65
- Charts & market / holdings data — 34 · avg 2.47

Verbatim quotes (exactly 3, anonymous, quotation marks, no usernames):
1. Theme: App reliability — “The app is super buggy at times, with painstakingly slow loading times for the market data, and this sometimes happen during the peak trading hours. When you reach out to support they keep saying same thing…”
2. Theme: Trading & orders — “ale fraud h ye. I placed order of buy however they sell my all quantity without placing any sell order. very serious and fraud activity done by groww.”
3. Theme: Customer support — “please don't download this app , because they have worst support system. my experience: I called their support team for email changing problem due to its locked for some reason,they told it's may take 2/3 working…”

Each quote card: left mint quote mark, theme pill, star hint (1–2★), tiny “verbatim · anonymous” caption. Never paraphrase.

Action ideas (exactly 3, numbered, each mapped to one top theme):
1. Reliability — Prioritize crash / freeze / post-update regressions from ≤2★ reviews and add release smoke checks for core screens.
2. Trading — Trace sell / stop-loss / square-off failures end-to-end and ship regression tests for the top order-lifecycle breakages.
3. Support — Reduce support dead-ends: publish ticket SLAs and route funding / trading escalations to a faster path.

SCREEN 1 — PULSE HOME
Goal: Leadership can understand the week in 20 seconds without scrolling past the fold on 1440px.

Layout:
- Sidebar + header as specified
- KPI strip of 4 cards
- Primary column (≈8/12): the one-page pulse article styled like a printed brief
  Title: “Groww Weekly Review Pulse — Week Ending 2026-09-08”
  Three sections with clear H2s: Top Themes · What Users Said · Action Ideas
  The pulse body must look ≤250 words, tight typesetting, generous line-height 1.5
- Secondary column (≈4/12):
  - “This week at a glance” rating distribution bar (1★ through 5★) using the counts above
  - Gate checklist mini-list (all green): Window, ≤5 themes, 3 quotes verbatim, 3 actions, ≤250 words, Privacy, Play-only
  - Delivery card: Google Doc link row + Gmail draft id row (`draft_…` truncated) + “Not sent” amber pill
  - Next run: “Monday 08:00 IST · weekly scheduler”

Primary CTA in the pulse article footer: “Open living Google Doc”. Secondary: “Copy pulse”. No “Send email” button on this screen.

SCREEN 2 — THEMES
Goal: Product sees all ≤5 themes, volume vs severity.

- Table or card grid of all 5 themes
- Columns: Theme, Reviews, Avg rating, ≤2★ count, Share of corpus, Rank
- Horizontal stacked bar per theme: low-star (rose) vs rest (mint/slate)
- Callout: “Top 3 are severity-ranked (≤2★ first), not by raw volume. App reliability is #1 because it has the most low-star reviews, even though its average is higher than Support.”
- Clicking a theme does not open a modal dump of PII — it filters Evidence.

SCREEN 3 — EVIDENCE
Goal: Support sees real wording. Privacy-first.

- Filter chips for the 5 themes + “Top 3 only”
- Exactly 3 featured pulse quotes in a highlighted row (the ones from Home)
- Below: 6–8 anonymous snippet cards from the corpus. Each card shows only: star rating, theme pill, date (e.g. 2 Sep 2026), and review text. IDs like `play-04eca2…` are OK. NEVER show reviewer name, email, photo, or device.
- Banner: “Quotes are verbatim Play Store text. Ellipsis means a truncated prefix, never a paraphrase.”

SCREEN 4 — ACTIONS
Goal: Product leaves with three concrete next steps.

- Three large numbered action cards, each tagged with its theme
- Owner suggestion chips (Product / Engineering / Support) — visual only, not a real assignment system
- Small “grounded in” line pointing back to the matching quote
- No Kanban, no Jira clone, no sprint board. This is a brief, not a PM tool.

SCREEN 5 — DELIVERY
Goal: Prove MCP-first shipping without exposing secrets.

Three status cards:
1. Google Docs — “Appended section 2026-W37 to living pulse doc” · button “Open Doc” · note “MCP tool: google_docs_append_content (append only, no new-doc create)”
2. Gmail — “Draft created · not sent” · subject “Groww Weekly Review Pulse — 2026-W37” · recipient shown as “self / alias” (mask the actual address) · note “MCP tool: gmail_create_draft · agent never calls gmail_send_email”
3. MCP health — green “Railway MCP healthy” · endpoint shown as a friendly label “mcp-server-1 · Railway” — do NOT render API keys or Bearer tokens

Timeline (vertical): Fetch reviews → Classify ≤5 themes → Compose pulse → Validate gates → Append Doc → Create Gmail draft.

Empty secret state: if something failed, show “Local pulse.md kept · delivery skipped” with a rose banner. No retry-key form.

SCREEN 6 — QUALITY GATES
Goal: Demo screen — all architecture §9 gates green.

A vertical checklist, each row: icon, gate name, one-line detail.
- Window — 2026-07-21 → 2026-09-08 (1,226 reviews)
- Theme count — 5 clustered; pulse shows top 3
- Quotes — 3; verbatim checked against corpus
- Actions — 3; each tied to a top theme
- Length — 204 words (limit 250)
- Privacy — no usernames / emails / phones / device IDs
- Source — Play Store only; language = en

Big PASS stamp / banner at top. If designing the fail variant, use a single failed row in rose and hide Doc/Gmail CTAs with helper text “Failed gates do not publish.”

SCREEN 7 — HISTORY
Goal: Archive of weekly pulses. Append-only living doc metaphor.

- List of week rows: 2026-W37 (current), then 2 placeholder earlier weeks (W36, W35) marked “sample / not loaded”
- Each row: week key, ending date, top theme name, word count, gates chip, Doc section link
- Selecting a week updates the header chip. Do not invent full fake pulses for older weeks — use “No snapshot in this demo” empty illustration (simple mint document icon, no photos).

SCREEN 8 — INSUFFICIENT SIGNAL (empty variant)
Same chrome. Replace the pulse article with a structured empty state:
- Title “Insufficient signal — week 2026-Wxx”
- Body: not enough English Play reviews in the 8-week window; pipeline widened toward 12 weeks and still below threshold.
- Still show the 3-section skeleton (Themes / Quotes / Actions) as disabled placeholders.
- Banner: “Gates did not pass · Google Doc and Gmail were not updated.”
- Secondary CTA: “Read last good pulse (2026-W37)”

SCREEN 9 — ACCESS GATE
Simple, calm splash. Centered card on #F6F7F9.
- groww wordmark + “Weekly Review Pulse”
- One sentence: “Internal briefing for Product, Support, and Leadership. Not the consumer Groww app.”
- Single password field + “Continue” mint button
- Footer: “No Google login on this surface. Docs and Gmail stay on MCP.”
No Sign in with Google. No Register. No marketing hero image.

INTERACTION NOTES (for the design, not a prototype backend)
- “Open Google Doc” is an external-link button
- “View Gmail draft” is a status surface, not an inbox
- Do not include a “Run weekly job” primary button on Home (that job is too long for a web request). If you add it, put it only on Delivery as a disabled / secondary control labeled “Run is handled by Monday 08:00 IST scheduler”
- Mobile: collapse sidebar into a bottom tab bar with Pulse / Themes / Evidence / Delivery; move Gates + History into an overflow “More” sheet

ACCESSIBILITY
WCAG AA contrast on mint-on-white and white-on-dark sidebar. Focus rings in mint. Do not rely on color alone for PASS/FAIL — include text labels.

OUTPUT
High-fidelity, production-looking UI. Desktop screens first, then matching mobile. Use the real sample copy above. No lorem ipsum. No invented user names. No extra features (chat bot, notifications center, billing, settings dump, dark-mode toggle unless it is a small header icon that does not change the default light theme).
```

---

## Follow-up prompts (paste after Prompt A, one at a time)

### Prompt B — tighten Pulse Home

```
Refine only the Pulse Home desktop screen. Keep the same sidebar, header, and tokens.

Make the pulse article feel like a one-page executive brief: max width ~680px, title 28–32px slate, section headings 13px uppercase tracking-wide muted, body 15px. Quotes should be indented cards with a 3px mint left border. Number the three actions as 01 / 02 / 03 in mint.

KPI cards: smaller, single-value, no decorative icons bigger than 16px. Rating distribution should be one horizontal stacked bar (1★ rose → 5★ mint) with counts under each segment: 473 / 77 / 105 / 99 / 472.

Remove any chat widgets, floating AI assistants, or extra charts that are not the rating bar.
```

### Prompt C — Themes screen

```
Create the Themes screen using the exact header, sidebar, and visual language from Pulse Home.

Show all 5 themes. Sort visually so the top 3 are full-width ranked cards and the remaining 2 sit in a quieter “Also clustered (not in pulse)” row.

Add a tiny legend: rose = ≤2★ severity, slate = other ratings. Include the callout about severity-aware ranking. No pie charts. No user photos.
```

### Prompt D — Evidence screen (privacy)

```
Create the Evidence screen, copying chrome from Pulse Home.

Privacy is the point: every card is anonymous. Show the three pulse quotes first as featured. Then a short list of unlabeled snippets with stars + theme + date only.

Add a persistent privacy bar: “No usernames, emails, or device IDs. Public Play Store text only.”

Do not add a search-by-reviewer field. Do not add export-all-reviews.
```

### Prompt E — Delivery + Gates

```
Create two screens that share Pulse Home chrome: Delivery and Quality Gates.

Delivery: three status cards (Docs, Gmail draft, MCP health) plus a 6-step vertical timeline. Gmail must say DRAFT / NOT SENT. Never show an API key.

Gates: seven rows all PASS with the exact details from the brief (204 words, 1,226 reviews, Play-only, privacy). Large PASS banner. Secondary “fail” annotation in a footnote only — do not switch the whole screen to fail unless I ask.
```

### Prompt F — History + empty state + access

```
Add three screens, same design system as Pulse Home:

1) History — week list, current W37 selected, W36/W35 as “snapshot not loaded”.
2) Insufficient signal — structured empty pulse, no Doc/Gmail CTAs, pointer back to last good week.
3) Access gate — centered password card, no Google SSO, groww wordmark, mint Continue.

Keep navigation, colors, and type identical.
```

### Prompt G — mobile

```
Generate mobile (390px) versions of Pulse Home, Evidence, Delivery, and Access Gate only.

Replace the left sidebar with a bottom tab bar: Pulse, Themes, Evidence, More. Header becomes: groww mark + week chip + hamburger-less overflow.

Stack KPI cards 2×2. Pulse article full width. Quotes remain verbatim. Do not hide the privacy caption. Mint CTA becomes a sticky bottom-adjacent button “Open Doc” above the tab bar (not overlapping it).
```

### Prompt H — global consistency pass

```
Select all screens. Make the top header, sidebar/nav, week chip, MCP pill, and page padding identical everywhere. Same 12px card radius, same #00B386 accent, same Inter typography scale. Remove any screen that drifted into a different color or a different nav pattern.
```

---

## What to tell Stitch *not* to design

These are explicit non-goals (assignment + deploy contract):

- Consumer Groww trading / MF / IPO screens
- Apple App Store review ingest
- Google account picker, OAuth consent, or Docs/Gmail REST settings
- MCP API key input, Bearer token fields, Railway env editors
- A button that **sends** email (`gmail_send_email` is opt-in on the Python job only)
- Full raw review dump or CSV uploader as a primary surface
- User profiles, avatars, reviewer identities
- A Vercel-hosted “Run full weekly job” spinner that pretends the graph runs in the browser

---

## After Stitch — handoff notes for Next.js

Map screens to the planned `web/` app (`Deployment.md`):

| Stitch screen | Likely route |
|---------------|----------------|
| Access gate | `/login` or middleware gate |
| Pulse Home | `/` (`app/page.tsx`) |
| Themes | `/themes` |
| Evidence | `/evidence` |
| Actions | `/actions` |
| Delivery | `/delivery` |
| Quality gates | `/gates` |
| History | `/history` |
| Insufficient signal | empty state on `/` when `insufficient_signal: true` |

Data the UI actually needs (from Pulse API / `run.json` + `themes.json` + `delivery.json`):

- `week_key`, `week_ending`, `review_count`, `word_count`, `validation_ok`
- `top_3` + full theme stats (count, avg_rating, ≤2★)
- pulse body (3 themes / 3 quotes / 3 actions)
- `doc_url`, `draft_id` (never `MCP_API_KEY`)
- MCP `/health` for the green/red chip

Export Stitch HTML as visual reference, then rebuild in Next.js App Router. Do not ship Stitch’s placeholder JS as production.
