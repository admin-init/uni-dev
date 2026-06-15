from __future__ import annotations

import logging
from typing import Any, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import NotRequired, TypedDict

from uni_dev.core.classification_router import classification_router
from uni_dev.core.escalation_router import escalation_router
from uni_dev.core.retry_controller import retry_controller
from uni_dev.core.verification_gate import verification_gate

logger = logging.getLogger(__name__)


class UniDevState(TypedDict):
    messages: list[BaseMessage]
    classification: str
    attempt_count: int
    test_results: dict[str, Any]
    migration_idx: int
    migration_plan: list[str]
    current_phase: str
    kb_path: str
    domain_model: NotRequired[dict[str, Any]]
    api_spec: NotRequired[str]
    test_files: NotRequired[list[str]]
    modified_files: NotRequired[list[str]]
    review_report: NotRequired[dict[str, Any]]
    next_action: NotRequired[dict[str, Any]]
    blockers: NotRequired[list[dict[str, Any]]]
    escalation_history: NotRequired[list[str]]
    status: NotRequired[str]


def _route_by_classification(state: UniDevState) -> Literal["DomainDesigner", "SpecWriter"]:
    entry = classification_router({"classification": state["classification"]})
    return entry["next_node"]  # type: ignore[return-value]


def _route_by_verification(state: UniDevState) -> Literal["Reviewer", "RetryController", "EscalationRouter"]:
    result = verification_gate(state)
    state["status"] = result["status"]
    if result["status"] == "pass":
        return "Reviewer"
    if result["status"] == "blocked":
        return "EscalationRouter"
    return "RetryController"


def _route_retry(state: UniDevState) -> Literal["CodeGenerator", "__end__"]:
    result = retry_controller({"attempt_count": state["attempt_count"]})
    state["attempt_count"] = result["attempt_count"]
    if result["status"] == "retry":
        return "CodeGenerator"
    return "__end__"


def _route_escalation(state: UniDevState) -> Literal["SpecWriter", "DomainDesigner", "__end__"]:
    result = escalation_router(state)
    state["escalation_history"] = result.get("escalation_history", [])
    return result["next_node"]  # type: ignore[return-value]


def _route_pause_if_instruction(state: UniDevState) -> Literal["__end__", "__next__"]:
    """Pause graph execution when a next_action instruction is set.

    When a node produces a CALL_SUBAGENT instruction, the graph must stop
    so the orchestrator loop can execute the sub-agent via task() and
    feed the result back into state. When no instruction is set, the
    node was skipped (already done), so continue to the next node.
    """
    if state.get("next_action"):
        return "__end__"
    return "__next__"


def _last_message_text(state: UniDevState) -> str:
    """Extract text from the last human message in state."""
    msgs = state.get("messages", [])
    for msg in reversed(msgs):
        content = getattr(msg, "content", None)
        if isinstance(content, str):
            return content
    return ""


def _domain_designer_node(state: UniDevState) -> dict[str, Any]:
    if state.get("domain_model"):
        return {"current_phase": "spec_write"}
    return {
        "current_phase": "spec_write",
        "next_action": {
            "type": "CALL_SUBAGENT",
            "subagent": "domain-designer",
            "input": {"issue": _last_message_text(state)},
        },
    }


def _spec_writer_node(state: UniDevState) -> dict[str, Any]:
    has_output = bool(state.get("api_spec"))
    needs_revision = any(
        b.get("suggested_action") == "REVISE_SPEC"
        for b in state.get("blockers", [])
    )
    if has_output and not needs_revision:
        return {"current_phase": "test_gen"}
    return {
        "current_phase": "test_gen",
        "next_action": {
            "type": "CALL_SUBAGENT",
            "subagent": "spec-writer",
            "input": {
                "revision_mode": needs_revision,
                "blockers": state.get("blockers", []),
                "domain_model": state.get("domain_model"),
                "existing_spec": state.get("api_spec"),
            },
        },
    }


