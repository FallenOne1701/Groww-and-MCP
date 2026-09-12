"""LangChain analysis layer: themes → quotes → actions → pulse (Phase 2)."""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.agent.loaders import load_reviews
from src.agent.llm import invoke_structured, llms_available
from src.agent.validators import (
    quote_is_verbatim,
    validate_all,
    word_count,
)
from src.agent.vocab import (
    DEFAULT_ACTIONS,
    THEME_IDS,
    THEME_VOCAB,
    confident_theme_id,
    heuristic_theme_id,
    keyword_hint,
)
from src.models import PulseDraft, Review, Theme

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = ROOT / "prompts"
OUTPUT_DIR = ROOT / "output"

Mode = Literal["llm", "heuristic", "auto"]

# Groq free-tier: keep batches small under ~8K TPM
REVIEW_TEXT_CHARS = 350
# Cap reviews sent to Groq for theme labeling (hybrid: rest use keywords)
DEFAULT_MAX_LLM_LABEL = 40
DEFAULT_HEURISTIC_MIN_SCORE = 1


def _env_int(name: str, default: int, *, minimum: int = 0) -> int:
    from src.agent.llm import load_env

    load_env()
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(minimum, int(raw))
    except ValueError:
        return default


def _default_batch_size() -> int:
    return _env_int("GROQ_BATCH_SIZE", 8, minimum=1)


def _default_max_llm_label() -> int:
    """Max reviews labeled by Groq; 0 = heuristic-only themes (0 Groq calls)."""
    return _env_int("GROQ_MAX_LLM_LABEL", DEFAULT_MAX_LLM_LABEL, minimum=0)


def _default_heuristic_min_score() -> int:
    """Keyword hit threshold to skip Groq (1 = any unique keyword match)."""
    return _env_int("GROQ_HEURISTIC_MIN_SCORE", DEFAULT_HEURISTIC_MIN_SCORE, minimum=0)


# --- Structured LLM outputs -------------------------------------------------


class ThemeAssignment(BaseModel):
    review_id: str
    theme_id: str


class ThemeBatchResult(BaseModel):
    assignments: list[ThemeAssignment]


class QuotePick(BaseModel):
    review_id: str
    quote: str


class QuoteSelectResult(BaseModel):
    quotes: list[QuotePick] = Field(..., min_length=3, max_length=3)


class ActionItem(BaseModel):
    theme_id: str
    action: str


class ActionIdeateResult(BaseModel):
    actions: list[ActionItem] = Field(..., min_length=3, max_length=3)


class PulseComposeResult(BaseModel):
    themes: list[str] = Field(..., min_length=3, max_length=3)
    quotes: list[str] = Field(..., min_length=3, max_length=3)
    actions: list[str] = Field(..., min_length=3, max_length=3)
    body: str


# --- Prompt / LLM helpers ----------------------------------------------------


def _read_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    return path.read_text(encoding="utf-8").strip()


def resolve_mode(mode: Mode) -> Literal["llm", "heuristic"]:
    if mode == "auto":
        return "llm" if llms_available() else "heuristic"
    if mode == "llm" and not llms_available():
        raise RuntimeError(
            "LLM mode needs both GROQ_API_KEY (theme classification) and "
            "GOOGLE_API_KEY or GEMINI_API_KEY (pulse reporting). "
            "Set them in .env or run with --mode heuristic."
        )
    return mode


def _batched(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def sample_reviews(reviews: list[Review], limit: int) -> list[Review]:
    """Rating-stratified sample so a small run still covers 1★–5★ polarity."""
    if limit <= 0 or limit >= len(reviews):
        return reviews
    by_rating: dict[float | None, list[Review]] = defaultdict(list)
    for r in reviews:
        by_rating[r.rating].append(r)
    # Stable order within each bucket
    for bucket in by_rating.values():
        bucket.sort(key=lambda r: r.id)

    keys = sorted(by_rating.keys(), key=lambda k: (k is None, k if k is not None else 0.0))
    picked: list[Review] = []
    # Round-robin across rating strata
    idxs = {k: 0 for k in keys}
    while len(picked) < limit:
        progressed = False
        for k in keys:
            i = idxs[k]
            bucket = by_rating[k]
            if i < len(bucket):
                picked.append(bucket[i])
                idxs[k] = i + 1
                progressed = True
                if len(picked) >= limit:
                    break
        if not progressed:
            break
    return picked


def _truncate_quote(text: str, max_words: int = 36) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).rstrip(",.;:") + "…"


