"""CLI: Phase-3 MCP delivery smoke test (Docs + Gmail draft).

Usage:
  python -m src.agent.run_delivery
  python -m src.agent.run_delivery --pulse output/pulse.md
  python -m src.agent.run_delivery --gmail-only --doc-url URL
  python -m src.agent.run_delivery --list-tools
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.agent.mcp_bridge import (
    McpAuthMissingError,
    McpDeliveryError,
    check_remote_health,
    list_remote_tools,
    load_env,
    resolve_mcp_url,
    resolve_pulse_doc_id,
    transport_mode,
)
from src.agent.tools_mcp import (
    DEFAULT_PULSE,
    create_or_update_pulse_doc,
    create_pulse_draft,
    default_pulse_title,
    deliver_pulse,
    get_mcp_langchain_tools,
)

ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Groww Weekly Review Pulse — Phase 3 MCP delivery smoke test"
    )
    p.add_argument(
        "--pulse",
        type=Path,
        default=DEFAULT_PULSE,
        help="Path to pulse markdown (default: output/pulse.md)",
    )
    p.add_argument("--title", default=None, help="Doc title / email subject override")
    p.add_argument(
        "--to",
        default=None,
        help="Gmail draft recipient (default: PULSE_DRAFT_RECIPIENT)",
    )
    p.add_argument(
        "--email-mode",
        choices=("link", "full"),
        default="link",
        help="Draft body: short summary + Doc link, or full pulse",
    )
    p.add_argument(
        "--gmail-only",
        action="store_true",
        help="Skip Docs; retry Gmail draft using --doc-url",
    )
    p.add_argument("--doc-url", default=None, help="Existing Doc URL for gmail-only retry")
    p.add_argument("--doc-id", default=None, help="Existing Doc id for gmail-only retry")
    p.add_argument(
        "--docs-only",
        action="store_true",
        help="Create/update Doc only (no Gmail draft)",
    )
    p.add_argument(
        "--list-tools",
        action="store_true",
        help="Print LangChain MCP tool wrappers and exit",
    )
    p.add_argument(
        "--list-remote-tools",
        action="store_true",
        help="Connect to MCP and list server tool names (needs MCP_API_KEY for http)",
    )
    p.add_argument(
        "--health",
        action="store_true",
        help="GET Railway /health and exit",
    )
    p.add_argument(
        "--transport",
        choices=("http", "remote", "railway", "inprocess", "stdio", "config"),
        default=None,
        help="Override MCP_TRANSPORT for this run",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_env()
    load_dotenv(ROOT / ".env", override=False)

    if args.transport:
        os.environ["MCP_TRANSPORT"] = args.transport

    if args.list_tools:
        tools = get_mcp_langchain_tools()
        for t in tools:
            print(f"- {t.name}: {t.description.splitlines()[0]}")
        print(f"MCP_TRANSPORT={transport_mode()}")
        print(f"MCP_URL={resolve_mcp_url()}")
        print(f"PULSE_DOC_ID={resolve_pulse_doc_id() or '(not set)'}")
        return 0

    if args.health:
        import asyncio

        report = asyncio.run(check_remote_health())
        print(json.dumps(report, indent=2))
        return 0 if report.get("ok") else 1

    if args.list_remote_tools:
        import asyncio

        try:
            tools = asyncio.run(list_remote_tools())
        except (McpAuthMissingError, McpDeliveryError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        for t in tools:
            print(f"- {t.get('name')}: {(t.get('description') or '')[:120]}")
        print(f"MCP_TRANSPORT={transport_mode()} MCP_URL={resolve_mcp_url()}")
        return 0

    pulse_path = args.pulse
    if not pulse_path.exists():
        print(
            f"ERROR: pulse file not found: {pulse_path}\n"
            "Run Phase 2 first: python -m src.agent.run_pulse --mode heuristic",
            file=sys.stderr,
        )
        return 1

    body = pulse_path.read_text(encoding="utf-8")
    title = args.title or default_pulse_title(pulse_path)
    recipient = (args.to or os.getenv("PULSE_DRAFT_RECIPIENT", "")).strip()
    if not recipient and not args.docs_only:
        # Stub-friendly default for local smoke tests
        if transport_mode() == "inprocess":
            recipient = "self@example.com"
            print(f"NOTE: using stub recipient {recipient} (set PULSE_DRAFT_RECIPIENT)")
        else:
            print(
                "ERROR: set PULSE_DRAFT_RECIPIENT or pass --to "
                "(see Docs/mcp-runbook.md)",
                file=sys.stderr,
            )
            return 1

    print(f"MCP_TRANSPORT={transport_mode()}")
    print(f"Pulse: {pulse_path} ({len(body.split())} words)")
    print(f"Title: {title}")

    try:
        if args.docs_only:
            doc = create_or_update_pulse_doc(title=title, body=body)
            summary = {"doc_id": doc["doc_id"], "doc_url": doc["url"], "draft_id": None}
        elif args.gmail_only:
            if not args.doc_url and not body:
                print("ERROR: --gmail-only needs --doc-url or pulse body", file=sys.stderr)
                return 1
            from src.agent.tools_mcp import build_email_body

            email_body = build_email_body(
                body, doc_url=args.doc_url, mode=args.email_mode
            )
            draft = create_pulse_draft(to=recipient, subject=title, body=email_body)
            summary = {
                "doc_id": args.doc_id,
                "doc_url": args.doc_url,
                "draft_id": draft["draft_id"],
            }
        else:
            summary = deliver_pulse(
                title=title,
                body=body,
                to=recipient,
                subject=title,
                email_mode=args.email_mode,
                gmail_only=False,
            )
    except McpAuthMissingError as exc:
        print(
            f"ERROR (MCP auth/config): {exc}\n"
            "Local pulse kept at output/pulse.md. See Docs/mcp-runbook.md.",
            file=sys.stderr,
        )
        return 2
    except McpDeliveryError as exc:
        print(f"ERROR (MCP delivery): {exc}", file=sys.stderr)
        return 1

    out_path = ROOT / "output" / "delivery.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {out_path}")
    print("Phase 3 smoke test OK (MCP Docs + Gmail draft).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
