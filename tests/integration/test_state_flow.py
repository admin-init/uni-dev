"""I4: Verify state fields propagate correctly between pipeline nodes.

Tests that each node reads expected input keys and writes expected output keys.
"""
from __future__ import annotations

from uni_dev.core.gates import ddd_verification_gate, sdd_verification_gate
from uni_dev.core.nodes.classify import classify_node


class TestClassifyNode:
    """Verify classify_node sets classification."""

    def test_sets_default_classification(self):
        result = classify_node({})
        assert result["classification"] == "add_feature"

    def test_preserves_existing_classification(self):
        result = classify_node({"classification": "refactor"})
        assert result["classification"] == "refactor"

    def test_rejects_invalid_classification(self):
        result = classify_node({"classification": "invalid_type"})
        assert result["classification"] == "add_feature"


class TestDddGateStateFlow:
    """Verify DDD gate reads domain_model from state."""

    def test_pass_with_valid_domain_yaml(self):
        state = {"domain_model": "entities:\n  - Pet\nbounded_contexts:\n  - clinic"}
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "pass"

    def test_fail_with_empty_state(self):
        result = ddd_verification_gate({})
        assert result["_gate_result"] == "fail"

    def test_fail_with_blockers(self):
        state = {
            "domain_model": "entities:\n  - Pet\nbounded_contexts:\n  - clinic",
            "blockers": [{"reason": "test blocker"}],
        }
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "fail"


class TestSddGateStateFlow:
    """Verify SDD gate reads api_spec from state."""

    def test_pass_with_valid_openapi_yaml(self):
        state = {
            "api_spec": "openapi: '3.0'\ninfo:\n  title: Test\npaths:\n  /test:\n    get:\n      responses:\n        '200':\n          description: OK"
        }
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "pass"

    def test_fail_with_missing_openapi_version(self):
        state = {"api_spec": "info:\n  title: Test\npaths:\n  /test:\n    get:\n      responses:\n        '200':\n          description: OK"}
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_fail_with_empty_paths(self):
        state = {"api_spec": "openapi: '3.0'\ninfo:\n  title: Test\npaths: {}"}
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "fail"

    def test_fail_with_missing_info(self):
        state = {"api_spec": "openapi: '3.0'\npaths:\n  /test:\n    get:\n      responses:\n        '200':\n          description: OK"}
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "fail"


class TestStateAccumulation:
    """Verify state accumulates correctly through gate transitions."""

    def test_after_ddd_pass_state_has_gate_result(self, state_after_ddd):
        result = ddd_verification_gate(state_after_ddd)
        assert result["_gate_result"] == "pass"
        state_after_ddd.update(result)
        assert state_after_ddd["_gate_result"] == "pass"

    def test_after_sdd_pass_state_has_gate_result(self, state_after_sdd):
        result = sdd_verification_gate(state_after_sdd)
        assert result["_gate_result"] == "pass"
        state_after_sdd.update(result)
        assert state_after_sdd["_gate_result"] == "pass"
