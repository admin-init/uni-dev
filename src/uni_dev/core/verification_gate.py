from __future__ import annotations

from typing import Any


def verification_gate(state: dict[str, Any]) -> dict[str, str]:
    """Deterministic pass/fail gate based on test results.

    Reads test_results from state. LLM cannot override.

    Args:
        state: UniDevState dict containing test_results key.

    Returns:
        {"status": "pass"} when tests pass with no failures.
        {"status": "fail"} otherwise.
    """
    test_results = state.get("test_results")
    if test_results is None:
        return {"status": "fail"}
    if test_results.get("pass") is not True:
        return {"status": "fail"}
    if test_results.get("failures"):
        return {"status": "fail"}
    return {"status": "pass"}
