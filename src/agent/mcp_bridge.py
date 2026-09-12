"""MCP client bridge for Docs + Gmail (Phase 3–4).

Connects via MCP only — no Google REST clients in this module.

Production target: [FallenOne1701/MCP-Server-1](https://github.com/FallenOne1701/MCP-Server-1)
deployed on Railway (Streamable HTTP):

  https://mcp-server-1-production.up.railway.app/mcp

Auth: ``Authorization: Bearer <MCP_API_KEY>`` (server-side Google OAuth stays on Railway).

Remote tools (do **not** call ``gmail_send_email`` in the graph happy path):

- ``google_docs_append_content`` — append pulse text to an existing Doc (``PULSE_DOC_ID``)
- ``gmail_create_draft`` — create a draft (``to`` is a string array)
- ``gmail_send_email`` — Phase 6 opt-in only (``--send-email`` / ``PULSE_EMAIL_SEND``)

Also supports:

- ``inprocess`` — local stub Docs/Gmail servers (offline smoke)
- ``stdio`` / ``config`` — servers from ``mcp.json``
"""

from __future__ import annotations

import json
import os
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_JSON = ROOT / "mcp.json"
EXAMPLE_MCP_JSON = ROOT / "mcp.json.example"

# Public HTTPS URL (Railway terminates TLS). Container PORT (e.g. 8080) is internal only.
DEFAULT_MCP_URL = "https://mcp-server-1-production.up.railway.app/mcp"
DEFAULT_HEALTH_URL = "https://mcp-server-1-production.up.railway.app/health"

_HTTP_MODES = frozenset({"http", "remote", "railway", "url"})
_CONFIG_MODES = frozenset({"stdio", "config"})

# Production MCP-Server-1 tool names
REMOTE_DOCS_TOOL = "google_docs_append_content"
REMOTE_GMAIL_TOOL = "gmail_create_draft"
# Never used by the pulse happy path (external side effect)
REMOTE_GMAIL_SEND_TOOL = "gmail_send_email"

_DOC_ID_FROM_URL = re.compile(
    r"(?:docs\.google\.com/document/d/|/d/)([a-zA-Z0-9_-]+)"
)


class McpDeliveryError(RuntimeError):
    """Delivery failed; local pulse.md should be retained."""


class McpAuthMissingError(McpDeliveryError):
    """MCP servers missing, misconfigured, or not authenticated."""


def load_env() -> None:
    load_dotenv(ROOT / ".env", override=False)


def mcp_config_path() -> Path:
    load_env()
    raw = os.getenv("MCP_CONFIG", "").strip()
    if raw:
        return Path(raw)
    if DEFAULT_MCP_JSON.exists():
        return DEFAULT_MCP_JSON
    return EXAMPLE_MCP_JSON


def transport_mode() -> str:
    """``http`` (Railway) | ``inprocess`` | ``stdio`` | ``config``."""
    load_env()
    return (os.getenv("MCP_TRANSPORT", "http") or "http").strip().lower()


def mcp_api_key() -> str:
    load_env()
    return (
        os.getenv("MCP_API_KEY", "").strip()
        or os.getenv("RAILWAY_MCP_API_KEY", "").strip()
    )


def normalize_mcp_url(url: str) -> str:
    """Ensure https + streamable-HTTP ``/mcp`` path when only a host is given.

    Do not append container PORT (e.g. 8080) to the public Railway hostname —
    TLS is on 443 via the public URL.
    """
    raw = (url or "").strip()
    if not raw:
        return DEFAULT_MCP_URL
    if raw.startswith("//"):
        raw = "https:" + raw
    if not raw.lower().startswith(("http://", "https://")):
        raw = "https://" + raw.lstrip("/")
    parsed = urlparse(raw)
    # Strip accidental :8080 on railway.app public hosts
    host = parsed.hostname or ""
    if host.endswith(".up.railway.app") and parsed.port == 8080:
        parsed = parsed._replace(netloc=host)
    path = (parsed.path or "").rstrip("/")
    if path in ("", "/"):
        parsed = parsed._replace(path="/mcp")
    elif path.endswith("/health"):
        parsed = parsed._replace(path="/mcp")
    return urlunparse(parsed)


