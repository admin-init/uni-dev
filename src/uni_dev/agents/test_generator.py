"""Test Generator — TDD phase sub-agent.

Generates contract tests and unit tests BEFORE implementation code is written.
Tests mirror source structure.
"""

from __future__ import annotations

from deepagents.graph import SubAgent

TEST_GENERATOR_SYSTEM_PROMPT = """\
You are a test engineer. Your role is to generate contract tests
and unit tests BEFORE any implementation code is written.

You follow Test-Driven Development:
- Write tests that will FAIL initially (Red phase)
- Contract tests: verify API responses match the OpenAPI spec
- Unit tests: verify business logic in isolation
- Tests mirror the source structure (src/foo/bar.py -> tests/test_bar.py)

Use tools:
- get_api_contract to read the spec
- verify_contract to validate responses
- Shell to run test frameworks (pytest, jest, etc.)

Output complete test files with proper imports, fixtures, and assertions.
"""


def create_test_generator(model_name: str | None = None) -> SubAgent:
    """Factory for the test generator sub-agent.

    Args:
        model_name: Optional model override (e.g. 'deepseek-v4-flash').

    Returns:
        SubAgent dict configured for test generation.
    """
    agent: SubAgent = {
        "name": "test-generator",
        "description": (
            "TDD test engineer. Writes contract tests and unit tests BEFORE "
            "implementation. Use when a spec is complete and tests are needed."
        ),
        "system_prompt": TEST_GENERATOR_SYSTEM_PROMPT,
    }
    if model_name is not None:
        agent["model"] = model_name
    return agent
