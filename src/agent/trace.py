"""Simple file traces for a successful (or failed) weekly run.

Optional LangSmith: set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY.
This module always writes a local JSON snapshot under output/traces/.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACE_DIR = ROOT / "output" / "traces"


def langsmith_enabled() -> bool:
    flag = (os.getenv("LANGCHAIN_TRACING_V2") or os.getenv("LANGSMITH_TRACING") or "").strip()
    return flag.lower() in {"1", "true", "yes", "on"}


def write_trace(
    payload: dict[str, Any],
    *,
    output_dir: Path | None = None,
    week_key: str | None = None,
) -> Path:
    """Persist one run snapshot (gates + graph summary). Returns the file path."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = (week_key or payload.get("week_key") or "run").replace(":", "-")
    traces = Path(output_dir or DEFAULT_TRACE_DIR)
    traces.mkdir(parents=True, exist_ok=True)
    path = traces / f"{key}_{stamp}.json"
    record = {
        "traced_at": datetime.now(timezone.utc).isoformat(),
        "langsmith_enabled": langsmith_enabled(),
        **payload,
    }
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    latest = traces / "latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path
