"""Tests for core/migration_stepper.py — deterministic sequential stepper."""

from uni_dev.core.migration_stepper import migration_stepper


def test_migration_stepper_advances_index():
    """Given idx=0 and plan of 3 items, advance idx to 1 and return 'next'."""
    state = {"migration_idx": 0, "migration_plan": ["auth", "users", "orders"]}
    result = migration_stepper(state)
    assert result == {"status": "next", "migration_idx": 1}


def test_migration_stepper_mid_sequence():
    """Given idx=1 and plan of 3 items, advance to 2 and return 'next'."""
    state = {"migration_idx": 1, "migration_plan": ["auth", "users", "orders"]}
    result = migration_stepper(state)
    assert result == {"status": "next", "migration_idx": 2}


def test_migration_stepper_last_item_returns_done():
    """Given idx=2 and plan of 3 items, advance to 3, len=3 so idx+1=3 >= 3 -> done."""
    state = {"migration_idx": 2, "migration_plan": ["auth", "users", "orders"]}
    result = migration_stepper(state)
    assert result == {"status": "done", "migration_idx": 3}


def test_migration_stepper_past_end_returns_done():
    """Given idx already >= len(plan), return done without incrementing further."""
    state = {"migration_idx": 3, "migration_plan": ["auth", "users", "orders"]}
    result = migration_stepper(state)
    assert result == {"status": "done", "migration_idx": 3}


def test_migration_stepper_empty_plan():
    """Given empty migration_plan, return done immediately."""
    state = {"migration_idx": 0, "migration_plan": []}
    result = migration_stepper(state)
    assert result == {"status": "done", "migration_idx": 0}


def test_migration_stepper_single_item():
    """Given single-item plan, advancing from 0 returns done."""
    state = {"migration_idx": 0, "migration_plan": ["auth"]}
    result = migration_stepper(state)
    assert result == {"status": "done", "migration_idx": 1}


def test_migration_stepper_no_llm():
    """Migration stepper is pure Python — no LLM imports or API calls."""
    import inspect
    source = inspect.getsource(migration_stepper)
    assert "import langchain" not in source
    assert "from langchain" not in source
    assert "invoke(" not in source
    assert "openai" not in source.lower()
    assert "anthropic" not in source.lower()
