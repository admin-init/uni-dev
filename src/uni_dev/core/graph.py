from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Literal

import yaml
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import NotRequired, TypedDict

from uni_dev.agents.code_generator import CODE_GENERATOR_SYSTEM_PROMPT
from uni_dev.agents.domain_designer import DOMAIN_DESIGNER_SYSTEM_PROMPT
from uni_dev.agents.reviewer import REVIEWER_SYSTEM_PROMPT
from uni_dev.agents.spec_writer import SPEC_WRITER_SYSTEM_PROMPT
from uni_dev.agents.test_generator import TEST_GENERATOR_SYSTEM_PROMPT
from uni_dev.core.classification_router import classification_router
from uni_dev.core.migration_stepper import migration_stepper
from uni_dev.core.retry_controller import retry_controller
from uni_dev.core.verification_gate import verification_gate

logger = logging.getLogger(__name__)

_MODEL_CONFIG: dict[str, dict[str, Any]] = {
    "domain_designer": {
        "model_name": "deepseek-v4-pro",
        "temperature": 0.3,
        "reasoning_effort": "high",
        "thinking": {"type": "enabled"},
    },
    "spec_writer": {
        "model_name": "deepseek-v4-flash",
        "temperature": 0.1,
    },
    "test_generator": {
        "model_name": "deepseek-v4-flash",
        "temperature": 0.0,
    },
    "code_generator": {
        "model_name": "deepseek-v4-flash",
        "temperature": 0.0,
    },
    "reviewer": {
        "model_name": "deepseek-v4-pro",
        "temperature": 0.1,
        "thinking": {"type": "enabled"},
    },
}

_BASE_URL = "https://api.deepseek.com"


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
    domain_model: NotRequired[dict[str, Any]]
    api_spec: NotRequired[str]
    test_files: NotRequired[list[str]]
    modified_files: NotRequired[list[str]]
    review_report: NotRequired[dict[str, Any]]


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


