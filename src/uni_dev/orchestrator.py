"""Orchestrator — Main deepagent wrapping M5 core + 5 LLM sub-agents.

Powers the DDD → SDD → TDD pipeline with DeepSeek models.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from deepagents import create_deep_agent
from deepagents.graph import SubAgent
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph

from uni_dev.agents.code_generator import create_code_generator
from uni_dev.agents.domain_designer import create_domain_designer
from uni_dev.agents.reviewer import create_reviewer
from uni_dev.agents.spec_writer import create_spec_writer
from uni_dev.agents.test_generator import create_test_generator
from uni_dev.monitoring import MonitorMiddleware

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "default.yaml"

_MODEL_TEMPERATURE_MAP: dict[str, float] = {
    "orchestrator": 0.3,
    "domain_designer": 0.3,
    "reviewer": 0.1,
    "spec_writer": 0.1,
    "code_generator": 0.0,
    "test_generator": 0.0,
}

_MODEL_MAP: dict[str, str] = {
    "domain_designer": "deepseek-v4-pro",
    "reviewer": "deepseek-v4-pro",
    "orchestrator": "deepseek-v4-pro",
    "spec_writer": "deepseek-v4-flash",
    "code_generator": "deepseek-v4-flash",
    "test_generator": "deepseek-v4-flash",
}


def _load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load pipeline configuration from YAML.

    Args:
        config_path: Path to config YAML. Defaults to config/default.yaml.

    Returns:
        Parsed configuration dict.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        logger.warning("Config file not found at %s, using defaults", path)
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _get_api_key() -> str:
    """Get DeepSeek API key from environment.

    Returns:
        API key string.

    Raises:
        ValueError: If DEEPSEEK_API_KEY environment variable is not set.
    """
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key or key.startswith("your_"):
        raise ValueError(
            "DEEPSEEK_API_KEY is not set. Create a .env file with your key, "
            "or set the environment variable. Get a key at: "
            "https://platform.deepseek.com/api_keys"
        )
    return key


def _create_model(
    model: str,
    base_url: str,
    api_key: str,
    temperature: float = 0.0,
    reasoning_effort: str | None = None,
    thinking: dict[str, str] | None = None,
) -> ChatOpenAI:
    """Create a ChatOpenAI model configured for DeepSeek.

    Args:
        model: Model identifier (deepseek-v4-pro or deepseek-v4-flash).
        base_url: API base URL.
        api_key: API key.
        temperature: Sampling temperature.
        reasoning_effort: Optional reasoning effort level.
        thinking: Optional thinking mode config.

    Returns:
        Configured ChatOpenAI instance.
    """
    kwargs: dict[str, Any] = {}
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    if thinking is not None:
        kwargs["extra_body"] = {"thinking": thinking}

    return ChatOpenAI(
        model=model,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        **kwargs,
    )


def _build_sub_agents(
    base_url: str,
    api_key: str,
) -> list[SubAgent]:
    """Build the list of sub-agents for the orchestrator.

    Args:
        base_url: DeepSeek API base URL.
        api_key: DeepSeek API key.

    Returns:
        List of SubAgent specs.
    """
    sub_agents: list[SubAgent] = []

    domain_model = _create_model(
        model=_MODEL_MAP["domain_designer"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["domain_designer"],
        reasoning_effort="high",
        thinking={"type": "enabled"},
    )
    sub_agents.append(
        create_domain_designer(model=domain_model)
    )

    spec_model = _create_model(
        model=_MODEL_MAP["spec_writer"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["spec_writer"],
    )
    sub_agents.append(
        create_spec_writer(model=spec_model)
    )

    test_model = _create_model(
        model=_MODEL_MAP["test_generator"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["test_generator"],
    )
    sub_agents.append(
        create_test_generator(model=test_model)  # type: ignore[arg-type]
    )

    code_model = _create_model(
        model=_MODEL_MAP["code_generator"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["code_generator"],
    )
    sub_agents.append(
        create_code_generator(model=code_model)  # type: ignore[arg-type]
    )

    reviewer_model = _create_model(
        model=_MODEL_MAP["reviewer"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["reviewer"],
        thinking={"type": "enabled"},
    )
    sub_agents.append(
        create_reviewer(model=reviewer_model)  # type: ignore[arg-type]
    )

    return sub_agents


MAX_LOOP_ITERATIONS = 50


def _merge_subagent_output(
    state: dict[str, Any],
    subagent_name: str,
    raw: dict[str, Any],
) -> dict[str, Any]:
    """Merge sub-agent output into the pipeline state.

    Maps agent output to the correct state field based on agent name.
    The raw dict comes from the SubAgent's structured output.

    Args:
        state: Current UniDevState dict.
        subagent_name: Name of the sub-agent that produced the output.
        raw: Raw result dict from the sub-agent.

    Returns:
        Updated state dict.
    """
    result = raw.get("result", raw)

    if subagent_name == "domain-designer":
        state["domain_model"] = result if isinstance(result, dict) else {"raw_output": str(result)}
    elif subagent_name == "spec-writer":
        state["api_spec"] = result if isinstance(result, str) else str(result)
    elif subagent_name == "test-generator":
        if isinstance(result, dict) and "test_files" in result:
            state["test_files"] = result["test_files"]
        elif isinstance(result, list):
            state["test_files"] = [str(f) for f in result]
        else:
            state["test_files"] = [str(result)]
    elif subagent_name == "code-generator":
        if isinstance(result, dict):
            state["modified_files"] = result.get("modified_files", result.get("files", []))
            if "test_results" in result:
                state["test_results"] = result["test_results"]
        else:
            state["modified_files"] = [str(result)]
    elif subagent_name == "reviewer":
        state["review_report"] = result if isinstance(result, dict) else {"raw_output": str(result)}

    return state


def run_pipeline_loop(
    initial_state: dict[str, Any],
    sub_agents: list[SubAgent],
    task_fn: Any = None,
) -> dict[str, Any]:
    """Re-entrant pipeline loop — drives the graph as a state machine.

    Registered as a tool on the deepagent. When running inside the
    deepagent runtime, task() is available from the tool context.
    For testing, pass a mock via task_fn.

    Loop:
    1. graph.invoke(state) → returns instruction via next_action
    2. If COMPLETE → return final state
    3. task(subagent, input) → execute LLM sub-agent with full tools
    4. Detect BLOCKED or merge result → loop

    Args:
        initial_state: Initial UniDevState dict with messages and classification.
        sub_agents: List of SubAgent dicts from _build_sub_agents().
        task_fn: Optional task function for sub-agent delegation. When None,
            imports from deepagents at runtime. Primarily for testing.

    Returns:
        Final state dict containing all pipeline outputs.

    Raises:
        RuntimeError: If loop exceeds MAX_LOOP_ITERATIONS.
    """
    from uni_dev.core.graph import build_graph

    if task_fn is None:
        from deepagents import task as _task
        task_fn = _task

    state = dict(initial_state)
    graph = build_graph()
    iterations = 0

    while iterations < MAX_LOOP_ITERATIONS:
        iterations += 1

        result = graph.invoke(state)
        state.update(result)

        action = state.get("next_action")
        if not action or action.get("type") == "COMPLETE":
            return state

        subagent_name = action["subagent"]
        subagent_input = action.get("input", {})

        raw = task_fn(subagent_name, description=subagent_input.get("description", subagent_name), **subagent_input)

        if isinstance(raw, dict) and raw.get("status") == "BLOCKED":
            blockers = state.get("blockers", [])
            blockers.append(raw)
            state["blockers"] = blockers
        else:
            state = _merge_subagent_output(state, subagent_name, raw if isinstance(raw, dict) else {"result": raw})

        state.pop("next_action", None)

    raise RuntimeError(
        f"Pipeline loop exceeded {MAX_LOOP_ITERATIONS} iterations"
    )


ORCHESTRATOR_SYSTEM_PROMPT = """\
You are uni-dev, a backend development automation framework.
You follow DDD → SDD → TDD methodology.

