"""Phase 5 CLI: architecture §9 quality gates.

Usage:
  python -m src.agent.run_gates
  python -m src.agent.run_gates --output-dir output --weeks 8
  python -m src.agent.run_gates --as-of 2026-09-12
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from src.agent.loaders import load_reviews
from src.agent.validators import GateReport, evaluate_artifact_dir, evaluate_gates
from src.ingest import MAX_WEEKS, MIN_WEEKS

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run architecture §9 gates on cleaned reviews + pulse artifacts"
    )
    p.add_argument(
        "--reviews",
        type=Path,
        default=None,
        help="Path to cleaned reviews.json or play_store.csv",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory with themes.json / pulse.md / delivery.json (default: output/)",
    )
    p.add_argument(
        "--weeks",
        type=int,
        default=None,
        help=f"Expected window length ({MIN_WEEKS}–{MAX_WEEKS}); default: infer from dates",
    )
    p.add_argument(
        "--as-of",
        dest="as_of",
        default=None,
        help="Window end date YYYY-MM-DD (default: newest review date)",
    )
    p.add_argument(
        "--insufficient-signal",
        action="store_true",
        help="Treat this run as a sparse week (relaxes exact 3/3/3)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Print the gate report as JSON only",
    )
    return p


def _print_report(report: GateReport) -> None:
    status = "PASS" if report.ok else "FAIL"
    print(f"Architecture section 9 gates: {status}")
    if report.insufficient_signal:
        print("Note: insufficient-signal week (MCP publish skipped by contract).")
    width = max(len(c.name) for c in report.checks) if report.checks else 8
    for check in report.checks:
        mark = "OK" if check.ok else "FAIL"
        print(f"  [{mark:<4}] {check.name:<{width}}  {check.detail}")
        for err in check.errors:
            print(f"         - {err}")
    for warning in report.warnings:
        print(f"  warn: {warning}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    reviews = load_reviews(args.reviews)
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    weeks = args.weeks
    if weeks is not None:
        weeks = max(MIN_WEEKS, min(MAX_WEEKS, weeks))

    out_dir: Path = args.output_dir
    if (out_dir / "pulse.md").exists():
        report = evaluate_artifact_dir(
            reviews=reviews,
            output_dir=out_dir,
            weeks=weeks,
            as_of=as_of,
            insufficient_signal=args.insufficient_signal,
        )
    else:
        from src.models import PulseDraft

        report = evaluate_gates(
            reviews,
            [],
            PulseDraft(
                week_ending=date.today(),
                themes=[],
                quotes=[],
                actions=[],
                body="",
                word_count=0,
            ),
            weeks=weeks,
            as_of=as_of,
            insufficient_signal=args.insufficient_signal,
        )
        report.warnings.append("pulse.md missing — ran review-only gates.")

    out_dir.mkdir(parents=True, exist_ok=True)
    gates_path = out_dir / "gates.json"
    gates_path.write_text(
        json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8"
    )

    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        _print_report(report)
        print(f"Wrote {gates_path}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
