"""CLI: smoke-test Groq + Gemini LLM wiring (Phase 2).

Tiny live API calls — does **not** run the full 1226-review pipeline.

Usage:
  python -m src.agent.run_llm_smoke
  python -m src.agent.run_llm_smoke --provider groq
  python -m src.agent.run_llm_smoke --provider gemini
  python -m src.agent.run_llm_smoke --sample 12   # mini pulse on N reviews
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from pydantic import BaseModel, Field

from src.agent.llm import (
    gemini_available,
    groq_available,
    invoke_structured,
    llms_available,
    load_env,
)
from src.agent.vocab import THEME_IDS


class _Ping(BaseModel):
    ok: bool = Field(..., description="True if you understood the request")
    echo: str = Field(..., description="Short echo of the user message")


class _ThemeOne(BaseModel):
    theme_id: str = Field(..., description="One of the fixed theme ids")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Smoke-test Groq / Gemini LLM connectivity for Weekly Review Pulse"
    )
    p.add_argument(
        "--provider",
        choices=("all", "groq", "gemini"),
        default="all",
        help="Which provider(s) to ping (default: all)",
    )
    p.add_argument(
        "--sample",
        type=int,
        default=0,
        metavar="N",
        help="If N>0, also run a mini LLM pulse on N cleaned reviews",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=4,
        help="Theme-label batch size for --sample (default 4)",
    )
    return p


def _status() -> dict[str, bool]:
    load_env()
    return {
        "groq_key": groq_available(),
        "gemini_key": gemini_available(),
        "llms_available": llms_available(),
    }


def ping_groq() -> dict:
    t0 = time.perf_counter()
    result = invoke_structured(
        _Ping,
        system="Reply with structured JSON only. Set ok=true and echo the user text briefly.",
        human="Groww weekly pulse smoke test",
        provider="groq",
    )
    elapsed = time.perf_counter() - t0
    return {
        "provider": "groq",
        "ok": bool(result.ok),
        "echo": result.echo,
        "seconds": round(elapsed, 2),
    }


def ping_gemini() -> dict:
    t0 = time.perf_counter()
    result = invoke_structured(
        _Ping,
        system="Reply with structured JSON only. Set ok=true and echo the user text briefly.",
        human="Groww weekly pulse smoke test",
        provider="gemini",
    )
    elapsed = time.perf_counter() - t0
    return {
        "provider": "gemini",
        "ok": bool(result.ok),
        "echo": result.echo,
        "seconds": round(elapsed, 2),
    }


def ping_groq_theme() -> dict:
    """One real theme-label call shaped like Phase 2."""
    human = (
        "Assign exactly one theme_id from: "
        + ", ".join(sorted(THEME_IDS))
        + "\n\nReview: rating=1 text=\"App keeps crashing after update and I cannot sell shares.\""
    )
    t0 = time.perf_counter()
    result = invoke_structured(
        _ThemeOne,
        system=(
            "You label Groww Play Store reviews. "
            "Return theme_id only from the fixed vocabulary."
        ),
        human=human,
        provider="groq",
    )
    elapsed = time.perf_counter() - t0
    tid = (result.theme_id or "").strip()
    return {
        "provider": "groq",
        "check": "theme_label",
        "theme_id": tid,
        "in_vocab": tid in THEME_IDS,
        "seconds": round(elapsed, 2),
    }


def run_sample_pulse(n: int, batch_size: int) -> dict:
    from src.agent.chains import run_and_persist
    from src.agent.loaders import load_reviews

    reviews = load_reviews()
    if n < len(reviews):
        # Stratify a bit: keep mix of ratings by taking every k-th after sort
        ranked = sorted(
            reviews,
            key=lambda r: (r.rating if r.rating is not None else 99.0, r.id),
        )
        step = max(1, len(ranked) // n)
        sample = ranked[::step][:n]
        # Write a temp sample file for the pipeline
        sample_path = Path("output") / "_llm_smoke_reviews.json"
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        sample_path.write_text(
            json.dumps([r.model_dump(mode="json") for r in sample], indent=2),
            encoding="utf-8",
        )
        reviews_path = sample_path
    else:
        reviews_path = None

    out_dir = Path("output") / "llm_smoke"
    t0 = time.perf_counter()
    summary = run_and_persist(
        mode="llm",
        batch_size=batch_size,
        reviews_path=reviews_path,
        output_dir=out_dir,
    )
    elapsed = time.perf_counter() - t0
    summary["seconds"] = round(elapsed, 2)
    summary["sample_n"] = n
    summary["output_dir"] = str(out_dir)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    status = _status()
    print("Key status:", json.dumps(status, indent=2))

    if args.provider in ("all", "groq") and not status["groq_key"]:
        print("ERROR: GROQ_API_KEY missing in .env", file=sys.stderr)
        return 2
    if args.provider in ("all", "gemini") and not status["gemini_key"]:
        print("ERROR: GOOGLE_API_KEY or GEMINI_API_KEY missing in .env", file=sys.stderr)
        return 2

    results: list[dict] = []
    failed = False

    if args.provider in ("all", "groq"):
        print("\n--- Groq ping ---")
        try:
            r = ping_groq()
            results.append(r)
            print(json.dumps(r, indent=2))
            r2 = ping_groq_theme()
            results.append(r2)
            print(json.dumps(r2, indent=2))
            if not r.get("ok") or not r2.get("in_vocab"):
                failed = True
        except Exception as exc:  # noqa: BLE001
            print(f"GROQ FAILED: {exc}", file=sys.stderr)
            results.append({"provider": "groq", "error": str(exc)})
            failed = True

    if args.provider in ("all", "gemini"):
        print("\n--- Gemini ping ---")
        try:
            r = ping_gemini()
            results.append(r)
            print(json.dumps(r, indent=2))
            if not r.get("ok"):
                failed = True
        except Exception as exc:  # noqa: BLE001
            print(f"GEMINI FAILED: {exc}", file=sys.stderr)
            results.append({"provider": "gemini", "error": str(exc)})
            failed = True

    if args.sample > 0:
        if not llms_available():
            print(
                "ERROR: --sample needs both Groq and Gemini keys",
                file=sys.stderr,
            )
            return 2
        print(f"\n--- Mini LLM pulse (n={args.sample}) ---")
        try:
            summary = run_sample_pulse(args.sample, args.batch_size)
            results.append({"check": "sample_pulse", **summary})
            print(json.dumps(summary, indent=2))
        except Exception as exc:  # noqa: BLE001
            print(f"SAMPLE PULSE FAILED: {exc}", file=sys.stderr)
            results.append({"check": "sample_pulse", "error": str(exc)})
            failed = True

    out = Path("output") / "llm_smoke_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"status": status, "results": results}, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    if failed:
        print("LLM smoke test: FAILED")
        return 1
    print("LLM smoke test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
