"""Dual-LLM helpers: Groq (classify) + Gemini (report)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel

from src.agent.rate_limit import GroqRateLimiter, invoke_with_rate_limit

ROOT = Path(__file__).resolve().parents[2]
Provider = Literal["groq", "gemini"]


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def groq_available() -> bool:
    load_env()
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def gemini_available() -> bool:
    load_env()
    # langchain-google-genai accepts GOOGLE_API_KEY or GEMINI_API_KEY
    return bool(
        os.getenv("GOOGLE_API_KEY", "").strip()
        or os.getenv("GEMINI_API_KEY", "").strip()
    )


def llms_available() -> bool:
    """Full LLM mode needs both: Groq for themes, Gemini for reporting."""
    return groq_available() and gemini_available()


def get_groq_chat():
    load_env()
    from langchain_groq import ChatGroq

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    return ChatGroq(model=model, temperature=0, max_retries=2)


def get_gemini_chat():
    load_env()
    from langchain_google_genai import ChatGoogleGenerativeAI

    # Prefer GEMINI_API_KEY if set; ChatGoogleGenerativeAI also reads GOOGLE_API_KEY
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv(
        "GOOGLE_API_KEY", ""
    ).strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": 0,
        "max_retries": 2,
    }
    if api_key:
        kwargs["google_api_key"] = api_key
    return ChatGoogleGenerativeAI(**kwargs)


def _structured(llm: Any, schema: type[BaseModel], *, provider: Provider):
    if provider == "groq":
        try:
            return llm.with_structured_output(
                schema, method="json_schema", strict=True
            )
        except TypeError:
            try:
                return llm.with_structured_output(schema, method="json_mode")
            except TypeError:
                return llm.with_structured_output(schema)

    # Gemini: native json_schema is the recommended default
    try:
        return llm.with_structured_output(schema, method="json_schema")
    except TypeError:
        return llm.with_structured_output(schema)


def _token_estimate(system: str, human: str, *, output_reserve: int = 400) -> int:
    return (
        GroqRateLimiter.estimate_tokens(system)
        + GroqRateLimiter.estimate_tokens(human)
        + output_reserve
    )


def _is_transient_llm_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        token in text
        for token in (
            "503",
            "unavailable",
            "high demand",
            "resource_exhausted",
            "429",
            "rate limit",
            "temporarily",
            "try again",
        )
    )


def invoke_structured(
    schema: type[BaseModel],
    system: str,
    human: str,
    *,
    provider: Provider,
):
    """Invoke structured output on Groq (rate-limited) or Gemini."""
    if provider == "groq":
        llm = get_groq_chat()
        structured = _structured(llm, schema, provider="groq")
        return invoke_with_rate_limit(
            structured,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": human},
            ],
            estimated_tokens=_token_estimate(system, human),
        )

    import time

    load_env()
    retries = max(1, int(os.getenv("GEMINI_MAX_RETRIES", "4")))
    llm = get_gemini_chat()
    structured = _structured(llm, schema, provider="gemini")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": human},
    ]
    last_exc: BaseException | None = None
    for attempt in range(retries):
        try:
            return structured.invoke(messages)
        except Exception as exc:  # noqa: BLE001 — retry transient provider faults
            last_exc = exc
            if attempt + 1 >= retries or not _is_transient_llm_error(exc):
                raise
            time.sleep(min(2 ** attempt, 8))
    assert last_exc is not None
    raise last_exc
