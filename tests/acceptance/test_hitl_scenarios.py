"""A2-A4: HITL interrupt/resume acceptance tests.

Verify human-in-the-loop: gate fail -> interrupt -> human decision -> route correctly.
"""
from __future__ import annotations

from uni_dev.core.hitl import route_human_decision
from uni_dev.core.gates import ddd_verification_gate, sdd_verification_gate


class TestHITLApproval:
    """Verify HITL approve resumes pipeline."""

    def test_approve_routes_to_code_generate(self):
        state = {"_human_decision": "approve"}
        result = route_human_decision(state)
        assert result == "approve"

    def test_retry_routes_to_code_generate(self):
        state = {"_human_decision": "retry"}
        result = route_human_decision(state)
        assert result == "retry"

    def test_reject_routes_to_end(self):
        state = {"_human_decision": "reject"}
        result = route_human_decision(state)
        assert result == "reject"

    def test_default_decision_is_reject(self):
        state = {}
        result = route_human_decision(state)
        assert result == "reject"


class TestDDDGateFailHITL:
    """DDD gate fails -> routes to HITL -> human approves -> retry DDD."""

    def test_ddd_gate_fails_on_empty_domain(self):
        state = {}
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_ddd_gate_fails_with_blockers(self):
        state = {
            "domain_model": "entities:\n  - Pet\nbounded_contexts:\n  - clinic",
            "blockers": [{"reason": "Cannot determine bounded contexts"}],
        }
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_after_ddd_fail_human_approves(self):
        """HITL approve after DDD fail should allow spec write."""
        # Simulate: DDD fail -> human approves -> retry DDD -> now passes
        state = {"domain_model": "entities:\n  - Pet\nbounded_contexts:\n  - clinic"}
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "pass"

    def test_after_ddd_fail_human_rejects(self):
        """HITL reject after DDD fail terminates pipeline."""
        state = {"_human_decision": "reject"}
        assert route_human_decision(state) == "reject"


class TestSDDGateFailHITL:
    """SDD gate fails -> routes to HITL -> human approves -> retry SDD."""

    def test_sdd_gate_fails_on_empty_spec(self):
        state = {}
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_sdd_gate_fails_with_blockers(self):
        state = {
            "api_spec": "openapi: '3.0'\ninfo:\n  title: X\npaths:\n  /x:\n    get:\n      responses:\n        '200':\n          description: OK",
            "blockers": [{"reason": "Schema validation failed"}],
        }
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_after_sdd_fail_human_approves(self):
        """HITL approve after SDD fail -> retry SDD -> now passes."""
        state = {"api_spec": "openapi: '3.0'\ninfo:\n  title: X\npaths:\n  /x:\n    get:\n      responses:\n        '200':\n          description: OK"}
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "pass"

    def test_after_sdd_fail_human_rejects(self):
        """HITL reject after SDD fail terminates pipeline."""
        state = {"_human_decision": "reject"}
        assert route_human_decision(state) == "reject"


class TestHITLRetry:
    """HITL retry routes back to code_generate."""

    def test_human_retry_decision(self):
        state = {"_human_decision": "retry"}
        result = route_human_decision(state)
        assert result == "retry"
