"""Groq free-tier rate limiting helpers (RPM / TPM budgets)."""

from __future__ import annotations

import os
import threading
import time
from collections import deque


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


class GroqRateLimiter:
    """Throttle LLM calls to stay under Groq request/token budgets.

    Defaults match the free-tier style limits:
      30 RPM · 8K TPM · (daily caps documented but not hard-enforced here)
    """

    def __init__(
        self,
        *,
        rpm: int | None = None,
        tpm: int | None = None,
        safety_factor: float = 0.85,
    ) -> None:
        self.rpm = rpm if rpm is not None else _env_int("GROQ_RPM", 30)
        self.tpm = tpm if tpm is not None else _env_int("GROQ_TPM", 8000)
        self.safety_factor = safety_factor
        self._lock = threading.Lock()
        self._request_times: deque[float] = deque()
        self._token_events: deque[tuple[float, int]] = deque()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Cheap token estimate (~4 chars/token) with a small floor."""
        if not text:
            return 0
        return max(1, (len(text) + 3) // 4)

    def _prune(self, now: float) -> None:
        cutoff = now - 60.0
        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()
        while self._token_events and self._token_events[0][0] < cutoff:
            self._token_events.popleft()

    def _tokens_used(self) -> int:
        return sum(n for _, n in self._token_events)

    def wait(self, estimated_tokens: int) -> None:
        """Block until a call with ``estimated_tokens`` fits under RPM/TPM."""
        budget_tokens = int(self.tpm * self.safety_factor)
        budget_rpm = max(1, int(self.rpm * self.safety_factor))
        estimated_tokens = max(1, estimated_tokens)

        while True:
            with self._lock:
                now = time.monotonic()
                self._prune(now)
                wait_s = 0.0

                if len(self._request_times) >= budget_rpm:
                    wait_s = max(wait_s, 60.0 - (now - self._request_times[0]) + 0.05)

                used = self._tokens_used()
                if used + estimated_tokens > budget_tokens:
                    if self._token_events:
                        wait_s = max(
                            wait_s,
                            60.0 - (now - self._token_events[0][0]) + 0.05,
                        )
                    else:
                        wait_s = max(wait_s, 1.0)

                # Also respect minimum spacing from RPM (30 → 2s)
                min_gap = 60.0 / max(self.rpm, 1)
                if self._request_times:
                    wait_s = max(wait_s, min_gap - (now - self._request_times[-1]))

                if wait_s <= 0:
                    self._request_times.append(now)
                    self._token_events.append((now, estimated_tokens))
                    return

            time.sleep(min(wait_s, 5.0))


# Process-wide limiter shared by all Groq LLM calls in a run
_LIMITER = GroqRateLimiter()


def get_rate_limiter() -> GroqRateLimiter:
    return _LIMITER


def invoke_with_rate_limit(structured_llm, messages: list, *, estimated_tokens: int):
    """Wait for budget, then invoke a LangChain runnable."""
    get_rate_limiter().wait(estimated_tokens)
    return structured_llm.invoke(messages)
