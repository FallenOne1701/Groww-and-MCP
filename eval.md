# Evaluation Plan: Groww Weekly Review Pulse

Eval framework aligned to `implementation-plan.md` (Phases 0–5) and the problem-statement success criteria.

**What “good” means:** A scannable weekly pulse from **Play Store** reviews only — ≤5 themes clustered, top **3** themes / **3** verbatim quotes / **3** grounded actions, **≤250 words**, **no PII** — published to **Google Docs** and a **Gmail draft** via **MCP**.

---

## 1. Eval Principles

| Principle | Practice |
|-----------|----------|
| **Gate before quality** | Structural/compliance checks must pass before human or LLM-as-judge scoring |
| **No publish on fail** | Failed gates → do not call Docs/Gmail MCP |
| **Separate automatic vs human** | Automate counts, verbatim, PII, window; humans judge theme relevance and action usefulness |
| **Phase-scoped** | Each phase has its own acceptance eval; E2E eval only after Phase 4 |
| **Fixtures + live** | Run fixture suites every commit-worthy change; run live Play export before demo |

---

## 2. Metric Catalog

### 2.1 Compliance metrics (must-pass / binary)

| ID | Metric | Pass condition | Phase |
|----|--------|----------------|-------|
| C1 | Source scope | All cleaned reviews `source == "play"`; no App Store | 1+ |
| C2 | Date window | All dates within configured 8–12 weeks of run date | 1+ |
| C3 | Schema | Every review matches `Review` required fields | 1 |
| C4 | PII-free cleaned | No username/email/phone/device-id fields retained | 1 |
| C5 | Theme cap | `len(themes) <= 5` | 2+ |
| C6 | Pulse structure | Exactly 3 themes, 3 quotes, 3 actions in pulse | 2+ |
| C7 | Word limit | `word_count(pulse) <= 250` | 2+ |
| C8 | Verbatim quotes | Each quote is substring (or allowed truncated prefix) of some review `text` | 2+ |
| C9 | Quote anonymity | No usernames/emails in quote lines | 2+ |
| C10 | PII-free pulse | Regex/heuristic scan clean on `pulse.md` | 2+ |
| C11 | Docs delivery | Doc exists via Docs MCP (`doc_id` / URL recorded) | 3–4 |
| C12 | Gmail draft | Draft exists via Gmail MCP (`draft_id`; not required to be sent) | 3–4 |
| C13 | MCP-first | No primary-path custom Google OAuth/REST client | 3–4 |
| C14 | Gate-before-publish | Invalid pulse never published in E2E run | 4–5 |

**Pass rule:** All applicable C* metrics = pass for that phase’s exit criteria.

### 2.2 Quality metrics (scored)

Use after compliance passes. Score **1–5** unless noted.

| ID | Metric | What to score | Target (v1) |
|----|--------|---------------|-------------|
| Q1 | Theme relevance | Themes reflect real volume/issues in the batch | Avg ≥ 3.5 |
| Q2 | Theme distinctness | Top 3 are not near-duplicates | Avg ≥ 3.5 |
| Q3 | Quote representativeness | Quotes illustrate the stated themes | Avg ≥ 3.5 |
| Q4 | Action concreteness | Actions are specific, product/support-ready | Avg ≥ 3.5 |
| Q5 | Action–theme grounding | Each action maps to an observed theme | 100% mapped (binary+) |
| Q6 | Scannability | Leadership can grasp pulse in &lt;2 minutes | Avg ≥ 4.0 |
| Q7 | Faithfulness | No invented user claims beyond reviews | Zero critical invents |

**Aggregate quality score (optional):**

```text
Quality = mean(Q1, Q2, Q3, Q4, Q6)   # Q5/Q7 treated as hard gates if failed
```

v1 demo bar: **Compliance 100%** + **Quality ≥ 3.5**.

### 2.3 Operational metrics

| ID | Metric | How measured | Useful for |
|----|--------|--------------|------------|
| O1 | E2E success rate | Successful graph runs / attempts | Phase 4–5 |
| O2 | Time-to-pulse | Wall clock ingest→local pulse | Phase 2 |
| O3 | Time-to-deliver | Pulse→Doc+draft | Phase 3–4 |
| O4 | Retry count | LLM parse/MCP retries per run | Hardening |
| O5 | Window used | 8 vs 12 weeks chosen | Sparse-data behavior |

---

## 3. Phase-Gated Eval

### Phase 0 — Setup

| Eval | Method | Pass |
|------|--------|------|
| Install | `pip install -r requirements.txt` | Exit 0 |
| Layout | Paths exist per plan (`data/`, `src/agent/`, `prompts/`) | All present |
| Models | Import `Review`, `Theme`, `PulseDraft` | No import errors |

