from __future__ import annotations

from typing import Any

_ESCALATION_TABLE: dict[str, str] = {
    "REVISE_SPEC": "SpecWriter",
    "REVISE_DESIGN": "DomainDesigner",
    "HUMAN_REQUIRED": "__end__",
}
MAX_ESCALATIONS = 3


def escalation_router(state: dict[str, Any]) -> dict[str, Any]:
    """Deterministic escalation router for blocked pipeline states.

    Reads blockers and escalation_history from state. Routes to the
    appropriate fallback target. Detects repeated escalation loops
    after 1 repetition. Falls back to HUMAN_REQUIRED after
    MAX_ESCALATIONS (3) total escalations.

    Args:
        state: UniDevState dict containing blockers and escalation_history.

    Returns:
        Dict with next_node key and optional status/blockers updates.
    """
    history = list(state.get("escalation_history", []))
    blockers = state.get("blockers", [])

    # Repeated same-path detection (fires on first repetition)
    if len(history) >= 2 and history[-1] == history[-2]:
        return {
            "next_node": "__end__",
            "status": "repeated_escalation_detected",
            "blockers": [{
                "reason": f"Repeated escalation: {history[-1]}",
                "suggested_action": "HUMAN_REQUIRED",
            }],
            "escalation_history": history,
        }

    # Global fallback
    if len(history) >= MAX_ESCALATIONS:
        return {
            "next_node": "__end__",
            "status": "max_escalations_exceeded",
            "escalation_history": history,
        }

    action = blockers[-1].get("suggested_action", "HUMAN_REQUIRED") if blockers else "HUMAN_REQUIRED"
    target = _ESCALATION_TABLE.get(action, "__end__")
    phase = state.get("current_phase", "unknown")
    history.append(f"{phase}->{target}")
    return {
        "next_node": target,
        "escalation_history": history,
    }
