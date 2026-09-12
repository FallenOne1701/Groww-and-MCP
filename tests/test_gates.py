"""Architecture §9 gate checks (Phase 5)."""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from src.agent.validators import (
    evaluate_gates,
    parse_pulse_markdown,
    quote_is_verbatim,
    scan_pii,
    validate_window,
    word_count,
)
from src.agent.vocab import THEME_VOCAB
from src.models import PulseDraft, Review, Theme


def _review(
    rid: str,
    text: str,
    *,
    rating: float = 1,
    days_ago: int = 3,
    source: str = "play",
    language: str = "en",
) -> Review:
    return Review(
        id=rid,
        source=source,  # type: ignore[arg-type]
        rating=rating,
        title=None,
        text=text,
        date=date.today() - timedelta(days=days_ago),
        language=language,
    )


def _theme(tid: str, count: int = 4) -> Theme:
    return Theme(
        id=tid,
        label=THEME_VOCAB[tid],
        review_count=count,
        avg_rating=2.0,
        summary=f"{count} reviews; 2 rated ≤2★",
        sample_ids=[],
    )


def _pulse(reviews: list[Review], quotes: list[str]) -> PulseDraft:
    themes = [
        THEME_VOCAB["app_reliability"],
        THEME_VOCAB["trading_orders"],
        THEME_VOCAB["customer_support"],
    ]
    actions = [
        "Prioritize crash regressions from low-rated reviews this week.",
        "Trace sell and stop-loss failures end to end.",
        "Publish support ticket SLAs for funding escalations.",
    ]
    body = (
        f"# Groww Weekly Review Pulse — Week Ending {date.today().isoformat()}\n\n"
        "## Top Themes\n"
        f"1. {themes[0]}\n2. {themes[1]}\n3. {themes[2]}\n\n"
        "## What Users Said\n"
        f"1. “{quotes[0]}”\n2. “{quotes[1]}”\n3. “{quotes[2]}”\n\n"
        "## Action Ideas\n"
        f"1. {actions[0]}\n2. {actions[1]}\n3. {actions[2]}\n"
    )
    return PulseDraft(
        week_ending=date.today(),
        themes=themes,
        quotes=quotes,
        actions=actions,
        body=body,
        word_count=word_count(body),
    )


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reviews = [
            _review("play-a", "The app crashes after the latest update and charts freeze."),
            _review("play-b", "I cannot sell my shares and the stop-loss never triggers."),
            _review(
                "play-c",
                "Customer support never replies to my ticket about funding delays.",
            ),
        ]
        self.quotes = [r.text for r in self.reviews]
        self.themes = [
            _theme("app_reliability"),
            _theme("trading_orders"),
            _theme("customer_support"),
        ]
        self.pulse = _pulse(self.reviews, self.quotes)

    def test_window_rejects_old_reviews(self) -> None:
        old = _review("play-old", "This review is from last year and should be dropped.", days_ago=200)
        result = validate_window([old], weeks=8, as_of=date.today())
        self.assertFalse(result.ok)

    def test_window_accepts_eight_week_corpus(self) -> None:
        result = validate_window(self.reviews, weeks=8, as_of=date.today())
        self.assertTrue(result.ok, result.errors)

    def test_quotes_must_be_verbatim(self) -> None:
        self.assertTrue(quote_is_verbatim(self.quotes[0], self.reviews))
        self.assertFalse(quote_is_verbatim("Users hate the imaginary checkout bug.", self.reviews))

    def test_truncated_prefix_is_verbatim(self) -> None:
        prefix = "The app crashes after the latest update…"
        self.assertTrue(quote_is_verbatim(prefix, self.reviews))

    def test_pii_scan_catches_email_and_phone(self) -> None:
        hits = scan_pii("Email me at user@example.com or 9876543210")
        self.assertIn("email pattern", hits)
        self.assertIn("phone pattern", hits)

    def test_redacted_tokens_are_not_pii(self) -> None:
        self.assertEqual(scan_pii("Contact [email] or [phone]"), [])

    def test_evaluate_gates_pass(self) -> None:
        report = evaluate_gates(self.reviews, self.themes, self.pulse, weeks=8)
        self.assertTrue(report.ok, report.as_dict())
        self.assertEqual({c.name for c in report.checks}, set(report.as_dict()["gates"]))

    def test_source_rejects_non_play(self) -> None:
        bad = _review("x", "This would be an App Store review that we must refuse.", source="play")
        bad.source = "appstore"  # type: ignore[assignment]
        report = evaluate_gates([bad], self.themes, self.pulse, weeks=8)
        self.assertFalse(report.ok)
        source = next(c for c in report.checks if c.name == "source")
        self.assertFalse(source.ok)

    def test_parse_pulse_markdown_roundtrip(self) -> None:
        parsed = parse_pulse_markdown(self.pulse.body)
        self.assertEqual(parsed.themes, self.pulse.themes)
        self.assertEqual(parsed.quotes, self.pulse.quotes)
        self.assertEqual(len(parsed.actions), 3)


if __name__ == "__main__":
    unittest.main()
