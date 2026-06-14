from __future__ import annotations

from typing import Any

MAX_ATTEMPTS = 3


def retry_controller(state: dict[str, Any]) -> dict[str, Any]:
    """Deterministic retry limiter with a fixed limit of 3 attempts.

    LLM cannot override or request a 4th attempt.

    Args:
        state: UniDevState dict containing attempt_count.

    Returns:
        {"status": "retry", "attempt_count": N+1} when N < MAX_ATTEMPTS.
        {"status": "escalate_to_human", "attempt_count": N+1} otherwise.
    """
    attempt_count = state.get("attempt_count", 0)
    attempt_count += 1
    if attempt_count <= MAX_ATTEMPTS:
        return {"status": "retry", "attempt_count": attempt_count}
    return {"status": "escalate_to_human", "attempt_count": attempt_count}