def resolve_mcp_url() -> str:
    """Resolve remote MCP base URL from env or mcp.json shared entries."""
    load_env()
    env_url = os.getenv("MCP_URL", "").strip()
    if env_url:
        return normalize_mcp_url(env_url)

    try:
        servers = _read_mcp_json()
    except (McpAuthMissingError, McpDeliveryError):
        return DEFAULT_MCP_URL

    for key in ("pulse", "remote", "railway", "google-workspace", "docs", "gmail"):
        entry = servers.get(key)
        if isinstance(entry, dict) and entry.get("url"):
            return normalize_mcp_url(str(entry["url"]))
    return DEFAULT_MCP_URL


def resolve_health_url() -> str:
    mcp = resolve_mcp_url()
    parsed = urlparse(mcp)
    return urlunparse(parsed._replace(path="/health", params="", query="", fragment=""))


def extract_document_id(value: str) -> str:
    """Accept a bare Docs id or a full docs.google.com URL."""
    raw = (value or "").strip()
    if not raw:
        return ""
    match = _DOC_ID_FROM_URL.search(raw)
    if match:
        return match.group(1)
    # Bare id (no slashes / query)
    if re.fullmatch(r"[a-zA-Z0-9_-]+", raw):
        return raw
    return raw


def resolve_pulse_doc_id() -> str:
    """Document id for ``google_docs_append_content`` (create-doc is not on MCP-Server-1)."""
    load_env()
    for key in (
        "PULSE_DOC_ID",
        "GOOGLE_PULSE_DOC_ID",
        "MCP_PULSE_DOC_ID",
        "GOOGLE_DOCS_DOCUMENT_ID",
    ):
        found = extract_document_id(os.getenv(key, ""))
        if found:
            return found
    try:
        servers = _read_mcp_json()
        for key in ("pulse", "remote", "railway", "docs"):
            entry = servers.get(key)
            if isinstance(entry, dict):
                found = extract_document_id(
                    str(entry.get("document_id") or entry.get("doc_id") or "")
                )
                if found:
                    return found
    except (McpAuthMissingError, McpDeliveryError):
        pass
    return ""


