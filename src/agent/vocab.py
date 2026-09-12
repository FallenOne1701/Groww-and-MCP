"""Fixed Phase-2 theme vocabulary and keyword hint helpers."""

from __future__ import annotations

import re
from typing import Final

# Exact five theme ids (implementation-plan Phase 2). Do not invent a 6th.
THEME_VOCAB: Final[dict[str, str]] = {
    "trading_orders": "Trading & order execution",
    "charts_market_data": "Charts & market / holdings data",
    "customer_support": "Customer support",
    "app_reliability": "App reliability & updates",
    "fees_funding": "Fees, brokerage & funding",
}

THEME_IDS: Final[frozenset[str]] = frozenset(THEME_VOCAB)

# Keyword probes → theme hints (non-exclusive; weak signal for LLM / heuristic)
_KEYWORD_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    (
        "trading_orders",
        re.compile(
            r"\b("
            r"buy|sell|stop[\s-]?loss|square[\s-]?off|order|ipo|f&o|fno|"
            r"futures?|options?|mandate|execute|execution|trade|trading|"
            r"limit\s+order|market\s+order|gtt|sl-m|intraday"
            r")\b",
            re.I,
        ),
    ),
    (
        "charts_market_data",
        re.compile(
            r"\b("
            r"chart|ohlc|candle|avg(?:erage)?\s*buy\s*price|holdings?|"
            r"portfolio\s+value|yield|market\s+data|price\s+(?:wrong|incorrect|mismatch)|"
            r"wrong\s+price|stale"
            r")\b",
            re.I,
        ),
    ),
    (
        "customer_support",
        re.compile(
            r"\b("
            r"support|customer\s+care|call\s+cent(?:er|re)|ticket|no\s+response|"
            r"helpline|chat\s+support|agent|complaint|escalate|kyc|verification|"
            r"onboarding|sign[\s-]?up"
            r")\b",
            re.I,
        ),
    ),
    (
        "app_reliability",
        re.compile(
            r"\b("
            r"crash|lag|slow|freeze|not\s+working|doesn'?t\s+work|bug|glitch|"
            r"update|force\s+close|hang|loading|blank\s+screen|error|"
            r"uninstall|worst\s+app|useless"
            r")\b",
            re.I,
        ),
    ),
    (
        "fees_funding",
        re.compile(
            r"\b("
            r"brokerage|fee|charge|charges|commission|upi|deposit|withdraw|"
            r"withdrawal|payment|fund(?:ing)?|bank\s+transfer|sip|mutual\s+fund|"
            r"amc|hidden\s+charge|expensive"
            r")\b",
            re.I,
        ),
    ),
]

# Default actions when LLM is unavailable (mapped by theme_id)
DEFAULT_ACTIONS: Final[dict[str, str]] = {
    "trading_orders": (
        "Trace sell / stop-loss / square-off failures end-to-end and ship "
        "regression tests for the top order-lifecycle breakages."
    ),
    "charts_market_data": (
        "Audit chart OHLC, average buy-price, and holdings display accuracy "
        "against exchange feeds after recent UI updates."
    ),
    "customer_support": (
        "Reduce support dead-ends: publish ticket SLAs and route funding / "
        "trading escalations to a faster path."
    ),
    "app_reliability": (
        "Prioritize crash / freeze / post-update regressions from ≤2★ reviews "
        "and add release smoke checks for core screens."
    ),
    "fees_funding": (
        "Clarify brokerage / F&O fee surfacing and fix UPI deposit–withdraw "
        "friction called out in low-rated funding reviews."
    ),
}


def keyword_hint(text: str) -> str | None:
    """Return the first matching theme_id hint, or None if unmatched."""
    for theme_id, pattern in _KEYWORD_PATTERNS:
        if pattern.search(text):
            return theme_id
    return None


def keyword_scores(text: str) -> dict[str, int]:
    """Count keyword hits per theme (for heuristic primary assignment)."""
    scores: dict[str, int] = {tid: 0 for tid in THEME_VOCAB}
    for theme_id, pattern in _KEYWORD_PATTERNS:
        scores[theme_id] = len(pattern.findall(text))
    return scores


def heuristic_theme_id(text: str) -> str:
    """Deterministic primary theme when LLM is unavailable."""
    scores = keyword_scores(text)
    best = max(scores.values())
    if best <= 0:
        return "app_reliability"
    # Prefer higher score; tie-break by severity-relevant theme order
    preference = (
        "trading_orders",
        "customer_support",
        "app_reliability",
        "charts_market_data",
        "fees_funding",
    )
    for tid in preference:
        if scores[tid] == best:
            return tid
    return "app_reliability"


def confident_theme_id(text: str, *, min_score: int = 1) -> str | None:
    """Return heuristic theme when keyword evidence is strong enough to skip the LLM.

    ``min_score`` is the minimum keyword hit count for the winning theme.
    Returns None when the review is ambiguous (send to Groq).
    """
    if min_score <= 0:
        return None
    scores = keyword_scores(text)
    best = max(scores.values())
    if best < min_score:
        return None
    # Unique winner only — ties stay ambiguous for the LLM
    winners = [tid for tid, n in scores.items() if n == best]
    if len(winners) != 1:
        return None
    return winners[0]
