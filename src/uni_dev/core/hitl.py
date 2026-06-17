from __future__ import annotations

import logging
from typing import Any

from langgraph.types import interrupt

logger = logging.getLogger(__name__)


def human_approval_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph interrupt: pauses execution for human decision."""
    phase = state.get("current_phase", "unknown")
    blockers = state.get("blockers", [])
    attempt_count = state.get("attempt_count", 0)

    reason_parts = []
    if blockers:
        for b in blockers:
            reason_parts.append(b.get("reason", "Unknown blocker"))
    if attempt_count >= 3:
        reason_parts.append(f"Retry limit exhausted ({attempt_count} attempts)")

    reason = "; ".join(reason_parts) if reason_parts else "Gate verification failed"

    decision = interrupt({
        "type": "human_approval",
        "reason": reason,
        "phase": phase,
        "options": ["approve", "reject", "retry"],
    })

    return {"_human_decision": decision}


def route_human_decision(state: dict[str, Any]) -> str:
    """Route based on human decision."""
    decision = state.get("_human_decision", "reject")
    if decision == "approve":
        return "approve"
    if decision == "retry":
        return "retry"
    return "reject"