**Sign-off:** Phase 0 exit criteria from implementation plan.

---

### Phase 1 — Ingest & Scrub

**Automatic suite**

| Test | Assert |
|------|--------|
| Happy path | `reviews.json` non-empty; all `source=="play"` |
| Window | `min(date) >= run_date - 12 weeks` (or configured bound) |
| Drop empty | Reviews with empty text not present |
| PII fields | Forbidden keys absent (`userName`, `email`, …) |
| PII in text | Injected email/phone in fixture → redacted or review excluded from quote pool |
| App Store filter | Mixed fixture → zero non-play rows |
| Sparse widen | 8w-empty / 12w-partial fixture → log shows widen behavior |

**Report fields:** `n_raw`, `n_cleaned`, `date_min`, `date_max`, `rating_histogram`, `window_weeks`.

**Pass:** All Phase 1 exit criteria + C1–C4.

---

### Phase 2 — Analysis & Pulse

**Automatic (compliance)**

| Test | Assert |
|------|--------|
| Theme count | ≤5 in `themes.json` |
| Pulse counts | 3 / 3 / 3 |
| Word count | ≤250 |
| Verbatim | `quote in review.text` or truncated-prefix rule |
| Unique quotes | 3 distinct strings |
| PII scan | No email/phone patterns in pulse |
| Structure | Required headings present (Top Themes, What Users Said, Action Ideas) |

**Human / LLM-as-judge (quality)** — on ≥1 live batch + 1 golden fixture:

| Rubric item | 1 | 3 | 5 |
|-------------|---|---|---|
| Q1 Theme relevance | Off-topic / random | Mostly plausible | Clearly matches dominant issues |
| Q3 Quote fit | Quotes don’t match themes | Weak link | Clear illustration |
| Q4 Actions | Vague fluff | Somewhat useful | Concrete next steps |
| Q6 Scannability | Dense / confusing | OK | One-page clear |

**Pass:** C5–C10 + Quality mean ≥ 3.5 on scored run(s).

---

### Phase 3 — MCP Tools

| Eval | Method | Pass |
|------|--------|------|
| Docs smoke | Create/update from sample `pulse.md` via MCP tool | URL/id returned; content visible |
| Gmail smoke | Create **draft** to self/alias | `draft_id` returned; appears in Drafts |
| Failure path | Unauthenticated / mock fail | Local pulse retained; clear error; no fake success |
| Integration style | Code review | MCP wrappers only; no bespoke Google API primary path |

**Pass:** C11–C13 for smoke run.

---

### Phase 4 — E2E Graph

| Eval | Method | Pass |
|------|--------|------|
| Single command | CLI/graph one run | Completes with artifacts |
| Validate-before-publish | Force invalid pulse (e.g. 4 quotes) | Docs/Gmail **not** called |
| Partial failure | Mock Gmail fail after Doc OK | Doc URL kept; Gmail retry path works |
| Idempotent naming | Two runs same week key | Doc strategy consistent (update or versioned) |
| DoD checklist | Manual + logs | All five Definition of Done items |

**Pass:** C1–C14 on a live Play export run; O1 documented.

---

### Phase 5 — Gates, Edge Cases, Demo

| Eval | Method | Pass |
|------|--------|------|
| Gate script | Automated C* on last run artifacts | All green |
| Fixture matrix | Key fixtures from `edge-case.md` §10 | Expected Blocker/Degrade behavior |
| Demo pack | pulse.md + Doc link + draft proof | Stakeholder walkthrough &lt;2 min comprehension (Q6) |
| Master checklist | Problem-statement items | All checked |

---

## 4. Automatic Gate Spec (Phase 5 deliverable)

Implement as `src/eval/gates.py` or a graph `validate` node. Pseudocode contract:

```text
gates(reviews, themes, pulse, meta) -> { pass: bool, failures: [GateFailure] }

GateFailure { id: "C8", message: "quote[2] not found in any review text" }
```

| Gate ID | Implementation hint |
|---------|---------------------|
| C2 | Compare ISO dates to `run_date - timedelta(weeks=window)` |
| C5 | `len(themes) <= 5` |
| C6 | Parse pulse sections / structured `PulseDraft` |
| C7 | `len(body.split()) <= 250` |
| C8 | `any(q in r.text or r.text.startswith(q.rstrip("…")) for r in reviews)` (define truncation rule precisely in code) |
| C10 | Regex for email, phone; optional blocklist |

**Publish rule:** `if not gates.pass: skip MCP tools`.

---

## 5. Eval Datasets

