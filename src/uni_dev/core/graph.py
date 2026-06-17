from __future__ import annotations

import os

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from uni_dev.core.factory import PipelineConfig
from uni_dev.core.gates import (
    ddd_verification_gate,
    retry_controller,
    sdd_verification_gate,
    test_result_judge,
)
from uni_dev.core.hitl import human_approval_node, route_human_decision
from uni_dev.core.nodes.classify import classify_node
from uni_dev.core.nodes.code_generate import make_code_generate_node
from uni_dev.core.nodes.domain_design import make_domain_design_node
from uni_dev.core.nodes.review import make_review_node
from uni_dev.core.nodes.run_tests import make_run_tests_node
from uni_dev.core.nodes.spec_write import make_spec_write_node
from uni_dev.core.nodes.test_generate import make_test_generate_node
from uni_dev.core.state import PipelineState

def compile_pipeline(
    config: PipelineConfig,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Compile the DDD->SDD->TDD business-semantic SOP graph.

    Args:
        config: Pipeline configuration with API key, base URL, etc.
        checkpointer: Optional checkpointer for pause/resume support.

    Returns:
        Compiled StateGraph with checkpoint support.
    """
    if config.langsmith_enabled:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "uni-dev"

    builder = StateGraph(PipelineState)

    domain_design = make_domain_design_node(config)
    spec_write = make_spec_write_node(config)
    test_generate = make_test_generate_node(config)
    code_generate = make_code_generate_node(config)
    run_tests = make_run_tests_node(config)
    review = make_review_node(config)

    builder.add_node("classify", classify_node)
    builder.add_node("domain_design", domain_design)
    builder.add_node("ddd_gate", ddd_verification_gate)
    builder.add_node("spec_write", spec_write)
    builder.add_node("sdd_gate", sdd_verification_gate)
    builder.add_node("test_generate", test_generate)
    builder.add_node("code_generate", code_generate)
    builder.add_node("run_tests", run_tests)
    builder.add_node("test_judge", test_result_judge)
    builder.add_node("retry_ctrl", retry_controller)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("review", review)

    builder.add_edge(START, "classify")
    builder.add_edge("classify", "domain_design")
    builder.add_edge("domain_design", "ddd_gate")

    builder.add_conditional_edges(
        "ddd_gate",
        lambda s: s.get("_gate_result", "fail"),
        {"pass": "spec_write", "fail": "human_approval"},
    )

    builder.add_edge("spec_write", "sdd_gate")

    builder.add_conditional_edges(
        "sdd_gate",
        lambda s: s.get("_gate_result", "fail"),
        {"pass": "test_generate", "fail": "human_approval"},
    )

    builder.add_edge("test_generate", "code_generate")
    builder.add_edge("code_generate", "run_tests")
    builder.add_edge("run_tests", "test_judge")

    builder.add_conditional_edges(
        "test_judge",
        lambda s: s.get("_gate_result", "fail"),
        {"pass": "review", "fail": "retry_ctrl"},
    )

    builder.add_conditional_edges(
        "retry_ctrl",
        lambda s: s.get("_gate_result", "escalate"),
        {"retry": "code_generate", "escalate": "human_approval"},
    )

    builder.add_conditional_edges(
        "human_approval",
        route_human_decision,
        {"approve": "code_generate", "retry": "code_generate", "reject": END},
    )

    builder.add_edge("review", END)

    return builder.compile(checkpointer=checkpointer)
