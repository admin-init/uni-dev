"""Tests for agents/reviewer.py — post-verification sub-agent."""

from uni_dev.agents.reviewer import (
    REVIEWER_SYSTEM_PROMPT,
    create_reviewer,
)


def test_create_reviewer_defaults():
    """Reviewer sub-agent with default model."""
    agent = create_reviewer()
    assert agent["name"] == "reviewer"
    assert "review" in agent["description"].lower()
    assert agent["system_prompt"] == REVIEWER_SYSTEM_PROMPT
    assert "model" not in agent


def test_create_reviewer_with_model():
    """Reviewer sub-agent with explicit model override."""
    agent = create_reviewer(model_name="deepseek-v4-pro")
    assert agent["name"] == "reviewer"
    assert agent["model"] == "deepseek-v4-pro"


def test_system_prompt_contains_key_phrases():
    """System prompt includes essential review guidance."""
    prompt = REVIEWER_SYSTEM_PROMPT
    assert "conforms" in prompt.lower()
    assert "security" in prompt.lower()
    assert "compare the implementation against the OpenAPI contract" in prompt
    assert "deterministic verification gate" in prompt
    assert "approved" in prompt
