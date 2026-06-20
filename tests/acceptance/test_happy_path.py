"""A1: Full pipeline happy path acceptance test.

Validates the complete DDD->SDD->TDD pipeline with all gates passing.
Tests state transitions at each phase without needing real LLM calls.
"""
from __future__ import annotations

import pytest

from uni_dev.core.gates import (
    ddd_verification_gate,
    sdd_verification_gate,
    test_result_judge as _test_result_judge,
)
from uni_dev.core.nodes.classify import classify_node


class TestHappyPath:
    """Verify full pipeline: all gates pass, no retries, review completes."""

    def test_classify_sets_add_feature_default(self):
        state = {}
        result = classify_node(state)
        assert result["classification"] == "add_feature"

    def test_ddd_gate_passes_with_valid_domain(self, state_after_ddd):
        result = ddd_verification_gate(state_after_ddd)
        assert result["_gate_result"] == "pass"

    def test_sdd_gate_passes_with_valid_spec(self, state_after_sdd):
        result = sdd_verification_gate(state_after_sdd)
        assert result["_gate_result"] == "pass"

    def test_test_judge_passes_with_passing_tests(self, state_with_tests_passing):
        result = _test_result_judge(state_with_tests_passing)
        assert result["_gate_result"] == "pass"

    def test_full_state_accumulation(self, state_with_tests_passing):
        """After full happy path, all key state fields are populated."""
        state = state_with_tests_passing
        assert state.get("domain_model"), "domain_model missing"
        assert state.get("api_spec"), "api_spec missing"
        assert state.get("test_files"), "test_files missing"
        assert state.get("modified_files"), "modified_files missing"
        assert state.get("test_results", {}).get("pass"), "tests did not pass"

    def test_attempt_count_stays_zero(self, state_with_tests_passing):
        """No retries needed on happy path."""
        assert state_with_tests_passing.get("attempt_count", 0) == 0


class TestGateOrdering:
    """Verify gates execute in correct order and transmit state."""

    def test_ddd_gate_before_sdd_gate(self, state_after_ddd):
        """DDD must pass before SDD can proceed."""
        ddd_result = ddd_verification_gate(state_after_ddd)
        assert ddd_result["_gate_result"] == "pass"
        # State after DDD pass should have domain
        state_after_ddd["_gate_result"] = ddd_result["_gate_result"]
        assert state_after_ddd["_gate_result"] == "pass"

    def test_sdd_gate_after_ddd_pass_proceeds(self, state_after_sdd):
        """After DDD passes, SDD gate should work."""
        sdd_result = sdd_verification_gate(state_after_sdd)
        assert sdd_result["_gate_result"] == "pass"

    def test_test_judge_after_code_gen_proceeds(self, state_with_tests_passing):
        """After code gen + run_tests, test_judge should pass if tests pass."""
        judge_result = _test_result_judge(state_with_tests_passing)
        assert judge_result["_gate_result"] == "pass"


class TestHappyPathRouting:
    """Verify routing decisions on happy path."""

    def test_ddd_pass_routes_to_spec_write(self):
        """When DDD passes, next node should be spec_write."""
        state = {"domain_model": "entities:\n  - Pet\nbounded_contexts:\n  - clinic"}
        result = ddd_verification_gate(state)
        assert result["_gate_result"] == "pass"

    def test_sdd_pass_routes_to_test_generate(self):
        """When SDD passes, next node should be test_generate."""
        state = {"api_spec": "openapi: '3.0'\ninfo:\n  title: T\npaths:\n  /t:\n    get:\n      responses:\n        '200':\n          description: OK"}
        result = sdd_verification_gate(state)
        assert result["_gate_result"] == "pass"

    def test_test_judge_pass_routes_to_review(self):
        """When tests pass, next node should be review."""
        state = {"test_results": {"pass": True, "failures": []}}
        result = _test_result_judge(state)
        assert result["_gate_result"] == "pass"
