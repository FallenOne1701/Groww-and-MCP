"""Google Docs MCP server (stub by default).

Tool: ``create_or_update_document`` — create/update a pulse document.

Run (stdio):
  python -m src.mcp_servers.docs_server
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from mcp.server.mcpserver import MCPServer

from src.mcp_servers._paths import DOCS_DIR, REGISTRY, ensure_dirs

server = MCPServer(
    name="groww-docs-mcp",
    instructions=(
        "Stub Google Docs MCP for Groww Weekly Review Pulse. "
        "Creates/updates markdown docs under output/mcp/docs/ and returns "
        "doc_id + url. Replace with a real Docs MCP server for Google Docs."
    ),
)


def _slug(title: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return (base or "pulse")[:80]


def _load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        return {"docs": {}, "drafts": {}}
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"docs": {}, "drafts": {}}
    data.setdefault("docs", {})
    data.setdefault("drafts", {})
    return data


def _save_registry(data: dict[str, Any]) -> None:
    ensure_dirs()
    REGISTRY.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _doc_id_for(title: str) -> str:
    digest = hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]
    return f"doc_{digest}"


@server.tool(
    name="create_or_update_document",
    description=(
        "Create or update a Google Docs-style pulse document. "
        "Idempotent by title: same title updates the existing doc. "
        "Returns doc_id and url."
    ),
)
def create_or_update_document(title: str, body: str) -> dict[str, str]:
    """Create or update a pulse document.

    Args:
        title: Document title (used for idempotent naming).
        body: Full pulse markdown/plain text.
    """
    ensure_dirs()
    title = (title or "").strip() or "Untitled Pulse"
    body = body or ""
    doc_id = _doc_id_for(title)
    path = DOCS_DIR / f"{doc_id}.md"
    content = f"# {title}\n\n{body.lstrip()}\n"
    path.write_text(content, encoding="utf-8")

    # Stub URL mimics Docs link shape for downstream email bodies.
    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    registry = _load_registry()
    registry["docs"][doc_id] = {
        "title": title,
        "path": str(path.resolve()),
        "url": url,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_registry(registry)
    return {"doc_id": doc_id, "url": url, "path": str(path.resolve())}


def main() -> None:
    ensure_dirs()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
