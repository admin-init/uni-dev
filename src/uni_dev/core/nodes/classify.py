from __future__ import annotations

from typing import Any

VALID_CLASSIFICATIONS = {"add_feature", "update_api", "remove_feature", "refactor"}


def classify_node(state: dict[str, Any]) -> dict[str, Any]:
    """Classify the issue type. Uses state classification or defaults."""
    classification = state.get("classification", "add_feature")
    if classification not in VALID_CLASSIFICATIONS:
        classification = "add_feature"
    return {"classification": classification}
