"""Phase 5 edge-case hardening: sparse weeks, long quotes, theme long-tail."""

from __future__ import annotations

from datetime import date

from src.agent.chains import (
    _truncate_quote,
    compose_pulse_markdown,
    week_ending_from_reviews,
)
from src.agent.validators import normalize_quote_for_match, word_count
from src.agent.vocab import DEFAULT_ACTIONS, THEME_IDS, THEME_VOCAB
from src.ingest import MAX_WEEKS, MIN_WEEKS, SPARSE_THRESHOLD, choose_window
from src.models import PulseDraft, Review, Theme

MAX_QUOTE_WORDS = 36


def truncate_verbatim_quote(text: str, max_words: int = MAX_QUOTE_WORDS) -> str:
    """Keep a verbatim prefix; add ellipsis only when truncated."""
    return _truncate_quote(text, max_words=max_words)


def merge_long_tail_assignments(assignments: dict[str, str]) -> dict[str, str]:
    """Map unknown / invented theme ids into the fixed ≤5 vocabulary."""
    merged: dict[str, str] = {}
    for review_id, theme_id in assignments.items():
        merged[review_id] = theme_id if theme_id in THEME_IDS else "app_reliability"
    return merged


def pad_top_themes(themes: list[Theme], k: int = 3) -> list[Theme]:
    """Ensure the pulse can list k theme slots; unused vocab is marked empty."""
    out = list(themes[:k])
    seen = {t.id for t in out}
    for tid, label in THEME_VOCAB.items():
        if len(out) >= k:
            break
        if tid in seen:
            continue
        out.append(
            Theme(
                id=tid,
                label=label,
                review_count=0,
                avg_rating=None,
                summary="Insufficient volume this window",
                sample_ids=[],
            )
        )
        seen.add(tid)
    return out


def pad_quotes_from_reviews(
    pairs: list[tuple[str, str]],
    reviews: list[Review],
    *,
    need: int = 3,
) -> list[tuple[str, str]]:
    """Fill up to ``need`` verbatim quotes from any remaining reviews."""
    used_ids = {rid for rid, _ in pairs}
    used_needles = {normalize_quote_for_match(q) for _, q in pairs}
    ordered = sorted(
        reviews,
        key=lambda r: (
            r.rating if r.rating is not None else 99.0,
            -word_count(r.text),
            r.id,
        ),
    )
    out = list(pairs)
    for review in ordered:
        if len(out) >= need:
            break
        if review.id in used_ids:
            continue
        quote = truncate_verbatim_quote(review.text)
        needle = normalize_quote_for_match(quote)
        if not needle or needle in used_needles:
            continue
        out.append((review.id, quote))
        used_ids.add(review.id)
        used_needles.add(needle)
    return out[:need]


def pad_actions(
    action_pairs: list[tuple[str, str]],
    top_themes: list[Theme],
    *,
    need: int = 3,
) -> list[tuple[str, str]]:
    """Fill default actions from top themes, then remaining vocab."""
    out = list(action_pairs[:need])
    seen = {tid for tid, _ in out}
    for theme in top_themes:
        if len(out) >= need:
            break
        if theme.id in seen:
            continue
        out.append((theme.id, DEFAULT_ACTIONS[theme.id]))
        seen.add(theme.id)
    for tid, action in DEFAULT_ACTIONS.items():
        if len(out) >= need:
            break
        if tid in seen:
            continue
        out.append((tid, action))
        seen.add(tid)
    return out[:need]


def resolve_analysis_window(
    reviews: list[Review],
    *,
    preferred_weeks: int = MIN_WEEKS,
    as_of: date | None = None,
    sparse_threshold: int = SPARSE_THRESHOLD,
) -> tuple[list[Review], int, bool, bool]:
    """Widen 8→12 on sparse weeks. Returns reviews, weeks used, widened, insufficient."""
    selected, used = choose_window(
        reviews,
        preferred_weeks=preferred_weeks,
        as_of=as_of,
        sparse_threshold=sparse_threshold,
    )
    preferred = max(MIN_WEEKS, min(MAX_WEEKS, preferred_weeks))
    widened = used > preferred
    insufficient = len(selected) < sparse_threshold
    return selected, used, widened, insufficient


def compose_insufficient_signal_markdown(
    *,
    week_ending: date,
    review_count: int,
    weeks: int,
    top_themes: list[Theme],
    quotes: list[str],
    actions: list[str],
) -> str:
    """Same 3-section contract plus an explicit insufficient-signal banner."""
    inner = compose_pulse_markdown(
        week_ending=week_ending,
        top_themes=top_themes,
        quotes=quotes,
        actions=actions,
    )
    banner = (
        f"**Insufficient signal:** only {review_count} Play Store reviews in the "
        f"last {weeks} weeks after widening toward {MAX_WEEKS}. "
        "Treat themes as directional, not a full weekly read.\n\n"
    )
    lines = inner.splitlines()
    if lines:
        body = lines[0] + "\n\n" + banner + "\n".join(lines[1:]).lstrip("\n")
    else:
        body = banner
    if not body.endswith("\n"):
        body += "\n"
    if word_count(body) > 250:
        body = compose_pulse_markdown(
            week_ending=week_ending,
            top_themes=top_themes,
            quotes=[truncate_verbatim_quote(q, max_words=20) for q in quotes],
            actions=[truncate_verbatim_quote(a, max_words=16) for a in actions],
        )
        lines = body.splitlines()
        short_banner = (
            f"**Insufficient signal:** {review_count} reviews in {weeks} weeks "
            f"(widened toward {MAX_WEEKS}).\n\n"
        )
        body = lines[0] + "\n\n" + short_banner + "\n".join(lines[1:]).lstrip("\n")
        if not body.endswith("\n"):
            body += "\n"
    return body


def build_sparse_pulse(
    reviews: list[Review],
    top_themes: list[Theme],
    quote_pairs: list[tuple[str, str]],
    action_pairs: list[tuple[str, str]],
    *,
    weeks: int,
) -> PulseDraft:
    """Structured pulse when the window is below the sparse floor."""
    padded_themes = pad_top_themes(top_themes)
    quotes = [q for _, q in quote_pairs[:3]]
    actions = [a for _, a in pad_actions(action_pairs, padded_themes)]
    ending = week_ending_from_reviews(reviews) if reviews else date.today()
    body = compose_insufficient_signal_markdown(
        week_ending=ending,
        review_count=len(reviews),
        weeks=weeks,
        top_themes=padded_themes,
        quotes=quotes,
        actions=actions,
    )
    return PulseDraft(
        week_ending=ending,
        themes=[t.label for t in padded_themes[:3]],
        quotes=quotes,
        actions=actions[:3],
        body=body,
        word_count=word_count(body),
    )
