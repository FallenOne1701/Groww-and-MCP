# Problem Statement: Groww Weekly Review Pulse

## Product Context

**Platform:** [Groww](https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN) (Groww Stocks, Mutual Fund, IPO — Apps on Google Play)

**App ID:** `com.nextbillion.groww`

**Play Store URL:** https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN

---

## Goal

Turn raw **Google Play Store** feedback into a **weekly pulse** the team can scan in minutes:

- What users care about
- What they actually said
- What to do next

Reviews are already public. The job is to **aggregate**, **theme**, **summarize**, and **deliver** that insight through familiar surfaces:

| Surface | Purpose |
|---------|---------|
| **Google Docs** | Written weekly pulse document |
| **Gmail** | Draft email you can send yourself |

Credentials and REST wiring are **not** handled manually — integrations go through MCP.

---

## End-to-End Flow (“Done” Looks Like)

1. **Pull** recent **Google Play Store** reviews for Groww (within the constraints below). App Store reviews are **out of scope**.
2. **Cluster** them into a small set of themes and distill a one-page weekly note.
3. **Publish** that note where stakeholders can read it (**Google Docs**).
4. **Create** a draft email to yourself (or an alias) that contains or links to that pulse (**Gmail**).

---

## Deliverables

### Weekly one-page pulse must include

1. **Top themes** — what people are talking about most
2. **Real user quotes** — verbatim snippets from reviews; no invented wording
3. **Three action ideas** — concrete next steps grounded in the themes

### Final step

Send yourself a **draft email** containing this weekly note (or a clear pointer to it).

---

## Who This Helps

| Audience | Why |
|----------|-----|
| **Product / Growth** | Prioritize fixes and improvements from real signals |
| **Support** | Align messaging with what users are actually saying |
| **Leadership** | One-page health check without drowning in raw reviews |

---

## What You Must Build

### 1. Review import

- Import **Play Store** reviews only (Groww: `com.nextbillion.groww`) from roughly the **last 8–12 weeks**
- Fields such as: rating, title, text, date (whatever the export provides)
- **Do not** ingest Apple App Store reviews

### 2. Theme clustering

- Group reviews into **at most 5 themes**
- Example theme areas (pick what fits Groww): onboarding, KYC, payments, statements, withdrawals

### 3. Weekly one-page note

Generate a note with:

| Element | Requirement |
|---------|-------------|
| Top themes | **Top 3** (subset of your ≤5 themes) |
| User quotes | **3** verbatim quotes |
| Action ideas | **3** concrete next steps |

### 4. Email draft

Draft an email with the note to yourself or an alias.

---

## Integrations: Google Docs & Gmail via MCP

Use **MCP (Model Context Protocol)** servers for Google Docs and Gmail — for example:

- Creating or updating the pulse document
- Creating the draft message

Do **not** integrate Google APIs directly as the primary path (no bespoke OAuth client + REST client code).

MCP servers expose tools your agent or app can call. Lean on that pattern so Docs and Gmail stay consistent with course tooling and avoid duplicating auth and HTTP plumbing.

> **Requirement:** MCP-first — choose MCP servers or connectors the environment provides for Docs and Gmail; do not call Google APIs manually as the main integration approach.

---

## Key Constraints

| Constraint | Rule |
|------------|------|
| **Reviews** | Use **public Play Store review exports only** — no App Store data; no scraping behind store logins or ToS-violating automation |
| **Themes** | Maximum **5** themes for clustering; the written pulse highlights the **top 3** |
| **Length** | Keep the note scannable and **≤250 words** where applicable |
| **Privacy** | Do **not** include PII — no usernames, emails, device IDs, or other identifiable reviewer data in any artifact (quotes should be anonymous / stripped as needed) |

---

## Success Criteria Checklist

- [x] Play Store reviews imported for the last 8–12 weeks (public exports only; no App Store)
- [x] Reviews clustered into ≤5 themes
- [x] One-page weekly pulse (≤250 words) with top 3 themes, 3 quotes, 3 action ideas
- [x] Pulse published to Google Docs via MCP
- [x] Draft email created in Gmail via MCP (self / alias)
- [x] No PII in any artifact
- [x] No invented quotes; all quotes verbatim from reviews
