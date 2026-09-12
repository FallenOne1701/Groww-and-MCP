"""LangChain / LangGraph agent package (Phases 2–6).

Phase 2 entrypoint: ``python -m src.agent.run_pulse``
Phase 3 entrypoint: ``python -m src.agent.run_delivery``
Phase 4 entrypoint: ``python -m src.agent.graph``
Phase 5 entrypoint: ``python -m src.agent.run_gates``
Phase 6 entrypoint: ``python -m src.agent.weekly_job --once``
"""

from src.agent.chains import run_analysis, run_and_persist
from src.agent.tools_mcp import (
    create_or_update_pulse_doc,
    create_pulse_draft,
    get_mcp_langchain_tools,
)

__all__ = [
    "run_analysis",
    "run_and_persist",
    "build_graph",
    "run_weekly_pulse",
    "create_or_update_pulse_doc",
    "create_pulse_draft",
    "get_mcp_langchain_tools",
]


def __getattr__(name: str):
    """Lazy exports for Phase 4 graph helpers (avoid import cycle with ``-m``)."""
    if name in ("build_graph", "run_weekly_pulse"):
        from src.agent import graph as _graph

        return getattr(_graph, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
