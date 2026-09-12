"""Weekly unattended pulse job (Phase 6).

Strict order: download Play reviews → classify → generate report →
(only if gates pass) Google Doc append **then** Gmail.

Usage:
  python -m src.agent.weekly_job --once
  python -m src.agent.weekly_job --once --mode heuristic --transport inprocess
  python -m src.agent.weekly_job --once --skip-fetch   # debug only
  python -m src.agent.weekly_job --print-schedule
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.agent.chains import week_ending_from_reviews
from src.agent.graph import iso_week_key, run_weekly_pulse
from src.agent.loaders import load_reviews
from src.agent.mcp_bridge import McpAuthMissingError, McpDeliveryError, load_env, transport_mode
from src.agent.tools_mcp import (
    build_email_body,
    create_or_update_pulse_doc,
    create_pulse_draft,
    send_pulse_email,
)
from src.ingest import (
    CLEANED_PATH,
    DEFAULT_PACKAGE,
    MAX_WEEKS,
    MIN_WEEKS,
    discover_raw_files,
    fetch_public_reviews,
    ingest_from_files,
    sanity_report,
    write_cleaned,
    write_export_csv,
)

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
LOCK_PATH = OUTPUT_DIR / "weekly_job.lock"
LOCK_STALE_SECONDS = 4 * 3600
IST = timezone(timedelta(hours=5, minutes=30))

# Exit codes (Task Scheduler / cron surface these)
EXIT_OK = 0
EXIT_FETCH = 1
EXIT_VALIDATE = 2
EXIT_DELIVERY = 3
EXIT_LOCK = 4
EXIT_USAGE = 5


class JobInProgressError(RuntimeError):
    """A weekly job is already running (overlap lock)."""


class FetchFailedError(RuntimeError):
    """Play fetch failed — refuse to classify a stale corpus."""


# --- Lock --------------------------------------------------------------------


def pid_is_running(pid: int) -> bool:
    """True if ``pid`` still refers to a live process."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        process_query_limited = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited, False, wintypes.DWORD(pid)
        )
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        # Access denied (5) → process exists but we cannot open it
        return ctypes.windll.kernel32.GetLastError() == 5
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _lock_payload() -> dict[str, Any]:
    return {
        "pid": os.getpid(),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
    }


