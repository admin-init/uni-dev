from __future__ import annotations

from typing import Any

ROUTING_TABLE: dict[str, str] = {
    "add_feature": "DomainDesigner",
    "update_api": "SpecWriter",
    "remove_feature": "DomainDesigner",
    "refactor": "DomainDesigner",
}

_DEFAULT_NODE = "DomainDesigner"


def classification_router(state: dict[str, Any]) -> dict[str, str]:
    """Routes issue classification to the next pipeline node.

    Uses an immutable routing table. LLM classifies; code routes.

    Args:
        state: UniDevState dict containing classification.

    Returns:
        {"next_node": "<node_name>"} based on classification lookup.
    """
    classification: Any = state.get("classification")
    next_node: str = _DEFAULT_NODE
    if isinstance(classification, str) and classification in ROUTING_TABLE:
        next_node = ROUTING_TABLE[classification]
    return {"next_node": next_node}