Core principles:
1. Specification First — OpenAPI contract written before any implementation
2. Test Before Code — Contract + unit tests before implementation
3. Domain Model First — Entities, aggregates, bounded contexts identified first
4. Deterministic Control — Verification gates, retry limits handled by Python
5. LLM for Intelligence — Code generation, architecture, spec writing

Always query the Knowledge Base before making decisions.
Defer to deterministic nodes (verification, retry, routing) — do not override them.

Pipeline execution:
1. Classify the issue: add_feature, update_api, remove_feature, or refactor
2. Call run_pipeline_loop with empty state_json="" to start the pipeline
3. The tool returns an instruction: {action: "CALL_TASK", subagent: "...", subagent_input: {...}, state_json: "..."}
4. Call task(subagent_type=<subagent>, description=<...>) with the subagent and input
5. Take the task() result and merge it into state_json, then call run_pipeline_loop again
6. Repeat until the tool returns {action: "COMPLETE", summary: {...}}
7. Report the summary to the user

The run_pipeline_loop tool enforces the correct ordering:
DomainDesigner → SpecWriter → TestGenerator → CodeGenerator → VerificationGate → Reviewer
You cannot skip steps — the tool will only advance when each phase completes.
"""


def _make_pipeline_tool(
    sub_agents: list[SubAgent],
    kb_path: str = ".uni-kb",
) -> Any:
    """Create the run_pipeline_loop tool for the deepagent.

    Returns instructions for the LLM to execute via task() calls.
    The LLM drives the loop — the graph enforces ordering.
    Each invocation feeds the result of the previous task() call
    back into the graph for the next step.

    Args:
        sub_agents: List of SubAgent dicts from _build_sub_agents().
        kb_path: Path to knowledge base directory.

    Returns:
        A callable tool function compatible with deepagent's tool interface.
    """
    from langchain_core.messages import HumanMessage

    def pipeline_tool(
        state_json: str = "",
        merge_subagent: str = "",
        merge_result_json: str = "",
    ) -> str:
        """Advance the DDD->SDD->TDD pipeline one step.

        Three modes:
        1. Start: pipeline_tool(state_json="")
        2. After task(): pipeline_tool(state_json=..., merge_subagent=..., merge_result_json=...)
        3. Re-invoke: pipeline_tool(state_json=...)  — for retry/blocked paths

        Args:
            state_json: JSON-serialized UniDevState from previous step.
            merge_subagent: Sub-agent name whose task() result to merge.
            merge_result_json: JSON result from the task() call.
        """
        import json as _json

        from uni_dev.core.graph import build_graph

        if state_json.strip():
            state = _json.loads(state_json)
        else:
            msg_text = ""
            state: dict[str, Any] = {
                "messages": [HumanMessage(content=msg_text)],
                "classification": "add_feature",
                "attempt_count": 0,
                "test_results": {"pass": False, "failures": [], "output": ""},
                "migration_idx": 0,
                "migration_plan": [],
                "current_phase": "ddd",
                "kb_path": kb_path,
            }

        if merge_subagent and merge_result_json:
            raw = _json.loads(merge_result_json)
            if isinstance(raw, dict) and raw.get("status") == "BLOCKED":
                blockers = state.get("blockers", [])
                blockers.append(raw)
                state["blockers"] = blockers
            else:
                state = _merge_subagent_output(
                    state, merge_subagent,
                    raw if isinstance(raw, dict) else {"result": raw},
                )
            state.pop("next_action", None)

        graph = build_graph()
        result = graph.invoke(state)
        state.update(result)

        action = state.get("next_action")
        if not action or action.get("type") == "COMPLETE":
            state["status"] = "complete"
            return _json.dumps(
                {
                    "action": "COMPLETE",
                    "summary": {
                        "domain_model": state.get("domain_model"),
                        "api_spec_exists": bool(state.get("api_spec")),
                        "test_files": state.get("test_files", []),
                        "modified_files": state.get("modified_files", []),
                        "test_results": state.get("test_results", {}),
                        "review_report": state.get("review_report", {}),
                        "blockers": state.get("blockers", []),
                        "phase": state.get("current_phase", "unknown"),
                    },
                },
                default=str,
            )

        subagent_name = action["subagent"]
        subagent_input = action.get("input", {})

        return _json.dumps(
            {
                "action": "CALL_TASK",
                "instruction": (
                    f"Call task(subagent_type='{subagent_name}', "
                    f"description='{subagent_input.get('description', subagent_name)}') "
                    f"with input: {_json.dumps(subagent_input, default=str)}"
                ),
                "subagent": subagent_name,
                "subagent_input": subagent_input,
                "state_json": _json.dumps(state, default=str),
            },
            default=str,
        )

    return pipeline_tool


def create_orchestrator(
    config_path: Path | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    monitor_db_path: str | None = ".uni-kb/monitor.db",
) -> CompiledStateGraph:
    """Create the main uni-dev orchestrator agent.

    Wires the deterministic pipeline as run_pipeline_loop tool
    and registers 5 LLM sub-agents for the DDD→SDD→TDD pipeline.

    Args:
        config_path: Path to config YAML. Defaults to config/default.yaml.
        api_key: DeepSeek API key. Defaults to DEEPSEEK_API_KEY env var.
        base_url: API base URL. Defaults to https://api.deepseek.com.
        monitor_db_path: Path for SQLite monitor store. Defaults to
            .uni-kb/monitor.db. Pass None to disable monitoring.

    Returns:
        Compiled deep agent StateGraph.

    Raises:
        ValueError: If API key is not provided and not found in environment.
    """
    config = _load_config(config_path)

    resolved_api_key = api_key if api_key is not None else _get_api_key()
    resolved_base_url = base_url if base_url is not None else (
        config.get("model", {}).get("base_url", "https://api.deepseek.com")
        or "https://api.deepseek.com"
    )

    orchestrator_model = _create_model(
        model=_MODEL_MAP["orchestrator"],
        base_url=resolved_base_url,
        api_key=resolved_api_key,
        temperature=_MODEL_TEMPERATURE_MAP["orchestrator"],
        reasoning_effort="high",
        thinking={"type": "enabled"},
    )

    sub_agents = _build_sub_agents(resolved_base_url, resolved_api_key)

    skills_path = (
        Path(__file__).resolve().parent.parent.parent / "skills" / "backend-dev"
    )
    skills = [str(skills_path)] if skills_path.exists() else []

    agents_md_path = (
        Path(__file__).resolve().parent.parent.parent.parent / "AGENTS.md"
    )
    memory = [str(agents_md_path)] if agents_md_path.exists() else []

    middleware = []
    if monitor_db_path is not None:
        middleware.append(MonitorMiddleware(db_path=monitor_db_path))

    pipeline_tool = _make_pipeline_tool(sub_agents, kb_path=".uni-kb")
    pipeline_tool.__name__ = "run_pipeline_loop"
    pipeline_tool.__doc__ = (
        "Run the full DDD→SDD→TDD→Verify pipeline for a given issue. "
        "Handles domain design, spec writing, test generation, code "
        "implementation, verification, and review automatically."
    )

    return create_deep_agent(
        model=orchestrator_model,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        subagents=sub_agents,
        middleware=middleware if middleware else (),
        skills=skills,
        memory=memory,
        tools=[pipeline_tool],
    )
