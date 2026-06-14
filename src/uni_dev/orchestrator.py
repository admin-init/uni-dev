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
from deepagents.graph import CompiledSubAgent, SubAgent
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph

from uni_dev.agents.code_generator import create_code_generator
from uni_dev.agents.domain_designer import create_domain_designer
from uni_dev.agents.reviewer import create_reviewer
from uni_dev.agents.spec_writer import create_spec_writer
from uni_dev.agents.test_generator import create_test_generator
from uni_dev.core.graph import build_graph

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
    model_name: str,
    base_url: str,
    api_key: str,
    temperature: float = 0.0,
    reasoning_effort: str | None = None,
    thinking: dict[str, str] | None = None,
) -> ChatOpenAI:
    """Create a ChatOpenAI model configured for DeepSeek.

    Args:
        model_name: Model identifier (deepseek-v4-pro or deepseek-v4-flash).
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
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
        **kwargs,
    )


def _build_sub_agents(
    base_url: str,
    api_key: str,
) -> list[SubAgent | CompiledSubAgent]:
    """Build the list of sub-agents for the orchestrator.

    Args:
        base_url: DeepSeek API base URL.
        api_key: DeepSeek API key.

    Returns:
        List of SubAgent and CompiledSubAgent specs.
    """
    sub_agents: list[SubAgent | CompiledSubAgent] = []

    domain_model = _create_model(
        model_name=_MODEL_MAP["domain_designer"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["domain_designer"],
        reasoning_effort="high",
        thinking={"type": "enabled"},
    )
    sub_agents.append(
        create_domain_designer(model_name=domain_model)  # type: ignore[arg-type]
    )

    spec_model = _create_model(
        model_name=_MODEL_MAP["spec_writer"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["spec_writer"],
    )
    sub_agents.append(
        create_spec_writer(model_name=spec_model)  # type: ignore[arg-type]
    )

    test_model = _create_model(
        model_name=_MODEL_MAP["test_generator"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["test_generator"],
    )
    sub_agents.append(
        create_test_generator(model_name=test_model)  # type: ignore[arg-type]
    )

    code_model = _create_model(
        model_name=_MODEL_MAP["code_generator"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["code_generator"],
    )
    sub_agents.append(
        create_code_generator(model_name=code_model)  # type: ignore[arg-type]
    )

    reviewer_model = _create_model(
        model_name=_MODEL_MAP["reviewer"],
        base_url=base_url,
        api_key=api_key,
        temperature=_MODEL_TEMPERATURE_MAP["reviewer"],
        thinking={"type": "enabled"},
    )
    sub_agents.append(
        create_reviewer(model_name=reviewer_model)  # type: ignore[arg-type]
    )

    pipeline_graph = build_graph()
    sub_agents.append(
        CompiledSubAgent(
            name="pipeline-controller",
            description=(
                "Deterministic workflow controller. Handles verification, "
                "retry, classification routing, and migration stepping. "
                "This is the non-overridable backbone."
            ),
            runnable=pipeline_graph,
        )
    )

    return sub_agents


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
2. Delegate to domain-designer for DDD analysis
3. Delegate to spec-writer for OpenAPI contracts
4. Delegate to test-generator for test creation
5. Delegate to code-generator for implementation
6. Deterministic verification gate checks results
7. Delegate to reviewer for final review and documentation

For each step, use the task() tool to delegate to the appropriate sub-agent.
"""


def create_orchestrator(
    config_path: Path | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> CompiledStateGraph:
    """Create the main uni-dev orchestrator agent.

    Wires the deterministic M5 pipeline graph as a CompiledSubAgent
    and registers 5 LLM sub-agents for the DDD→SDD→TDD pipeline.

    Args:
        config_path: Path to config YAML. Defaults to config/default.yaml.
        api_key: DeepSeek API key. Defaults to DEEPSEEK_API_KEY env var.
        base_url: API base URL. Defaults to https://api.deepseek.com.

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
        model_name=_MODEL_MAP["orchestrator"],
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

    return create_deep_agent(
        model=orchestrator_model,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        subagents=sub_agents,
        skills=skills,
    )
