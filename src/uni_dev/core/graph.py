from __future__ import annotations

import logging

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from uni_dev.core.gates import (
    ddd_verification_gate,
    retry_controller,
    sdd_verification_gate,
    test_result_judge,
)
from uni_dev.core.hitl import human_approval_node, route_human_decision
from uni_dev.core.nodes.classify import classify_node
from uni_dev.core.nodes.code_generate import code_generate_node
from uni_dev.core.nodes.domain_design import domain_design_node
from uni_dev.core.nodes.review import review_node
from uni_dev.core.nodes.run_tests import run_tests_node
from uni_dev.core.nodes.spec_write import spec_write_node
from uni_dev.core.nodes.test_generate import test_generate_node
from uni_dev.core.state import PipelineState

logger = logging.getLogger(__name__)


def compile_pipeline(
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    """Compile the DDD->SDD->TDD business-semantic SOP graph.

    Args:
        checkpointer: Optional checkpointer for pause/resume support.

    Returns:
        Compiled StateGraph with checkpoint support.
    """
    builder = StateGraph(PipelineState)

    builder.add_node("classify", classify_node)
    builder.add_node("domain_design", domain_design_node)
    builder.add_node("ddd_gate", ddd_verification_gate)
    builder.add_node("spec_write", spec_write_node)
    builder.add_node("sdd_gate", sdd_verification_gate)
    builder.add_node("test_generate", test_generate_node)
    builder.add_node("code_generate", code_generate_node)
    builder.add_node("run_tests", run_tests_node)
    builder.add_node("test_judge", test_result_judge)
    builder.add_node("retry_ctrl", retry_controller)
    builder.add_node("human_approval", human_approval_node)
    builder.add_node("review", review_node)

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
