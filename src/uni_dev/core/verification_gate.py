from __future__ import annotations

from typing import Any


def verification_gate(state: dict[str, Any]) -> dict[str, str]:
    """Deterministic pass/fail/blocked gate based on blockers and test results.

    Checks for blockers before evaluating test_results. LLM cannot override.

    Args:
        state: UniDevState dict containing blockers and test_results keys.

    Returns:
        {"status": "blocked"} when blockers exist in state.
        {"status": "pass"} when tests pass with no failures.
        {"status": "fail"} otherwise.
    """
    if state.get("blockers"):
        return {"status": "blocked"}

    test_results = state.get("test_results")
    if test_results is None:
        return {"status": "fail"}
    if test_results.get("pass") is not True:
        return {"status": "fail"}
    if test_results.get("failures"):
        return {"status": "fail"}
    return {"status": "pass"}
