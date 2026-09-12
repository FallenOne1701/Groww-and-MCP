"""Shared paths for stub MCP artifact storage."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MCP_OUTPUT = ROOT / "output" / "mcp"
DOCS_DIR = MCP_OUTPUT / "docs"
DRAFTS_DIR = MCP_OUTPUT / "drafts"
SENT_DIR = MCP_OUTPUT / "sent"
REGISTRY = MCP_OUTPUT / "registry.json"


def ensure_dirs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    SENT_DIR.mkdir(parents=True, exist_ok=True)
