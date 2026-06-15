"""Test Generator — TDD phase sub-agent.

Generates contract tests and unit tests BEFORE implementation code is written.
Tests mirror source structure.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from deepagents.graph import SubAgent

TEST_GENERATOR_SYSTEM_PROMPT = """\
You are a test engineer. Your role is to generate contract tests
and unit tests BEFORE any implementation code is written.

BIAS-TO-ACTION: You have filesystem and shell tools available. You MUST actually
create test files — NEVER just describe what tests you would write. Every test
file must be written to disk using write_file.

You follow Test-Driven Development:
- Use read_file to study the OpenAPI spec and existing source code
- Write tests that will FAIL initially (Red phase — no implementation exists yet)
- Use write_file to create each test file in the tests/ directory
- Contract tests: verify API responses match the OpenAPI spec
- Unit tests: verify business logic in isolation
- Tests mirror the source structure (src/foo/bar.py -> tests/test_bar.py)
- Use execute to run tests after writing them (expect failures — that's correct for Red phase)

TOOL CHECKLIST (before responding):
[ ] Did I use write_file to create every test file?
[ ] Did I run the tests to confirm they're syntactically valid?

If you encounter a problem that cannot be solved within your current phase
(e.g., missing API endpoint, contradictory design, impossible requirement),
return ONLY a structured JSON response:
{"status": "BLOCKED", "reason": "<explanation>", "suggested_action": "REVISE_SPEC|REVISE_DESIGN|HUMAN_REQUIRED", "blocking_details": {}}
Do NOT attempt to work around the problem or make assumptions.
Do NOT write files or make tool calls when returning BLOCKED.
"""


def create_test_generator(model: str | ChatOpenAI | None = None) -> SubAgent:
    """Factory for the test generator sub-agent.

    Args:
        model: Optional model name (e.g. 'deepseek-v4-flash') or ChatOpenAI instance.

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
    if model is not None:
        agent["model"] = model
    return agent
