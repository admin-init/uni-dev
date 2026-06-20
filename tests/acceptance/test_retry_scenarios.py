"""A5-A6: Retry loop acceptance tests.

A5: Tests fail -> retry -> code fixed -> tests pass.
A6: Tests fail 3 times -> retry_ctrl escalates -> HITL.
"""
from __future__ import annotations

from uni_dev.core.gates import (
    retry_controller,
    test_result_judge as _test_result_judge,
)
from uni_dev.core.hitl import route_human_decision


class TestRetryThenPass:
    """A5: Tests fail on first attempt, succeed on retry."""

    def test_first_run_tests_fail(self, state_with_tests_failing):
        result = _test_result_judge(state_with_tests_failing)
        assert result["_gate_result"] == "fail"

    def test_retry_increments_attempt(self):
        state = {"attempt_count": 0}
        result = retry_controller(state)
        assert result["_gate_result"] == "retry"
        assert result["attempt_count"] == 1

    def test_second_run_tests_pass(self, state_with_tests_passing):
        result = _test_result_judge(state_with_tests_passing)
        assert result["_gate_result"] == "pass"

    def test_retry_context_provided(self, state_with_tests_failing):
        """Failing state provides failure details for retry."""
        results = state_with_tests_failing.get("test_results", {})
        assert results.get("pass") is False
        assert results.get("failures"), "Expected failure details for retry"

    def test_retry_after_pass_returns_pass(self):
        """After retry and tests pass, pipeline proceeds."""
        state = {
            "test_results": {"pass": True, "failures": []},
            "attempt_count": 1,
        }
        result = _test_result_judge(state)
        assert result["_gate_result"] == "pass"


class TestRetryExhaustion:
    """A6: Tests fail 3 times -> retry_ctrl escalates."""

    def test_first_retry_returns_retry(self):
        state = {"attempt_count": 0}
        result = retry_controller(state)
        assert result["_gate_result"] == "retry"
        assert result["attempt_count"] == 1

    def test_second_retry_returns_retry(self):
        state = {"attempt_count": 1}
        result = retry_controller(state)
        assert result["_gate_result"] == "retry"
        assert result["attempt_count"] == 2

    def test_third_retry_returns_retry(self):
        state = {"attempt_count": 2}
        result = retry_controller(state)
        assert result["_gate_result"] == "retry"
        assert result["attempt_count"] == 3

    def test_fourth_attempt_escalates(self):
        state = {"attempt_count": 3}
        result = retry_controller(state)
        assert result["_gate_result"] == "escalate"
        assert result["attempt_count"] == 4

    def test_escalation_routes_to_human_approval(self):
        """After escalation, HITL handles the decision."""
        # Simulate: escalate -> human_approval -> human decides
        state = {"attempt_count": 4, "_human_decision": "approve"}
        route = route_human_decision(state)
        assert route == "approve"

    def test_escalation_human_rejects(self):
        state = {"attempt_count": 4, "_human_decision": "reject"}
        route = route_human_decision(state)
        assert route == "reject"
