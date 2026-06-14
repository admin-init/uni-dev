# uni-dev — Backend Development Automation

Multi-agent framework that automates the full backend SDLC: DDD → SDD → TDD.

Built on deepagents (low-workload harness) + langgraph (controllable key nodes). Consumes uni-kb as its single source of truth.

## Design Principles

| # | Principle | Implementation |
|---|-----------|----------------|
| 1 | Specification First | OpenAPI contract written before any code |
| 2 | Test Before Code | Contract + unit tests before implementation |
| 3 | Domain Model First | Entities, aggregates, bounded contexts first |
| 4 | Deterministic Control | Verification gates, retry, routing — pure Python |
| 5 | LLM for Intelligence | Code gen, architecture, specs — LLM sub-agents |
| 6 | Single Source of Truth | All agents query uni-kb, never trust memory |

## Architecture

```
Issue (GitHub / Codeberg / CLI)
  │
  ▼
┌──────────────────────────────────────────────┐
│  Orchestrator (deepagents create_deep_agent)  │
│  System prompt: DDD → SDD → TDD methodology   │
├──────────────────────────────────────────────┤
│  LLM Sub-Agents                               │
│  ┌────────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ domain-    │ │ spec-    │ │ code-       │ │
│  │ designer   │ │ writer   │ │ generator   │ │
│  └────────────┘ └──────────┘ └─────────────┘ │
│  ┌────────────┐ ┌──────────┐                 │
│  │ test-      │ │ reviewer │                 │
│  │ generator  │ └──────────┘                 │
│  └────────────┘                              │
├──────────────────────────────────────────────┤
│  Deterministic Control (pure Python, 0 LLM)   │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐    │
│  │Verif.Gate│ │Retry Ctrl│ │Class.Router│    │
│  │   ①      │ │   ②      │ │    ④      │    │
│  └──────────┘ └──────────┘ └───────────┘    │
│  ┌───────────┐                               │
│  │Mig.Stepper│                               │
│  │    ③      │                               │
│  └───────────┘                               │
├──────────────────────────────────────────────┤
│  Knowledge Base (uni-kb)                      │
│  SQLite · ChromaDB · NetworkX · MCP           │
└──────────────────────────────────────────────┘
```

## Phase 5: Deterministic Core

### 5.1 Four LangGraph Nodes (`core/`)

Zero LLM calls. Cannot be overridden, hallucinated, or skipped. ~50 LOC total.

| # | Node | File | Logic | LOC |
|---|------|------|-------|-----|
| ① | Verification Gate | `core/verification_gate.py` | Reads MCP `compare_api_responses()` + `verify_contract()` + test exit code. Returns `pass` / `fail`. | ~16 |
| ② | Retry Controller | `core/retry_controller.py` | `attempts < 3 ? "retry" : "escalate_to_human"` | ~10 |
| ③ | Migration Stepper | `core/migration_stepper.py` | `idx += 1; return "done" if idx >= len(plan) else "next"` | ~11 |
| ④ | Classification Router | `core/classification_router.py` | Dict lookup: `routes.get(type, default)`. Immutable table. | ~13 |

### 5.2 Compiled StateGraph (`core/graph.py`)

```
[START] → ClassificationRouter
  ├─ "add_feature"  → DomainDesigner → SpecWriter → TestGenerator → CodeGenerator → VerificationGate
  ├─ "update_api"   → SpecWriter                    → TestGenerator → CodeGenerator → VerificationGate
  ├─ "remove"       → DomainDesigner → SpecWriter                    → CodeGenerator → VerificationGate
  └─ "refactor"     → DomainDesigner → SpecWriter → TestGenerator → CodeGenerator → VerificationGate

VerificationGate
  ├─ "pass"         → Reviewer → [END]
  └─ "fail"         → RetryController
                        ├─ "retry"            → back to CodeGenerator
                        └─ "escalate_to_human" → [END]
```

### 5.3 State Schema

```python
class UniDevState(TypedDict):
    messages: list[BaseMessage]
    classification: str       # add_feature | update_api | remove | refactor
    attempt_count: int
    test_results: dict        # {pass: bool, failures: list, output: str}
    migration_idx: int
    migration_plan: list[str]
    current_phase: str        # ddd | sdd | tdd | verify | done
    kb_path: str              # .uni-dev/ path
```

## Phase 6: Orchestrator + Sub-Agents

### 6.1 Orgestrator (`orchestrator.py`)

Main deepagent that wraps the deterministic graph. Sub-agents for creative/LLM work.

```python
agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    system_prompt="DDD → SDD → TDD methodology. Query KB before decisions.",
    subagents=[
        domain_designer_subagent,
        spec_writer_subagent,
        code_generator_subagent,
        test_generator_subagent,
        reviewer_subagent,
        CompiledSubAgent(
            name="pipeline-controller",
            description="Deterministic workflow controller.",
            runnable=compile_pipeline_graph(),
        ),
    ],
    skills=["skills/backend-dev/"],
)
```

### 6.2 Sub-Agents (`agents/`)

| Agent | Phase | Responsibility | Key Tools |
|-------|-------|----------------|-----------|
| `domain_designer.py` | DDD | Identify entities, aggregates, bounded contexts | `search_code`, `get_class_structure`, `get_dependency_graph` |
| `spec_writer.py` | SDD | Write OpenAPI 3.0 YAML contracts | `get_api_contract`, `get_entity_spec`, filesystem |
| `test_generator.py` | TDD | Contract tests + unit tests (before code) | `get_api_contract`, `verify_contract`, shell |
| `code_generator.py` | TDD | Implement from spec, fix from test failures | filesystem, shell, `get_business_logic_doc` |
| `reviewer.py` | Post | Verify, document, identify gaps | All MCP tools, `compare_api_responses` |

## Phase 7: Security Filter

### `security/log_filter.py`

Middleware that intercepts tool call args/results — redacts PII/secrets before logging or KB insertion.

Patterns:
- JWT tokens (`Bearer eyJ...`)
- API keys (`api_key=sk-...`)
- Passwords (`password=...`)
- Email addresses
- Database connection strings
- Redis URLs

Integrates as a deepagent middleware that wraps all tool calls.

## Phase 8: Webhooks + CLI

### CLI (`main.py`)

```bash
uni-dev init /path/to/project     # Scaffold .uni-dev/ with KB
uni-dev listen --port 8080        # Start webhook server
uni-dev run "Add avatar upload"   # Single-shot pipeline run
uni-dev status                    # Migration dashboard
```

### Webhooks (`webhooks/`)

| Endpoint | Source |
|----------|--------|
| `POST /webhook/github` | GitHub Issues / PR events |
| `POST /webhook/codeberg` | Codeberg / Tea issues |

FastAPI server. Validates payload, extracts issue content, enqueues to orchestrator.

## Dependencies

```
uni-kb
deepagents>=0.5.3
langgraph
langchain
langchain-openai
langchain-anthropic
click
fastapi
uvicorn
pyyaml
```

## Pipeline Flow Summary

```
Issue Received → ClassificationRouter
  → [DDD] DomainDesigner queries KB, outputs domain model
  → [SDD] SpecWriter generates/updates OpenAPI contract
  → [TDD] TestGenerator writes tests
  → [TDD] CodeGenerator implements code
  → [TDD] VerificationGate checks tests pass + contract valid
    → pass: Reviewer documents, updates KB → END
    → fail: RetryController (max 3) → back to CodeGenerator
         → exhausted: escalate_to_human → END
```
