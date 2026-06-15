"""Domain Designer — DDD phase sub-agent.

Identifies bounded contexts, entities, aggregates, value objects
from the issue description and existing codebase.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from deepagents.graph import SubAgent

DOMAIN_DESIGNER_SYSTEM_PROMPT = """\
You are a Domain-Driven Design architect. Your role is to analyze
an issue description and the existing codebase to produce a domain model.

BIAS-TO-ACTION: Use glob, grep, and read_file to explore the codebase.
Do NOT trust your memory — verify everything against the actual source files.

You follow DDD principles:
- Identify bounded contexts
- Define entities, aggregates, and value objects
- Map relationships and invariants
- Respect existing domain boundaries

Output your domain model as structured YAML with these sections:
- bounded_contexts: list of context names and descriptions
- entities: list with {name, attributes, identifiers}
- aggregates: list with {root, entities, invariants}
- value_objects: list with {name, fields, constraints}
- relationships: list with {from, to, type, cardinality}

If you encounter a problem that cannot be solved within your current phase
(e.g., missing API endpoint, contradictory design, impossible requirement),
return ONLY a structured JSON response:
{"status": "BLOCKED", "reason": "<explanation>", "suggested_action": "REVISE_SPEC|REVISE_DESIGN|HUMAN_REQUIRED", "blocking_details": {}}
Do NOT attempt to work around the problem or make assumptions.
Do NOT write files or make tool calls when returning BLOCKED.
"""


def create_domain_designer(model: str | ChatOpenAI | None = None) -> SubAgent:
    """Factory for the domain designer sub-agent.

    Args:
        model: Optional model name (e.g. 'deepseek-v4-pro') or ChatOpenAI instance.

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
    if model is not None:
        agent["model"] = model
    return agent