def _read_mcp_json() -> dict[str, Any]:
    path = mcp_config_path()
    if not path.exists():
        raise McpAuthMissingError(
            f"MCP config not found at {path}. "
            "Copy mcp.json.example → mcp.json and configure the Railway pulse entry "
            "(see Docs/mcp-runbook.md)."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise McpDeliveryError(f"Invalid MCP config JSON at {path}: {exc}") from exc
    servers = data.get("mcpServers") or data.get("servers")
    if not isinstance(servers, dict) or not servers:
        raise McpAuthMissingError(
            f"No mcpServers defined in {path}. Add a pulse/remote HTTP entry."
        )
    return servers


def _python_cmd() -> str:
    return sys.executable


def _stdio_params(entry: dict[str, Any]) -> StdioServerParameters:
    command = entry.get("command") or _python_cmd()
    args = list(entry.get("args") or [])
    if command in ("python", "python3", "py"):
        command = _python_cmd()
    env = entry.get("env")
    cwd = entry.get("cwd")
    kwargs: dict[str, Any] = {"command": command, "args": args}
    if isinstance(env, dict):
        kwargs["env"] = {str(k): str(v) for k, v in env.items()}
    if cwd:
        kwargs["cwd"] = str(cwd)
    return StdioServerParameters(**kwargs)


def _server_entry(servers: dict[str, Any], role: str) -> dict[str, Any]:
    load_env()
    env_key = f"MCP_{role.upper()}_SERVER"
    override = os.getenv(env_key, "").strip()
    if override and override in servers:
        key = override
    else:
        aliases = {
            "docs": (
                "docs",
                "google_docs",
                "google-docs",
                "workspace_docs",
                "pulse",
                "remote",
                "railway",
                "google-workspace",
            ),
            "gmail": (
                "gmail",
                "google_gmail",
                "google-gmail",
                "mail",
                "pulse",
                "remote",
                "railway",
                "google-workspace",
            ),
        }
        key = None
        for candidate in aliases.get(role, (role,)):
            if candidate in servers:
                key = candidate
                break
        if key is None:
            raise McpAuthMissingError(
                f"No '{role}' MCP server in config. "
                f"Expected one of {aliases.get(role)}. "
                "Or set MCP_TRANSPORT=http and MCP_URL "
                f"({DEFAULT_MCP_URL}). See Docs/mcp-runbook.md."
            )
    entry = servers[key]
    if not isinstance(entry, dict):
        raise McpDeliveryError(f"MCP server entry '{key}' must be an object")
    return entry


def using_remote_http() -> bool:
    return transport_mode() in _HTTP_MODES


def docs_tool_name(entry: dict[str, Any] | None = None) -> str:
    load_env()
    # Stubs / stdio: prefer the server entry tool; ignore Railway env overrides.
    if not using_remote_http():
        if entry:
            for k in ("docs_tool", "tool"):
                if entry.get(k):
                    return str(entry[k])
        return "create_or_update_document"

    override = os.getenv("MCP_DOCS_CREATE_TOOL", "").strip()
    if override:
        return override
    if entry:
        for k in ("docs_tool", "tool"):
            if entry.get(k):
                return str(entry[k])
    return REMOTE_DOCS_TOOL


def gmail_tool_name(entry: dict[str, Any] | None = None) -> str:
    load_env()
    if not using_remote_http():
        if entry and entry.get("gmail_tool"):
            return str(entry["gmail_tool"])
        if entry and entry.get("tool"):
            name = str(entry["tool"])
            if name != REMOTE_DOCS_TOOL:
                return name
        return "create_draft"

    override = os.getenv("MCP_GMAIL_DRAFT_TOOL", "").strip()
    if override:
        return override
    if entry and entry.get("gmail_tool"):
        return str(entry["gmail_tool"])
    if entry and entry.get("tool"):
        name = str(entry["tool"])
        if "gmail" in name or name == "create_draft":
            return name
    return REMOTE_GMAIL_TOOL


def _result_text(result: Any) -> str:
    chunks: list[str] = []
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            chunks.append(text)
        elif isinstance(block, dict) and block.get("text"):
            chunks.append(str(block["text"]))
    return "\n".join(chunks).strip()


def _parse_tool_payload(result: Any) -> dict[str, Any]:
    """Normalize CallToolResult / structured content into a plain dict."""
    if result is None:
        return {}

    structured = getattr(result, "structured_content", None) or getattr(
        result, "structuredContent", None
    )
    payload: dict[str, Any] | None = None
    if isinstance(structured, dict):
        payload = structured
    else:
        text = _result_text(result)
        if text:
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                if getattr(result, "is_error", False) or getattr(result, "isError", False):
                    raise McpDeliveryError(text) from None
                return {"raw": text}

    if payload is None:
        if getattr(result, "is_error", False) or getattr(result, "isError", False):
            raise McpDeliveryError(_result_text(result) or "MCP tool returned an error")
        return {}

    # MCP-Server-1 failure envelope (also returned with isError=true)
    if payload.get("success") is False:
        err = payload.get("error") or {}
        code = err.get("code") if isinstance(err, dict) else None
        message = (
            (err.get("message") if isinstance(err, dict) else None)
            or str(err)
            or "MCP tool reported success=false"
        )
        if code in (
            "AUTHENTICATION_REQUIRED",
            "AUTHORIZATION_DENIED",
            "UNAUTHORIZED",
        ):
            raise McpAuthMissingError(
                f"{code}: {message} "
                "On Railway: set GOOGLE_REFRESH_TOKEN (or complete /oauth/start with "
                "ENABLE_OAUTH_SETUP=true). Local output/pulse.md was kept."
            )
        raise McpDeliveryError(f"{code or 'ERROR'}: {message}")

    if getattr(result, "is_error", False) or getattr(result, "isError", False):
        raise McpDeliveryError(_result_text(result) or "MCP tool returned an error")
    return payload


def _http_entry_for_role(role: str) -> dict[str, Any]:
    url = resolve_mcp_url()
    entry: dict[str, Any] = {
        "url": url,
        "transport": "http",
        "docs_tool": REMOTE_DOCS_TOOL,
        "gmail_tool": REMOTE_GMAIL_TOOL,
    }
    try:
        servers = _read_mcp_json()
        shared = None
        for key in ("pulse", "remote", "railway", "google-workspace", role):
            if key in servers and isinstance(servers[key], dict):
                shared = servers[key]
                break
        if shared:
            if shared.get("docs_tool"):
                entry["docs_tool"] = shared["docs_tool"]
            if shared.get("gmail_tool"):
                entry["gmail_tool"] = shared["gmail_tool"]
            if shared.get("document_id") or shared.get("doc_id"):
                entry["document_id"] = shared.get("document_id") or shared.get("doc_id")
            if shared.get("url"):
                entry["url"] = normalize_mcp_url(str(shared["url"]))
    except (McpAuthMissingError, McpDeliveryError):
        pass
    return entry


def _iter_exceptions(exc: BaseException) -> list[BaseException]:
    """Flatten ExceptionGroup / BaseExceptionGroup into leaf exceptions."""
    if isinstance(exc, BaseExceptionGroup):
        out: list[BaseException] = []
        for sub in exc.exceptions:
            out.extend(_iter_exceptions(sub))
        return out
    return [exc]


def _root_exception(exc: BaseException) -> BaseException:
    leaves = _iter_exceptions(exc)
    return leaves[0] if leaves else exc


def _map_http_connect_error(role: str, url: str, exc: BaseException) -> Exception:
    root = _root_exception(exc)
    msg = str(root).lower()
    if any(
        k in msg
        for k in (
            "401",
            "unauthorized",
            "forbidden",
            "auth",
            "credential",
            "token",
            "login",
        )
    ):
        return McpAuthMissingError(
            f"{role} MCP auth failed at {url}: {root}. "
            "Check MCP_API_KEY and Railway Google OAuth. "
            "Local output/pulse.md was kept."
        )
    if any(
        k in msg
        for k in (
            "502",
            "503",
            "504",
            "bad gateway",
            "timed out",
            "timeout",
            "failed to respond",
            "connect",
            "application failed",
        )
    ):
        return McpDeliveryError(
            f"Remote MCP unreachable at {url} ({root}). "
            "Check Railway deployment /health, then retry. "
            "Local output/pulse.md was kept. "
            "Fallback: MCP_TRANSPORT=inprocess for stub Docs/Gmail."
        )
    return McpDeliveryError(f"Failed to connect to remote MCP ({url}): {root}")


@asynccontextmanager
async def _open_http_client(
    role: str,
) -> AsyncIterator[tuple[Client, dict[str, Any]]]:
    entry = _http_entry_for_role(role)
    url = str(entry["url"])
    api_key = mcp_api_key()
    if not api_key:
        raise McpAuthMissingError(
            "MCP_API_KEY is required for Railway Streamable HTTP. "
            "Set it in .env (same value as Railway → Variables → MCP_API_KEY). "
            "Local output/pulse.md was kept. See Docs/mcp-runbook.md."
        )

    http = create_mcp_http_client(
        headers={"Authorization": f"Bearer {api_key}"}
    )
    # Separate connect failures from tool-call failures so cleanup
    # ExceptionGroups do not mask the real MCP tool error.
    async with http:
        transport = streamable_http_client(url, http_client=http)
        client_cm = Client(transport)
        try:
            client = await client_cm.__aenter__()
        except BaseException as exc:
            raise _map_http_connect_error(role, url, exc) from exc

        body_error: BaseException | None = None
        try:
            yield client, entry
        except BaseException as exc:
            body_error = exc
            raise
        finally:
            try:
                suppress = await client_cm.__aexit__(
                    None if body_error is None else type(body_error),
                    body_error,
                    body_error.__traceback__ if body_error else None,
                )
                if suppress:
                    body_error = None
            except BaseException as exit_exc:
                if body_error is None:
                    raise _map_http_connect_error(role, url, exit_exc) from exit_exc
                # Prefer the in-body tool/auth error over teardown TaskGroup noise.
                raise body_error from exit_exc


@asynccontextmanager
async def _open_client(role: str) -> AsyncIterator[tuple[Client, dict[str, Any]]]:
    mode = transport_mode()
    if mode in _HTTP_MODES:
        async with _open_http_client(role) as pair:
            yield pair
        return

    if mode == "inprocess":
        if role == "docs":
            from src.mcp_servers.docs_server import server as docs_server

            entry = {"tool": "create_or_update_document"}
            async with Client(docs_server) as client:
                yield client, entry
            return
        if role == "gmail":
            from src.mcp_servers.gmail_server import server as gmail_server

            entry = {"tool": "create_draft", "send_tool": "send_email"}
            async with Client(gmail_server) as client:
                yield client, entry
            return
        raise McpDeliveryError(f"Unknown MCP role: {role}")

    if mode not in _CONFIG_MODES:
        raise McpAuthMissingError(
            f"Unknown MCP_TRANSPORT={mode!r}. "
            "Use http | inprocess | stdio | config (see Docs/mcp-runbook.md)."
        )

    servers = _read_mcp_json()
    entry = _server_entry(servers, role)
    url = entry.get("url")
    transport = (entry.get("transport") or ("http" if url else "stdio")).lower()

    if url or transport in (
        "http",
        "sse",
        "streamable-http",
        "streamable_http",
        "remote",
    ):
        if not url:
            raise McpAuthMissingError(
                f"{role} MCP entry uses HTTP transport but has no url. "
                f"Set url in mcp.json or MCP_URL={DEFAULT_MCP_URL}."
            )
        # Force HTTP path with auth
        os.environ.setdefault("MCP_TRANSPORT", "http")
        async with _open_http_client(role) as pair:
            client, http_entry = pair
            yield client, {**http_entry, **entry}
        return

    params = _stdio_params(entry)
    try:
        async with Client(params) as client:
            yield client, entry
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if any(k in msg for k in ("auth", "unauthorized", "credential", "token", "login")):
            raise McpAuthMissingError(
                f"{role} MCP auth missing or expired: {exc}. "
                "Re-auth via your MCP host (Docs/mcp-runbook.md). "
                "Local output/pulse.md was kept."
            ) from exc
        raise McpDeliveryError(f"Failed to connect to {role} MCP server: {exc}") from exc


def _build_append_content(title: str, body: str) -> str:
    """Section header + pulse body for idempotent weekly appends."""
    heading = (title or "Groww Weekly Review Pulse").strip()
    text = (body or "").strip()
    return f"{heading}\n\n{text}\n"


async def call_docs_tool(title: str, body: str) -> dict[str, Any]:
    async with _open_client("docs") as (client, entry):
        tool = docs_tool_name(entry)
        if tool == REMOTE_GMAIL_SEND_TOOL:
            raise McpDeliveryError(
                f"Refusing to call {REMOTE_GMAIL_SEND_TOOL} for Docs publish."
            )

        if tool == REMOTE_DOCS_TOOL or tool.endswith("append_content"):
            document_id = resolve_pulse_doc_id() or extract_document_id(
                str(entry.get("document_id") or entry.get("doc_id") or "")
            )
            if not document_id:
                raise McpAuthMissingError(
                    "PULSE_DOC_ID is required for google_docs_append_content. "
                    "Create/open a Google Doc, copy its id from the URL "
                    "(docs.google.com/document/d/<ID>/edit), set PULSE_DOC_ID in .env. "
                    "MCP-Server-1 cannot create new Docs — only append. "
                    "Local output/pulse.md was kept."
                )
            args = {
                "document_id": document_id,
                "content": _build_append_content(title, body),
                "add_newline_before": True,
                "add_newline_after": True,
            }
            try:
                result = await client.call_tool(tool, args)
            except BaseException as exc:
                root = _root_exception(exc)
                if isinstance(root, (McpAuthMissingError, McpDeliveryError)):
                    raise root from exc
                raise McpDeliveryError(
                    f"Docs MCP tool '{tool}' failed: {root}"
                ) from exc
            payload = _parse_tool_payload(result)
            return _normalize_doc_payload(payload, title=title, fallback_id=document_id)

        # Stub / create_or_update style tools
        attempts = [
            {"title": title, "body": body},
            {"name": title, "content": body},
            {"document_title": title, "text": body},
        ]
        last_err: Exception | None = None
        for args in attempts:
            try:
                result = await client.call_tool(tool, args)
                payload = _parse_tool_payload(result)
                return _normalize_doc_payload(payload, title=title)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                continue
        raise McpDeliveryError(
            f"Docs MCP tool '{tool}' failed: {_root_exception(last_err) if last_err else last_err}"
        ) from last_err


async def call_gmail_tool(to: str, subject: str, body: str) -> dict[str, Any]:
    async with _open_client("gmail") as (client, entry):
        tool = gmail_tool_name(entry)
        if tool == REMOTE_GMAIL_SEND_TOOL:
            raise McpDeliveryError(
                "Refusing gmail_send_email — pulse delivery creates drafts only. "
                f"Set MCP_GMAIL_DRAFT_TOOL={REMOTE_GMAIL_TOOL}."
            )

        recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
        if not recipients:
            raise McpAuthMissingError("Gmail draft requires at least one recipient.")

        if tool == REMOTE_GMAIL_TOOL or tool.startswith("gmail_create"):
            args = {
                "to": recipients,
                "subject": subject,
                "body": body,
                "is_html": False,
            }
            try:
                result = await client.call_tool(tool, args)
            except BaseException as exc:
                root = _root_exception(exc)
                if isinstance(root, (McpAuthMissingError, McpDeliveryError)):
                    raise root from exc
                raise McpDeliveryError(
                    f"Gmail MCP tool '{tool}' failed: {root}"
                ) from exc
            payload = _parse_tool_payload(result)
            return _normalize_draft_payload(payload)

        attempts = [
            {"to": to, "subject": subject, "body": body},
            {"to": recipients, "subject": subject, "body": body},
            {"recipient": to, "subject": subject, "body": body},
            {"to": to, "subject": subject, "content": body},
            {"to_address": to, "subject": subject, "message": body},
        ]
        last_err: Exception | None = None
        for args in attempts:
            try:
                result = await client.call_tool(tool, args)
                payload = _parse_tool_payload(result)
                return _normalize_draft_payload(payload)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                continue
        raise McpDeliveryError(
            f"Gmail MCP tool '{tool}' failed: {_root_exception(last_err) if last_err else last_err}"
        ) from last_err


def gmail_send_tool_name(entry: dict[str, Any] | None = None) -> str:
    """Resolve the opt-in send tool (never used by the Phase 4 graph)."""
    load_env()
    if not using_remote_http():
        if entry and entry.get("send_tool"):
            return str(entry["send_tool"])
        return "send_email"
    override = os.getenv("MCP_GMAIL_SEND_TOOL", "").strip()
    if override:
        return override
    if entry and entry.get("send_tool"):
        return str(entry["send_tool"])
    return REMOTE_GMAIL_SEND_TOOL


async def call_gmail_send_tool(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send email via MCP. Opt-in Phase 6 path only — graph never calls this."""
    async with _open_client("gmail") as (client, entry):
        tool = gmail_send_tool_name(entry)
        recipients = [addr.strip() for addr in to.split(",") if addr.strip()]
        if not recipients:
            raise McpAuthMissingError("Gmail send requires at least one recipient.")

        if using_remote_http() or tool == REMOTE_GMAIL_SEND_TOOL or tool.startswith(
            "gmail_send"
        ):
            args = {
                "to": recipients,
                "subject": subject,
                "body": body,
                "is_html": False,
            }
            try:
                result = await client.call_tool(tool, args)
            except BaseException as exc:
                root = _root_exception(exc)
                if isinstance(root, (McpAuthMissingError, McpDeliveryError)):
                    raise root from exc
                raise McpDeliveryError(
                    f"Gmail MCP send tool '{tool}' failed: {root}"
                ) from exc
            payload = _parse_tool_payload(result)
            return _normalize_send_payload(payload)

        attempts = [
            {"to": to, "subject": subject, "body": body},
            {"to": recipients, "subject": subject, "body": body},
            {"recipient": to, "subject": subject, "body": body},
        ]
        last_err: Exception | None = None
        for args in attempts:
            try:
                result = await client.call_tool(tool, args)
                payload = _parse_tool_payload(result)
                return _normalize_send_payload(payload)
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                continue
        raise McpDeliveryError(
            f"Gmail MCP send tool '{tool}' failed: "
            f"{_root_exception(last_err) if last_err else last_err}"
        ) from last_err


def _normalize_doc_payload(
    payload: dict[str, Any],
    *,
    title: str,
    fallback_id: str | None = None,
) -> dict[str, Any]:
    doc_id = (
        payload.get("doc_id")
        or payload.get("documentId")
        or payload.get("document_id")
        or payload.get("id")
        or fallback_id
    )
    url = (
        payload.get("url")
        or payload.get("webViewLink")
        or payload.get("link")
        or payload.get("document_url")
    )
    if not doc_id and url:
        doc_id = extract_document_id(str(url)) or "unknown"
    if not doc_id:
        raise McpDeliveryError(
            f"Docs MCP response missing document_id/url. Got keys: {sorted(payload)}"
        )
    if not url:
        url = f"https://docs.google.com/document/d/{doc_id}/edit"
    return {
        "doc_id": str(doc_id),
        "url": str(url),
        "title": title,
        "appended_characters": payload.get("appended_characters"),
        "raw": payload,
    }


def _normalize_draft_payload(payload: dict[str, Any]) -> dict[str, Any]:
    draft_id = (
        payload.get("draft_id")
        or payload.get("draftId")
        or payload.get("id")
        or payload.get("message_id")
    )
    if not draft_id:
        raise McpDeliveryError(
            f"Gmail MCP response missing draft_id. Got keys: {sorted(payload)}"
        )
    return {
        "draft_id": str(draft_id),
        "message_id": payload.get("message_id"),
        "thread_id": payload.get("thread_id"),
        "raw": payload,
    }


def _normalize_send_payload(payload: dict[str, Any]) -> dict[str, Any]:
    message_id = (
        payload.get("message_id")
        or payload.get("messageId")
        or payload.get("id")
        or payload.get("thread_id")
    )
    if not message_id:
        raise McpDeliveryError(
            f"Gmail MCP send response missing message_id. Got keys: {sorted(payload)}"
        )
    return {
        "message_id": str(message_id),
        "thread_id": payload.get("thread_id"),
        "raw": payload,
    }


async def check_remote_health() -> dict[str, Any]:
    """GET /health on the Railway host (no MCP_API_KEY required)."""
    import urllib.request

    url = resolve_health_url()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {"raw": body}
            return {"ok": True, "status_code": resp.status, "url": url, **data}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": url, "error": str(exc)}


async def list_remote_tools() -> list[dict[str, Any]]:
    """List tools from the configured remote/inprocess MCP (debug helper)."""
    mode = transport_mode()
    if mode == "inprocess":
        return [
            {"name": "create_or_update_document", "server": "docs-stub"},
            {"name": "create_draft", "server": "gmail-stub"},
            {"name": "send_email", "server": "gmail-stub"},
        ]
    async with _open_http_client("docs") as (client, _entry):
        result = await client.list_tools()
        items = getattr(result, "tools", result) or []
        out: list[dict[str, Any]] = []
        for t in items:
            out.append(
                {
                    "name": getattr(t, "name", str(t)),
                    "description": (getattr(t, "description", None) or "")[:300],
                    "inputSchema": getattr(t, "inputSchema", None)
                    or getattr(t, "input_schema", None),
                }
            )
        return out
