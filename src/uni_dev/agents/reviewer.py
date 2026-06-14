"""Reviewer — Post-verification sub-agent.

Reviews implementation against spec, generates documentation updates,
identifies gaps. Only runs after the deterministic verification gate passes.
"""

from __future__ import annotations

from deepagents.graph import SubAgent

REVIEWER_SYSTEM_PROMPT = """\
You are a code reviewer. Your role is to verify that the
implementation conforms to the specification, passes all tests,
and follows project conventions.

You review after the deterministic verification gate passes:
- Compare API responses against the OpenAPI contract
- Verify all tests pass
- Check for security issues (no hardcoded secrets, proper auth)
- Identify documentation gaps
- Generate migration checklist updates

Use tools:
- compare_api_responses to validate against contract
- verify_contract for schema conformance
- get_migration_checklist for migration status
- All MCP exploration tools

Output a structured review report:
- approved: true/false
- issues: list of problems found
- recommendations: list of improvements
- doc_updates: documentation changes needed
"""


def create_reviewer(model_name: str | None = None) -> SubAgent:
    """Factory for the reviewer sub-agent.

    Args:
        model_name: Optional model override (e.g. 'deepseek-v4-pro').

    Returns:
        SubAgent dict configured for post-verification review.
    """
    agent: SubAgent = {
        "name": "reviewer",
        "description": (
            "Code reviewer. Validates implementation against spec, checks "
            "for security issues, identifies documentation gaps. Use after "
            "all tests pass to review and document changes."
        ),
        "system_prompt": REVIEWER_SYSTEM_PROMPT,
    }
    if model_name is not None:
        agent["model"] = model_name
    return agent
