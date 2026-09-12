"""Play Store review ingestion (Phase 1).

Loads public exports from data/raw/ (CSV or JSON), optionally fetches public
Groww reviews via google-play-scraper into data/raw/, filters to an 8–12 week
window, assigns opaque ids, scrubs PII, and writes data/cleaned/reviews.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from langdetect import DetectorFactory, LangDetectException, detect

from src.models import Review
from src.scrub import (
    assert_no_retained_pii_fields,
    review_to_clean_dict,
    scrub_reviews,
)

# Deterministic language detection
DetectorFactory.seed = 0

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
CLEANED_PATH = ROOT / "data" / "cleaned" / "reviews.json"
EXPORT_CSV_PATH = ROOT / "data" / "exports" / "play_store.csv"

DEFAULT_PACKAGE = os.getenv("APP_PACKAGE_ID", "com.nextbillion.groww")
DEFAULT_WEEKS = int(os.getenv("REVIEW_WINDOW_WEEKS", "8"))
MIN_WEEKS = 8
MAX_WEEKS = 12
# Soft floor: if fewer than this after preferred window, widen toward 12
SPARSE_THRESHOLD = 30
MIN_WORDS = 8

# English word tokens (Latin letters / digits; apostrophes in contractions)
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z]+)?")

# Indic + other non-Latin scripts commonly seen in Play reviews
_NON_LATIN_SCRIPT_RE = re.compile(
    "["
    "\u0900-\u097F"  # Devanagari (Hindi/Marathi)
    "\u0980-\u09FF"  # Bengali
    "\u0A00-\u0A7F"  # Gurmukhi
    "\u0A80-\u0AFF"  # Gujarati
    "\u0B00-\u0B7F"  # Oriya
    "\u0B80-\u0BFF"  # Tamil
    "\u0C00-\u0C7F"  # Telugu
    "\u0C80-\u0CFF"  # Kannada
    "\u0D00-\u0D7F"  # Malayalam
    "\u0600-\u06FF"  # Arabic
    "\u4E00-\u9FFF"  # CJK
    "\u3040-\u30FF"  # Japanese kana
    "\uAC00-\uD7AF"  # Hangul
    "]"
)


def opaque_id(*parts: Any) -> str:
    """Stable opaque local id (never a username)."""
    material = "|".join("" if p is None else str(p) for p in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"play-{digest}"


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        # millis or seconds since epoch
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).date()
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    # ISO / common Play Console forms
    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            pass
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    return None


def _get(row: dict[str, Any], *keys: str) -> Any:
    lower_map = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
        lk = key.lower()
        if lk in lower_map and lower_map[lk] not in (None, ""):
            return lower_map[lk]
    return None


def _coerce_rating(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None
    if rating < 1 or rating > 5:
        return None
    return rating


def _row_to_review(row: dict[str, Any], *, package_hint: str | None = None) -> Review | None:
    """Map a raw export / scraper row to Review, or None if unusable."""
    package = _get(
        row,
        "Package Name",
        "packageName",
        "package",
        "appId",
        "app_id",
    )
    if package and package_hint and str(package).strip() != package_hint:
        return None

    text = _get(row, "text", "content", "Review Text", "review_text", "body")
    title = _get(row, "title", "Review Title", "review_title")
    if text is None or str(text).strip() == "":
        # Title-only → treat title as text (edge I-13)
        if title and str(title).strip():
            text = str(title).strip()
            title = None
        else:
            return None

    review_date = _parse_date(
        _get(
            row,
            "date",
            "at",
            "Review Submit Date and Time",
            "reviewSubmitDateAndTime",
            "submitted_at",
            "created_at",
        )
    )
    if review_date is None:
        # Try millis fields
        review_date = _parse_date(
            _get(
                row,
                "Review Submit Millis Since Epoch",
                "reviewSubmitMillisSinceEpoch",
                "timestamp",
            )
        )
    if review_date is None:
        return None

    rating = _coerce_rating(
        _get(row, "rating", "score", "Star Rating", "star_rating", "stars")
    )
    language = _get(
        row,
        "language",
        "Reviewer Language",
        "reviewerLanguage",
        "lang",
    )
    if language is not None:
        language = str(language).strip() or None

    # Opaque id from content fingerprint — do not use usernames / store ids as ids
    rid = opaque_id(review_date.isoformat(), rating, str(text).strip(), title)

    try:
        return Review(
            id=rid,
            source="play",
            rating=rating,
            title=str(title).strip() if title not in (None, "") else None,
            text=str(text).strip(),
            date=review_date,
            language=language,
        )
    except ValueError:
        return None


def _load_json_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for key in ("reviews", "data", "results", "items"):
            if isinstance(data.get(key), list):
                return [r for r in data[key] if isinstance(r, dict)]
        # Single review object
        return [data]
    raise ValueError(f"unsupported JSON shape in {path}")


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    # Play Console CSVs are often UTF-16; try common encodings
    last_err: Exception | None = None
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "latin-1"):
        try:
            with path.open("r", encoding=encoding, newline="") as fh:
                sample = fh.read(4096)
                fh.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
                except csv.Error:
                    dialect = csv.excel
                reader = csv.DictReader(fh, dialect=dialect)
                return [dict(row) for row in reader]
        except Exception as exc:  # noqa: BLE001 — try next encoding
            last_err = exc
            continue
    raise ValueError(f"could not read CSV {path}: {last_err}")


def load_raw_file(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _load_json_rows(path)
    if suffix in {".csv", ".tsv"}:
        return _load_csv_rows(path)
    raise ValueError(f"unsupported export type: {path.suffix}")


def discover_raw_files(raw_dir: Path = RAW_DIR) -> list[Path]:
    if not raw_dir.exists():
        return []
    files = [
        p
        for p in sorted(raw_dir.iterdir())
        if p.is_file() and p.suffix.lower() in {".json", ".csv", ".tsv"}
    ]
    return files


def fetch_public_reviews(
    *,
    package_id: str = DEFAULT_PACKAGE,
    lang: str = "en",
    country: str = "in",
    weeks: int = MAX_WEEKS,
    out_path: Path | None = None,
    max_pages: int = 40,
    page_size: int = 200,
) -> Path:
    """Fetch public Play Store reviews (no login) into data/raw/.

    Uses the community google-play-scraper client against publicly listed
    reviews. Does not authenticate or bypass store logins.
    """
    try:
        from google_play_scraper import Sort, reviews as gp_reviews
    except ImportError as exc:
        raise SystemExit(
            "google-play-scraper is required for --fetch. "
            "Run: pip install google-play-scraper"
        ) from exc

    cutoff = date.today() - timedelta(weeks=weeks)
    collected: list[dict[str, Any]] = []
    token = None
    oldest_seen: date | None = None

    for _ in range(max_pages):
        batch, token = gp_reviews(
            package_id,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=page_size,
            continuation_token=token,
        )
        if not batch:
            break
        for item in batch:
            # Serialize datetimes for JSON dump
            row = dict(item)
            for key, value in list(row.items()):
                if isinstance(value, datetime):
                    row[key] = value.astimezone(timezone.utc).isoformat()
            collected.append(row)
            d = _parse_date(item.get("at"))
            if d is not None and (oldest_seen is None or d < oldest_seen):
                oldest_seen = d
        if oldest_seen is not None and oldest_seen < cutoff:
            break
        if token is None:
            break

    out = out_path or (
        RAW_DIR
        / f"groww_play_reviews_{date.today().isoformat()}_{lang}_{country}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "package_id": package_id,
        "source": "play",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "lang": lang,
        "country": country,
        "review_count": len(collected),
        "reviews": collected,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(collected)} raw reviews -> {out}")
    return out


def filter_window(
    reviews: list[Review],
    *,
    weeks: int,
    as_of: date | None = None,
) -> list[Review]:
    as_of = as_of or date.today()
    weeks = max(MIN_WEEKS, min(MAX_WEEKS, weeks))
    start = as_of - timedelta(weeks=weeks)
    return [r for r in reviews if start <= r.date <= as_of]


def choose_window(
    reviews: list[Review],
    *,
    preferred_weeks: int = DEFAULT_WEEKS,
    as_of: date | None = None,
    sparse_threshold: int = SPARSE_THRESHOLD,
) -> tuple[list[Review], int]:
    """Prefer preferred_weeks; if sparse and preferred < 12, widen toward 12."""
    as_of = as_of or date.today()
    preferred = max(MIN_WEEKS, min(MAX_WEEKS, preferred_weeks))
    selected = filter_window(reviews, weeks=preferred, as_of=as_of)
    used = preferred
    if len(selected) < sparse_threshold and preferred < MAX_WEEKS:
        for weeks in range(preferred + 1, MAX_WEEKS + 1):
            widened = filter_window(reviews, weeks=weeks, as_of=as_of)
            used = weeks
            selected = widened
            if len(selected) >= sparse_threshold:
                break
        print(
            f"Sparse at {preferred}w ({len(filter_window(reviews, weeks=preferred, as_of=as_of))} reviews); "
            f"widened to {used}w -> {len(selected)} reviews"
        )
    return selected, used


def count_words(text: str) -> int:
    """Count English-style word tokens in review text."""
    return len(_WORD_RE.findall(text or ""))


def is_english_text(text: str) -> bool:
    """True only when review body is English (script + detector checks)."""
    body = (text or "").strip()
    if not body:
        return False

    # Any Indic / CJK / Arabic script => not English
    if _NON_LATIN_SCRIPT_RE.search(body):
        return False

    latin_letters = len(re.findall(r"[A-Za-z]", body))
    # Unicode letters that are not A-Za-z (accents OK via latin block separately)
    other_letters = len(re.findall(r"[^\W\d_A-Za-z]", body, flags=re.UNICODE))
    if latin_letters == 0:
        return False
    # Allow light punctuation/emoji; reject if non-Latin letters are material
    if other_letters > 0 and other_letters / max(latin_letters, 1) > 0.15:
        return False

    try:
        lang = detect(body)
    except LangDetectException:
        return False
    return lang == "en"


def filter_quality(
    reviews: list[Review],
    *,
    min_words: int = MIN_WORDS,
) -> tuple[list[Review], dict[str, int]]:
    """Drop short and non-English reviews; mark kept rows as language=en."""
    kept: list[Review] = []
    dropped_short = 0
    dropped_non_english = 0

    for review in reviews:
        if count_words(review.text) < min_words:
            dropped_short += 1
            continue
        if not is_english_text(review.text):
            dropped_non_english += 1
            continue
        kept.append(review.model_copy(update={"language": "en"}))

    return kept, {
        "dropped_short_text": dropped_short,
        "dropped_non_english": dropped_non_english,
    }


def dedupe(reviews: list[Review]) -> list[Review]:
    seen: set[str] = set()
    out: list[Review] = []
    for review in reviews:
        key = opaque_id(review.date.isoformat(), review.rating, review.text)
        if key in seen:
            continue
        seen.add(key)
        # Re-bind id to content fingerprint for stability
        out.append(review.model_copy(update={"id": key}))
    return out


def ingest_rows(
    rows: Iterable[dict[str, Any]],
    *,
    package_id: str = DEFAULT_PACKAGE,
    weeks: int = DEFAULT_WEEKS,
    as_of: date | None = None,
) -> tuple[list[Review], dict[str, Any]]:
    as_of = as_of or date.today()
    parsed: list[Review] = []
    dropped_empty = 0
    dropped_date = 0
    dropped_package = 0

    for row in rows:
        package = _get(
            row,
            "Package Name",
            "packageName",
            "package",
            "appId",
            "app_id",
        )
        if package and str(package).strip() not in {package_id, ""}:
            dropped_package += 1
            continue

        text = _get(row, "text", "content", "Review Text", "review_text", "body")
        title = _get(row, "title", "Review Title", "review_title")
        if (text is None or str(text).strip() == "") and not (
            title and str(title).strip()
        ):
            dropped_empty += 1
            continue
        if _parse_date(
            _get(
                row,
                "date",
                "at",
                "Review Submit Date and Time",
                "reviewSubmitDateAndTime",
                "submitted_at",
                "created_at",
                "Review Submit Millis Since Epoch",
                "reviewSubmitMillisSinceEpoch",
                "timestamp",
            )
        ) is None:
            dropped_date += 1
            continue

        review = _row_to_review(row, package_hint=package_id if package else None)
        if review is None:
            dropped_empty += 1
            continue
        parsed.append(review)

    parsed = dedupe(parsed)
    windowed, used_weeks = choose_window(parsed, preferred_weeks=weeks, as_of=as_of)
    scrubbed = scrub_reviews(windowed)
    quality, quality_stats = filter_quality(scrubbed, min_words=MIN_WORDS)

    stats = {
        "parsed": len(parsed),
        "in_window": len(windowed),
        "after_scrub": len(scrubbed),
        "after_quality": len(quality),
        "weeks_used": used_weeks,
        "as_of": as_of.isoformat(),
        "window_start": (as_of - timedelta(weeks=used_weeks)).isoformat(),
        "dropped_empty_text": dropped_empty,
        "dropped_bad_date": dropped_date,
        "dropped_wrong_package": dropped_package,
        "dropped_short_text": quality_stats["dropped_short_text"],
        "dropped_non_english": quality_stats["dropped_non_english"],
        "min_words": MIN_WORDS,
        "language_kept": "en",
        "package_id": package_id,
    }
    return quality, stats


def ingest_from_files(
    paths: list[Path],
    *,
    package_id: str = DEFAULT_PACKAGE,
    weeks: int = DEFAULT_WEEKS,
    as_of: date | None = None,
) -> tuple[list[Review], dict[str, Any]]:
    if not paths:
        raise FileNotFoundError(
            f"No raw export files found under {RAW_DIR}. "
            "Place a CSV/JSON export there or run with --fetch."
        )
    all_rows: list[dict[str, Any]] = []
    for path in paths:
        print(f"Loading {path.name} ...")
        all_rows.extend(load_raw_file(path))

    # Abort if package field present and entirely wrong app
    packages = {
        str(_get(r, "Package Name", "packageName", "package", "appId", "app_id")).strip()
        for r in all_rows
        if _get(r, "Package Name", "packageName", "package", "appId", "app_id")
    }
    packages.discard("")
    packages.discard("None")
    if packages and package_id not in packages and not any(
        p == package_id for p in packages
    ):
        raise SystemExit(
            f"Export package(s) {sorted(packages)} do not include {package_id}; aborting."
        )

    reviews, stats = ingest_rows(
        all_rows, package_id=package_id, weeks=weeks, as_of=as_of
    )
    stats["raw_rows"] = len(all_rows)
    stats["source_files"] = [str(p.name) for p in paths]
    return reviews, stats


def write_cleaned(reviews: list[Review], path: Path = CLEANED_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = [review_to_clean_dict(r) for r in reviews]
    assert_no_retained_pii_fields(records)
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def write_export_csv(
    reviews: list[Review], path: Path = EXPORT_CSV_PATH
) -> Path:
    """Mirror cleaned reviews to data/exports/play_store.csv."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["id", "source", "rating", "title", "text", "date", "language"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for review in reviews:
            row = review_to_clean_dict(review)
            writer.writerow({key: row.get(key, "") or "" for key in fields})
    return path


