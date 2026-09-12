"""Sparse-week, quote truncate, and long-tail merge (Phase 5)."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from src.agent.edges import (
    build_sparse_pulse,
    merge_long_tail_assignments,
    pad_quotes_from_reviews,
    pad_top_themes,
    resolve_analysis_window,
    truncate_verbatim_quote,
)
from src.agent.validators import parse_pulse_markdown, quote_is_verbatim, word_count
from src.ingest import SPARSE_THRESHOLD
from src.models import Review
from src.agent.vocab import THEME_VOCAB


def _review(rid: str, text: str, *, days_ago: int = 5, rating: float = 1) -> Review:
    return Review(
        id=rid,
        source="play",
        rating=rating,
        title=None,
        text=text,
        date=date.today() - timedelta(days=days_ago),
        language="en",
    )


class EdgeCaseTests(unittest.TestCase):
    def test_truncate_keeps_verbatim_prefix(self) -> None:
        text = " ".join(["crash"] * 50)
        truncated = truncate_verbatim_quote(text, max_words=8)
        self.assertTrue(truncated.endswith("…"))
        self.assertTrue(quote_is_verbatim(truncated, [_review("play-t", text)]))

    def test_merge_long_tail_into_fixed_vocab(self) -> None:
        merged = merge_long_tail_assignments(
            {"a": "onboarding", "b": "trading_orders", "c": "kyc"}
        )
        self.assertEqual(merged["a"], "app_reliability")
        self.assertEqual(merged["b"], "trading_orders")
        self.assertEqual(merged["c"], "app_reliability")
        self.assertTrue(set(merged.values()) <= set(THEME_VOCAB))

    def test_pad_quotes_fills_to_three(self) -> None:
        reviews = [
            _review("play-1", "The app crashes every time I open the holdings page today."),
            _review("play-2", "I cannot sell my order and the stop-loss does not fire."),
            _review("play-3", "Support never answers tickets about failed UPI deposits."),
        ]
        padded = pad_quotes_from_reviews([], reviews)
        self.assertEqual(len(padded), 3)
        for _, quote in padded:
            self.assertTrue(quote_is_verbatim(quote, reviews))

    def test_pad_top_themes_caps_at_three_from_vocab(self) -> None:
        padded = pad_top_themes([])
        self.assertEqual(len(padded), 3)
        self.assertTrue(all(t.id in THEME_VOCAB for t in padded))

    def test_widen_window_when_preferred_is_sparse(self) -> None:
        reviews = [
            _review(
                f"play-{i}",
                "The trading app failed my sell order after the update again.",
                days_ago=70,
            )
            for i in range(8)
        ]
        selected, used, widened, insufficient = resolve_analysis_window(
            reviews, preferred_weeks=8, as_of=date.today(), sparse_threshold=30
        )
        self.assertTrue(widened)
        self.assertGreater(used, 8)
        self.assertTrue(insufficient)
        self.assertEqual(len(selected), 8)

    def test_insufficient_signal_pulse_is_structured(self) -> None:
        reviews = [
            _review("play-1", "The app crashes every time I open the holdings page today."),
            _review("play-2", "I cannot sell my order and the stop-loss does not fire."),
            _review("play-3", "Support never answers tickets about failed UPI deposits."),
        ]
        quotes = pad_quotes_from_reviews([], reviews)
        pulse = build_sparse_pulse(reviews, [], quotes, [], weeks=12)
        self.assertLessEqual(pulse.word_count, 250)
        self.assertEqual(pulse.word_count, word_count(pulse.body))
        self.assertIn("Insufficient signal", pulse.body)
        parsed = parse_pulse_markdown(pulse.body)
        self.assertEqual(len(parsed.themes), 3)
        self.assertEqual(len(parsed.actions), 3)
        self.assertGreaterEqual(len(parsed.quotes), 1)
        self.assertLess(len(reviews), SPARSE_THRESHOLD)

    def test_graph_sparse_week_writes_local_pulse(self) -> None:
        from src.agent.graph import run_weekly_pulse

        reviews = [
            _review("play-1", "The app crashes every time I open the holdings page today."),
            _review("play-2", "I cannot sell my order and the stop-loss does not fire."),
            _review("play-3", "Support never answers tickets about failed UPI deposits."),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            reviews_path = Path(tmp) / "reviews.json"
            reviews_path.write_text(
                json.dumps([r.model_dump(mode="json") for r in reviews], indent=2),
                encoding="utf-8",
            )
            out_dir = Path(tmp) / "output"
            summary = run_weekly_pulse(
                weeks=8,
                mode="heuristic",
                reviews_path=reviews_path,
                output_dir=out_dir,
                skip_delivery=True,
            )
            self.assertTrue(summary["insufficient_signal"])
            self.assertTrue(summary["window_widened"])
            self.assertTrue(summary["validation_ok"], summary)
            self.assertTrue((out_dir / "pulse.md").exists())
            body = (out_dir / "pulse.md").read_text(encoding="utf-8")
            self.assertIn("Insufficient signal", body)
            self.assertTrue((out_dir / "gates.json").exists())
            self.assertTrue((out_dir / "traces" / "latest.json").exists())


if __name__ == "__main__":
    unittest.main()
