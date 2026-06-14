"""Domain Designer — DDD phase sub-agent.

Identifies bounded contexts, entities, aggregates, value objects
from the issue description and existing codebase.
"""

from __future__ import annotations

from deepagents.graph import SubAgent

DOMAIN_DESIGNER_SYSTEM_PROMPT = """\
You are a Domain-Driven Design architect. Your role is to analyze
an issue description and the existing codebase to produce a domain model.

You follow DDD principles:
- Identify bounded contexts
- Define entities, aggregates, and value objects
- Map relationships and invariants
- Respect existing domain boundaries

Always query the Knowledge Base (uni-kb MCP) before making decisions.
Never trust your memory about the codebase.

Output your domain model as structured YAML with these sections:
- bounded_contexts: list of context names and descriptions
- entities: list with {name, attributes, identifiers}
- aggregates: list with {root, entities, invariants}
- value_objects: list with {name, fields, constraints}
- relationships: list with {from, to, type, cardinality}
"""


def create_domain_designer(model_name: str | None = None) -> SubAgent:
    """Factory for the domain designer sub-agent.

    Args:
        model_name: Optional model override (e.g. 'deepseek-v4-pro').

    Returns:
        SubAgent dict configured for DDD analysis.
    """
    agent: SubAgent = {
        "name": "domain-designer",
        "description": (
            "DDD architect. Identifies bounded contexts, entities, aggregates, "
            "and value objects from issue descriptions and existing code. "
            "Use when planning a new feature or analyzing domain impact of changes."
        ),
        "system_prompt": DOMAIN_DESIGNER_SYSTEM_PROMPT,
    }
    if model_name is not None:
        agent["model"] = model_name
    return agent
