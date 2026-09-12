"""Phase 6 weekly job: lock, schedule, idempotency, fail-closed fetch."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from src.agent.weekly_job import (
    FetchFailedError,
    JobInProgressError,
    JobLock,
    already_delivered,
    deliver_after_gates,
    doc_already_published,
    download_reviews,
    env_send_email,
    load_prior_run,
    lock_is_held,
    next_scheduled_run,
    pid_is_running,
    schedule_hour,
    schedule_weekday,
)


class LockTests(unittest.TestCase):
    def test_overlap_refuses_second_acquire(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "weekly_job.lock"
            first = JobLock(path)
            first.acquire()
            second = JobLock(path)
            with self.assertRaises(JobInProgressError):
                second.acquire()
            first.release()
            second.acquire()
            second.release()
            self.assertFalse(path.exists())

    def test_stale_lock_is_taken_over(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "weekly_job.lock"
            path.write_text(
                json.dumps(
                    {
                        "pid": 99999999,
                        "started_at": (
                            datetime.now().astimezone() - timedelta(hours=8)
                        ).isoformat(),
                    }
                ),
                encoding="utf-8",
            )
            self.assertFalse(lock_is_held(path, stale_after=3600))
            lock = JobLock(path, stale_after=3600)
            lock.acquire()
            self.assertTrue(path.exists())
            lock.release()

    def test_pid_is_running_self(self) -> None:
        self.assertTrue(pid_is_running(os.getpid()))
        self.assertFalse(pid_is_running(0))


class ScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env = patch.dict(
            os.environ,
            {
                "PULSE_SCHEDULE_WEEKDAY": "0",
                "PULSE_SCHEDULE_HOUR": "8",
                "PULSE_SCHEDULE_MINUTE": "0",
            },
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()

    def test_next_run_is_monday_0800_ist_when_after_slot(self) -> None:
        # Friday 12 Sep 2026 20:12 IST → next Monday 14 Sep 08:00 IST
        friday = datetime.fromisoformat("2026-09-12T20:12:00+05:30")
        nxt = next_scheduled_run(friday)
        self.assertEqual(nxt.weekday(), 0)
        self.assertEqual(nxt.hour, 8)
        self.assertEqual(nxt.minute, 0)
        self.assertEqual(nxt.date().isoformat(), "2026-09-14")

    def test_same_monday_before_0800_fires_today(self) -> None:
        monday_dawn = datetime.fromisoformat("2026-09-14T07:00:00+05:30")
        nxt = next_scheduled_run(monday_dawn)
        self.assertEqual(nxt.date().isoformat(), "2026-09-14")
        self.assertEqual(nxt.hour, 8)

    def test_same_monday_after_0800_rolls_forward(self) -> None:
        monday_noon = datetime.fromisoformat("2026-09-14T08:00:00+05:30")
        nxt = next_scheduled_run(monday_noon)
        self.assertEqual(nxt.date().isoformat(), "2026-09-21")

    def test_defaults_monday_hour_8(self) -> None:
        self.assertEqual(schedule_weekday(), 0)
        self.assertEqual(schedule_hour(), 8)


class IdempotencyTests(unittest.TestCase):
    def test_already_delivered_requires_both_ids(self) -> None:
        prior = {
            "week_key": "2026-W37",
            "validation_ok": True,
            "doc_id": "doc-1",
            "draft_id": "draft-1",
        }
        self.assertTrue(already_delivered(prior, "2026-W37"))
        self.assertFalse(already_delivered(prior, "2026-W38"))
        self.assertFalse(already_delivered({**prior, "draft_id": None}, "2026-W37"))

    def test_doc_only_is_gmail_retry(self) -> None:
        prior = {"week_key": "2026-W37", "doc_id": "doc-1", "draft_id": None}
        self.assertTrue(doc_already_published(prior, "2026-W37"))
        self.assertFalse(already_delivered(prior, "2026-W37"))

    def test_deliver_skips_when_week_complete(self) -> None:
        prior = {
            "week_key": "2026-W37",
            "validation_ok": True,
            "doc_id": "doc-1",
            "doc_url": "https://docs.google.com/document/d/doc-1/edit",
            "draft_id": "draft-1",
        }
        out = deliver_after_gates(
            week_key="2026-W37",
            title="Pulse",
            pulse_body="# pulse",
            recipient="ops@example.com",
            prior=prior,
            skip_delivery=False,
            send_email=False,
            email_mode="link",
        )
        self.assertTrue(out["skipped"])
        self.assertEqual(out["doc_id"], "doc-1")
        self.assertEqual(out["draft_id"], "draft-1")

    def test_deliver_skip_delivery_flag(self) -> None:
        out = deliver_after_gates(
            week_key="2026-W37",
            title="Pulse",
            pulse_body="# pulse",
            recipient="ops@example.com",
            prior={},
            skip_delivery=True,
            send_email=False,
            email_mode="link",
        )
        self.assertTrue(out["skipped"])
        self.assertIsNone(out["doc_id"])


class FetchClosedTests(unittest.TestCase):
    def test_skip_fetch_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "reviews.json"
            with patch("src.agent.weekly_job.CLEANED_PATH", missing):
                with self.assertRaises(FetchFailedError):
                    download_reviews(weeks=8, skip_fetch=True)

    def test_fetch_exception_is_fail_closed(self) -> None:
        with patch(
            "src.agent.weekly_job.fetch_public_reviews",
            side_effect=RuntimeError("network down"),
        ):
            with self.assertRaises(FetchFailedError) as ctx:
                download_reviews(weeks=8, skip_fetch=False)
        self.assertIn("stale", str(ctx.exception).lower())


class SendFlagTests(unittest.TestCase):
    def test_send_email_off_by_default(self) -> None:
        with patch.dict(os.environ, {"PULSE_EMAIL_SEND": ""}, clear=False):
            self.assertFalse(env_send_email(False))
        self.assertTrue(env_send_email(True))

    def test_send_email_env_true(self) -> None:
        with patch.dict(os.environ, {"PULSE_EMAIL_SEND": "true"}):
            self.assertTrue(env_send_email(False))


class PriorRunTests(unittest.TestCase):
    def test_load_prior_run_missing_and_corrupt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            self.assertEqual(load_prior_run(path), {})
            path.write_text("not-json", encoding="utf-8")
            self.assertEqual(load_prior_run(path), {})


if __name__ == "__main__":
    unittest.main()
