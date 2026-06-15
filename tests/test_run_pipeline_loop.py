"""Tests for run_pipeline_loop() — re-entrant state machine loop."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage

from uni_dev.core.graph import UniDevState
from uni_dev.orchestrator import run_pipeline_loop


def _initial_state(**overrides):
    """Create an initial UniDevState."""
    state: UniDevState = {
        "messages": [HumanMessage(content="Add login")],
        "classification": "add_feature",
        "attempt_count": 0,
        "test_results": {"pass": False, "failures": [], "output": ""},
        "migration_idx": 0,
        "migration_plan": [],
        "current_phase": "ddd",
        "kb_path": "/tmp/.uni-dev",
    }
    state.update(overrides)
    return state


class FakeGraph:
    """Fake graph that returns predetermined sequences."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.call_count = 0

    def invoke(self, state):
        if self.call_count >= len(self.responses):
            return {"next_action": {"type": "COMPLETE"}}
        response = self.responses[self.call_count]
        self.call_count += 1
        return response


def _fake_task(subagent_name, description="", **kwargs):
    """Fake task() function."""
    if subagent_name == "domain-designer":
        return {"result": {"entities": ["User"], "bounded_contexts": ["auth"]}}
    elif subagent_name == "spec-writer":
        return {"result": "openapi: 3.0.0\npaths:\n  /login:\n    post:"}
    elif subagent_name == "test-generator":
        return {"result": {"test_files": ["tests/test_login.py"]}}
    elif subagent_name == "code-generator":
        return {"result": {"modified_files": ["src/login.py"], "test_results": {"pass": True, "failures": [], "output": "OK"}}}
    elif subagent_name == "reviewer":
        return {"result": {"approved": True, "issues": [], "recommendations": []}}
    return {"result": {}}


def _fake_task_blocked(subagent_name, description="", **kwargs):
    """Fake task that returns BLOCKED only for code-generator on first call."""
    if subagent_name == "code-generator":
        return {
            "status": "BLOCKED",
            "reason": "Cannot implement without spec revision",
            "suggested_action": "REVISE_SPEC",
            "blocking_details": {},
        }
    return _fake_task(subagent_name, description=description, **kwargs)


@patch("uni_dev.core.graph.build_graph")
def test_run_pipeline_loop_completes_full_cycle(mock_build_graph):
    """Full cycle: domain_designer → spec_writer → test_generator → code_generator → reviewer → COMPLETE."""
    responses = [
        {"current_phase": "spec_write", "next_action": {"type": "CALL_SUBAGENT", "subagent": "domain-designer", "input": {"issue": "Add login"}}},
        {"current_phase": "test_gen", "next_action": {"type": "CALL_SUBAGENT", "subagent": "spec-writer", "input": {}}},
        {"current_phase": "code_gen", "next_action": {"type": "CALL_SUBAGENT", "subagent": "test-generator", "input": {}}},
        {"current_phase": "verify", "next_action": {"type": "CALL_SUBAGENT", "subagent": "code-generator", "input": {}}},
        {"current_phase": "done", "next_action": {"type": "CALL_SUBAGENT", "subagent": "reviewer", "input": {}}},
        {"next_action": {"type": "COMPLETE"}},
    ]
    mock_build_graph.return_value = FakeGraph(responses)
    state = _initial_state()
    result = run_pipeline_loop(state, sub_agents=[], task_fn=_fake_task)
    assert result["domain_model"] == {"entities": ["User"], "bounded_contexts": ["auth"]}
    assert "openapi" in result["api_spec"]
    assert result["review_report"]["approved"] is True


@patch("uni_dev.core.graph.build_graph")
def test_run_pipeline_loop_handles_blocked(mock_build_graph):
    """BLOCKED sub-agent response populates blockers in state."""
    responses = [
        {"current_phase": "code_gen", "next_action": {"type": "CALL_SUBAGENT", "subagent": "code-generator", "input": {}}},
        {"current_phase": "test_gen", "next_action": {"type": "CALL_SUBAGENT", "subagent": "spec-writer", "input": {"revision_mode": True}}},
        {"next_action": {"type": "COMPLETE"}},
    ]
    mock_build_graph.return_value = FakeGraph(responses)
    state = _initial_state()
    result = run_pipeline_loop(state, sub_agents=[], task_fn=_fake_task_blocked)
    assert len(result["blockers"]) == 1
    assert result["blockers"][0]["suggested_action"] == "REVISE_SPEC"


@patch("uni_dev.core.graph.build_graph")
def test_run_pipeline_loop_complete_on_no_action(mock_build_graph):
    """Returns state immediately when graph produces no next_action."""
    mock_task = MagicMock()
    mock_build_graph.return_value = FakeGraph([{"current_phase": "done"}])
    state = _initial_state(domain_model={"done": True})
    result = run_pipeline_loop(state, sub_agents=[], task_fn=mock_task)
    assert result["domain_model"] == {"done": True}
    mock_task.assert_not_called()


@patch("uni_dev.core.graph.build_graph")
def test_run_pipeline_loop_complete_on_explicit_complete(mock_build_graph):
    """Returns state when next_action type is COMPLETE."""
    mock_task = MagicMock()
    mock_build_graph.return_value = FakeGraph([{"next_action": {"type": "COMPLETE"}}])
    state = _initial_state()
    result = run_pipeline_loop(state, sub_agents=[], task_fn=mock_task)
    assert "next_action" in result
    mock_task.assert_not_called()
