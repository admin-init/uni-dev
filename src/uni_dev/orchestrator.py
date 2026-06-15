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

Pipeline:
1. Classify the issue (add_feature, update_api, remove_feature, refactor)
2. Call run_pipeline_loop with the initial state — it handles the full DDD→SDD→TDD→Verify pipeline automatically
3. Review the final state and report results to the user

For deterministic pipeline execution, use the run_pipeline_loop tool.
For individual phase work, use task() to delegate to sub-agents directly.
"""


def create_orchestrator(
    config_path: Path | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    monitor_db_path: str | None = ".uni-kb/monitor.db",
) -> CompiledStateGraph:
    """Create the main uni-dev orchestrator agent.

    Wires the deterministic M5 pipeline graph as a CompiledSubAgent
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

    return create_deep_agent(
        model=orchestrator_model,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        subagents=sub_agents,
        middleware=middleware if middleware else (),
        skills=skills,
        memory=memory,
    )
