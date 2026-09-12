"""Load Phase-1 cleaned Groww Play reviews for analysis."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from src.models import Review

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = ROOT / "data" / "cleaned" / "reviews.json"
DEFAULT_CSV = ROOT / "data" / "exports" / "play_store.csv"


def load_reviews(
    path: Path | None = None,
    *,
    prefer_json: bool = True,
) -> list[Review]:
    """Load reviews from cleaned JSON (preferred) or export CSV."""
    if path is not None:
        if path.suffix.lower() == ".csv":
            return _load_csv(path)
        return _load_json(path)

    if prefer_json and DEFAULT_JSON.exists():
        return _load_json(DEFAULT_JSON)
    if DEFAULT_CSV.exists():
        return _load_csv(DEFAULT_CSV)
    if DEFAULT_JSON.exists():
        return _load_json(DEFAULT_JSON)
    raise FileNotFoundError(
        f"No Phase 1 corpus found. Expected {DEFAULT_JSON} or {DEFAULT_CSV}."
    )


def _load_json(path: Path) -> list[Review]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return [Review.model_validate(item) for item in raw]


def _load_csv(path: Path) -> list[Review]:
    reviews: list[Review] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            reviews.append(
                Review.model_validate(
                    {
                        "id": row["id"],
                        "source": row.get("source") or "play",
                        "rating": float(row["rating"])
                        if row.get("rating") not in (None, "")
                        else None,
                        "title": row.get("title") or None,
                        "text": row["text"],
                        "date": row["date"],
                        "language": row.get("language") or None,
                    }
                )
            )
    return reviews
