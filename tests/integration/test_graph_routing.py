"""I1: Verify the compiled SOP graph has correct nodes and edge topology.

Tests the structural correctness of the StateGraph — no LLM calls needed.
"""
from __future__ import annotations

import pytest

from uni_dev.core.factory import PipelineConfig
from uni_dev.core.graph import compile_pipeline


EXPECTED_NODES = {
    "__start__",
    "__end__",
    "classify",
    "domain_design",
    "ddd_gate",
    "spec_write",
    "sdd_gate",
    "test_generate",
    "code_generate",
    "run_tests",
    "test_judge",
    "retry_ctrl",
    "human_approval",
    "review",
}

STATIC_EDGES = {
    ("__start__", "classify"),
    ("classify", "domain_design"),
    ("domain_design", "ddd_gate"),
    ("spec_write", "sdd_gate"),
    ("test_generate", "code_generate"),
    ("code_generate", "run_tests"),
    ("run_tests", "test_judge"),
    ("review", "__end__"),
}


@pytest.fixture
def graph():
    """Return graph dict from compiled pipeline."""
    config = PipelineConfig(api_key="sk-test")
    pipeline = compile_pipeline(config)
    return pipeline.get_graph()


def _edge_tuple(edge) -> tuple:
    """Normalize edge to (source, target) tuple."""
    if isinstance(edge, tuple) and len(edge) >= 2:
        return (edge[0], edge[1])
    return edge


class TestGraphNodes:
    """Verify all 12 business-semantic nodes exist."""

    def test_all_expected_nodes_present(self, graph):
        node_ids = set(graph.nodes.keys())
        missing = EXPECTED_NODES - node_ids
        assert not missing, f"Missing nodes: {missing}"

    def test_no_extra_nodes(self, graph):
        node_ids = set(graph.nodes.keys())
        extra = node_ids - EXPECTED_NODES
        assert not extra, f"Unexpected nodes: {extra}"


class TestStaticEdges:
    """Verify all fixed (non-conditional) edges exist."""

    def test_all_static_edges_present(self, graph):
        edge_set = {_edge_tuple(e) for e in graph.edges}
        missing = STATIC_EDGES - edge_set
        assert not missing, f"Missing static edges: {missing}"


class TestConditionalEdgeMaps:
    """Verify conditional edges have correct route maps."""

    def test_ddd_gate_pass_routes_to_spec_write(self, graph):
        self._assert_edge_exists(graph, "ddd_gate", "spec_write")

    def test_ddd_gate_fail_routes_to_human_approval(self, graph):
        self._assert_edge_exists(graph, "ddd_gate", "human_approval")

    def test_sdd_gate_pass_routes_to_test_generate(self, graph):
        self._assert_edge_exists(graph, "sdd_gate", "test_generate")

    def test_sdd_gate_fail_routes_to_human_approval(self, graph):
        self._assert_edge_exists(graph, "sdd_gate", "human_approval")

    def test_test_judge_pass_routes_to_review(self, graph):
        self._assert_edge_exists(graph, "test_judge", "review")

    def test_test_judge_fail_routes_to_retry_ctrl(self, graph):
        self._assert_edge_exists(graph, "test_judge", "retry_ctrl")

    def test_retry_ctrl_retry_routes_to_code_generate(self, graph):
        self._assert_edge_exists(graph, "retry_ctrl", "code_generate")

    def test_retry_ctrl_escalate_routes_to_human_approval(self, graph):
        self._assert_edge_exists(graph, "retry_ctrl", "human_approval")

    def test_human_approve_routes_to_code_generate(self, graph):
        self._assert_edge_exists(graph, "human_approval", "code_generate")

    def test_human_retry_routes_to_code_generate(self, graph):
        self._assert_edge_exists(graph, "human_approval", "code_generate")

    def test_human_reject_routes_to_end(self, graph):
        self._assert_edge_exists(graph, "human_approval", "__end__")

    def _assert_edge_exists(self, graph, source: str, target: str):
        edge_set = {_edge_tuple(e) for e in graph.edges}
        assert (source, target) in edge_set, (
            f"Expected edge {source} -> {target} not found"
        )
