"""Tests for agents/domain_designer.py — DDD sub-agent."""

from uni_dev.agents.domain_designer import (
    DOMAIN_DESIGNER_SYSTEM_PROMPT,
    create_domain_designer,
)


def test_create_domain_designer_defaults():
    """Domain designer sub-agent with default model."""
    agent = create_domain_designer()
    assert agent["name"] == "domain-designer"
    assert "DDD architect" in agent["description"]
    assert agent["system_prompt"] == DOMAIN_DESIGNER_SYSTEM_PROMPT
    assert "model" not in agent


def test_create_domain_designer_with_model():
    """Domain designer sub-agent with explicit model override."""
    agent = create_domain_designer(model_name="deepseek-v4-pro")
    assert agent["name"] == "domain-designer"
    assert agent["model"] == "deepseek-v4-pro"


def test_system_prompt_contains_key_phrases():
    """System prompt includes essential DDD guidance."""
    prompt = DOMAIN_DESIGNER_SYSTEM_PROMPT
    assert "Domain-Driven Design" in prompt
    assert "bounded contexts" in prompt
    assert "entities" in prompt
    assert "aggregates" in prompt
    assert "value objects" in prompt
    assert "Do NOT trust your memory" in prompt