def _read_lock(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def lock_is_held(path: Path, *, stale_after: int = LOCK_STALE_SECONDS) -> bool:
    """True when an in-progress lock exists and is not stale."""
    if not path.exists():
        return False
    data = _read_lock(path)
    pid = data.get("pid")
    if pid is not None and pid_is_running(int(pid)):
        started_raw = data.get("started_at") or ""
        try:
            started = datetime.fromisoformat(str(started_raw).replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - started.astimezone(timezone.utc)).total_seconds()
            if age > stale_after:
                return False
        except (TypeError, ValueError):
            return True
        return True
    return False


class JobLock:
    """Exclusive ``output/weekly_job.lock`` so two jobs cannot overlap."""

    def __init__(self, path: Path | None = None, *, stale_after: int = LOCK_STALE_SECONDS):
        self.path = path or LOCK_PATH
        self.stale_after = stale_after
        self._owned = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and lock_is_held(self.path, stale_after=self.stale_after):
            prior = _read_lock(self.path)
            raise JobInProgressError(
                f"Weekly job already running (pid={prior.get('pid')}, "
                f"started={prior.get('started_at')}). Lock: {self.path}"
            )
        if self.path.exists():
            self.path.unlink(missing_ok=True)
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise JobInProgressError(
                f"Weekly job lock already exists: {self.path}"
            ) from exc
        try:
            os.write(fd, json.dumps(_lock_payload(), indent=2).encode("utf-8"))
        finally:
            os.close(fd)
        self._owned = True

    def release(self) -> None:
        if not self._owned:
            return
        try:
            current = _read_lock(self.path)
            if current.get("pid") == os.getpid():
                self.path.unlink(missing_ok=True)
        except OSError:
            pass
        self._owned = False

    def __enter__(self) -> JobLock:
        self.acquire()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()


# --- Schedule (Monday 08:00 IST) ---------------------------------------------


def schedule_weekday() -> int:
    """0 = Monday … 6 = Sunday (``PULSE_SCHEDULE_WEEKDAY``)."""
    raw = os.getenv("PULSE_SCHEDULE_WEEKDAY", "0").strip() or "0"
    try:
        value = int(raw)
    except ValueError:
        value = 0
    return max(0, min(6, value))


def schedule_hour() -> int:
    raw = os.getenv("PULSE_SCHEDULE_HOUR", "8").strip() or "8"
    try:
        value = int(raw)
    except ValueError:
        value = 8
    return max(0, min(23, value))


def schedule_minute() -> int:
    raw = os.getenv("PULSE_SCHEDULE_MINUTE", "0").strip() or "0"
    try:
        value = int(raw)
    except ValueError:
        value = 0
    return max(0, min(59, value))


def next_scheduled_run(now: datetime | None = None) -> datetime:
    """Next Monday 08:00 IST (or configured weekday/hour) as an aware datetime."""
    current = now or datetime.now(IST)
    if current.tzinfo is None:
        current = current.replace(tzinfo=IST)
    else:
        current = current.astimezone(IST)
    target = current.replace(
        hour=schedule_hour(),
        minute=schedule_minute(),
        second=0,
        microsecond=0,
    )
    days_ahead = (schedule_weekday() - current.weekday()) % 7
    if days_ahead == 0 and current >= target:
        days_ahead = 7
    return target + timedelta(days=days_ahead)


# --- Fetch -------------------------------------------------------------------


def download_reviews(
    *,
    weeks: int,
    package_id: str = DEFAULT_PACKAGE,
    lang: str = "en",
    country: str = "in",
    skip_fetch: bool = False,
) -> dict[str, Any]:
    """Refresh cleaned Play reviews. Fail closed if fetch is required and fails."""
    weeks = max(MIN_WEEKS, min(MAX_WEEKS, weeks))
    info: dict[str, Any] = {
        "skipped": bool(skip_fetch),
        "weeks": weeks,
        "package_id": package_id,
        "cleaned_path": str(CLEANED_PATH),
        "fetched_at": None,
        "review_count": 0,
        "window_start": None,
        "window_end": None,
    }

    if skip_fetch:
        if not CLEANED_PATH.exists():
            raise FetchFailedError(
                f"--skip-fetch but cleaned corpus missing: {CLEANED_PATH}"
            )
        reviews = load_reviews(CLEANED_PATH)
        info["review_count"] = len(reviews)
        if reviews:
            dates = [r.date for r in reviews]
            info["window_start"] = min(dates).isoformat()
            info["window_end"] = max(dates).isoformat()
        print(
            "WARNING: --skip-fetch is debug-only; classifying existing cleaned file "
            "(not a fresh Play download).",
            file=sys.stderr,
        )
        return info

    started = datetime.now(timezone.utc)
    try:
        raw_path = fetch_public_reviews(
            package_id=package_id,
            lang=lang,
            country=country,
            weeks=weeks,
        )
    except SystemExit as exc:
        raise FetchFailedError(
            f"Play --fetch failed; refusing to classify a stale corpus. {exc}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise FetchFailedError(
            f"Play --fetch failed; refusing to classify a stale corpus. {exc}"
        ) from exc

    info["fetched_at"] = started.isoformat()
    info["raw_path"] = str(raw_path)

    try:
        paths = discover_raw_files()
        reviews, stats = ingest_from_files(paths, package_id=package_id, weeks=weeks)
        write_cleaned(reviews)
        write_export_csv(reviews)
        sanity_report(reviews, stats)
    except Exception as exc:  # noqa: BLE001
        raise FetchFailedError(
            f"Ingest after fetch failed; refusing stale classify. {exc}"
        ) from exc

    if not CLEANED_PATH.exists():
        raise FetchFailedError(
            f"Fetch completed but {CLEANED_PATH} was not written; refusing stale classify."
        )
    mtime = datetime.fromtimestamp(CLEANED_PATH.stat().st_mtime, tz=timezone.utc)
    if mtime + timedelta(seconds=5) < started:
        raise FetchFailedError(
            f"{CLEANED_PATH} was not refreshed by this fetch (mtime {mtime.isoformat()}); "
            "refusing to classify a stale corpus."
        )

    info["review_count"] = len(reviews)
    info["weeks_used"] = stats.get("weeks_used")
    info["window_start"] = stats.get("window_start")
    info["window_end"] = stats.get("as_of")
    info["stats"] = {
        k: stats[k]
        for k in (
            "parsed",
            "in_window",
            "after_quality",
            "dropped_non_english",
            "dropped_short_text",
        )
        if k in stats
    }
    print(
        f"Download OK: {len(reviews)} cleaned EN Play reviews "
        f"({info['window_start']} -> {info['window_end']})"
    )
    return info


# --- Idempotency -------------------------------------------------------------


def load_prior_run(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def already_delivered(prior: dict[str, Any], week_key: str) -> bool:
    """Skip Doc + email when this week already has both delivery ids."""
    return (
        bool(week_key)
        and prior.get("week_key") == week_key
        and bool(prior.get("validation_ok"))
        and bool(prior.get("doc_id"))
        and bool(prior.get("draft_id"))
    )


def doc_already_published(prior: dict[str, Any], week_key: str) -> bool:
    return (
        bool(week_key)
        and prior.get("week_key") == week_key
        and bool(prior.get("doc_id"))
    )


def peek_week_key(reviews_path: Path | None = None) -> str:
    reviews = load_reviews(reviews_path)
    if not reviews:
        return ""
    return iso_week_key(week_ending_from_reviews(reviews))


# --- Delivery ----------------------------------------------------------------


def env_send_email(cli_flag: bool) -> bool:
    if cli_flag:
        return True
    raw = (os.getenv("PULSE_EMAIL_SEND", "") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def deliver_after_gates(
    *,
    week_key: str,
    title: str,
    pulse_body: str,
    recipient: str,
    prior: dict[str, Any],
    skip_delivery: bool,
    send_email: bool,
    email_mode: str,
) -> dict[str, Any]:
    """Append Doc then Gmail. Partial retry: Doc-ok / draft-missing → Gmail only."""
    result: dict[str, Any] = {
        "doc_id": None,
        "doc_url": None,
        "draft_id": None,
        "sent_id": None,
        "skipped": False,
        "gmail_only": False,
        "errors": [],
    }
    if skip_delivery:
        result["skipped"] = True
        return result

    if already_delivered(prior, week_key):
        result.update(
            {
                "doc_id": prior.get("doc_id"),
                "doc_url": prior.get("doc_url"),
                "draft_id": prior.get("draft_id"),
                "sent_id": prior.get("sent_id"),
                "skipped": True,
            }
        )
        print(
            f"Idempotent skip: {week_key} already has doc_id + draft_id "
            "(no duplicate append / mail)."
        )
        return result

    if doc_already_published(prior, week_key):
        result["doc_id"] = prior.get("doc_id")
        result["doc_url"] = prior.get("doc_url")
        result["gmail_only"] = True
        print(f"Partial retry: Doc already published for {week_key}; Gmail only.")
    else:
        try:
            doc = create_or_update_pulse_doc(title=title, body=pulse_body)
            result["doc_id"] = doc["doc_id"]
            result["doc_url"] = doc["url"]
        except (McpAuthMissingError, McpDeliveryError) as exc:
            result["errors"].append(f"Docs MCP failed (local pulse kept): {exc}")

    mode = email_mode
    if not result.get("doc_url") and mode == "link":
        mode = "full"
    email_body = build_email_body(
        pulse_body, doc_url=result.get("doc_url"), mode=mode
    )
    to = (recipient or "").strip()
    if not to:
        if transport_mode() == "inprocess":
            to = "self@example.com"
        else:
            result["errors"].append(
                "Draft recipient missing. Set PULSE_DRAFT_RECIPIENT or --recipient"
            )
            return result

    try:
        draft = create_pulse_draft(to=to, subject=title, body=email_body)
        result["draft_id"] = draft["draft_id"]
        result["recipient"] = to
    except (McpAuthMissingError, McpDeliveryError) as exc:
        hint = ""
        if result.get("doc_url"):
            hint = (
                f" Retry: python -m src.agent.run_delivery --gmail-only "
                f"--doc-url {result['doc_url']}"
            )
        result["errors"].append(f"Gmail MCP failed: {exc}.{hint}")
        return result

    if send_email:
        try:
            sent = send_pulse_email(to=to, subject=title, body=email_body)
            result["sent_id"] = sent["message_id"]
        except (McpAuthMissingError, McpDeliveryError) as exc:
            result["errors"].append(
                f"Gmail send failed after draft {result['draft_id']}: {exc}"
            )
    return result


def patch_run_artifacts(
    output_dir: Path,
    *,
    delivery: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> None:
    run_path = output_dir / "run.json"
    run = load_prior_run(run_path)
    run["doc_id"] = delivery.get("doc_id")
    run["doc_url"] = delivery.get("doc_url")
    run["draft_id"] = delivery.get("draft_id")
    run["sent_id"] = delivery.get("sent_id")
    run["delivery_skipped"] = bool(delivery.get("skipped"))
    if not delivery.get("skipped"):
        run["skip_delivery"] = False
    run["recipient"] = delivery.get("recipient") or run.get("recipient")
    errors = list(run.get("errors") or [])
    errors.extend(delivery.get("errors") or [])
    run["errors"] = errors
    run["mcp_transport"] = transport_mode()
    if extra:
        run.update(extra)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    delivery_path = output_dir / "delivery.json"
    delivery_path.write_text(
        json.dumps(
            {
                "title": run.get("title"),
                "week_key": run.get("week_key"),
                "doc_id": run.get("doc_id"),
                "doc_url": run.get("doc_url"),
                "draft_id": run.get("draft_id"),
                "sent_id": run.get("sent_id"),
                "delivery_skipped": run.get("delivery_skipped"),
                "errors": errors,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_job_artifact(output_dir: Path, payload: dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "weekly_job.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


# --- Orchestration -----------------------------------------------------------


def run_weekly_job(
    *,
    weeks: int = 8,
    recipient: str | None = None,
    mode: str = "heuristic",
    skip_fetch: bool = False,
    skip_delivery: bool = False,
    send_email: bool = False,
    email_mode: str = "link",
    transport: str | None = None,
    output_dir: Path | None = None,
    package_id: str | None = None,
    lang: str = "en",
    country: str = "in",
    allow_sparse_delivery: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Download → classify → pulse → Doc + Gmail. Used by ``--once`` and the waiter."""
    load_env()
    load_dotenv(ROOT / ".env", override=False)
    if transport:
        os.environ["MCP_TRANSPORT"] = transport

    out_dir = output_dir or OUTPUT_DIR
    started = datetime.now(timezone.utc)
    job: dict[str, Any] = {
        "started_at": started.isoformat(),
        "sequence": "fetch -> classify -> pulse -> Docs append -> Gmail",
        "mode": mode,
        "weeks": weeks,
        "skip_fetch": skip_fetch,
        "skip_delivery": skip_delivery,
        "send_email": send_email,
        "mcp_transport": transport_mode(),
    }

    fetch_info = download_reviews(
        weeks=weeks,
        package_id=package_id or DEFAULT_PACKAGE,
        lang=lang,
        country=country,
        skip_fetch=skip_fetch,
    )
    job["fetch"] = fetch_info

    prior = load_prior_run(out_dir / "run.json")
    week_key_hint = peek_week_key()
    job["week_key"] = week_key_hint

    to = (recipient or os.getenv("PULSE_DRAFT_RECIPIENT", "")).strip()
    summary = run_weekly_pulse(
        weeks=weeks,
        recipient=to or None,
        mode=mode,  # type: ignore[arg-type]
        limit=limit,
        output_dir=out_dir,
        email_mode=email_mode,
        skip_delivery=True,
        allow_sparse_delivery=allow_sparse_delivery,
    )
    job["classify"] = {
        "week_key": summary.get("week_key"),
        "review_count": summary.get("review_count"),
        "top_3": summary.get("top_3"),
        "word_count": summary.get("word_count"),
        "validation_ok": summary.get("validation_ok"),
        "insufficient_signal": summary.get("insufficient_signal"),
        "window_widened": summary.get("window_widened"),
    }
    week_key = str(summary.get("week_key") or week_key_hint or "")
    job["week_key"] = week_key

    if not summary.get("validation_ok"):
        job["exit_reason"] = "validation_failed"
        job["validation_errors"] = summary.get("validation_errors") or []
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_job_artifact(out_dir, job)
        return {
            "ok": False,
            "exit_code": EXIT_VALIDATE,
            "summary": summary,
            "job": job,
        }

    if summary.get("insufficient_signal") and not allow_sparse_delivery:
        job["exit_reason"] = "insufficient_signal_skip_mcp"
        job["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_job_artifact(out_dir, job)
        return {
            "ok": True,
            "exit_code": EXIT_OK,
            "summary": summary,
            "job": job,
        }

    pulse_path = Path(summary["pulse_path"]) if summary.get("pulse_path") else out_dir / "pulse.md"
    pulse_body = pulse_path.read_text(encoding="utf-8") if pulse_path.exists() else ""
    title = str(summary.get("title") or f"Groww Weekly Review Pulse - {week_key}")

    delivery = deliver_after_gates(
        week_key=week_key,
        title=title,
        pulse_body=pulse_body,
        recipient=to,
        prior=prior,
        skip_delivery=skip_delivery,
        send_email=send_email,
        email_mode=email_mode,
    )
    job["delivery"] = {
        "doc_id": delivery.get("doc_id"),
        "doc_url": delivery.get("doc_url"),
        "draft_id": delivery.get("draft_id"),
        "sent_id": delivery.get("sent_id"),
        "skipped": delivery.get("skipped"),
        "gmail_only": delivery.get("gmail_only"),
        "errors": delivery.get("errors") or [],
    }
    patch_run_artifacts(out_dir, delivery=delivery)
    # Re-read so callers see patched ids
    summary = load_prior_run(out_dir / "run.json") or summary
    job["finished_at"] = datetime.now(timezone.utc).isoformat()

    if delivery.get("errors") and not skip_delivery:
        job["exit_reason"] = "delivery_failed"
        write_job_artifact(out_dir, job)
        return {
            "ok": False,
            "exit_code": EXIT_DELIVERY,
            "summary": summary,
            "job": job,
        }

    job["exit_reason"] = "ok" if not delivery.get("skipped") else "idempotent_skip"
    write_job_artifact(out_dir, job)
    return {
        "ok": True,
        "exit_code": EXIT_OK,
        "summary": summary,
        "job": job,
    }


# --- CLI ---------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Phase 6 weekly job: fetch Play reviews → classify → pulse → "
            "Docs append + Gmail (draft by default)."
        )
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run the pipeline now and exit (Task Scheduler / cron entrypoint)",
    )
    p.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Debug only: classify existing cleaned file (do not use on the schedule)",
    )
    p.add_argument(
        "--skip-delivery",
        action="store_true",
        help="Classify + gates only (no Docs / Gmail)",
    )
    p.add_argument(
        "--send-email",
        action="store_true",
        help="Opt-in inbox send via gmail_send_email (default: draft only)",
    )
    p.add_argument(
        "--mode",
        choices=("auto", "llm", "heuristic"),
        default=os.getenv("PULSE_WEEKLY_MODE", "heuristic") or "heuristic",
        help="Analysis mode (default heuristic — safer for unattended quota)",
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
        help="Gmail To: (default: PULSE_DRAFT_RECIPIENT)",
    )
    p.add_argument(
        "--transport",
        choices=("http", "remote", "railway", "inprocess", "stdio", "config"),
        default=None,
        help="Override MCP_TRANSPORT for this run",
    )
    p.add_argument(
        "--email-mode",
        choices=("link", "full"),
        default="link",
        help="Email body: summary + Doc link, or full pulse",
    )
    p.add_argument(
        "--allow-sparse-delivery",
        action="store_true",
        help="Publish Docs/Gmail even on an insufficient-signal week",
    )
    p.add_argument("--limit", type=int, default=None, help="Stratified sample size")
    p.add_argument("--package", default=None, help="Play package id")
    p.add_argument("--lang", default="en")
    p.add_argument("--country", default="in")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for run/pulse/job artifacts (default: output/)",
    )
    p.add_argument(
        "--print-schedule",
        action="store_true",
        help="Print next Monday 08:00 IST fire time and exit",
    )
    return p


def _wait_until(target: datetime) -> None:
    print(f"Waiting until {target.isoformat()} (IST weekly slot)...")
    while True:
        now = datetime.now(IST)
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(remaining, 60.0))


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env", override=False)
    args = build_parser().parse_args(argv)

    if args.print_schedule:
        nxt = next_scheduled_run()
        print(
            f"Next run: {nxt.isoformat()} "
            f"(weekday={schedule_weekday()} hour={schedule_hour():02d}:"
            f"{schedule_minute():02d} IST)"
        )
        print("Entrypoint: python -m src.agent.weekly_job --once")
        return EXIT_OK

    if not args.once:
        nxt = next_scheduled_run()
        print(
            "No --once: sleeping until the next scheduled slot "
            f"({nxt.isoformat()} IST), then running once."
        )
        print("Task Scheduler should call this module with --once instead.")
        try:
            _wait_until(nxt)
        except KeyboardInterrupt:
            print("Interrupted while waiting.", file=sys.stderr)
            return EXIT_USAGE

    weeks = max(MIN_WEEKS, min(MAX_WEEKS, args.weeks))
    send = env_send_email(args.send_email)
    print(
        f"Phase 6 weekly job | once weeks={weeks} mode={args.mode} "
        f"skip_fetch={args.skip_fetch} skip_delivery={args.skip_delivery} "
        f"send_email={send}"
    )
    print(f"MCP_TRANSPORT={args.transport or transport_mode()}")

    lock = JobLock()
    try:
        lock.acquire()
    except JobInProgressError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_LOCK

    try:
        result = run_weekly_job(
            weeks=weeks,
            recipient=args.recipient,
            mode=args.mode,
            skip_fetch=args.skip_fetch,
            skip_delivery=args.skip_delivery,
            send_email=send,
            email_mode=args.email_mode,
            transport=args.transport,
            output_dir=args.output_dir,
            package_id=args.package,
            lang=args.lang,
            country=args.country,
            allow_sparse_delivery=args.allow_sparse_delivery,
            limit=args.limit,
        )
    except FetchFailedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        write_job_artifact(
            args.output_dir or OUTPUT_DIR,
            {
                "exit_reason": "fetch_failed",
                "error": str(exc),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return EXIT_FETCH
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_FETCH
    finally:
        lock.release()

    job = result.get("job") or {}
    summary = result.get("summary") or {}
    print(json.dumps({"job": job, "run": summary}, indent=2, default=str))

    code = int(result.get("exit_code") or EXIT_OK)
    if code == EXIT_VALIDATE:
        print("Validation failed - Docs/Gmail skipped.", file=sys.stderr)
    elif code == EXIT_DELIVERY:
        print("Delivery failed (local pulse kept).", file=sys.stderr)
    elif job.get("exit_reason") == "insufficient_signal_skip_mcp":
        print("Insufficient-signal pulse written locally; MCP skipped.")
    elif job.get("exit_reason") == "idempotent_skip":
        print(f"Phase 6 OK - {job.get('week_key')} already delivered (idempotent skip).")
    elif args.skip_delivery:
        print("Phase 6 analysis OK (delivery skipped).")
    else:
        print(
            f"Phase 6 OK - fetch -> classify -> pulse -> Doc + Gmail "
            f"({job.get('week_key')})."
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
