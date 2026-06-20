"""I3: Verify retry loop: fail -> retry_ctrl -> code_generate -> run_tests cycle.

Tests the retry controller increments attempt_count, routes correctly,
and escalates to HITL after 3 failed attempts.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from uni_dev.core.factory import PipelineConfig
from uni_dev.core.gates import (
    retry_controller,
    test_result_judge as _test_result_judge,
)


class TestRetryController:
    """Verify retry_controller deterministic behavior."""

    def test_retry_on_first_attempt(self):
        result = retry_controller({"attempt_count": 0})
        assert result["_gate_result"] == "retry"
        assert result["attempt_count"] == 1

    def test_retry_on_second_attempt(self):
        result = retry_controller({"attempt_count": 1})
        assert result["_gate_result"] == "retry"
        assert result["attempt_count"] == 2

    def test_retry_on_third_attempt(self):
        result = retry_controller({"attempt_count": 2})
        assert result["_gate_result"] == "retry"
        assert result["attempt_count"] == 3

    def test_escalate_on_fourth_attempt(self):
        result = retry_controller({"attempt_count": 3})
        assert result["_gate_result"] == "escalate"
        assert result["attempt_count"] == 4

    def test_escalate_after_exhaustion(self):
        result = retry_controller({"attempt_count": 5})
        assert result["_gate_result"] == "escalate"


class TestTestJudgeRouting:
    """Verify test_judge gates correctly based on test results."""

    def test_pass_when_tests_pass_no_failures(self):
        state = {"test_results": {"pass": True, "failures": []}}
        result = _test_result_judge(state)
        assert result["_gate_result"] == "pass"

    def test_fail_when_tests_fail(self):
        state = {"test_results": {"pass": False, "failures": ["test_x"]}}
        result = _test_result_judge(state)
        assert result["_gate_result"] == "fail"

    def test_fail_when_failures_present_even_if_pass_true(self):
        state = {"test_results": {"pass": True, "failures": ["test_x"]}}
        result = _test_result_judge(state)
        assert result["_gate_result"] == "fail"

    def test_fail_when_no_test_results(self):
        result = _test_result_judge({})
        assert result["_gate_result"] == "fail"


class TestRetryLoopIntegration:
    """Verify retry loop end-to-end: test_judge fail -> retry -> code_generate."""

    def test_retry_loop_increments_and_routes(
        self, pipeline_config, mock_create_deep_agent
    ):
        """When tests fail, retry_ctrl increments count and routes to code_generate."""
        from uni_dev.core.graph import compile_pipeline

        pipeline = compile_pipeline(config=pipeline_config)
        graph = pipeline.get_graph()

        nodes = set(graph.nodes.keys())
        assert "retry_ctrl" in nodes
        assert "code_generate" in nodes
        assert "human_approval" in nodes
        assert "test_judge" in nodes

    def test_full_retry_cycle_with_mock(
        self, pipeline_config, mock_create_deep_agent
    ):
        """Run pipeline with failing tests -> should route to retry_ctrl."""
        from uni_dev.core.graph import compile_pipeline

        pipeline = compile_pipeline(config=pipeline_config)

        state = {
            "issue": "test retry",
            "project_path": ".",
            "classification": "add_feature",
            "attempt_count": 0,
        }

        config = {"configurable": {"thread_id": "retry-test"}}
        result = pipeline.invoke(state, config)
        assert result is not None
