from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from uni_dev.orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    _MODEL_MAP,
    _MODEL_TEMPERATURE_MAP,
    _build_sub_agents,
    _create_model,
    _get_api_key,
    _load_config,
    create_orchestrator,
)


class TestGetApiKey:
    def test_raises_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DEEPSEEK_API_KEY", None)
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
                _get_api_key()

    def test_returns_key(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "sk-test123"}):
            assert _get_api_key() == "sk-test123"

    def test_raises_on_placeholder(self):
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "your_api_key_here"}):
            with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
                _get_api_key()


class TestCreateModel:
    def test_basic(self):
        model = _create_model(
            model="deepseek-v4-flash",
            base_url="https://api.deepseek.com",
            api_key="sk-test",
            temperature=0.0,
        )
        assert model is not None

    def test_with_reasoning(self):
        model = _create_model(
            model="deepseek-v4-pro",
            base_url="https://api.deepseek.com",
            api_key="sk-test",
            temperature=0.3,
            reasoning_effort="high",
            thinking={"type": "enabled"},
        )
        assert model is not None


class TestModelMaps:
    def test_model_map_assignments(self):
        assert _MODEL_MAP["domain_designer"] == "deepseek-v4-pro"
        assert _MODEL_MAP["reviewer"] == "deepseek-v4-pro"
        assert _MODEL_MAP["orchestrator"] == "deepseek-v4-pro"
        assert _MODEL_MAP["spec_writer"] == "deepseek-v4-flash"
        assert _MODEL_MAP["code_generator"] == "deepseek-v4-flash"
        assert _MODEL_MAP["test_generator"] == "deepseek-v4-flash"

    def test_temperature_map(self):
        assert _MODEL_TEMPERATURE_MAP["code_generator"] == 0.0
        assert _MODEL_TEMPERATURE_MAP["test_generator"] == 0.0
        assert _MODEL_TEMPERATURE_MAP["orchestrator"] == 0.3


class TestBuildSubAgents:
    def test_build_sub_agents(self):
        agents = _build_sub_agents("https://api.deepseek.com", "sk-test")
        assert len(agents) == 5
        names = {a["name"] for a in agents}
        assert names == {
            "domain-designer",
            "spec-writer",
            "test-generator",
            "code-generator",
            "reviewer",
        }


class TestOrchestratorSystemPrompt:
    def test_contains_methodology(self):
        assert "DDD" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "SDD" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "TDD" in ORCHESTRATOR_SYSTEM_PROMPT

    def test_contains_pipeline_steps(self):
        assert "domain-designer" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "spec-writer" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "test-generator" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "code-generator" in ORCHESTRATOR_SYSTEM_PROMPT
        assert "reviewer" in ORCHESTRATOR_SYSTEM_PROMPT

    def test_no_pipeline_loop_reference(self):
        assert "run_pipeline_loop" not in ORCHESTRATOR_SYSTEM_PROMPT
        assert "CALL_TASK" not in ORCHESTRATOR_SYSTEM_PROMPT


class TestLoadConfig:
    def test_defaults(self):
        config = _load_config()
        assert isinstance(config, dict)


class TestCreateOrchestrator:
    def test_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DEEPSEEK_API_KEY", None)
            with pytest.raises(ValueError):
                create_orchestrator()

    def test_with_explicit_key(self):
        agent = create_orchestrator(api_key="sk-test", monitor_db_path=None)
        assert agent is not None
