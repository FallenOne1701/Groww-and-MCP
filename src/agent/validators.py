"""Architecture §9 quality gates for themes, pulse, and delivery artifacts.

Gates (must pass before MCP publish):
  window · theme_count · quotes · actions · length · privacy · source
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

from src.agent.vocab import THEME_IDS, THEME_VOCAB
from src.ingest import MAX_WEEKS, MIN_WEEKS
from src.models import PulseDraft, Review, Theme
from src.scrub import _DROP_KEYS, _KEEP_KEYS

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?91[\s-]*)?[6-9]\d{9}(?!\d)"
)
_DEVICE_ID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
    r"|\b(?:gaid|idfa|android[_-]?id)\s*[:=]\s*\S+\b",
    re.IGNORECASE,
)
_HANDLE_RE = re.compile(r"(?<!\w)@[A-Za-z][A-Za-z0-9._]{2,}\b")
_REDACTED = re.compile(r"\[(?:email|phone|device_id)\]", re.IGNORECASE)
_ELLIPSIS_SUFFIX = re.compile(r"(?:\u2026|\.\.\.)\s*$")
_WEEK_ENDING_RE = re.compile(
    r"week ending\s+(\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)
_ITEM_RE = re.compile(r"^\s*\d+\.\s+(.*)$")

GATE_NAMES = (
    "window",
    "theme_count",
    "quotes",
    "actions",
    "length",
    "privacy",
    "source",
)


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)

    def raise_if_failed(self) -> None:
        if not self.ok:
            joined = "\n".join(f"- {e}" for e in self.errors)
            raise ValueError(f"Validation failed:\n{joined}")


@dataclass
class GateCheck:
    name: str
    ok: bool
    detail: str
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": self.ok,
            "detail": self.detail,
            "errors": list(self.errors),
        }


@dataclass
class GateReport:
    ok: bool
    checks: list[GateCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    insufficient_signal: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "insufficient_signal": self.insufficient_signal,
            "warnings": list(self.warnings),
            "gates": {c.name: c.as_dict() for c in self.checks},
        }


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def normalize_quote_for_match(quote: str) -> str:
    """Strip wrapping quotes and trailing ellipsis for substring checks."""
    q = quote.strip()
    if len(q) >= 2 and q[0] in "\"'“‘" and q[-1] in "\"'”’":
        q = q[1:-1].strip()
    q = _ELLIPSIS_SUFFIX.sub("", q).strip()
    return q


def quote_is_verbatim(quote: str, reviews: list[Review]) -> bool:
    """True if quote is a substring of some review text (or allowed truncated prefix)."""
    needle = normalize_quote_for_match(quote)
    if not needle:
        return False
    for review in reviews:
        text = review.text
        if needle in text:
            return True
        if text.startswith(needle):
            return True
    return False


def scan_pii(text: str) -> list[str]:
    """Return PII kinds found in free text (ignores [email]/[phone] redaction tokens)."""
    hits: list[str] = []
    residual = _REDACTED.sub(" ", text or "")
    if _EMAIL_RE.search(residual):
        hits.append("email pattern")
    if _PHONE_RE.search(residual):
        hits.append("phone pattern")
    if _DEVICE_ID_RE.search(residual):
        hits.append("device id pattern")
    if _HANDLE_RE.search(residual):
        hits.append("username handle")
    return hits


def validate_reviews(reviews: list[Review]) -> ValidationResult:
    errors: list[str] = []
    if not reviews:
        errors.append("no reviews loaded")
    for r in reviews:
        if r.source != "play":
            errors.append(f"review {r.id}: source must be 'play' (got {r.source!r})")
        if (r.language or "").lower() != "en":
            errors.append(f"review {r.id}: language must be 'en' (got {r.language!r})")
    return ValidationResult(ok=not errors, errors=errors)


def validate_window(
    reviews: list[Review],
    *,
    weeks: int | None = None,
    as_of: date | None = None,
    slack_days: int = 2,
) -> ValidationResult:
    """Reviews must sit inside an ~8–12 week window (architecture §9)."""
    errors: list[str] = []
    if not reviews:
        return ValidationResult(ok=False, errors=["no reviews loaded"])

    dates = [r.date for r in reviews]
    newest = max(dates)
    oldest = min(dates)
    as_of = as_of or newest
    max_weeks = MAX_WEEKS
    if weeks is not None:
        max_weeks = max(MIN_WEEKS, min(MAX_WEEKS, weeks))

    oldest_allowed = as_of - timedelta(weeks=max_weeks, days=slack_days)
    newest_allowed = as_of + timedelta(days=slack_days)
    outside = [r for r in reviews if r.date < oldest_allowed or r.date > newest_allowed]
    if outside:
        errors.append(
            f"{len(outside)} review(s) outside {max_weeks}-week window "
            f"ending {as_of.isoformat()} (oldest allowed {oldest_allowed.isoformat()})"
        )

    span_days = (newest - oldest).days
    if span_days > MAX_WEEKS * 7 + slack_days:
        errors.append(
            f"date span {span_days} days exceeds {MAX_WEEKS}-week cap ({MAX_WEEKS * 7} days)"
        )
    return ValidationResult(ok=not errors, errors=errors)


def validate_themes(themes: list[Theme]) -> ValidationResult:
    errors: list[str] = []
    if len(themes) > 5:
        errors.append(f"theme count {len(themes)} exceeds cap 5")
    seen: set[str] = set()
    for t in themes:
        if t.id not in THEME_IDS:
            errors.append(f"unknown theme id {t.id!r}; must be ⊆ {sorted(THEME_IDS)}")
        if t.id in seen:
            errors.append(f"duplicate theme id {t.id!r}")
        seen.add(t.id)
        expected_label = THEME_VOCAB.get(t.id)
        if expected_label and t.label != expected_label:
            errors.append(
                f"theme {t.id}: label {t.label!r} != fixed label {expected_label!r}"
            )
    return ValidationResult(ok=not errors, errors=errors)


def validate_pulse(
    pulse: PulseDraft,
    *,
    reviews: list[Review],
    require_exact_triples: bool = True,
) -> ValidationResult:
    errors: list[str] = []
    if require_exact_triples:
        if len(pulse.themes) != 3:
            errors.append(f"expected exactly 3 themes, got {len(pulse.themes)}")
        if len(pulse.quotes) != 3:
            errors.append(f"expected exactly 3 quotes, got {len(pulse.quotes)}")
        if len(pulse.actions) != 3:
            errors.append(f"expected exactly 3 actions, got {len(pulse.actions)}")

    wc = word_count(pulse.body)
    if wc > 250:
        errors.append(f"pulse body word count {wc} exceeds 250")
    if pulse.word_count != wc:
        errors.append(
            f"pulse.word_count ({pulse.word_count}) != computed body words ({wc})"
        )

    for i, quote in enumerate(pulse.quotes, start=1):
        if not quote_is_verbatim(quote, reviews):
            errors.append(f"quote {i} is not a verbatim substring of any review text")

    for kind in scan_pii(pulse.body):
        errors.append(f"pulse body contains possible PII ({kind})")

    return ValidationResult(ok=not errors, errors=errors)


def validate_actions(
    pulse: PulseDraft,
    themes: list[Theme],
    *,
    action_pairs: list[tuple[str, str]] | None = None,
    require_exact: bool = True,
) -> ValidationResult:
    errors: list[str] = []
    if require_exact and len(pulse.actions) != 3:
        errors.append(f"expected exactly 3 actions, got {len(pulse.actions)}")
    for i, action in enumerate(pulse.actions, start=1):
        if not action.strip():
            errors.append(f"action {i} is empty")
        elif word_count(action) < 4:
            errors.append(f"action {i} is too short to be a concrete next step")
    observed = {t.id for t in themes} | set(THEME_IDS)
    if action_pairs:
        for i, (tid, _) in enumerate(action_pairs, start=1):
            if tid not in observed:
                errors.append(f"action {i} theme_id {tid!r} is not an observed/vocab theme")
    return ValidationResult(ok=not errors, errors=errors)


def validate_privacy_artifacts(
    texts: Iterable[str],
    *,
    records: list[dict[str, Any]] | None = None,
) -> ValidationResult:
    """Scan pulse/theme/delivery text and cleaned record keys for PII."""
    errors: list[str] = []
    for idx, text in enumerate(texts, start=1):
        for kind in scan_pii(text):
            errors.append(f"artifact text {idx} contains possible PII ({kind})")
    for record in records or []:
        extras = set(record.keys()) - _KEEP_KEYS
        leaked = extras & _DROP_KEYS
        if leaked:
            errors.append(f"cleaned record retains PII fields: {sorted(leaked)}")
    return ValidationResult(ok=not errors, errors=errors)


def validate_source(reviews: list[Review]) -> ValidationResult:
    """Play Store public exports only — no App Store, English-only corpus."""
    return validate_reviews(reviews)


def validate_all(
    reviews: list[Review],
    themes: list[Theme],
    pulse: PulseDraft,
    *,
    weeks: int | None = None,
    as_of: date | None = None,
    action_pairs: list[tuple[str, str]] | None = None,
    require_exact_triples: bool = True,
) -> ValidationResult:
    errors: list[str] = []
    for part in (
        validate_source(reviews),
        validate_window(reviews, weeks=weeks, as_of=as_of),
        validate_themes(themes),
        validate_pulse(
            pulse, reviews=reviews, require_exact_triples=require_exact_triples
        ),
        validate_actions(
            pulse,
            themes,
            action_pairs=action_pairs,
            require_exact=require_exact_triples,
        ),
    ):
        errors.extend(part.errors)
    return ValidationResult(ok=not errors, errors=errors)


def parse_pulse_markdown(body: str) -> PulseDraft:
    """Reconstruct a PulseDraft from the fixed pulse markdown contract."""
    themes: list[str] = []
    quotes: list[str] = []
    actions: list[str] = []
    section = ""
    for raw in body.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            if "theme" in heading:
                section = "themes"
            elif "said" in heading or "quote" in heading:
                section = "quotes"
            elif "action" in heading:
                section = "actions"
            else:
                section = ""
            continue
        match = _ITEM_RE.match(line)
        if not match or not section:
            continue
        item = match.group(1).strip()
        if section == "themes":
            label = re.sub(r"\s*\(\d+\s+reviews.*$", "", item).strip()
            themes.append(label)
        elif section == "quotes":
            quotes.append(normalize_quote_for_match(item))
        elif section == "actions":
            actions.append(item)

    ending = date.today()
    found = _WEEK_ENDING_RE.search(body)
    if found:
        ending = date.fromisoformat(found.group(1))
    return PulseDraft(
        week_ending=ending,
        themes=themes[:3],
        quotes=quotes[:3],
        actions=actions[:3],
        body=body if body.endswith("\n") else body + "\n",
        word_count=word_count(body),
    )


def themes_from_json(payload: dict[str, Any]) -> list[Theme]:
    return [Theme.model_validate(item) for item in payload.get("themes") or []]


def evaluate_gates(
    reviews: list[Review],
    themes: list[Theme],
    pulse: PulseDraft,
    *,
    weeks: int | None = None,
    as_of: date | None = None,
    action_pairs: list[tuple[str, str]] | None = None,
    extra_texts: list[str] | None = None,
    cleaned_records: list[dict[str, Any]] | None = None,
    insufficient_signal: bool = False,
    require_exact_triples: bool | None = None,
) -> GateReport:
    """Run architecture §9 gates and return a named report."""
    if require_exact_triples is None:
        require_exact_triples = not insufficient_signal

    warnings: list[str] = []
    if insufficient_signal:
        warnings.append(
            "Insufficient signal week: MCP publish is skipped; local pulse is still gated."
        )
        if require_exact_triples is False:
            warnings.append("Exact 3/3/3 relaxed because the window is below the sparse floor.")

    source = validate_source(reviews)
    window = validate_window(reviews, weeks=weeks, as_of=as_of)
    theme_res = validate_themes(themes)
    pulse_res = validate_pulse(
        pulse, reviews=reviews, require_exact_triples=require_exact_triples
    )
    action_res = validate_actions(
        pulse,
        themes,
        action_pairs=action_pairs,
        require_exact=require_exact_triples,
    )
    privacy_texts = [pulse.body, *[t.summary for t in themes], *(extra_texts or [])]
    privacy = validate_privacy_artifacts(privacy_texts, records=cleaned_records)

    theme_errors = list(theme_res.errors)
    if require_exact_triples and len(pulse.themes) != 3:
        theme_errors.append(f"pulse shows {len(pulse.themes)} themes; expected top 3")
    if len(themes) > 5:
        theme_errors.append(f"clustered theme count {len(themes)} exceeds cap 5")

    quote_errors = [
        e
        for e in pulse_res.errors
        if "quote" in e.lower() or "verbatim" in e.lower() or "expected exactly 3 quotes" in e
    ]
    length_errors = [
        e
        for e in pulse_res.errors
        if "word count" in e.lower() or "word_count" in e.lower()
    ]
    privacy_errors = list(privacy.errors) + [
        e for e in pulse_res.errors if "PII" in e
    ]

    wc = word_count(pulse.body)
    span = ""
    if reviews:
        dates = [r.date for r in reviews]
        span = f"{min(dates).isoformat()} -> {max(dates).isoformat()} ({len(reviews)} reviews)"

    checks = [
        GateCheck(
            "window",
            window.ok,
            span or "no reviews",
            list(window.errors),
        ),
        GateCheck(
            "theme_count",
            not theme_errors,
            f"{len(themes)} clustered; pulse top {len(pulse.themes)}",
            theme_errors,
        ),
        GateCheck(
            "quotes",
            not quote_errors,
            f"{len(pulse.quotes)} quotes; verbatim checked against corpus",
            quote_errors,
        ),
        GateCheck(
            "actions",
            action_res.ok,
            f"{len(pulse.actions)} actions",
            list(action_res.errors),
        ),
        GateCheck(
            "length",
            not length_errors,
            f"{wc} words (limit 250)",
            length_errors,
        ),
        GateCheck(
            "privacy",
            not privacy_errors,
            "no usernames / emails / phones / device ids in artifacts",
            privacy_errors,
        ),
        GateCheck(
            "source",
            source.ok,
            "Play Store only; language=en",
            list(source.errors),
        ),
    ]
    return GateReport(
        ok=all(c.ok for c in checks),
        checks=checks,
        warnings=warnings,
        insufficient_signal=insufficient_signal,
    )


def evaluate_artifact_dir(
    *,
    reviews: list[Review],
    output_dir: Path,
    weeks: int | None = None,
    as_of: date | None = None,
    insufficient_signal: bool = False,
) -> GateReport:
    """Evaluate gates from persisted Phase 2–4 artifacts."""
    themes_path = output_dir / "themes.json"
    pulse_path = output_dir / "pulse.md"
    if not pulse_path.exists():
        report = GateReport(ok=False, insufficient_signal=insufficient_signal)
        report.checks.append(
            GateCheck("length", False, "pulse.md missing", ["pulse.md not found"])
        )
        return report

    pulse = parse_pulse_markdown(pulse_path.read_text(encoding="utf-8"))
    themes: list[Theme] = []
    extra_texts: list[str] = []
    if themes_path.exists():
        payload = json.loads(themes_path.read_text(encoding="utf-8"))
        themes = themes_from_json(payload)
        extra_texts.extend(t.summary for t in themes if t.summary)
    cleaned_records = [r.model_dump(mode="json") for r in reviews]
    return evaluate_gates(
        reviews,
        themes,
        pulse,
        weeks=weeks,
        as_of=as_of,
        extra_texts=extra_texts,
        cleaned_records=cleaned_records,
        insufficient_signal=insufficient_signal,
    )
