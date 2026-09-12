"""LangGraph end-to-end orchestration (Phase 4–5).

One run: cleaned Play reviews → themes → pulse → §9 gates → Docs MCP → Gmail draft.

Usage:
  python -m src.agent.graph
  python -m src.agent.graph --weeks 12 --recipient you@example.com
  python -m src.agent.graph --mode heuristic
  python -m src.agent.graph --skip-delivery
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

from src.agent.chains import (
    Mode,
    aggregate_themes,
    compose_pulse_llm,
    compose_pulse_markdown,
    ideate_actions_heuristic,
    ideate_actions_llm,
    label_themes_heuristic,
    label_themes_llm,
    normalize_display_quote,
    quote_candidates,
    rank_top_themes,
    resolve_mode,
    sample_reviews,
    select_quotes_heuristic,
    select_quotes_llm,
    themes_to_jsonable,
    week_ending_from_reviews,
    write_outputs,
    _default_batch_size,
    _default_heuristic_min_score,
    _default_max_llm_label,
)
from src.agent.loaders import load_reviews
from src.agent.mcp_bridge import McpAuthMissingError, McpDeliveryError, load_env, transport_mode
from src.agent.tools_mcp import (
    build_email_body,
    create_or_update_pulse_doc,
    create_pulse_draft,
)
from src.agent.edges import (
    build_sparse_pulse,
    merge_long_tail_assignments,
    pad_actions,
    pad_quotes_from_reviews,
    pad_top_themes,
    resolve_analysis_window,
    truncate_verbatim_quote,
)
from src.agent.trace import write_trace
from src.agent.validators import evaluate_gates, quote_is_verbatim, word_count
from src.ingest import MIN_WEEKS, MAX_WEEKS
from src.models import PulseDraft, Review, Theme
from src.scrub import scrub_reviews

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"


class PulseGraphState(TypedDict, total=False):
    """Threaded state for the weekly pulse LangGraph."""

    # Inputs / config
    weeks: int
    recipient: str
    mode: str
    resolved_mode: str
    limit: int | None
    batch_size: int | None
    max_llm_label: int | None
    heuristic_min_score: int | None
    reviews_path: str | None
    output_dir: str
    email_mode: str
    skip_delivery: bool
    allow_sparse_delivery: bool
    product_name: str

    # Pipeline data
    reviews: list[Review]
    assignments: dict[str, str]
    themes: list[Theme]
    top_themes: list[Theme]
    quotes: list[str]
    actions: list[str]
    quote_pairs: list[tuple[str, str]]
    action_pairs: list[tuple[str, str]]
    pulse: PulseDraft | None
    pulse_body: str
    week_ending: str
    week_key: str
    run_id: str
    title: str

    # Window / sparse
    window_widened: bool
    insufficient_signal: bool

    # Validation
    validation_ok: bool
    validation_errors: list[str]
    gate_report: dict[str, Any]

    # Delivery
    doc_id: str | None
    doc_url: str | None
    draft_id: str | None

    # Diagnostics
    errors: list[str]
    themes_path: str | None
    pulse_path: str | None
    run_path: str | None
    trace_path: str | None


def iso_week_key(d: date) -> str:
    """Return ISO week key ``YYYY-Www`` for idempotent Doc/email naming."""
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


def pulse_title(*, product: str, week_key: str, week_ending: date) -> str:
    return (
        f"{product} Weekly Review Pulse - {week_key} "
        f"(week ending {week_ending.isoformat()})"
    )


def _append_error(state: PulseGraphState, message: str) -> list[str]:
    errors = list(state.get("errors") or [])
    errors.append(message)
    return errors


# --- Nodes -------------------------------------------------------------------


def node_load(state: PulseGraphState) -> dict[str, Any]:
    """Load Phase-1 corpus, widen 8→12 when sparse, flag insufficient signal."""
    path_raw = state.get("reviews_path")
    path = Path(path_raw) if path_raw else None
    reviews = load_reviews(path)
    preferred = int(state.get("weeks") or MIN_WEEKS)
    preferred = max(MIN_WEEKS, min(MAX_WEEKS, preferred))
    reviews, weeks, widened, insufficient = resolve_analysis_window(
        reviews, preferred_weeks=preferred
    )
    limit = state.get("limit")
    if limit is not None and limit > 0:
        reviews = sample_reviews(reviews, int(limit))
    errors = list(state.get("errors") or [])
    if insufficient:
        errors.append(
            f"Insufficient signal: {len(reviews)} reviews after widening to {weeks}w"
        )
    if not reviews:
        return {
            "reviews": [],
            "weeks": weeks,
            "window_widened": widened,
            "insufficient_signal": True,
            "errors": _append_error(
                state,
                f"No reviews in the last {weeks} weeks after load/filter",
            ),
        }
    return {
        "reviews": reviews,
        "weeks": weeks,
        "window_widened": widened,
        "insufficient_signal": insufficient,
        "errors": errors,
    }


def node_scrub(state: PulseGraphState) -> dict[str, Any]:
    """Re-scrub PII (idempotent on already-cleaned Phase-1 data)."""
    reviews = state.get("reviews") or []
    if not reviews:
        return {"reviews": [], "errors": list(state.get("errors") or [])}
    cleaned = scrub_reviews(reviews)
    if not cleaned:
        return {
            "reviews": [],
            "errors": _append_error(state, "All reviews dropped during scrub"),
        }
    return {"reviews": cleaned}


def node_theme(state: PulseGraphState) -> dict[str, Any]:
    reviews = state.get("reviews") or []
    if not reviews:
        return {"assignments": {}, "resolved_mode": state.get("resolved_mode") or "heuristic"}
    raw_mode = state.get("mode") or "auto"
    if raw_mode not in ("auto", "llm", "heuristic"):
        raw_mode = "auto"
    resolved = resolve_mode(raw_mode)  # type: ignore[arg-type]
    batch_size = state.get("batch_size")
    if resolved == "llm":
        assignments = label_themes_llm(
            reviews,
            batch_size=batch_size or _default_batch_size(),
            max_llm_label=state.get("max_llm_label"),
            heuristic_min_score=state.get("heuristic_min_score"),
        )
    else:
        assignments = label_themes_heuristic(reviews)
    assignments = merge_long_tail_assignments(assignments)
    return {"assignments": assignments, "resolved_mode": resolved}


def node_rank(state: PulseGraphState) -> dict[str, Any]:
    reviews = state.get("reviews") or []
    assignments = state.get("assignments") or {}
    themes = aggregate_themes(reviews, assignments)
    top3 = rank_top_themes(themes, assignments, reviews, k=3)
    return {"themes": themes, "top_themes": top3}


def node_quotes(state: PulseGraphState) -> dict[str, Any]:
    reviews = state.get("reviews") or []
    assignments = state.get("assignments") or {}
    top3 = state.get("top_themes") or []
    top_ids = [t.id for t in top3]
    candidates = quote_candidates(reviews, assignments, top_ids)
    resolved = state.get("resolved_mode") or "heuristic"
    if resolved == "llm":
        quote_pairs = select_quotes_llm(candidates, top_ids, reviews)
    else:
        quote_pairs = select_quotes_heuristic(candidates, top_ids)
    if len(quote_pairs) < 3:
        quote_pairs = pad_quotes_from_reviews(quote_pairs, reviews)
    quote_pairs = [
        (rid, truncate_verbatim_quote(quote)) for rid, quote in quote_pairs
    ]
    quotes = [q for _, q in quote_pairs]
    return {"quote_pairs": quote_pairs, "quotes": quotes}


def node_actions(state: PulseGraphState) -> dict[str, Any]:
    top3 = state.get("top_themes") or []
    quote_pairs = state.get("quote_pairs") or []
    resolved = state.get("resolved_mode") or "heuristic"
    if resolved == "llm":
        action_pairs = ideate_actions_llm(top3, quote_pairs)
    else:
        action_pairs = ideate_actions_heuristic(top3)
    if len(action_pairs) < 3:
        action_pairs = pad_actions(action_pairs, top3)
    actions = [a for _, a in action_pairs]
    return {"action_pairs": action_pairs, "actions": actions}


def node_compose(state: PulseGraphState) -> dict[str, Any]:
    reviews = state.get("reviews") or []
    top3 = list(state.get("top_themes") or [])
    quote_pairs = list(state.get("quote_pairs") or [])
    action_pairs = list(state.get("action_pairs") or [])
    errors = list(state.get("errors") or [])
    insufficient = bool(state.get("insufficient_signal"))

    if len(quote_pairs) < 3:
        quote_pairs = pad_quotes_from_reviews(quote_pairs, reviews)
    if len(top3) < 3:
        top3 = pad_top_themes(top3)
    if len(action_pairs) < 3:
        action_pairs = pad_actions(action_pairs, top3)

    if len(quote_pairs) < 3 and not insufficient:
        msg = (
            f"Need 3 quote candidates; only found {len(quote_pairs)}. "
            "Widen candidate filters or check corpus."
        )
        errors.append(msg)
        return {
            "errors": errors,
            "pulse": None,
            "pulse_body": "",
            "quotes": [],
            "actions": [],
            "validation_ok": False,
            "validation_errors": [msg],
        }

    quotes = [q for _, q in quote_pairs]
    actions = [a for _, a in action_pairs]
    week_ending = week_ending_from_reviews(reviews)
    week_key = iso_week_key(week_ending)
    product = (state.get("product_name") or "Groww").strip() or "Groww"
    title = pulse_title(product=product, week_key=week_key, week_ending=week_ending)
    resolved = state.get("resolved_mode") or "heuristic"

    if insufficient:
        pulse = build_sparse_pulse(
            reviews,
            top3,
            list(quote_pairs),
            action_pairs,
            weeks=int(state.get("weeks") or MIN_WEEKS),
        )
        return {
            "pulse": pulse,
            "pulse_body": pulse.body,
            "quotes": pulse.quotes,
            "actions": pulse.actions,
            "week_ending": pulse.week_ending.isoformat(),
            "week_key": week_key,
            "run_id": week_key,
            "title": title,
            "top_themes": top3,
            "errors": errors,
        }

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
    return {
        "pulse": pulse,
        "pulse_body": pulse.body,
        "quotes": pulse.quotes,
        "actions": pulse.actions,
        "week_ending": week_ending.isoformat(),
        "week_key": week_key,
        "run_id": week_key,
        "title": title,
        "errors": errors,
    }


def node_validate(state: PulseGraphState) -> dict[str, Any]:
    """Validate pulse; persist local artifacts only when gates pass.

    Stops delivery when validation fails (conditional edge).
    """
    reviews = state.get("reviews") or []
    themes = state.get("themes") or []
    pulse = state.get("pulse")
    errors = list(state.get("errors") or [])

    if pulse is None:
        msg = "No pulse to validate (compose failed)"
        errors.append(msg)
        return {
            "validation_ok": False,
            "validation_errors": [msg],
            "errors": errors,
            "themes_path": None,
            "pulse_path": None,
        }

    insufficient = bool(state.get("insufficient_signal"))
    report = evaluate_gates(
        reviews,
        themes,
        pulse,
        weeks=state.get("weeks"),
        action_pairs=state.get("action_pairs"),
        extra_texts=[pulse.body],
        cleaned_records=[r.model_dump(mode="json") for r in reviews],
        insufficient_signal=insufficient,
        require_exact_triples=not (
            insufficient and (len(pulse.quotes) < 3 or len(pulse.themes) < 3)
        ),
    )
    if not report.ok:
        gate_errors = [e for c in report.checks for e in c.errors]
        errors.extend(gate_errors)
        return {
            "validation_ok": False,
            "validation_errors": gate_errors,
            "gate_report": report.as_dict(),
            "errors": errors,
            "themes_path": None,
            "pulse_path": None,
        }

    out_dir = Path(state.get("output_dir") or str(OUTPUT_DIR))
    week_ending = pulse.week_ending
    top3 = state.get("top_themes") or []
    assignments = state.get("assignments") or {}
    resolved = state.get("resolved_mode") or "heuristic"
    limit = state.get("limit")

    payload = themes_to_jsonable(
        themes,
        top3,
        assignments_count=len(assignments),
        mode=resolved,
        week_ending=week_ending,
    )
    payload["week_key"] = state.get("week_key") or iso_week_key(week_ending)
    payload["run_id"] = state.get("run_id") or payload["week_key"]
    payload["token_budget"] = {
        "review_limit": limit,
        "review_count": len(reviews),
        "weeks": state.get("weeks"),
        "max_llm_label": (
            _default_max_llm_label()
            if state.get("max_llm_label") is None
            else state.get("max_llm_label")
        ),
        "heuristic_min_score": (
            _default_heuristic_min_score()
            if state.get("heuristic_min_score") is None
            else state.get("heuristic_min_score")
        ),
        "batch_size": state.get("batch_size") or _default_batch_size(),
    }
    payload["insufficient_signal"] = insufficient
    payload["window_widened"] = bool(state.get("window_widened"))
    themes_path, pulse_path = write_outputs(payload, pulse, output_dir=out_dir)
    gates_path = out_dir / "gates.json"
    gates_path.write_text(
        json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return {
        "validation_ok": True,
        "validation_errors": [],
        "gate_report": report.as_dict(),
        "themes_path": str(themes_path),
        "pulse_path": str(pulse_path),
        "errors": errors,
    }


def node_publish_doc(state: PulseGraphState) -> dict[str, Any]:
    """Publish validated pulse via Docs MCP."""
    if state.get("skip_delivery"):
        return {"doc_id": None, "doc_url": None}
    body = state.get("pulse_body") or ""
    title = state.get("title") or "Groww Weekly Review Pulse"
    try:
        doc = create_or_update_pulse_doc(title=title, body=body)
        return {"doc_id": doc["doc_id"], "doc_url": doc["url"]}
    except (McpAuthMissingError, McpDeliveryError) as exc:
        return {
            "doc_id": None,
            "doc_url": None,
            "errors": _append_error(
                state,
                f"Docs MCP failed (local pulse kept): {exc}",
            ),
        }


def node_draft_email(state: PulseGraphState) -> dict[str, Any]:
    """Create Gmail draft via Gmail MCP (does not send)."""
    if state.get("skip_delivery"):
        return {"draft_id": None}
    # If Docs failed hard with auth and we have no body path, still try draft
    # only when we have a pulse — prefer link mode when doc_url present.
    body = state.get("pulse_body") or ""
    title = state.get("title") or "Groww Weekly Review Pulse"
    recipient = (state.get("recipient") or "").strip()
    if not recipient:
        if transport_mode() == "inprocess":
            recipient = "self@example.com"
        else:
            return {
                "draft_id": None,
                "errors": _append_error(
                    state,
                    "Draft recipient missing. Set PULSE_DRAFT_RECIPIENT or --recipient",
                ),
            }

    # If Docs failed, still allow draft with full pulse body
    doc_url = state.get("doc_url")
    email_mode = state.get("email_mode") or "link"
    if not doc_url and email_mode == "link":
        email_mode = "full"

    email_body = build_email_body(body, doc_url=doc_url, mode=email_mode)
    try:
        draft = create_pulse_draft(to=recipient, subject=title, body=email_body)
        return {"draft_id": draft["draft_id"], "recipient": recipient}
    except (McpAuthMissingError, McpDeliveryError) as exc:
        retry_hint = ""
        if state.get("doc_url"):
            retry_hint = (
                f" Retry: python -m src.agent.run_delivery --gmail-only "
                f"--doc-url {state['doc_url']}"
            )
        return {
            "draft_id": None,
            "errors": _append_error(
                state,
                f"Gmail MCP failed: {exc}.{retry_hint}",
            ),
        }


def _route_after_validate(state: PulseGraphState) -> Literal["publish_doc", "end"]:
    if not state.get("validation_ok") or state.get("skip_delivery"):
        return "end"
    if state.get("insufficient_signal") and not state.get("allow_sparse_delivery"):
        return "end"
    return "publish_doc"


def _route_after_load(state: PulseGraphState) -> Literal["scrub", "end"]:
    if state.get("reviews"):
        return "scrub"
    return "end"


def build_graph() -> Any:
    """Compile LangGraph: load → scrub → … → validate → (publish → draft | end)."""
    graph = StateGraph(PulseGraphState)

    graph.add_node("load", node_load)
    graph.add_node("scrub", node_scrub)
    graph.add_node("theme", node_theme)
    graph.add_node("rank", node_rank)
    graph.add_node("quotes", node_quotes)
    graph.add_node("actions", node_actions)
    graph.add_node("compose", node_compose)
    graph.add_node("validate", node_validate)
    graph.add_node("publish_doc", node_publish_doc)
    graph.add_node("draft_email", node_draft_email)

    graph.add_edge(START, "load")
    graph.add_conditional_edges(
        "load",
        _route_after_load,
        {"scrub": "scrub", "end": END},
    )
    graph.add_edge("scrub", "theme")
    graph.add_edge("theme", "rank")
    graph.add_edge("rank", "quotes")
    graph.add_edge("quotes", "actions")
    graph.add_edge("actions", "compose")
    graph.add_edge("compose", "validate")
    graph.add_conditional_edges(
        "validate",
        _route_after_validate,
        {"publish_doc": "publish_doc", "end": END},
    )
    graph.add_edge("publish_doc", "draft_email")
    graph.add_edge("draft_email", END)

    return graph.compile()


def initial_state(
    *,
    weeks: int = 8,
    recipient: str | None = None,
    mode: Mode = "auto",
    limit: int | None = None,
    batch_size: int | None = None,
    max_llm_label: int | None = None,
    heuristic_min_score: int | None = None,
    reviews_path: Path | None = None,
    output_dir: Path | None = None,
    email_mode: str = "link",
    skip_delivery: bool = False,
    allow_sparse_delivery: bool = False,
    product_name: str | None = None,
) -> PulseGraphState:
    load_env()
    load_dotenv(ROOT / ".env", override=False)
    to = (recipient or os.getenv("PULSE_DRAFT_RECIPIENT", "")).strip()
    product = (
        product_name
        or os.getenv("PULSE_PRODUCT_NAME", "Groww").strip()
        or "Groww"
    )
    return {
        "weeks": max(MIN_WEEKS, min(MAX_WEEKS, weeks)),
        "recipient": to,
        "mode": mode,
        "limit": limit,
        "batch_size": batch_size,
        "max_llm_label": max_llm_label,
        "heuristic_min_score": heuristic_min_score,
        "reviews_path": str(reviews_path) if reviews_path else None,
        "output_dir": str(output_dir or OUTPUT_DIR),
        "email_mode": email_mode,
        "skip_delivery": skip_delivery,
        "allow_sparse_delivery": allow_sparse_delivery,
        "product_name": product,
        "window_widened": False,
        "insufficient_signal": False,
        "reviews": [],
        "assignments": {},
        "themes": [],
        "top_themes": [],
        "quotes": [],
        "actions": [],
        "quote_pairs": [],
        "action_pairs": [],
        "pulse": None,
        "pulse_body": "",
        "week_ending": "",
        "week_key": "",
        "run_id": "",
        "title": "",
        "validation_ok": False,
        "validation_errors": [],
        "gate_report": {},
        "doc_id": None,
        "doc_url": None,
        "draft_id": None,
        "errors": [],
        "themes_path": None,
        "pulse_path": None,
        "run_path": None,
        "trace_path": None,
    }


def summarize_result(state: PulseGraphState) -> dict[str, Any]:
    pulse = state.get("pulse")
    top = state.get("top_themes") or []
    return {
        "run_id": state.get("run_id") or state.get("week_key"),
        "week_key": state.get("week_key"),
        "week_ending": state.get("week_ending"),
        "title": state.get("title"),
        "mode": state.get("resolved_mode") or state.get("mode"),
        "weeks": state.get("weeks"),
        "review_count": len(state.get("reviews") or []),
        "top_3": [t.id for t in top],
        "word_count": pulse.word_count if pulse else None,
        "validation_ok": bool(state.get("validation_ok")),
        "validation_errors": list(state.get("validation_errors") or []),
        "themes_path": state.get("themes_path"),
        "pulse_path": state.get("pulse_path"),
        "doc_id": state.get("doc_id"),
        "doc_url": state.get("doc_url"),
        "draft_id": state.get("draft_id"),
        "recipient": state.get("recipient") or None,
        "skip_delivery": bool(state.get("skip_delivery")),
        "window_widened": bool(state.get("window_widened")),
        "insufficient_signal": bool(state.get("insufficient_signal")),
        "gates": state.get("gate_report") or {},
        "errors": list(state.get("errors") or []),
        "mcp_transport": transport_mode(),
    }


def write_run_artifact(state: PulseGraphState) -> Path:
    out_dir = Path(state.get("output_dir") or str(OUTPUT_DIR))
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_result(state)
    run_path = out_dir / "run.json"
    run_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    delivery = {
        "title": summary.get("title"),
        "week_key": summary.get("week_key"),
        "doc_id": summary.get("doc_id"),
        "doc_url": summary.get("doc_url"),
        "draft_id": summary.get("draft_id"),
        "errors": summary.get("errors") or [],
    }
    (out_dir / "delivery.json").write_text(
        json.dumps(delivery, indent=2) + "\n", encoding="utf-8"
    )
    return run_path


def run_weekly_pulse(**kwargs: Any) -> dict[str, Any]:
    """Execute the compiled graph and persist ``output/run.json``."""
    state = initial_state(**kwargs)
    app = build_graph()
    final: PulseGraphState = app.invoke(state)
    run_path = write_run_artifact(final)
    summary = summarize_result(final)
    summary["run_path"] = str(run_path)
    out_dir = Path(final.get("output_dir") or str(OUTPUT_DIR))
    trace_path = write_trace(
        {
            "summary": summary,
            "gates": final.get("gate_report") or {},
            "validation_ok": bool(final.get("validation_ok")),
            "insufficient_signal": bool(final.get("insufficient_signal")),
        },
        output_dir=out_dir / "traces",
        week_key=summary.get("week_key"),
    )
    summary["trace_path"] = str(trace_path)
    return summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Groww Weekly Review Pulse - Phase 4-5 LangGraph E2E "
            "(data -> pulse -> section 9 gates -> Docs -> Gmail draft)"
        )
    )
    p.add_argument(
        "--weeks",
        type=int,
        default=int(os.getenv("REVIEW_WINDOW_WEEKS", "8") or "8"),
        help=f"Review window in weeks ({MIN_WEEKS}–{MAX_WEEKS}; default 8)",
    )
    p.add_argument(
        "--recipient",
        "--to",
        dest="recipient",
        default=None,
        help="Gmail draft To: (default: PULSE_DRAFT_RECIPIENT)",
    )
    p.add_argument(
        "--mode",
        choices=("auto", "llm", "heuristic"),
        default="auto",
        help="Analysis mode (auto uses LLM keys when set)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Rating-stratified sample size (e.g. 200). Default: full window",
    )
    p.add_argument("--batch-size", type=int, default=None)
    p.add_argument("--max-llm-label", type=int, default=None)
    p.add_argument("--heuristic-min-score", type=int, default=None)
    p.add_argument(
        "--reviews",
        type=Path,
        default=None,
        help="Path to cleaned reviews.json or play_store.csv",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for themes.json, pulse.md, run.json (default: output/)",
    )
    p.add_argument(
        "--email-mode",
        choices=("link", "full"),
        default="link",
        help="Draft body: summary + Doc link, or full pulse",
    )
    p.add_argument(
        "--skip-delivery",
        action="store_true",
        help="Run analysis + validate only (no Docs/Gmail MCP)",
    )
    p.add_argument(
        "--allow-sparse-delivery",
        action="store_true",
        help="Publish Docs/Gmail even on an insufficient-signal week (default: skip MCP)",
    )
    p.add_argument(
        "--transport",
        choices=("http", "remote", "railway", "inprocess", "stdio", "config"),
        default=None,
        help="Override MCP_TRANSPORT for this run",
    )
    p.add_argument(
        "--print-graph",
        action="store_true",
        help="Print node order and exit",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env", override=False)
    args = build_parser().parse_args(argv)

    if args.print_graph:
        print(
            "load (widen 8→12 if sparse) -> scrub -> theme (merge ≤5) -> rank -> "
            "quotes (truncate) -> actions -> compose -> validate (§9) -> "
            "[publish_doc -> draft_email | END]"
        )
        print("Week key naming: YYYY-Www in Doc title + email subject")
        print("Insufficient signal or failed gates → END (no MCP)")
        return 0

    if args.transport:
        os.environ["MCP_TRANSPORT"] = args.transport

    weeks = max(MIN_WEEKS, min(MAX_WEEKS, args.weeks))
    print(f"Phase 4-5 LangGraph E2E | weeks={weeks} mode={args.mode}")
    print(f"MCP_TRANSPORT={transport_mode()} skip_delivery={args.skip_delivery}")

    try:
        summary = run_weekly_pulse(
            weeks=weeks,
            recipient=args.recipient,
            mode=args.mode,
            limit=args.limit,
            batch_size=args.batch_size,
            max_llm_label=args.max_llm_label,
            heuristic_min_score=args.heuristic_min_score,
            reviews_path=args.reviews,
            output_dir=args.output_dir,
            email_mode=args.email_mode,
            skip_delivery=args.skip_delivery,
            allow_sparse_delivery=args.allow_sparse_delivery,
        )
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2))

    if not summary.get("validation_ok"):
        print(
            "Validation failed — Docs/Gmail skipped. See validation_errors.",
            file=sys.stderr,
        )
        return 2

    if summary.get("errors") and not args.skip_delivery:
        # Partial delivery (e.g. Doc OK, draft failed)
        print("Completed with delivery errors (local pulse kept).", file=sys.stderr)
        return 3

    if summary.get("insufficient_signal") and not args.allow_sparse_delivery:
        print("Insufficient-signal pulse written locally; MCP skipped.", file=sys.stderr)
        return 0

    if args.skip_delivery:
        print("Phase 4-5 analysis OK (delivery skipped).")
    else:
        print(
            "Phase 4-5 E2E OK - themes + pulse + gates + Docs + Gmail draft "
            f"({summary.get('week_key')})."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