# --- Aggregate / rank --------------------------------------------------------


def aggregate_themes(
    reviews: list[Review],
    assignments: dict[str, str],
    *,
    sample_limit: int = 12,
) -> list[Theme]:
    """Build Theme[] for all ≤5 vocab themes that appear (plus empty zeros optional)."""
    by_theme: dict[str, list[Review]] = defaultdict(list)
    for review in reviews:
        tid = assignments.get(review.id)
        if tid not in THEME_IDS:
            tid = "app_reliability"
        by_theme[tid].append(review)

    themes: list[Theme] = []
    for tid, label in THEME_VOCAB.items():
        group = by_theme.get(tid, [])
        if not group:
            continue
        ratings = [r.rating for r in group if r.rating is not None]
        avg = sum(ratings) / len(ratings) if ratings else None
        # Prefer low-rated samples for evidence
        ordered = sorted(
            group,
            key=lambda r: (r.rating if r.rating is not None else 99.0, r.id),
        )
        sample_ids = [r.id for r in ordered[:sample_limit]]
        low = sum(1 for r in group if r.rating is not None and r.rating <= 2)
        themes.append(
            Theme(
                id=tid,
                label=label,
                review_count=len(group),
                avg_rating=round(avg, 3) if avg is not None else None,
                summary=f"{len(group)} reviews; {low} rated ≤2★",
                sample_ids=sample_ids,
            )
        )
    return themes


def rank_top_themes(themes: list[Theme], assignments: dict[str, str], reviews: list[Review], k: int = 3) -> list[Theme]:
    """Severity-aware ranking: ≤2★ count, then volume, then lower avg, then id."""
    by_id = {r.id: r for r in reviews}
    low_counts: dict[str, int] = defaultdict(int)
    for rid, tid in assignments.items():
        rev = by_id.get(rid)
        if rev and rev.rating is not None and rev.rating <= 2:
            low_counts[tid] += 1

    def sort_key(t: Theme) -> tuple:
        avg = t.avg_rating if t.avg_rating is not None else 5.0
        return (-low_counts[t.id], -t.review_count, avg, t.id)

    return sorted(themes, key=sort_key)[:k]


# --- Theme labeling ----------------------------------------------------------


def label_themes_heuristic(reviews: list[Review]) -> dict[str, str]:
    return {r.id: heuristic_theme_id(r.text) for r in reviews}


def label_themes_llm(
    reviews: list[Review],
    *,
    batch_size: int | None = None,
    max_llm_label: int | None = None,
    heuristic_min_score: int | None = None,
) -> dict[str, str]:
    """Hybrid theme labels: keyword-confident free, ambiguous → capped Groq batches.

    Minimizes Groq calls/tokens:
    1. Assign confident keyword matches locally (no API).
    2. Rank remaining by severity (low ★ first) and send at most ``max_llm_label``.
    3. Anything past the cap falls back to heuristic.
    """
    batch_size = batch_size or _default_batch_size()
    max_llm = (
        _default_max_llm_label() if max_llm_label is None else max(0, max_llm_label)
    )
    min_score = (
        _default_heuristic_min_score()
        if heuristic_min_score is None
        else max(0, heuristic_min_score)
    )

    assignments: dict[str, str] = {}
    uncertain: list[Review] = []

    for r in reviews:
        confident = confident_theme_id(r.text, min_score=min_score)
        if confident is not None:
            assignments[r.id] = confident
        else:
            uncertain.append(r)

    # Prefer low-rated ambiguous reviews for the scarce LLM budget
    uncertain.sort(
        key=lambda r: (r.rating if r.rating is not None else 99.0, r.id)
    )
    to_llm = uncertain[:max_llm]
    for r in uncertain[max_llm:]:
        assignments[r.id] = heuristic_theme_id(r.text)

    if not to_llm:
        return assignments

    system = _read_prompt("theme_cluster.md")
    for batch in _batched(to_llm, batch_size):
        payload = []
        for r in batch:
            item: dict[str, Any] = {
                "id": r.id,
                "rating": r.rating,
                "text": r.text[:REVIEW_TEXT_CHARS],
            }
            hint = keyword_hint(r.text)
            if hint:
                item["hint"] = hint
            payload.append(item)

        human = (
            "Label each review with exactly one theme_id from the fixed vocabulary.\n"
            f"Reviews JSON:\n{json.dumps(payload, ensure_ascii=False)}"
        )
        result: ThemeBatchResult = invoke_structured(
            ThemeBatchResult, system, human, provider="groq"
        )
        by_batch = {a.review_id: a.theme_id for a in result.assignments}
        for r in batch:
            tid = by_batch.get(r.id) or keyword_hint(r.text) or "app_reliability"
            if tid not in THEME_IDS:
                tid = keyword_hint(r.text) or "app_reliability"
            assignments[r.id] = tid
        for r in batch:
            assignments.setdefault(r.id, heuristic_theme_id(r.text))

    return assignments


