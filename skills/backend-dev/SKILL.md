# Backend Development Skill

> Progressive disclosure skill for uni-dev agents

## Methodology

uni-dev follows **DDD → SDD → TDD**:

1. **Domain-Driven Design** — Identify bounded contexts, entities, aggregates, value objects before any code.
2. **Specification-Driven Development** — Write OpenAPI 3.0 YAML contracts before implementation. The spec is the source of truth.
3. **Test-Driven Development** — Write tests first (Red), implement to pass (Green), refactor.

## Knowledge Base

The Knowledge Base (uni-kb) is the **single source of truth** about the codebase. Always query it before making decisions. Never trust memory.

### Key MCP Tools

| Tool | Use |
|------|-----|
| `search_code` | Find code by keyword or semantic search |
| `get_api_contract` | Read OpenAPI spec for an endpoint |
| `get_entity_spec` | Get entity/table schema |
| `get_business_logic_doc` | Read method implementation docs |
| `get_dependency_graph` | Understand module relationships |
| `verify_contract` | Validate implementation against spec |
| `compare_api_responses` | Check API responses match contract |
| `get_migration_checklist` | Check migration status |

## Deterministic Rules

These are **non-negotiable**:
- Verification gate is pure Python — no LLM override
- Retry limit is fixed at 3 attempts — no 4th try
- Migration stepping is sequential — no skipping
- Classification routing is immutable — no dynamic dispatch

## File Conventions

- Tests mirror source: `src/foo/bar.py` → `tests/test_bar.py`
- Python type hints on all public functions
- Google-style docstrings
- Zero `print()` — use `logging`
- Max line length: 100 characters
- No hardcoded secrets — use env vars

## Security

- All credentials via environment variables or config
- Never log or store API keys, tokens, or passwords
- Auth check on every endpoint that requires it
