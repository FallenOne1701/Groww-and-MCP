"""Gmail MCP server (stub by default).

Tool: ``create_draft`` — create a Gmail draft (never auto-sends).

Run (stdio):
  python -m src.mcp_servers.gmail_server
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from mcp.server.mcpserver import MCPServer

from src.mcp_servers._paths import DRAFTS_DIR, REGISTRY, SENT_DIR, ensure_dirs

server = MCPServer(
    name="groww-gmail-mcp",
    instructions=(
        "Stub Gmail MCP for Groww Weekly Review Pulse. "
        "Creates draft artifacts under output/mcp/drafts/ and returns draft_id. "
        "Never sends email. Replace with a real Gmail MCP server for production."
    ),
)


def _load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        return {"docs": {}, "drafts": {}}
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"docs": {}, "drafts": {}}
    data.setdefault("docs", {})
    data.setdefault("drafts", {})
    data.setdefault("sent", {})
    return data


def _save_registry(data: dict[str, Any]) -> None:
    ensure_dirs()
    REGISTRY.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _draft_id_for(to: str, subject: str, body: str) -> str:
    raw = f"{to}|{subject}|{body[:200]}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"draft_{digest}"


@server.tool(
    name="create_draft",
    description=(
        "Create a Gmail draft to the given recipient. Does not send. "
        "Returns draft_id."
    ),
)
def create_draft(to: str, subject: str, body: str) -> dict[str, str]:
    """Create a Gmail draft (stub: writes local JSON artifact).

    Args:
        to: Recipient email (self or alias).
        subject: Email subject line.
        body: Full note or short summary + Docs link.
    """
    ensure_dirs()
    to = (to or "").strip()
    if not to:
        raise ValueError("draft recipient (to) is required")
    subject = (subject or "").strip() or "Groww Weekly Review Pulse"
    body = body or ""
    draft_id = _draft_id_for(to, subject, body)
    path = DRAFTS_DIR / f"{draft_id}.json"
    payload = {
        "draft_id": draft_id,
        "to": to,
        "subject": subject,
        "body": body,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    registry = _load_registry()
    registry["drafts"][draft_id] = {
        "to": to,
        "subject": subject,
        "path": str(path.resolve()),
        "created_at": payload["created_at"],
    }
    _save_registry(registry)
    return {"draft_id": draft_id, "path": str(path.resolve())}


def _message_id_for(to: str, subject: str, body: str) -> str:
    raw = f"send|{to}|{subject}|{body[:200]}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return f"msg_{digest}"


@server.tool(
    name="send_email",
    description=(
        "Send an email to the given recipient (opt-in weekly job only). "
        "Returns message_id. Not used by the assignment graph happy path."
    ),
)
def send_email(to: str, subject: str, body: str) -> dict[str, str]:
    """Stub send: write a local sent artifact (no real SMTP).

    Args:
        to: Recipient email (self or alias).
        subject: Email subject line.
        body: Full note or short summary + Docs link.
    """
    ensure_dirs()
    to = (to or "").strip()
    if not to:
        raise ValueError("send recipient (to) is required")
    subject = (subject or "").strip() or "Groww Weekly Review Pulse"
    body = body or ""
    message_id = _message_id_for(to, subject, body)
    path = SENT_DIR / f"{message_id}.json"
    payload = {
        "message_id": message_id,
        "to": to,
        "subject": subject,
        "body": body,
        "status": "sent",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    registry = _load_registry()
    registry.setdefault("sent", {})
    registry["sent"][message_id] = {
        "to": to,
        "subject": subject,
        "path": str(path.resolve()),
        "created_at": payload["created_at"],
    }
    _save_registry(registry)
    return {"message_id": message_id, "id": message_id, "path": str(path.resolve())}


def main() -> None:
    ensure_dirs()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