# --- Quote selection ---------------------------------------------------------


def quote_candidates(
    reviews: list[Review],
    assignments: dict[str, str],
    top_theme_ids: list[str],
    *,
    max_per_theme: int = 40,
) -> list[dict[str, Any]]:
    """rating ≤3 and ≥12 words in top themes."""
    pool: list[dict[str, Any]] = []
    per_theme: dict[str, int] = defaultdict(int)
    ordered = sorted(
        reviews,
        key=lambda r: (r.rating if r.rating is not None else 99.0, r.id),
    )
    for r in ordered:
        tid = assignments.get(r.id)
        if tid not in top_theme_ids:
            continue
        if r.rating is not None and r.rating > 3:
            continue
        if word_count(r.text) < 12:
            continue
        if per_theme[tid] >= max_per_theme:
            continue
        per_theme[tid] += 1
        pool.append(
            {
                "id": r.id,
                "theme_id": tid,
                "rating": r.rating,
                "text": r.text,
            }
        )
    return pool


_HINGLISH_RE = re.compile(
    r"\b("
    r"hai|hain|nahi|nahin|kya|kyun|ke|ki|ka|ko|se|me|mein|aur|ore|"
    r"bahut|bhot|app\s+bhot|karne|karte|gaya|gaya|tha|thi|ho\s+gya|"
    r"please\s+fix|mat\s+download"
    r")\b",
    re.I,
)


