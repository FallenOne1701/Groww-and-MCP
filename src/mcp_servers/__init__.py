"""Local MCP servers for Docs + Gmail delivery (Phase 3).

These servers speak the Model Context Protocol. The agent never calls Google
REST APIs directly — it only invokes MCP tools via ``src.agent.tools_mcp``.

Default servers are **stubs** that persist artifacts under ``output/mcp/`` so
smoke tests work without Google OAuth. Point ``mcp.json`` at real Docs/Gmail
MCP servers for production delivery (see ``Docs/mcp-runbook.md``).
"""
