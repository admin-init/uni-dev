"""Tests for core/graph.py — compiled StateGraph wiring."""

from uni_dev.core.graph import build_graph, UniDevState


def test_uni_dev_state_typed_dict():
    """UniDevState can be instantiated with all fields."""
    state: UniDevState = {
        "messages": [],
        "classification": "add_feature",
        "attempt_count": 0,
        "test_results": {"pass": False, "failures": [], "output": ""},
        "migration_idx": 0,
        "migration_plan": [],
        "current_phase": "ddd",
        "kb_path": "/tmp/.uni-dev",
    }
    assert state["classification"] == "add_feature"
    assert state["attempt_count"] == 0
    assert state["current_phase"] == "ddd"


def test_uni_dev_state_minimal_fields():
    """UniDevState with minimal required fields."""
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


def test_build_graph_returns_compiled_graph():
    """build_graph returns a compiled graph with expected attributes."""
    graph = build_graph()
    assert graph is not None


def test_build_graph_has_required_nodes():
    """The compiled graph contains all 4 deterministic core nodes."""
    graph = build_graph()
    graph_dict = graph.get_graph()
    node_names = set(graph_dict.nodes)
    required = {
        "classification_router",
        "verification_gate",
        "retry_controller",
        "migration_stepper",
    }
    assert required.issubset(node_names), f"Missing nodes: {required - node_names}"


def test_build_graph_no_llm():
    """graph.py is pure wiring — no LLM API calls (openai, anthropic, langchain invocation)."""
    import inspect
    source = inspect.getsource(build_graph)
    assert "invoke(" not in source
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
    assert "ChatModel" not in source
    assert "llm.invoke" not in source.lower()
