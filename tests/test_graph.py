"""Tests for core/graph.py — compiled StateGraph with instruction-producing nodes."""

from unittest.mock import MagicMock

from langchain_core.messages import HumanMessage

from uni_dev.core.graph import (
    UniDevState,
    _code_generator_node,
    _domain_designer_node,
    _last_message_text,
    _reviewer_node,
    _spec_writer_node,
    _test_generator_node,
    build_graph,
)


def _base_state(**overrides):
    """Create a base UniDevState for testing."""
    state: UniDevState = {
        "messages": [HumanMessage(content="Add user avatar upload")],
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


# State schema tests
def test_uni_dev_state_has_new_fields():
    """UniDevState accepts next_action, blockers, escalation_history, status."""
    state = _base_state(
        next_action={"type": "CALL_SUBAGENT", "subagent": "domain-designer"},
        blockers=[{"reason": "test", "suggested_action": "HUMAN_REQUIRED"}],
        escalation_history=["ddd->SpecWriter"],
        status="pass",
    )
    assert state["next_action"]["subagent"] == "domain-designer"
    assert state["blockers"][0]["reason"] == "test"
    assert len(state["escalation_history"]) == 1
    assert state["status"] == "pass"


def test_uni_dev_state_minimal():
    """UniDevState with only required fields."""
    state: UniDevState = {
        "messages": [],
        "classification": "refactor",
        "attempt_count": 0,
        "test_results": {"pass": True, "failures": [], "output": ""},
        "migration_idx": 0,
        "migration_plan": [],
        "current_phase": "sdd",
        "kb_path": "",
    }
    assert state["classification"] == "refactor"


# Domain designer node tests
def test_domain_designer_produces_instruction_when_empty():
    """First call produces CALL_SUBAGENT instruction."""
    state = _base_state()
    result = _domain_designer_node(state)
    assert result["next_action"]["type"] == "CALL_SUBAGENT"
    assert result["next_action"]["subagent"] == "domain-designer"
    assert result["current_phase"] == "spec_write"


def test_domain_designer_skips_when_done():
    """Second call skips when domain_model exists."""
    state = _base_state(domain_model={"entities": ["User"]})
    result = _domain_designer_node(state)
    assert result == {"current_phase": "spec_write"}
    assert "next_action" not in result


# Spec writer node tests
def test_spec_writer_produces_instruction_when_empty():
    """First call produces CALL_SUBAGENT for spec-writer."""
    state = _base_state(domain_model={"entities": ["User"]})
    result = _spec_writer_node(state)
    assert result["next_action"]["subagent"] == "spec-writer"
    assert not result["next_action"]["input"]["revision_mode"]


def test_spec_writer_skips_when_done():
    """Skips when api_spec exists."""
    state = _base_state(api_spec="openapi: 3.0.0")
    result = _spec_writer_node(state)
    assert result == {"current_phase": "test_gen"}


def test_spec_writer_revises_on_revise_spec_blocker():
    """Produces instruction with revision_mode=True when blockers contain REVISE_SPEC."""
    state = _base_state(
        api_spec="openapi: 3.0.0",
        blockers=[{"reason": "missing endpoint", "suggested_action": "REVISE_SPEC"}],
    )
    result = _spec_writer_node(state)
    assert result["next_action"]["input"]["revision_mode"] is True
    assert result["next_action"]["input"]["existing_spec"] == "openapi: 3.0.0"


# Test generator node tests
def test_test_generator_produces_instruction_when_empty():
    """First call produces CALL_SUBAGENT for test-generator."""
    state = _base_state(api_spec="openapi: 3.0.0")
    result = _test_generator_node(state)
    assert result["next_action"]["subagent"] == "test-generator"


def test_test_generator_skips_when_done():
    """Skips when test_files exist."""
    state = _base_state(test_files=["test_api.py"])
    result = _test_generator_node(state)
    assert result == {"current_phase": "code_gen"}


# Code generator node tests
def test_code_generator_produces_instruction_when_empty():
    """First call produces CALL_SUBAGENT for code-generator."""
    state = _base_state(api_spec="...", test_files=["test_x.py"])
    result = _code_generator_node(state)
    assert result["next_action"]["subagent"] == "code-generator"
    assert not result["next_action"]["input"]["retry"]


def test_code_generator_skips_when_done_and_passing():
    """Skips when modified_files exist and tests pass."""
    state = _base_state(
        modified_files=["src/app.py"],
        test_results={"pass": True, "failures": [], "output": "OK"},
    )
    result = _code_generator_node(state)
    assert result == {"current_phase": "verify"}


def test_code_generator_retry_on_failure():
    """Retries when tests fail — returns instruction with retry=True."""
    state = _base_state(
        modified_files=["src/app.py"],
        test_results={"pass": False, "failures": ["test_login"], "output": "FAIL"},
    )
    result = _code_generator_node(state)
    assert result["next_action"]["input"]["retry"] is True
    assert "test_login" in result["next_action"]["input"]["failures"]


# Reviewer node tests
def test_reviewer_produces_instruction_when_empty():
    """First call produces CALL_SUBAGENT for reviewer."""
    state = _base_state(
        api_spec="...",
        modified_files=["src/app.py"],
        test_results={"pass": True, "failures": [], "output": "OK"},
    )
    result = _reviewer_node(state)
    assert result["next_action"]["subagent"] == "reviewer"


def test_reviewer_skips_when_done():
    """Skips when review_report exists."""
    state = _base_state(review_report={"approved": True})
    result = _reviewer_node(state)
    assert result == {"current_phase": "done"}


# Graph wiring tests
def test_build_graph_returns_compiled_graph():
    """build_graph returns a compiled graph with expected attributes."""
    graph = build_graph()
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "get_graph")


