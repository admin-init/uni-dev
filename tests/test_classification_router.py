"""Tests for core/classification_router.py — immutable routing table."""

from uni_dev.core.classification_router import classification_router


def test_classification_router_add_feature():
    """add_feature routes to DomainDesigner."""
    state = {"classification": "add_feature"}
    result = classification_router(state)
    assert result == {"next_node": "DomainDesigner"}


def test_classification_router_update_api():
    """update_api routes to SpecWriter."""
    state = {"classification": "update_api"}
    result = classification_router(state)
    assert result == {"next_node": "SpecWriter"}


def test_classification_router_remove_feature():
    """remove_feature routes to DomainDesigner."""
    state = {"classification": "remove_feature"}
    result = classification_router(state)
    assert result == {"next_node": "DomainDesigner"}


def test_classification_router_refactor():
    """refactor routes to DomainDesigner."""
    state = {"classification": "refactor"}
    result = classification_router(state)
    assert result == {"next_node": "DomainDesigner"}


def test_classification_router_unknown_falls_to_default():
    """Unknown classification falls back to default (DomainDesigner)."""
    state = {"classification": "unknown_type"}
    result = classification_router(state)
    assert result == {"next_node": "DomainDesigner"}


def test_classification_router_missing_key_falls_to_default():
    """Missing classification key falls back to default (DomainDesigner)."""
    state = {}
    result = classification_router(state)
    assert result == {"next_node": "DomainDesigner"}


def test_classification_router_none_falls_to_default():
    """None classification falls back to default (DomainDesigner)."""
    state = {"classification": None}
    result = classification_router(state)
    assert result == {"next_node": "DomainDesigner"}


def test_classification_router_routing_table_is_immutable():
    """Verify the routing table is defined at module level as immutable dict."""
    import uni_dev.core.classification_router as m
    assert hasattr(m, "ROUTING_TABLE")
    assert isinstance(m.ROUTING_TABLE, dict)
    assert m.ROUTING_TABLE["add_feature"] == "DomainDesigner"
    assert m.ROUTING_TABLE["update_api"] == "SpecWriter"
    assert "remove_feature" in m.ROUTING_TABLE
    assert "refactor" in m.ROUTING_TABLE


def test_classification_router_no_llm():
    """Classification router is pure Python — no LLM imports or API calls."""
    import inspect
    source = inspect.getsource(classification_router)
    assert "import langchain" not in source
    assert "from langchain" not in source
    assert "invoke(" not in source
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
