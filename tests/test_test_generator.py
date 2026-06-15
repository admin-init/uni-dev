"""Tests for agents/test_generator.py — TDD sub-agent."""

from uni_dev.agents.test_generator import (
    TEST_GENERATOR_SYSTEM_PROMPT,
    create_test_generator,
)


def test_create_test_generator_defaults():
    """Test generator sub-agent with default model."""
    agent = create_test_generator()
    assert agent["name"] == "test-generator"
    assert "TDD" in agent["description"] or "test" in agent["description"].lower()
    assert agent["system_prompt"] == TEST_GENERATOR_SYSTEM_PROMPT
    assert "model" not in agent


def test_create_test_generator_with_model():
    """Test generator sub-agent with explicit model override."""
    agent = create_test_generator(model="deepseek-v4-flash")
    assert agent["name"] == "test-generator"
    assert agent["model"] == "deepseek-v4-flash"


def test_system_prompt_contains_key_phrases():
    """System prompt includes essential TDD guidance."""
    prompt = TEST_GENERATOR_SYSTEM_PROMPT
    assert "Test-Driven Development" in prompt
    assert "contract tests" in prompt.lower()
    assert "FAIL initially" in prompt
    assert "read_file to study the OpenAPI spec" in prompt
