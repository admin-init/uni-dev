"""Tests for agents/code_generator.py — TDD sub-agent."""

from uni_dev.agents.code_generator import (
    CODE_GENERATOR_SYSTEM_PROMPT,
    create_code_generator,
)


def test_create_code_generator_defaults():
    """Code generator sub-agent with default model."""
    agent = create_code_generator()
    assert agent["name"] == "code-generator"
    assert "implementation" in agent["description"].lower()
    assert agent["system_prompt"] == CODE_GENERATOR_SYSTEM_PROMPT
    assert "model" not in agent


def test_create_code_generator_with_model():
    """Code generator sub-agent with explicit model override."""
    agent = create_code_generator(model_name="deepseek-v4-flash")
    assert agent["name"] == "code-generator"
    assert agent["model"] == "deepseek-v4-flash"


def test_system_prompt_contains_key_phrases():
    """System prompt includes essential TDD guidance."""
    prompt = CODE_GENERATOR_SYSTEM_PROMPT
    assert "Test-Driven Development" in prompt
    assert "failing tests" in prompt.lower()
    assert "Green phase" in prompt
    assert "OpenAPI" in prompt
