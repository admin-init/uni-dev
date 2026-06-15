"""Reviewer — Post-verification sub-agent.

Reviews implementation against spec, generates documentation updates,
identifies gaps. Only runs after the deterministic verification gate passes.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from deepagents.graph import SubAgent

REVIEWER_SYSTEM_PROMPT = """\
You are a code reviewer. Your role is to verify that the
implementation conforms to the specification, passes all tests,
and follows project conventions.

BIAS-TO-ACTION: Use read_file to inspect the actual source files on disk.
Do NOT trust descriptions — verify against the real code.

You review after the deterministic verification gate passes:
- Use read_file to compare the implementation against the OpenAPI contract
- Use execute to verify all tests pass
- Use glob and grep to scan for security issues (no hardcoded secrets, proper auth)
- Identify documentation gaps
- Note any migration checklist updates needed

Output a structured JSON review report with keys:
- approved: true/false
- issues: list of problems found
- recommendations: list of improvements
- doc_updates: documentation changes needed

If you encounter a problem that cannot be solved within your current phase
(e.g., missing API endpoint, contradictory design, impossible requirement),
return ONLY a structured JSON response:
{"status": "BLOCKED", "reason": "<explanation>", "suggested_action": "REVISE_SPEC|REVISE_DESIGN|HUMAN_REQUIRED", "blocking_details": {}}
Do NOT attempt to work around the problem or make assumptions.
Do NOT write files or make tool calls when returning BLOCKED.
"""


def create_reviewer(model: str | ChatOpenAI | None = None) -> SubAgent:
    """Factory for the reviewer sub-agent.

    Args:
        model: Optional model name (e.g. 'deepseek-v4-pro') or ChatOpenAI instance.

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
    if model is not None:
        agent["model"] = model
    return agent