| Dataset | Purpose | When |
|---------|---------|------|
| `fixtures/golden_clean.json` | Happy-path regression | Every Phase 2+ change |
| `fixtures/with_pii.json` | Scrub + pulse PII gates | Phase 1–2, 5 |
| `fixtures/sparse_8w.json` | Window widen / low signal | Phase 1, 5 |
| `fixtures/mixed_play_appstore.json` | Play-only filter | Phase 1, 5 |
| `fixtures/spam_heavy.json` | Theme quality / quote pool | Phase 2 quality |
| `fixtures/long_reviews.json` | Quote truncation | Phase 2, 5 |
| **Live** Groww Play export (8–12w) | Demo + Q* scoring | Phase 2, 4, 5 |

Do not commit secrets; large raw exports stay gitignored.

---

## 6. Human Eval Protocol

**When:** At least once before demo (Phase 5); optionally after major prompt changes (Phase 2).

**Raters:** Ideally 1 product/support-minded reader (can be self + peer).

**Procedure:**

1. Confirm automatic gates C1–C10 pass  
2. Blind to pipeline internals; read only `pulse.md` (+ optional theme counts)  
3. Score Q1–Q4, Q6 on 1–5 sheet  
4. Flag any invented claim (Q7) as critical fail  
5. Record scores in `output/eval_YYYY-Www.json` or a short table in notes  

**Sheet template:**

```text
Run id / week: __
Compliance: PASS / FAIL
Q1 Theme relevance: _/5
Q2 Theme distinctness: _/5
Q3 Quote representativeness: _/5
Q4 Action concreteness: _/5
Q5 All actions grounded? Y/N
Q6 Scannability: _/5
Q7 Invented claims? Y/N (N required)
Notes: __
```

---

## 7. LLM-as-Judge (Optional)

Use only **after** verbatim/PII/structure gates pass. Judge prompt must receive:

- Pulse text  
- Top theme labels + counts (not full raw dump)  
- Instruction: score Q1–Q4, Q6; list any suspected non-verbatim or invented content  

**Do not** let the judge override C8 (verbatim); code remains source of truth for quotes.

---

## 8. Acceptance Scorecard (Demo Ready)

| Area | Requirement | Status |
|------|-------------|--------|
| Data | Play-only, 8–12 weeks, scrubbed | ☐ |
| Themes | ≤5 clustered; top 3 in note | ☐ |
| Quotes | 3 verbatim, anonymous | ☐ |
| Actions | 3 concrete, theme-grounded | ☐ |
| Length | ≤250 words | ☐ |
| Privacy | No PII in artifacts | ☐ |
| Docs | Published via Docs MCP | ☐ |
| Gmail | Draft via Gmail MCP | ☐ |
| Quality | Mean Q ≥ 3.5; Q7 clean | ☐ |
| E2E | One-command run documented | ☐ |

**Demo-ready** = all rows checked.

---

## 9. Mapping to Implementation-Plan Master Checklist

| Master checklist item | Eval IDs |
|-----------------------|----------|
| Play Store import 8–12 weeks | C1, C2, Phase 1 suite |
| ≤5 themes | C5 |
| Pulse: top 3 / 3 quotes / 3 actions / ≤250w | C6, C7, Q* |
| Docs via MCP | C11 |
| Gmail draft via MCP | C12 |
| No PII | C4, C9, C10 |
| Verbatim quotes | C8, Q7 |

---

## 10. Regression Cadence

| Trigger | What to run |
|---------|-------------|
| Change to `ingest` / `scrub` | Phase 1 automatic suite |
| Change to prompts / chains | Phase 2 compliance + 1 human or judge pass on golden |
| Change to MCP tools | Phase 3 smoke |
| Change to graph | Phase 4 E2E on golden (+ live before demo) |
| Pre-demo | Full scorecard §8 + edge fixtures |

---

## 11. Failure Taxonomy (for eval logs)

| Code | Meaning | Typical action |
|------|---------|----------------|
| `COMPLIANCE` | C* failed | Fix data/prompt/validator; no publish |
| `QUALITY_LOW` | Q* below target | Prompt iterate; still may demo if compliance holds and time-boxed |
| `DELIVERY` | MCP failed | Keep local pulse; fix auth/retry |
| `OPS` | Timeout/rate limit | Retry/backoff; record O4 |

---

## 12. Definition of Eval-Done

Evaluation for this project is complete when:

1. Automatic gates (C1–C14 as applicable) are implemented and green on a live run  
2. At least one human quality pass meets targets  
3. Demo scorecard §8 is fully checked  
4. Known limitations documented (App Store out of scope, draft-not-send, etc.)

This closes Phase 5 exit criteria from `implementation-plan.md`.
