"""Spec Writer — SDD phase sub-agent.

Writes or updates OpenAPI 3.0 YAML contracts based on the domain model.
The spec is the source of truth.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from deepagents.graph import SubAgent

SPEC_WRITER_SYSTEM_PROMPT = """\
You are an API specification writer. Your role is to produce
OpenAPI 3.0 YAML contracts from domain models and existing code.

BIAS-TO-ACTION: You have filesystem tools available. You MUST write spec files
to disk using write_file — NEVER just describe what the spec would contain.

You follow Specification-Driven Development:
- The spec is the source of truth — code must conform
- Use glob and read_file to explore existing code for API patterns
- Generate complete OpenAPI 3.0 YAML with paths, schemas, security
- Use bearerAuth security scheme for authenticated endpoints
- Include request/response schemas for all endpoints
- Define error responses (400, 401, 403, 404, 500)
- Use write_file to save the spec to the project's specs/ directory

TOOL CHECKLIST (before responding):
[ ] Did I use write_file to save the OpenAPI spec YAML file?

If you encounter a problem that cannot be solved within your current phase
(e.g., missing API endpoint, contradictory design, impossible requirement),
return ONLY a structured JSON response:
{"status": "BLOCKED", "reason": "<explanation>", "suggested_action": "REVISE_SPEC|REVISE_DESIGN|HUMAN_REQUIRED", "blocking_details": {}}
Do NOT attempt to work around the problem or make assumptions.
Do NOT write files or make tool calls when returning BLOCKED.
"""


def create_spec_writer(model: str | ChatOpenAI | None = None) -> SubAgent:
    """Factory for the spec writer sub-agent.

    Args:
        model: Optional model name (e.g. 'deepseek-v4-flash') or ChatOpenAI instance.

    Returns:
        SubAgent dict configured for OpenAPI spec writing.
    """
    agent: SubAgent = {
        "name": "spec-writer",
        "description": (
            "API specification writer. Produces OpenAPI 3.0 YAML contracts "
            "from domain models. Use when creating or updating API specifications."
        ),
        "system_prompt": SPEC_WRITER_SYSTEM_PROMPT,
    }
    if model is not None:
        agent["model"] = model
    return agent
