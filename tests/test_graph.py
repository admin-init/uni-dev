from __future__ import annotations

from uni_dev.core.graph import compile_pipeline
from uni_dev.core.state import PipelineState


class TestCompilePipeline:
    def test_compiles_without_checkpointer(self):
        pipeline = compile_pipeline()
        assert pipeline is not None

    def test_returns_compiled_graph(self):
        pipeline = compile_pipeline()
        assert hasattr(pipeline, "invoke")

    def test_has_expected_nodes(self):
        pipeline = compile_pipeline()
        graph = pipeline.get_graph()
        node_ids = set(graph.nodes.keys())
        expected = {
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
        assert expected.issubset(node_ids)


class TestPipelineState:
    def test_state_has_required_fields(self):
        state: PipelineState = {
            "issue": "test",
            "project_path": ".",
            "classification": "add_feature",
            "attempt_count": 0,
        }
        assert state["issue"] == "test"
        assert state["attempt_count"] == 0
