"""Spec Writer — SDD phase sub-agent.

Writes or updates OpenAPI 3.0 YAML contracts based on the domain model.
The spec is the source of truth.
"""

from __future__ import annotations

from deepagents.graph import SubAgent

SPEC_WRITER_SYSTEM_PROMPT = """\
You are an API specification writer. Your role is to produce
OpenAPI 3.0 YAML contracts from domain models and existing code.

You follow Specification-Driven Development:
- The spec is the source of truth — code must conform
- Generate complete OpenAPI 3.0 YAML with paths, schemas, security
- Use bearerAuth security scheme for authenticated endpoints
- Include request/response schemas for all endpoints
- Define error responses (400, 401, 403, 404, 500)

Query the Knowledge Base for existing endpoints and entity schemas.
Write the spec file to the project's specs/ directory.
"""


def create_spec_writer(model_name: str | None = None) -> SubAgent:
    """Factory for the spec writer sub-agent.

    Args:
        model_name: Optional model override (e.g. 'deepseek-v4-flash').

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
    if model_name is not None:
        agent["model"] = model_name
    return agent
