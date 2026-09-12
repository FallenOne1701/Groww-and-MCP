"""PII scrubber for Play Store review records (Phase 1).

Drops identity fields and redacts emails / phones / device-like IDs from text.
Keeps only analysis fields: id, source, rating, title, text, date, language.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Mapping

from src.models import Review

# Fields never retained in cleaned artifacts
_DROP_KEYS = {
    "username",
    "user_name",
    "userName",
    "author",
    "author_name",
    "reviewer",
    "reviewer_name",
    "name",
    "email",
    "user_email",
    "phone",
    "phone_number",
    "device",
    "device_id",
    "deviceId",
    "advertising_id",
    "advertisingId",
    "gaid",
    "idfa",
    "user_image",
    "userImage",
    "avatar",
    "review_link",
    "reviewLink",
    "reply_content",
    "replyContent",
    "developer_reply",
    "thumbs_up_count",
    "thumbsUpCount",
}

# Analysis-only schema keys
_KEEP_KEYS = frozenset(
    {"id", "source", "rating", "title", "text", "date", "language"}
)

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
# Indian mobiles (+91 / 10-digit) and common intl patterns
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?91[\s-]*)?[6-9]\d{9}(?!\d)"
    r"|(?<!\d)\+?\d{1,3}[\s.-]?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}(?!\d)"
)
# UUID / GAID-like tokens and long hex device ids
_DEVICE_ID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
    r"|\b(?:gaid|idfa|android[_-]?id)\s*[:=]\s*\S+\b"
    r"|\b[0-9a-f]{16,}\b",
    re.IGNORECASE,
)


def redact_pii_text(value: str | None) -> str | None:
    """Redact emails, phones, and device-like IDs from free text."""
    if value is None:
        return None
    text = value
    text = _EMAIL_RE.sub("[email]", text)
    text = _PHONE_RE.sub("[phone]", text)
    text = _DEVICE_ID_RE.sub("[device_id]", text)
    cleaned = text.strip()
    return cleaned or None


def drop_pii_fields(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a shallow copy without known PII / non-analysis keys."""
    return {
        key: value
        for key, value in record.items()
        if key not in _DROP_KEYS and key in _KEEP_KEYS
    }


def scrub_review(review: Review) -> Review:
    """Return a Review with title/text redacted and only schema fields."""
    title = redact_pii_text(review.title)
    text = redact_pii_text(review.text)
    if not text:
        raise ValueError("review text empty after PII scrub")
    return Review(
        id=review.id,
        source="play",
        rating=review.rating,
        title=title,
        text=text,
        date=review.date,
        language=review.language,
    )


def scrub_reviews(reviews: list[Review]) -> list[Review]:
    """Scrub a list of reviews; drop any that lose all text after redaction."""
    cleaned: list[Review] = []
    for review in reviews:
        try:
            cleaned.append(scrub_review(review))
        except ValueError:
            continue
    return cleaned


def assert_no_retained_pii_fields(records: list[Mapping[str, Any]]) -> None:
    """Raise if any cleaned record still contains disallowed keys."""
    for record in records:
        extras = set(record.keys()) - _KEEP_KEYS
        leaked = extras & _DROP_KEYS
        if leaked:
            raise ValueError(f"cleaned record retains PII fields: {sorted(leaked)}")


def review_to_clean_dict(review: Review) -> dict[str, Any]:
    """Serialize a scrubbed Review to the analysis-only dict shape."""
    payload = review.model_dump(mode="json")
    # Ensure date is ISO date string
    if isinstance(review.date, date):
        payload["date"] = review.date.isoformat()
    return drop_pii_fields(payload)
