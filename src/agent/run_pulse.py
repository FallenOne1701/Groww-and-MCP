"""CLI: run Phase-2 analysis → output/themes.json + output/pulse.md.

Usage:
  python -m src.agent.run_pulse
  python -m src.agent.run_pulse --mode heuristic
  python -m src.agent.run_pulse --mode llm --limit 200
  python -m src.agent.run_pulse --mode llm --max-llm-label 40 --batch-size 8
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.agent.chains import run_and_persist
from src.agent.loaders import DEFAULT_CSV, DEFAULT_JSON, load_reviews
from src.agent.validators import validate_reviews


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Groww Weekly Review Pulse — Phase 2 analysis (local artifacts)"
    )
    p.add_argument(
        "--mode",
        choices=("auto", "llm", "heuristic"),
        default="auto",
        help="auto uses Groq+Gemini when keys are set, else heuristic",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Rating-stratified sample size (e.g. 200). Default: full corpus",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Reviews per Groq theme-label call (default GROQ_BATCH_SIZE or 8)",
    )
    p.add_argument(
        "--max-llm-label",
        type=int,
        default=None,
        help=(
            "Max ambiguous reviews sent to Groq for themes "
            "(default GROQ_MAX_LLM_LABEL or 40; 0 = keyword-only themes)"
        ),
    )
    p.add_argument(
        "--heuristic-min-score",
        type=int,
        default=None,
        help=(
            "Keyword hit score to skip Groq for a review "
            "(default GROQ_HEURISTIC_MIN_SCORE or 1)"
        ),
    )
    p.add_argument(
        "--reviews",
        type=Path,
        default=None,
        help="Path to cleaned reviews.json or play_store.csv (default: Phase 1 paths)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for themes.json and pulse.md (default: output/)",
    )
    p.add_argument(
        "--dry-run-validate",
        action="store_true",
        help="Only load reviews and validate Play/EN constraints",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.dry_run_validate:
        reviews = load_reviews(args.reviews)
        result = validate_reviews(reviews)
        print(f"Loaded {len(reviews)} reviews from Phase 1 corpus")
        print(f"JSON default exists: {DEFAULT_JSON.exists()} ({DEFAULT_JSON})")
        print(f"CSV default exists: {DEFAULT_CSV.exists()} ({DEFAULT_CSV})")
        if not result.ok:
            print("Validation errors:")
            for e in result.errors[:20]:
                print(f"  - {e}")
            return 1
        print("Review source/language gates: OK")
        return 0

    try:
        summary = run_and_persist(
            mode=args.mode,
            batch_size=args.batch_size,
            max_llm_label=args.max_llm_label,
            heuristic_min_score=args.heuristic_min_score,
            limit=args.limit,
            reviews_path=args.reviews,
            output_dir=args.output_dir,
        )
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2))
    print("Wrote themes + pulse; validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
