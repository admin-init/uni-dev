from __future__ import annotations

from typing import Any


def migration_stepper(state: dict[str, Any]) -> dict[str, Any]:
    """Deterministic sequential stepper for migration plans.

    Advances migration_idx by 1. LLM cannot skip or reorder.

    Args:
        state: UniDevState dict containing migration_idx and migration_plan.

    Returns:
        {"status": "next", "migration_idx": N+1} when more steps remain.
        {"status": "done", "migration_idx": N} when plan is exhausted.
    """
    plan = state.get("migration_plan", [])
    idx = state.get("migration_idx", 0)
    if not plan or idx >= len(plan):
        return {"status": "done", "migration_idx": idx}
    idx += 1
    if idx >= len(plan):
        return {"status": "done", "migration_idx": idx}
    return {"status": "next", "migration_idx": idx}
