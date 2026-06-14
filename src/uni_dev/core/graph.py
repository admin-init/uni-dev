from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from uni_dev.core.classification_router import classification_router
from uni_dev.core.migration_stepper import migration_stepper
from uni_dev.core.retry_controller import retry_controller
from uni_dev.core.verification_gate import verification_gate


class UniDevState(TypedDict):
    """Shared state flowing through the uni-dev pipeline."""

    messages: list[BaseMessage]
    classification: str
    attempt_count: int
    test_results: dict[str, Any]
    migration_idx: int
    migration_plan: list[str]
    current_phase: str
    kb_path: str


def _route_by_classification(state: UniDevState) -> Literal[
    "DomainDesigner", "SpecWriter"
]:
    entry = classification_router({"classification": state["classification"]})
    return entry["next_node"]  # type: ignore[return-value]


def _route_by_verification(state: UniDevState) -> Literal[
    "Reviewer", "retry_controller"
]:
    result = verification_gate({"test_results": state["test_results"]})
    if result["status"] == "pass":
        return "Reviewer"
    return "retry_controller"


def _route_retry(state: UniDevState) -> Literal[
    "CodeGenerator", "__end__"
]:
    result = retry_controller({"attempt_count": state["attempt_count"]})
    state["attempt_count"] = result["attempt_count"]
    if result["status"] == "retry":
        return "CodeGenerator"
    return "__end__"


def _noop(state: UniDevState) -> dict[str, Any]:
    """Placeholder for LLM sub-agent nodes."""
    return {}


def build_graph() -> CompiledStateGraph:
    """Compile the deterministic pipeline StateGraph.

    Wires all 4 core nodes with conditional edges. LLM sub-agent nodes
    (DomainDesigner, SpecWriter, TestGenerator, CodeGenerator, Reviewer)
    are placeholders to be wired by the orchestrator.

    Returns:
        Compiled StateGraph ready for use as a CompiledSubAgent runnable.
    """
    builder = StateGraph(UniDevState)

    builder.add_node("classification_router", classification_router)
    builder.add_node("verification_gate", verification_gate)
    builder.add_node("retry_controller", retry_controller)
    builder.add_node("migration_stepper", migration_stepper)

    builder.add_node("DomainDesigner", _noop)
    builder.add_node("SpecWriter", _noop)
    builder.add_node("TestGenerator", _noop)
    builder.add_node("CodeGenerator", _noop)
    builder.add_node("Reviewer", _noop)

    builder.add_edge(START, "classification_router")

    builder.add_conditional_edges(
        "classification_router",
        _route_by_classification,
        {"DomainDesigner": "DomainDesigner", "SpecWriter": "SpecWriter"},
    )

    builder.add_edge("DomainDesigner", "SpecWriter")
    builder.add_edge("SpecWriter", "TestGenerator")
    builder.add_edge("TestGenerator", "CodeGenerator")
    builder.add_edge("CodeGenerator", "verification_gate")

    builder.add_conditional_edges(
        "verification_gate",
        _route_by_verification,
        {"Reviewer": "Reviewer", "retry_controller": "retry_controller"},
    )

    builder.add_conditional_edges(
        "retry_controller",
        _route_retry,
        {"CodeGenerator": "CodeGenerator", "__end__": END},
    )

    builder.add_edge("Reviewer", END)

    return builder.compile()