def sanity_report(reviews: list[Review], stats: dict[str, Any] | None = None) -> None:
    print("\n=== Ingest sanity report ===")
    if stats:
        for key in (
            "source_files",
            "package_id",
            "raw_rows",
            "parsed",
            "weeks_used",
            "window_start",
            "as_of",
            "in_window",
            "after_scrub",
            "after_quality",
            "dropped_empty_text",
            "dropped_bad_date",
            "dropped_wrong_package",
            "dropped_short_text",
            "dropped_non_english",
            "min_words",
            "language_kept",
        ):
            if key in stats:
                print(f"  {key}: {stats[key]}")

    print(f"  cleaned_count: {len(reviews)}")
    if not reviews:
        print("  date_min/max: n/a")
        print("  rating_histogram: {}")
        print("  retained_pii_fields: none (empty set)")
        return

    dates = [r.date for r in reviews]
    print(f"  date_min: {min(dates).isoformat()}")
    print(f"  date_max: {max(dates).isoformat()}")

    hist: Counter[str] = Counter()
    for r in reviews:
        hist[str(int(r.rating)) if r.rating is not None else "null"] += 1
    print("  rating_histogram:", dict(sorted(hist.items(), key=lambda x: x[0])))

    sample_keys = set().union(*(review_to_clean_dict(r).keys() for r in reviews[:5]))
    print(f"  schema_keys: {sorted(sample_keys)}")
    print("  retained_pii_fields: none (username/email/device fields dropped)")
    print(f"  source_values: {sorted({r.source for r in reviews})}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Ingest + scrub Groww Play Store reviews (Phase 1)."
    )
    p.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch public Play reviews into data/raw/ before ingest",
    )
    p.add_argument(
        "--input",
        type=Path,
        action="append",
        default=None,
        help="Raw CSV/JSON path (repeatable). Default: all files in data/raw/",
    )
    p.add_argument(
        "--weeks",
        type=int,
        default=DEFAULT_WEEKS,
        help=f"Preferred lookback weeks ({MIN_WEEKS}–{MAX_WEEKS}, default {DEFAULT_WEEKS})",
    )
    p.add_argument(
        "--package",
        default=DEFAULT_PACKAGE,
        help=f"Play package id (default {DEFAULT_PACKAGE})",
    )
    p.add_argument(
        "--lang",
        default="en",
        help="Play storefront language for --fetch (default en)",
    )
    p.add_argument(
        "--country",
        default="in",
        help="Play storefront country for --fetch (default in)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=CLEANED_PATH,
        help=f"Cleaned JSON output (default {CLEANED_PATH})",
    )
    p.add_argument(
        "--sanity-only",
        action="store_true",
        help="Print sanity report for existing cleaned file and exit",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    weeks = max(MIN_WEEKS, min(MAX_WEEKS, args.weeks))

    if args.sanity_only:
        path = args.output
        if not path.exists():
            print(f"Missing cleaned file: {path}", file=sys.stderr)
            return 1
        data = json.loads(path.read_text(encoding="utf-8"))
        reviews = [Review.model_validate(row) for row in data]
        sanity_report(reviews)
        return 0

    if args.fetch:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        fetch_public_reviews(
            package_id=args.package,
            lang=args.lang,
            country=args.country,
            weeks=weeks,
        )

    paths = args.input or discover_raw_files()
    reviews, stats = ingest_from_files(
        paths, package_id=args.package, weeks=weeks
    )
    out = write_cleaned(reviews, args.output)
    export_path = write_export_csv(reviews)
    sanity_report(reviews, stats)
    print(f"\nWrote cleaned reviews -> {out}")
    print(f"Wrote CSV export -> {export_path}")
    print(f"Confirmation: {len(reviews)} reviews in window; zero retained PII fields.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
