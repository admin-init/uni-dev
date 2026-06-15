"""Tests for orchestrator.py — main deepagent assembly."""

import os
from unittest.mock import patch

from uni_dev.orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    _build_sub_agents,
    _create_model,
    _get_api_key,
    _load_config,
    _MODEL_MAP,
    _MODEL_TEMPERATURE_MAP,
    _merge_subagent_output,
    MAX_LOOP_ITERATIONS,
    create_orchestrator,
    run_pipeline_loop,
)


def test_get_api_key_raises_when_missing():
    """Raises ValueError when DEEPSEEK_API_KEY is not set."""
    with patch.dict(os.environ, {}, clear=True):
        try:
            _get_api_key()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "DEEPSEEK_API_KEY" in str(e)


def test_get_api_key_returns_key():
    """Returns key when DEEPSEEK_API_KEY is set."""
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test-key"}, clear=True):
        assert _get_api_key() == "sk-test-key"


def test_get_api_key_raises_on_placeholder():
    """Raises when DEEPSEEK_API_KEY is the placeholder value."""
    with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "your_deepseek_api_key_here"}, clear=True):
        try:
            _get_api_key()
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


def test_create_model_basic():
    """Creates ChatOpenAI model with basic settings."""
    model = _create_model(
        model="deepseek-v4-flash",
        base_url="https://api.deepseek.com",
        api_key="sk-test",
    )
    assert model.model_name == "deepseek-v4-flash"
    assert model.openai_api_base == "https://api.deepseek.com"
    assert model.temperature == 0.0


def test_create_model_with_reasoning():
    """Creates ChatOpenAI with reasoning_effort and thinking params."""
    model = _create_model(
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com",
        api_key="sk-test",
        temperature=0.3,
        reasoning_effort="high",
        thinking={"type": "enabled"},
    )
    assert model.model_name == "deepseek-v4-pro"
    assert model.temperature == 0.3
    assert model.reasoning_effort == "high"
    assert model.extra_body == {"thinking": {"type": "enabled"}}


def test_model_map_assignments():
    """Verifies model assignments match the plan."""
    assert _MODEL_MAP["orchestrator"] == "deepseek-v4-pro"
    assert _MODEL_MAP["domain_designer"] == "deepseek-v4-pro"
    assert _MODEL_MAP["reviewer"] == "deepseek-v4-pro"
    assert _MODEL_MAP["spec_writer"] == "deepseek-v4-flash"
    assert _MODEL_MAP["code_generator"] == "deepseek-v4-flash"
    assert _MODEL_MAP["test_generator"] == "deepseek-v4-flash"


def test_temperature_map():
    """Verifies temperature settings."""
    assert _MODEL_TEMPERATURE_MAP["orchestrator"] == 0.3
    assert _MODEL_TEMPERATURE_MAP["domain_designer"] == 0.3
    assert _MODEL_TEMPERATURE_MAP["code_generator"] == 0.0
    assert _MODEL_TEMPERATURE_MAP["test_generator"] == 0.0


def test_build_sub_agents():
    """Builds all 6 sub-agents (5 LLM + 1 compiled)."""
    agents = _build_sub_agents(
        base_url="https://api.deepseek.com",
        api_key="sk-test",
    )
    assert len(agents) == 5
    names = [a["name"] for a in agents if hasattr(a, "__getitem__")]
    assert "domain-designer" in names
    assert "spec-writer" in names
    assert "test-generator" in names
    assert "code-generator" in names
    assert "reviewer" in names
    # pipeline-controller CompiledSubAgent removed — graph is driven by run_pipeline_loop now


def test_create_orchestrator_requires_api_key():
    """Raises ValueError when no API key is available."""
    with patch.dict(os.environ, {}, clear=True):
        try:
            create_orchestrator()
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "DEEPSEEK_API_KEY" in str(e)


def test_create_orchestrator_with_explicit_key():
    """Creates orchestrator when API key is passed directly."""
    agent = create_orchestrator(api_key="sk-test", base_url="https://api.deepseek.com")
    assert agent is not None


def test_orchestrator_system_prompt():
    """System prompt includes essential pipeline phases."""
    prompt = ORCHESTRATOR_SYSTEM_PROMPT
    assert "DDD" in prompt
    assert "SDD" in prompt
    assert "TDD" in prompt
    assert "OpenAPI" in prompt
    assert "verification" in prompt.lower()
    assert "task()" in prompt


def test_load_config_defaults():
    """Loading missing config returns empty dict."""
    config = _load_config()
    assert isinstance(config, dict)


def test_merge_subagent_output_domain_designer():
    """_merge_subagent_output writes domain_model."""
    state = {}
    state = _merge_subagent_output(state, "domain-designer", {"result": {"entities": ["User"]}})
    assert state["domain_model"] == {"entities": ["User"]}


def test_merge_subagent_output_spec_writer():
    """_merge_subagent_output writes api_spec."""
    state = {}
    state = _merge_subagent_output(state, "spec-writer", {"result": "openapi: 3.0.0\n..."})
    assert "openapi" in state["api_spec"]


def test_merge_subagent_output_code_generator_with_test_results():
    """_merge_subagent_output handles code-generator with modified_files and test_results."""
    state = {}
    result = {"result": {"modified_files": ["src/app.py"], "test_results": {"pass": True, "failures": []}}}
    state = _merge_subagent_output(state, "code-generator", result)
    assert state["modified_files"] == ["src/app.py"]
    assert state["test_results"]["pass"] is True


def test_merge_subagent_output_reviewer():
    """_merge_subagent_output writes review_report."""
    state = {}
    state = _merge_subagent_output(state, "reviewer", {"result": {"approved": True, "issues": []}})
    assert state["review_report"]["approved"] is True


def test_max_loop_iterations():
    """MAX_LOOP_ITERATIONS is the circuit breaker constant."""
    assert MAX_LOOP_ITERATIONS == 50
    assert isinstance(MAX_LOOP_ITERATIONS, int)
