from __future__ import annotations

from uni_dev.core.gates import (
    MAX_ATTEMPTS,
    ddd_verification_gate,
    retry_controller,
    sdd_verification_gate,
    test_result_judge as _test_result_judge,
)


class TestDddVerificationGate:
    def test_pass_with_domain_model(self):
        state = {"domain_model": "entities: [Pet]"}
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "pass"

    def test_fail_without_domain_model(self):
        state = {}
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_fail_with_blockers(self):
        state = {"domain_model": "entities: [Pet]", "blockers": [{"reason": "x"}]}
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "fail"


class TestSddVerificationGate:
    def test_pass_with_spec(self):
        state = {"api_spec": "openapi: 3.0"}
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "pass"

    def test_fail_without_spec(self):
        state = {}
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_fail_with_blockers(self):
        state = {"api_spec": "openapi: 3.0", "blockers": [{"reason": "x"}]}
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "fail"


class TestTestResultJudge:
    def test_pass(self):
        state = {"test_results": {"pass": True, "failures": []}}
        result = _test_result_judge(state)
        assert result["_gate_result"] == "pass"

    def test_fail_on_exit_code(self):
        state = {"test_results": {"pass": False, "failures": ["test_x"]}}
        result = _test_result_judge(state)
        assert result["_gate_result"] == "fail"

    def test_fail_on_none(self):
        state = {}
        result = _test_result_judge(state)
        assert result["_gate_result"] == "fail"

    def test_fail_with_failures(self):
        state = {"test_results": {"pass": True, "failures": ["test_x"]}}
        result = _test_result_judge(state)
        assert result["_gate_result"] == "fail"


class TestRetryController:
    def test_retry_under_limit(self):
        state = {"attempt_count": 0}
        result = retry_controller(state)
        assert result["_gate_result"] == "retry"
        assert result["attempt_count"] == 1

    def test_retry_at_limit(self):
        state = {"attempt_count": 2}
        result = retry_controller(state)
        assert result["_gate_result"] == "retry"
        assert result["attempt_count"] == 3

    def test_escalate_over_limit(self):
        state = {"attempt_count": 3}
        result = retry_controller(state)
        assert result["_gate_result"] == "escalate"
        assert result["attempt_count"] == 4

    def test_max_attempts_constant(self):
        assert MAX_ATTEMPTS == 3
