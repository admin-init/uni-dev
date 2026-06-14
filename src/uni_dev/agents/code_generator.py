"""Code Generator — TDD phase sub-agent.

Implements code conforming to the OpenAPI spec. Uses test failures
to guide corrections.
"""

from __future__ import annotations

from deepagents.graph import SubAgent

CODE_GENERATOR_SYSTEM_PROMPT = """\
You are a backend implementation engineer. Your role is to write
code that conforms to the OpenAPI specification and passes all tests.

You follow Test-Driven Development:
- Read the failing tests first — they define what to implement
- Write minimal code to make tests pass (Green phase)
- Refactor for clarity, performance, and convention adherence

Use tools:
- MCP tools to query the existing codebase for patterns and conventions
- Shell to run builds, lints, and tests
- Filesystem to read existing files and write new ones

Respect existing code patterns:
- Follow the project's coding conventions
- Use existing utilities and libraries
- Match naming, formatting, and architectural patterns
"""


def create_code_generator(model_name: str | None = None) -> SubAgent:
    """Factory for the code generator sub-agent.

    Args:
        model_name: Optional model override (e.g. 'deepseek-v4-flash').

    Returns:
        SubAgent dict configured for code implementation.
    """
    agent: SubAgent = {
        "name": "code-generator",
        "description": (
            "Backend implementation engineer. Writes code to conform to the "
            "OpenAPI spec and pass all tests. Use when specs and tests are ready."
        ),
        "system_prompt": CODE_GENERATOR_SYSTEM_PROMPT,
    }
    if model_name is not None:
        agent["model"] = model_name
    return agent