def test_graph_has_escalation_router_node():
    """The compiled graph includes the EscalationRouter node."""
    graph = build_graph()
    node_names = list(graph.get_graph().nodes.keys())
    assert "EscalationRouter" in node_names


def test_graph_has_all_instruction_nodes():
    """The compiled graph includes all 5 instruction-producing nodes."""
    graph = build_graph()
    node_names = list(graph.get_graph().nodes.keys())
    for name in ("DomainDesigner", "SpecWriter", "TestGenerator", "CodeGenerator", "Reviewer"):
        assert name in node_names


def test_graph_has_deterministic_core_nodes():
    """The compiled graph includes all deterministic core nodes."""
    graph = build_graph()
    node_names = list(graph.get_graph().nodes.keys())
    for name in ("classification_router", "verification_gate", "retry_controller"):
        assert name in node_names


def test_graph_invoke_with_full_state_runs_to_completion():
    """Graph runs to completion when state has all required fields filled."""
    graph = build_graph()
    state = _base_state(
        classification="add_feature",
        domain_model={"entities": ["User"]},
        api_spec="openapi: 3.0.0",
        test_files=["tests/test_user.py"],
        modified_files=["src/user.py"],
        test_results={"pass": True, "failures": [], "output": "OK"},
    )
    result = graph.invoke(state)
    assert result.get("current_phase") == "done"


def test_graph_pauses_on_next_action():
    """Graph routes to END when a node produces a next_action instruction."""
    graph = build_graph()
    state = _base_state(classification="add_feature")
    result = graph.invoke(state)
    assert "next_action" in result
    assert result["next_action"]["subagent"] == "domain-designer"
    assert result["current_phase"] == "spec_write"


def test_graph_resumes_after_phase_complete():
    """Graph advances past completed phases when state is populated."""
    graph = build_graph()
    state = _base_state(
        classification="add_feature",
        domain_model={"entities": ["User"]},
    )
    result = graph.invoke(state)
    assert result["next_action"]["subagent"] == "spec-writer"
    assert result["current_phase"] == "test_gen"


def test_graph_no_llm_in_node_source():
    """Instruction-producing nodes have no LLM imports or API calls."""
    import inspect
    for func in (
        _domain_designer_node,
        _spec_writer_node,
        _test_generator_node,
        _code_generator_node,
        _reviewer_node,
    ):
        source = inspect.getsource(func)
        assert "ChatOpenAI" not in source
        assert "invoke(" not in source
        assert ".invoke" not in source


def test_last_message_text():
    """_last_message_text extracts from HumanMessage."""
    state = _base_state()
    text = _last_message_text(state)
    assert text == "Add user avatar upload"


def test_last_message_text_empty():
    """_last_message_text returns empty string when no messages."""
    state: UniDevState = {
        "messages": [],
        "classification": "",
        "attempt_count": 0,
        "test_results": {},
        "migration_idx": 0,
        "migration_plan": [],
        "current_phase": "",
        "kb_path": "",
    }
    assert _last_message_text(state) == ""
