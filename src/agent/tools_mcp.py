"""LangChain tools wrapping Docs + Gmail MCP (Phase 3).

Public surface required by the implementation plan:

- ``create_or_update_pulse_doc(title, body) -> {doc_id, url}``
- ``create_pulse_draft(to, subject, body) -> {draft_id}``

Happy path uses MCP only — no bespoke Google OAuth/REST client here.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from src.agent.mcp_bridge import (
    McpAuthMissingError,
    McpDeliveryError,
    call_docs_tool,
    call_gmail_send_tool,
    call_gmail_tool,
    load_env,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PULSE = ROOT / "output" / "pulse.md"

__all__ = [
    "McpAuthMissingError",
    "McpDeliveryError",
    "create_or_update_pulse_doc",
    "create_pulse_draft",
    "send_pulse_email",
    "deliver_pulse",
    "get_mcp_langchain_tools",
    "DocPublishResult",
    "DraftCreateResult",
]


class DocPublishResult(BaseModel):
    doc_id: str
    url: str


class DraftCreateResult(BaseModel):
    draft_id: str


class _DocArgs(BaseModel):
    title: str = Field(..., description="Pulse document title")
    body: str = Field(..., description="Full pulse markdown/plain text")


class _DraftArgs(BaseModel):
    to: str = Field(..., description="Draft recipient (self or alias)")
    subject: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body (full pulse or summary + Doc link)")


def _run(coro: Any) -> Any:
    """Run an async MCP call from sync LangChain tool / CLI context."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    # Already inside an event loop (e.g. notebook / LangGraph async).
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def create_or_update_pulse_doc(title: str, body: str) -> dict[str, str]:
    """Publish pulse via Docs MCP. Returns ``{doc_id, url}``."""
    load_env()
    try:
        payload = _run(call_docs_tool(title=title, body=body))
    except McpAuthMissingError:
        raise
    except McpDeliveryError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise McpDeliveryError(f"Docs MCP call failed: {exc}") from exc
    return {"doc_id": payload["doc_id"], "url": payload["url"]}


def create_pulse_draft(to: str, subject: str, body: str) -> dict[str, str]:
    """Create Gmail draft via Gmail MCP. Returns ``{draft_id}``."""
    load_env()
    to = (to or "").strip() or os.getenv("PULSE_DRAFT_RECIPIENT", "").strip()
    if not to:
        raise McpAuthMissingError(
            "Draft recipient missing. Set PULSE_DRAFT_RECIPIENT in .env "
            "or pass `to=` (see Docs/mcp-runbook.md)."
        )
    try:
        payload = _run(call_gmail_tool(to=to, subject=subject, body=body))
    except McpAuthMissingError:
        raise
    except McpDeliveryError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise McpDeliveryError(f"Gmail MCP call failed: {exc}") from exc
    return {"draft_id": payload["draft_id"]}


def send_pulse_email(to: str, subject: str, body: str) -> dict[str, str]:
    """Send email via Gmail MCP. Phase 6 opt-in only — graph never calls this."""
    load_env()
    to = (to or "").strip() or os.getenv("PULSE_DRAFT_RECIPIENT", "").strip()
    if not to:
        raise McpAuthMissingError(
            "Send recipient missing. Set PULSE_DRAFT_RECIPIENT in .env "
            "or pass `to=` (see Docs/scheduler.md)."
        )
    try:
        payload = _run(call_gmail_send_tool(to=to, subject=subject, body=body))
    except McpAuthMissingError:
        raise
    except McpDeliveryError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise McpDeliveryError(f"Gmail MCP send failed: {exc}") from exc
    return {"message_id": payload["message_id"]}


def build_email_body(
    pulse_body: str,
    *,
    doc_url: str | None = None,
    mode: str = "link",
) -> str:
    """Build Gmail draft body: full pulse, or short blurb + Doc link."""
    mode = (mode or "link").strip().lower()
    if mode == "full" or not doc_url:
        return pulse_body
    return (
        "Groww Weekly Review Pulse is ready.\n\n"
        f"Doc: {doc_url}\n\n"
        "---\n"
        "Preview (first lines):\n\n"
        + "\n".join(pulse_body.strip().splitlines()[:12])
    )


def deliver_pulse(
    title: str,
    body: str,
    *,
    to: str | None = None,
    subject: str | None = None,
    email_mode: str = "link",
    gmail_only: bool = False,
    doc_url: str | None = None,
    doc_id: str | None = None,
) -> dict[str, Any]:
    """Publish Doc then create draft. Supports Gmail-only retry with Doc URL.

    On MCP auth/config failure, raises ``McpAuthMissingError`` / ``McpDeliveryError``
    after leaving local ``output/pulse.md`` untouched.
    """
    load_env()
    recipient = (to or os.getenv("PULSE_DRAFT_RECIPIENT", "")).strip()
    subj = (subject or title).strip()
    result: dict[str, Any] = {
        "title": title,
        "doc_id": doc_id,
        "doc_url": doc_url,
        "draft_id": None,
        "errors": [],
    }

    if not gmail_only:
        try:
            doc = create_or_update_pulse_doc(title=title, body=body)
            result["doc_id"] = doc["doc_id"]
            result["doc_url"] = doc["url"]
        except (McpAuthMissingError, McpDeliveryError) as exc:
            result["errors"].append(str(exc))
            raise

    email_body = build_email_body(
        body, doc_url=result.get("doc_url"), mode=email_mode
    )
    try:
        draft = create_pulse_draft(to=recipient, subject=subj, body=email_body)
        result["draft_id"] = draft["draft_id"]
    except (McpAuthMissingError, McpDeliveryError) as exc:
        # Doc OK / draft failed → caller can retry Gmail-only with doc_url.
        result["errors"].append(str(exc))
        result["retry"] = "gmail_only"
        raise McpDeliveryError(
            f"Gmail draft failed after Doc publish ({result.get('doc_url')}). "
            f"Retry with --gmail-only --doc-url. Detail: {exc}"
        ) from exc

    return result


def get_mcp_langchain_tools() -> list[StructuredTool]:
    """LangChain ``BaseTool`` wrappers for agent/graph use (Phase 4)."""

    def _doc_tool(title: str, body: str) -> str:
        out = create_or_update_pulse_doc(title=title, body=body)
        return f"doc_id={out['doc_id']} url={out['url']}"

    def _draft_tool(to: str, subject: str, body: str) -> str:
        out = create_pulse_draft(to=to, subject=subject, body=body)
        return f"draft_id={out['draft_id']}"

    return [
        StructuredTool.from_function(
            func=_doc_tool,
            name="create_or_update_pulse_doc",
            description=(
                "Create or update the weekly pulse Google Doc via Docs MCP. "
                "Args: title, body. Returns doc_id and url."
            ),
            args_schema=_DocArgs,
        ),
        StructuredTool.from_function(
            func=_draft_tool,
            name="create_pulse_draft",
            description=(
                "Create a Gmail draft via Gmail MCP (does not send). "
                "Args: to, subject, body. Returns draft_id."
            ),
            args_schema=_DraftArgs,
        ),
    ]


def default_pulse_title(pulse_path: Path | None = None) -> str:
    load_env()
    product = os.getenv("PULSE_PRODUCT_NAME", "Groww").strip() or "Groww"
    path = pulse_path or DEFAULT_PULSE
    if path.exists():
        first = path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        if first:
            return first
    return f"{product} Weekly Review Pulse"
