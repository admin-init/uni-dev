"""Tests for agents/spec_writer.py — SDD sub-agent."""

from uni_dev.agents.spec_writer import (
    SPEC_WRITER_SYSTEM_PROMPT,
    create_spec_writer,
)


def test_create_spec_writer_defaults():
    """Spec writer sub-agent with default model."""
    agent = create_spec_writer()
    assert agent["name"] == "spec-writer"
    assert "specification" in agent["description"].lower()
    assert agent["system_prompt"] == SPEC_WRITER_SYSTEM_PROMPT
    assert "model" not in agent


def test_create_spec_writer_with_model():
    """Spec writer sub-agent with explicit model override."""
    agent = create_spec_writer(model_name="deepseek-v4-flash")
    assert agent["name"] == "spec-writer"
    assert agent["model"] == "deepseek-v4-flash"


def test_system_prompt_contains_key_phrases():
    """System prompt includes essential SDD guidance."""
    prompt = SPEC_WRITER_SYSTEM_PROMPT
    assert "OpenAPI 3.0" in prompt
    assert "source of truth" in prompt
    assert "bearerAuth" in prompt
    assert "Specification-Driven Development" in prompt