def _english_signal(text: str) -> float:
    """Rough Latin-letter ratio so heuristic quotes prefer scannable EN evidence."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    latin = sum(1 for ch in letters if "a" <= ch.lower() <= "z")
    base = latin / len(letters)
    # Penalize common romanized-Hindi tokens (corpus is EN-tagged but noisy)
    hinglish_hits = len(_HINGLISH_RE.findall(text))
    return max(0.0, base - 0.08 * hinglish_hits)


def _quote_rank_key(c: dict[str, Any]) -> tuple:
    from src.agent.vocab import keyword_scores

    rating = c["rating"] if c["rating"] is not None else 99.0
    theme_hit = keyword_scores(c["text"]).get(c["theme_id"], 0)
    # Prefer theme-aligned wording, then low rating, English signal, length
    return (
        -theme_hit,
        rating,
        -_english_signal(c["text"]),
        -min(len(c["text"]), 240),
        c["id"],
    )


def select_quotes_heuristic(
    candidates: list[dict[str, Any]],
    top_theme_ids: list[str],
) -> list[tuple[str, str]]:
    """One strong quote per top theme when possible."""
    from src.agent.vocab import keyword_scores

    picked: list[tuple[str, str]] = []
    used_ids: set[str] = set()
    ranked = sorted(candidates, key=_quote_rank_key)
    for tid in top_theme_ids:
        for c in ranked:
            if c["theme_id"] != tid or c["id"] in used_ids:
                continue
            if _english_signal(c["text"]) < 0.85:
                continue
            # Require at least one theme keyword so quotes illustrate the theme
            if keyword_scores(c["text"]).get(tid, 0) < 1:
                continue
            q = _truncate_quote(c["text"])
            picked.append((c["id"], q))
            used_ids.add(c["id"])
            break
    # Fill to 3 from remaining (relax keyword / English thresholds if needed)
    for min_hits, threshold in ((1, 0.85), (0, 0.85), (0, 0.0)):
        for c in ranked:
            if len(picked) >= 3:
                break
            if c["id"] in used_ids:
                continue
            if _english_signal(c["text"]) < threshold:
                continue
            if keyword_scores(c["text"]).get(c["theme_id"], 0) < min_hits:
                continue
            picked.append((c["id"], _truncate_quote(c["text"])))
            used_ids.add(c["id"])
        if len(picked) >= 3:
            break
    return picked[:3]


def select_quotes_llm(
    candidates: list[dict[str, Any]],
    top_theme_ids: list[str],
    reviews: list[Review],
) -> list[tuple[str, str]]:
    if len(candidates) < 3:
        return select_quotes_heuristic(candidates, top_theme_ids)

    system = _read_prompt("quote_select.md")
    # Cap payload size for Groq TPM
    slim = [
        {
            "id": c["id"],
            "theme_id": c["theme_id"],
            "rating": c["rating"],
            "text": c["text"][:REVIEW_TEXT_CHARS],
        }
        for c in candidates[:60]
    ]
    human = (
        f"Top theme ids (prefer diversity): {top_theme_ids}\n"
        f"Candidates JSON:\n{json.dumps(slim, ensure_ascii=False)}"
    )
    result: QuoteSelectResult = invoke_structured(
        QuoteSelectResult, system, human, provider="gemini"
    )
    by_id = {r.id: r for r in reviews}
    validated: list[tuple[str, str]] = []
    for pick in result.quotes:
        review = by_id.get(pick.review_id)
        quote = pick.quote.strip()
        if review and quote_is_verbatim(quote, [review]):
            validated.append(
                (pick.review_id, _truncate_quote(normalize_display_quote(quote)))
            )
        elif review and quote_is_verbatim(quote, reviews):
            validated.append(
                (pick.review_id, _truncate_quote(normalize_display_quote(quote)))
            )

    if len(validated) < 3:
        return select_quotes_heuristic(candidates, top_theme_ids)
    return validated[:3]


def normalize_display_quote(quote: str) -> str:
    q = quote.strip()
    if len(q) >= 2 and q[0] in "\"'“‘" and q[-1] in "\"'”’":
        q = q[1:-1].strip()
    return q


# --- Actions -----------------------------------------------------------------


def ideate_actions_heuristic(top_themes: list[Theme]) -> list[tuple[str, str]]:
    return [(t.id, DEFAULT_ACTIONS[t.id]) for t in top_themes[:3]]


def ideate_actions_llm(
    top_themes: list[Theme],
    quotes: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    system = _read_prompt("action_ideate.md")
    payload = {
        "top_themes": [
            {
                "theme_id": t.id,
                "label": t.label,
                "review_count": t.review_count,
                "avg_rating": t.avg_rating,
                "summary": t.summary,
            }
            for t in top_themes
        ],
        "quotes": [{"review_id": rid, "quote": q} for rid, q in quotes],
    }
    human = f"Evidence JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    result: ActionIdeateResult = invoke_structured(
        ActionIdeateResult, system, human, provider="gemini"
    )
    actions: list[tuple[str, str]] = []
    for item in result.actions:
        tid = item.theme_id if item.theme_id in THEME_IDS else top_themes[0].id
        actions.append((tid, item.action.strip()))
    if len(actions) < 3:
        return ideate_actions_heuristic(top_themes)
    return actions[:3]


# --- Compose -----------------------------------------------------------------


def week_ending_from_reviews(reviews: list[Review]) -> date:
    return max(r.date for r in reviews)


def compose_pulse_markdown(
    *,
    week_ending: date,
    top_themes: list[Theme],
    quotes: list[str],
    actions: list[str],
) -> str:
    lines = [
        f"# Groww Weekly Review Pulse — Week Ending {week_ending.isoformat()}",
        "",
        "## Top Themes",
    ]
    for i, t in enumerate(top_themes[:3], start=1):
        lines.append(f"{i}. {t.label} ({t.review_count} reviews, avg {t.avg_rating})")
    lines += ["", "## What Users Said"]
    for i, q in enumerate(quotes[:3], start=1):
        lines.append(f"{i}. “{q}”")
    lines += ["", "## Action Ideas"]
    for i, a in enumerate(actions[:3], start=1):
        lines.append(f"{i}. {a}")
    body = "\n".join(lines).strip() + "\n"
    # Trim theme detail lines if over 250 words
    if word_count(body) > 250:
        lines = [
            f"# Groww Weekly Review Pulse — Week Ending {week_ending.isoformat()}",
            "",
            "## Top Themes",
        ]
        for i, t in enumerate(top_themes[:3], start=1):
            lines.append(f"{i}. {t.label}")
        lines += ["", "## What Users Said"]
        for i, q in enumerate(quotes[:3], start=1):
            short = _truncate_quote(q, max_words=28)
            lines.append(f"{i}. “{short}”")
        lines += ["", "## Action Ideas"]
        for i, a in enumerate(actions[:3], start=1):
            lines.append(f"{i}. {_truncate_quote(a, max_words=22)}")
        body = "\n".join(lines).strip() + "\n"
    return body


def compose_pulse_llm(
    *,
    week_ending: date,
    top_themes: list[Theme],
    quotes: list[str],
    actions: list[str],
) -> PulseComposeResult:
    system = _read_prompt("pulse_compose.md")
    payload = {
        "week_ending": week_ending.isoformat(),
        "themes": [t.label for t in top_themes[:3]],
        "quotes": quotes[:3],
        "actions": actions[:3],
    }
    human = (
        "Compose the pulse using ONLY this evidence. Keep ≤250 words.\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
    return invoke_structured(PulseComposeResult, system, human, provider="gemini")


# --- Persistence -------------------------------------------------------------


def themes_to_jsonable(
    themes: list[Theme],
    top_themes: list[Theme],
    *,
    assignments_count: int,
    mode: str,
    week_ending: date,
) -> dict[str, Any]:
    return {
        "week_ending": week_ending.isoformat(),
        "mode": mode,
        "vocabulary": THEME_VOCAB,
        "labeled_reviews": assignments_count,
        "themes": [t.model_dump(mode="json") for t in themes],
        "top_3": [t.id for t in top_themes],
    }


def write_outputs(
    themes_payload: dict[str, Any],
    pulse: PulseDraft,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    themes_path = out / "themes.json"
    pulse_path = out / "pulse.md"
    themes_path.write_text(
        json.dumps(themes_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    pulse_path.write_text(pulse.body if pulse.body.endswith("\n") else pulse.body + "\n", encoding="utf-8")
    return themes_path, pulse_path


# --- Pipeline ----------------------------------------------------------------


def run_analysis(
    reviews: list[Review] | None = None,
    *,
    mode: Mode = "auto",
    batch_size: int | None = None,
    max_llm_label: int | None = None,
    heuristic_min_score: int | None = None,
    limit: int | None = None,
    reviews_path: Path | None = None,
) -> tuple[list[Theme], list[Theme], PulseDraft, dict[str, str], str]:
    """Run Phase-2 analysis. Returns (all_themes, top3, pulse, assignments, resolved_mode)."""
    resolved = resolve_mode(mode)
    reviews = reviews if reviews is not None else load_reviews(reviews_path)
    if limit is not None and limit > 0:
        reviews = sample_reviews(reviews, limit)
    batch_size = batch_size or _default_batch_size()

    if resolved == "llm":
        assignments = label_themes_llm(
            reviews,
            batch_size=batch_size,
            max_llm_label=max_llm_label,
            heuristic_min_score=heuristic_min_score,
        )
    else:
        assignments = label_themes_heuristic(reviews)

    themes = aggregate_themes(reviews, assignments)
    top3 = rank_top_themes(themes, assignments, reviews, k=3)
    top_ids = [t.id for t in top3]

    candidates = quote_candidates(reviews, assignments, top_ids)
    if resolved == "llm":
        quote_pairs = select_quotes_llm(candidates, top_ids, reviews)
        action_pairs = ideate_actions_llm(top3, quote_pairs)
    else:
        quote_pairs = select_quotes_heuristic(candidates, top_ids)
        action_pairs = ideate_actions_heuristic(top3)

    if len(quote_pairs) < 3:
        raise RuntimeError(
            f"Need 3 quote candidates; only found {len(quote_pairs)}. "
            "Widen candidate filters or check corpus."
        )

    quotes = [q for _, q in quote_pairs]
    actions = [a for _, a in action_pairs]
    week_ending = week_ending_from_reviews(reviews)

    if resolved == "llm":
        composed = compose_pulse_llm(
            week_ending=week_ending,
            top_themes=top3,
            quotes=quotes,
            actions=actions,
        )
        body = composed.body.strip() + "\n"
        theme_labels = composed.themes
        quotes = [normalize_display_quote(q) for q in composed.quotes]
        actions = [a.strip() for a in composed.actions]
        # Ensure quotes remain verbatim; fall back to selected quotes if not
        if not all(quote_is_verbatim(q, reviews) for q in quotes):
            quotes = [q for _, q in quote_pairs]
            actions = [a for _, a in action_pairs]
            body = compose_pulse_markdown(
                week_ending=week_ending,
                top_themes=top3,
                quotes=quotes,
                actions=actions,
            )
            theme_labels = [t.label for t in top3]
    else:
        body = compose_pulse_markdown(
            week_ending=week_ending,
            top_themes=top3,
            quotes=quotes,
            actions=actions,
        )
        theme_labels = [t.label for t in top3]

    # Final hard clamp
    if word_count(body) > 250:
        body = compose_pulse_markdown(
            week_ending=week_ending,
            top_themes=top3,
            quotes=quotes,
            actions=actions,
        )

    pulse = PulseDraft(
        week_ending=week_ending,
        themes=theme_labels[:3],
        quotes=quotes[:3],
        actions=actions[:3],
        body=body,
        word_count=word_count(body),
    )

    result = validate_all(reviews, themes, pulse)
    result.raise_if_failed()

    return themes, top3, pulse, assignments, resolved


def run_and_persist(
    *,
    mode: Mode = "auto",
    batch_size: int | None = None,
    max_llm_label: int | None = None,
    heuristic_min_score: int | None = None,
    limit: int | None = None,
    reviews_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    reviews = load_reviews(reviews_path)
    if limit is not None and limit > 0:
        reviews = sample_reviews(reviews, limit)
    themes, top3, pulse, assignments, resolved = run_analysis(
        reviews,
        mode=mode,
        batch_size=batch_size,
        max_llm_label=max_llm_label,
        heuristic_min_score=heuristic_min_score,
        # already sampled above; avoid double-sample
        limit=None,
        reviews_path=reviews_path,
    )
    week_ending = pulse.week_ending
    payload = themes_to_jsonable(
        themes,
        top3,
        assignments_count=len(assignments),
        mode=resolved,
        week_ending=week_ending,
    )
    # Attach severity ranking diagnostics
    by_id = {r.id: r for r in reviews}
    low_counts: dict[str, int] = defaultdict(int)
    for rid, tid in assignments.items():
        rev = by_id.get(rid)
        if rev and rev.rating is not None and rev.rating <= 2:
            low_counts[tid] += 1
    payload["severity"] = {
        tid: {"low_star_count": low_counts[tid]} for tid in THEME_VOCAB
    }
    payload["token_budget"] = {
        "review_limit": limit,
        "review_count": len(reviews),
        "max_llm_label": (
            _default_max_llm_label() if max_llm_label is None else max_llm_label
        ),
        "heuristic_min_score": (
            _default_heuristic_min_score()
            if heuristic_min_score is None
            else heuristic_min_score
        ),
        "batch_size": batch_size or _default_batch_size(),
    }
    themes_path, pulse_path = write_outputs(payload, pulse, output_dir=output_dir)
    return {
        "mode": resolved,
        "review_count": len(reviews),
        "themes_path": str(themes_path),
        "pulse_path": str(pulse_path),
        "top_3": [t.id for t in top3],
        "word_count": pulse.word_count,
        "week_ending": week_ending.isoformat(),
        "token_budget": payload["token_budget"],
    }
