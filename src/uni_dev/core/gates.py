from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3


def ddd_verification_gate(state: dict[str, Any]) -> dict[str, str]:
    """Validate domain model completeness. Zero LLM."""
    if state.get("blockers"):
        return {"_gate_result": "fail"}
    domain = state.get("domain_model", "")
    if not domain:
        return {"_gate_result": "fail"}
    return {"_gate_result": "pass"}


def sdd_verification_gate(state: dict[str, Any]) -> dict[str, str]:
    """Validate OpenAPI spec structure. Zero LLM."""
    if state.get("blockers"):
        return {"_gate_result": "fail"}
    spec = state.get("api_spec", "")
    if not spec:
        return {"_gate_result": "fail"}
    return {"_gate_result": "pass"}


def test_result_judge(state: dict[str, Any]) -> dict[str, str]:
    """Read pytest exit code. Zero LLM."""
    test_results = state.get("test_results")
    if test_results is None:
        return {"_gate_result": "fail"}
    if test_results.get("pass") is not True:
        return {"_gate_result": "fail"}
    if test_results.get("failures"):
        return {"_gate_result": "fail"}
    return {"_gate_result": "pass"}


def retry_controller(state: dict[str, Any]) -> dict[str, Any]:
    """Fixed 3-attempt limit. Zero LLM."""
    attempt_count = state.get("attempt_count", 0)
    attempt_count += 1
    if attempt_count <= MAX_ATTEMPTS:
        return {"attempt_count": attempt_count, "_gate_result": "retry"}
    return {"attempt_count": attempt_count, "_gate_result": "escalate"}