def _test_generator_node(state: UniDevState) -> dict[str, Any]:
    if state.get("test_files"):
        return {"current_phase": "code_gen"}
    return {
        "current_phase": "code_gen",
        "next_action": {
            "type": "CALL_SUBAGENT",
            "subagent": "test-generator",
            "input": {"api_spec": state["api_spec"]},
        },
    }


def _code_generator_node(state: UniDevState) -> dict[str, Any]:
    test_results = state.get("test_results", {})
    has_output = bool(state.get("modified_files"))
    all_pass = test_results.get("pass") if test_results else False
    if has_output and all_pass:
        return {"current_phase": "verify"}
    is_retry = has_output and not all_pass
    return {
        "current_phase": "verify",
        "next_action": {
            "type": "CALL_SUBAGENT",
            "subagent": "code-generator",
            "input": {
                "retry": is_retry,
                "failures": test_results.get("failures", []),
                "api_spec": state.get("api_spec"),
                "test_files": state.get("test_files"),
                "previous_code": state.get("modified_files"),
            },
        },
    }


def _reviewer_node(state: UniDevState) -> dict[str, Any]:
    if state.get("review_report"):
        return {"current_phase": "done"}
    return {
        "current_phase": "done",
        "next_action": {
            "type": "CALL_SUBAGENT",
            "subagent": "reviewer",
            "input": {
                "api_spec": state.get("api_spec"),
                "modified_files": state.get("modified_files"),
                "test_results": state.get("test_results"),
            },
        },
    }


def build_graph() -> CompiledStateGraph:
    """Compile the re-entrant pipeline StateGraph.

    Nodes are idempotent instruction producers. The graph is invoked
    repeatedly by the orchestrator's run_pipeline_loop() — each
    invocation returns a next_action instruction which the orchestrator
    executes via task(), then feeds results back into state for the
    next invoke().

    Returns:
        Compiled StateGraph for use by run_pipeline_loop().
    """
    builder = StateGraph(UniDevState)

    # Deterministic core
    builder.add_node("classification_router", classification_router)
    builder.add_node("verification_gate", verification_gate)
    builder.add_node("retry_controller", retry_controller)
    builder.add_node("EscalationRouter", escalation_router)

    # LLM instruction-producing nodes
    builder.add_node("DomainDesigner", _domain_designer_node)
    builder.add_node("SpecWriter", _spec_writer_node)
    builder.add_node("TestGenerator", _test_generator_node)
    builder.add_node("CodeGenerator", _code_generator_node)
    builder.add_node("Reviewer", _reviewer_node)

    builder.add_edge(START, "classification_router")

    builder.add_conditional_edges(
        "classification_router",
        _route_by_classification,
        {"DomainDesigner": "DomainDesigner", "SpecWriter": "SpecWriter"},
    )

    builder.add_conditional_edges(
        "DomainDesigner",
        _route_pause_if_instruction,
        {"__end__": END, "__next__": "SpecWriter"},
    )
    builder.add_conditional_edges(
        "SpecWriter",
        _route_pause_if_instruction,
        {"__end__": END, "__next__": "TestGenerator"},
    )
    builder.add_conditional_edges(
        "TestGenerator",
        _route_pause_if_instruction,
        {"__end__": END, "__next__": "CodeGenerator"},
    )
    builder.add_conditional_edges(
        "CodeGenerator",
        _route_pause_if_instruction,
        {"__end__": END, "__next__": "verification_gate"},
    )

    builder.add_conditional_edges(
        "verification_gate",
        _route_by_verification,
        {
            "Reviewer": "Reviewer",
            "RetryController": "retry_controller",
            "EscalationRouter": "EscalationRouter",
        },
    )

    builder.add_conditional_edges(
        "retry_controller",
        _route_retry,
        {"CodeGenerator": "CodeGenerator", "__end__": END},
    )

    builder.add_conditional_edges(
        "EscalationRouter",
        _route_escalation,
        {
            "SpecWriter": "SpecWriter",
            "DomainDesigner": "DomainDesigner",
            "__end__": END,
        },
    )

    builder.add_edge("Reviewer", END)

    return builder.compile()