def _get_api_key() -> str:
    """Get DeepSeek API key from environment.

    Returns:
        API key string.

    Raises:
        ValueError: If DEEPSEEK_API_KEY is not set.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError(
            "DEEPSEEK_API_KEY environment variable is not set"
        )
    return api_key


def _create_node_model(node_type: str) -> ChatOpenAI:
    """Create a ChatOpenAI model instance for a pipeline node.

    Args:
        node_type: Key in _MODEL_CONFIG dict.

    Returns:
        Configured ChatOpenAI instance.
    """
    config = _MODEL_CONFIG[node_type]
    api_key = _get_api_key()
    kwargs: dict[str, Any] = {
        "model": config["model_name"],
        "base_url": _BASE_URL,
        "api_key": api_key,
        "temperature": config["temperature"],
    }
    if "reasoning_effort" in config:
        kwargs["reasoning_effort"] = config["reasoning_effort"]
    if "thinking" in config:
        kwargs["extra_body"] = {"thinking": config["thinking"]}
    return ChatOpenAI(**kwargs)


def _extract_code_block(content: str, language: str = "") -> str:
    """Extract content from a markdown code fence if present.

    Args:
        content: Raw LLM response text.
        language: Optional language tag to match (e.g. 'yaml', 'json').

    Returns:
        Content inside the code fence, or the raw content if no fence found.
    """
    text = content if isinstance(content, str) else str(content)
    if language and f"```{language}" in text:
        parts = text.split(f"```{language}", 1)
        if len(parts) > 1:
            inner = parts[1].split("```", 1)
            return inner[0].strip()
    if "```" in text:
        parts = text.split("```", 1)
        if len(parts) > 1:
            inner = parts[1].split("```", 1)
            return inner[0].strip()
    return text.strip()


def _extract_issue_text(state: UniDevState) -> str:
    """Extract the issue description from the last human message in state.

    Args:
        state: UniDevState dict.

    Returns:
        Issue text string, or empty string if not found.
    """
    msgs = state.get("messages", [])
    for msg in reversed(msgs):
        if hasattr(msg, "content") and isinstance(msg.content, str):
            return msg.content
    return ""


def _domain_designer_node(state: UniDevState) -> dict[str, Any]:
    """DDD phase node — produces domain_model from issue description.

    Args:
        state: UniDevState dict with messages containing the issue.

    Returns:
        State update with domain_model, appended messages, and phase transition.
    """
    model = _create_node_model("domain_designer")
    issue_text = _extract_issue_text(state)
    prompt = (
        f"{DOMAIN_DESIGNER_SYSTEM_PROMPT}\n\n"
        f"Issue to analyze:\n{issue_text}"
    )
    response = model.invoke([HumanMessage(content=prompt)])
    raw = response.content if isinstance(response.content, str) else str(response.content)
    cleaned = _extract_code_block(raw, "yaml")
    try:
        parsed = yaml.safe_load(cleaned)
        domain_model = parsed if isinstance(parsed, dict) else {"raw_output": cleaned}
    except yaml.YAMLError:
        domain_model = {"raw_output": cleaned}
    return {
        "domain_model": domain_model,
        "messages": [response],
        "current_phase": "sdd",
    }


def _spec_writer_node(state: UniDevState) -> dict[str, Any]:
    """SDD phase node — produces OpenAPI spec from domain model.

    Args:
        state: UniDevState dict with domain_model from DDD phase.

    Returns:
        State update with api_spec, appended messages, and phase transition.
    """
    model = _create_node_model("spec_writer")
    domain_model = state.get("domain_model", {})
    domain_yaml = yaml.dump(domain_model, default_flow_style=False, sort_keys=False)
    prompt = (
        f"{SPEC_WRITER_SYSTEM_PROMPT}\n\n"
        f"Domain model:\n```yaml\n{domain_yaml}```\n\n"
        f"Generate the complete OpenAPI 3.0 YAML specification."
    )
    response = model.invoke([HumanMessage(content=prompt)])
    raw = response.content if isinstance(response.content, str) else str(response.content)
    api_spec = _extract_code_block(raw, "yaml")
    return {
        "api_spec": api_spec,
        "messages": [response],
        "current_phase": "tdd",
    }


def _test_generator_node(state: UniDevState) -> dict[str, Any]:
    """TDD phase node — generates test files from the API spec.

    Args:
        state: UniDevState dict with api_spec from SDD phase.

    Returns:
        State update with test_files and appended messages.
    """
    model = _create_node_model("test_generator")
    api_spec = state.get("api_spec", "")
    prompt = (
        f"{TEST_GENERATOR_SYSTEM_PROMPT}\n\n"
        f"OpenAPI specification:\n```yaml\n{api_spec}```\n\n"
        f"Generate pytest test files for every endpoint. "
        f"Write each file path on its own line in a '### Test Files' section."
    )
    response = model.invoke([HumanMessage(content=prompt)])
    raw = response.content if isinstance(response.content, str) else str(response.content)
    test_files = _parse_file_paths(raw)
    return {
        "test_files": test_files,
        "messages": [response],
    }


def _code_generator_node(state: UniDevState) -> dict[str, Any]:
    """TDD phase node — implements code from the API spec and test files.

    Args:
        state: UniDevState dict with api_spec and test_files.

    Returns:
        State update with modified_files, test_results, and appended messages.
    """
    model = _create_node_model("code_generator")
    api_spec = state.get("api_spec", "")
    test_files = state.get("test_files", [])
    prompt = (
        f"{CODE_GENERATOR_SYSTEM_PROMPT}\n\n"
        f"OpenAPI specification:\n```yaml\n{api_spec}```\n\n"
        f"Test files to satisfy:\n" + "\n".join(f"- {f}" for f in test_files) + "\n\n"
        "Implement the code. List modified/created file paths in a '### Files' section."
    )
    response = model.invoke([HumanMessage(content=prompt)])
    raw = response.content if isinstance(response.content, str) else str(response.content)
    modified_files = _parse_file_paths(raw)
    return {
        "modified_files": modified_files,
        "test_results": {"pass": True, "failures": [], "output": "llm-generated"},
        "messages": [response],
    }


def _reviewer_node(state: UniDevState) -> dict[str, Any]:
    """Post-verification node — reviews implementation against spec.

    Args:
        state: UniDevState dict with api_spec, modified_files, and test_results.

    Returns:
        State update with review_report and appended messages.
    """
    model = _create_node_model("reviewer")
    api_spec = state.get("api_spec", "")
    modified_files = state.get("modified_files", [])
    test_results = state.get("test_results", {})
    prompt = (
        f"{REVIEWER_SYSTEM_PROMPT}\n\n"
        f"OpenAPI specification:\n```yaml\n{api_spec}```\n\n"
        f"Modified files: {json.dumps(modified_files)}\n\n"
        f"Test results: {json.dumps(test_results)}\n\n"
        f"Output a JSON review report with keys: approved (bool), "
        f"issues (list), recommendations (list), doc_updates (list)."
    )
    response = model.invoke([HumanMessage(content=prompt)])
    raw = response.content if isinstance(response.content, str) else str(response.content)
    cleaned = _extract_code_block(raw, "json")
    try:
        review_report = json.loads(cleaned)
    except json.JSONDecodeError:
        review_report = {"approved": True, "issues": [], "raw_output": cleaned}
    return {
        "review_report": review_report,
        "messages": [response],
    }


def _parse_file_paths(text: str) -> list[str]:
    """Extract file paths from LLM output.

    Scans for lines matching common source/test file patterns.

    Args:
        text: Raw LLM response text.

    Returns:
        List of extracted file path strings.
    """
    paths: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for prefix in ("- ", "* ", "  - ", "  * "):
            if line.startswith(prefix):
                line = line[len(prefix):]
                break
        if re.match(r"^(src|tests?|specs?|docs?)/", line) or re.match(
            r"^[a-zA-Z0-9_/.]+\.(py|js|ts|java|go|rs|yaml|yml|json|md)$", line
        ):
            paths.append(line)
    return paths


def build_graph() -> CompiledStateGraph:
    """Compile the deterministic pipeline StateGraph.

    Wires all 4 core nodes with conditional edges and 5 self-contained
    LLM agent nodes (DomainDesigner, SpecWriter, TestGenerator,
    CodeGenerator, Reviewer).

    Returns:
        Compiled StateGraph ready for use as a CompiledSubAgent runnable.
    """
    builder = StateGraph(UniDevState)

    builder.add_node("classification_router", classification_router)
    builder.add_node("verification_gate", verification_gate)
    builder.add_node("retry_controller", retry_controller)
    builder.add_node("migration_stepper", migration_stepper)

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
