# uni-dev — Universal Backend Development Framework

Multi-agent automation for the full backend SDLC: **DDD → SDD → TDD**.
Powered by DeepSeek via langchain-openai, built on deepagents + langgraph.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Continuous Runner + TUI](#continuous-runner--tui)
- [Webhooks](#webhooks)
- [Monitoring](#monitoring)
- [Pipeline Methodology](#pipeline-methodology)
- [Architecture](#architecture)
- [Security](#security)

---

## Prerequisites

- **Python 3.11+**
- **uv** (package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **DeepSeek API key** — get one at [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys)
- **uni-kb** — the Knowledge Base library (installed automatically as a dependency)

---

## Installation

```bash
git clone git@github.com:admin-init/uni-dev.git
cd uni-dev

# Create virtual environment and install
uv venv
uv pip install -e ".[dev]"
```

The `uni-kb` dependency is resolved from GitHub automatically.

---

## Configuration

### 1. Set your DeepSeek API key

Copy the example file and add your key:

```bash
cp .env.example .env
# Edit .env and replace the placeholder:
# DEEPSEEK_API_KEY=sk-your-actual-key
```

The orchestrator reads `DEEPSEEK_API_KEY` from the environment. You can also pass it via `--api-key` or set it as an env var directly:

```bash
export DEEPSEEK_API_KEY=sk-your-actual-key
```

### 2. Model configuration (optional)

Edit `config/default.yaml` to change model assignments, temperatures, or thinking mode. Defaults are:

| Role | Model | Reasoning |
|------|-------|-----------|
| orchestrator | `deepseek-v4-pro` | high |
| domain-designer | `deepseek-v4-pro` | high |
| reviewer | `deepseek-v4-pro` | — |
| spec-writer | `deepseek-v4-flash` | — |
| code-generator | `deepseek-v4-flash` | — |
| test-generator | `deepseek-v4-flash` | — |

### 3. Webhook secret (optional)

Required if you use the webhook server:

```bash
export WEBHOOK_SECRET=your-hmac-secret
```

---

## Quick Start

### 1. Initialize a project's knowledge base

Point uni-dev at your backend source tree. This parses code into SQLite, ChromaDB, and a NetworkX dependency graph:

```bash
uni-dev init /path/to/your/backend
```

This creates a `.uni-dev/` directory with the knowledge base data.

### 2. Run the pipeline on an issue

```bash
uni-dev run "Add user avatar upload endpoint with S3 storage"
```

The orchestrator will:
1. **DDD** — `domain-designer` analyzes the domain, identifies entities/aggregates
2. **SDD** — `spec-writer` generates an OpenAPI 3.0 contract
3. **TDD** — `test-generator` writes contract + unit tests
4. **TDD** — `code-generator` implements the code to pass tests
5. **Verify** — deterministic gate checks test results
6. **Review** — `reviewer` validates the implementation

Each sub-agent task is recorded by the monitor middleware.

### 3. Check the pipeline dashboard

```bash
uni-dev status
```

Shows recent task runs, success/error counts, and average durations:

```
=== uni-dev Pipeline Status ===

Total runs:   5
Success:      4
Errors:       1
Running:      0
Avg duration: 3200ms

Agent                  Status     Duration  ID
domain-designer        success     4521ms   a1b2c3d4e5f6
spec-writer            success     2134ms   b2c3d4e5f6a1
test-generator         success     3892ms   c3d4e5f6a1b2
code-generator         error      15234ms   d4e5f6a1b2c3
code-generator         success    11023ms   e5f6a1b2c3d4
```

### 4. Start continuous watch mode

For hands-off automation, run the continuous runner with the TUI dashboard:

```bash
uni-dev watch
```

This:
- Starts a background runner that polls for pending issues every 5 seconds
- Opens a Textual TUI dashboard showing the issue queue, detail panel, and pipeline log
- Automatically invokes the orchestrator for each pending issue
- Accepts webhook events and queues them for processing
- Lets you draft new issues via an LLM-powered chat modal (press `n`)

To run headless (no dashboard):

```bash
uni-dev watch --no-tui
```

### 5. Start the webhook server (optional)

If you want issues to arrive via GitHub/Codeberg webhooks instead of the CLI:

```bash
uni-dev listen --port 8080
```

Webhook events are automatically inserted into the issue queue and picked up by `uni-dev watch`.

Then configure your GitHub/Codeberg repository's webhook settings to point to `http://your-server:8080/webhook/github`.

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `uni-dev init <path>` | Initialize knowledge base for a project |
| `uni-dev run "<issue>"` | Run the DDD→SDD→TDD pipeline (one-shot) |
| `uni-dev watch` | Start continuous runner + TUI dashboard |
| `uni-dev listen [-p PORT]` | Start webhook server (separate process) |
| `uni-dev status [-d DB]` | Show pipeline status dashboard |
| `uni-dev approve <id>` | Approve a needs_human issue |
| `uni-dev reject <id>` | Reject a needs_human issue |
| `uni-dev retry <id>` | Retry a needs_human/failed issue |
| `uni-dev --version` | Show version |
| `uni-dev --help` | Show all commands |

### `uni-dev watch` options

| Option | Description |
|--------|-------------|
| `-i, --poll-interval SECS` | Seconds between polls (default: `5`) |
| `--no-tui` | Run headless (runner only, no dashboard) |
| `--db PATH` | IssueStore database path (default: `.uni-dev/issues.db`) |
| `--monitor-db PATH` | MonitorStore database path (default: `.uni-dev/monitor.db`) |

### `uni-dev run` options

| Option | Description |
|--------|-------------|
| `-m, --model MODEL` | Model for orchestrator (default: `deepseek-v4-pro`) |
| `-k, --api-key KEY` | DeepSeek API key (default: `$DEEPSEEK_API_KEY`) |
| `-c, --classify TYPE` | Issue type: `add_feature`, `update_api`, `remove_feature`, `refactor` |
| `--no-monitor` | Disable the monitor middleware |

### `uni-dev listen` options

| Option | Description |
|--------|-------------|
| `-p, --port PORT` | Port to bind (default: `8080`) |
| `-h, --host HOST` | Host to bind (default: `0.0.0.0`) |
| `-s, --secret SECRET` | Webhook HMAC secret (default: `$WEBHOOK_SECRET`) |

### `uni-dev status` options

| Option | Description |
|--------|-------------|
| `-d, --db PATH` | Path to monitor database (default: `.uni-dev/monitor.db`) |

---

## Continuous Runner + TUI

`uni-dev watch` is the long-running mode. It handles the full automation loop:

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   uni-dev watch                          │
│                                                          │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │ Webhook    │   │ Issue Queue  │   │ Pipeline     │  │
│  │ Listener   │──►│  (SQLite)    │──►│ Runner       │  │
│  │ :8080      │   │ issues.db    │   │ (background) │  │
│  └────────────┘   └──────────────┘   └──────┬───────┘  │
│                                              │          │
│  ┌────────────┐   ┌──────────────┐           ▼          │
│  │ Chat Modal │   │ TUI Dashboard│   ┌──────────────┐  │
│  │ (press 'n')│   │ (Textual)    │   │ Orchestrator │  │
│  │ v4-flash   │   │ queue|detail │   │ (background  │  │
│  └─────┬──────┘   │ |log panel   │   │  thread)     │  │
│        │          └──────────────┘   └──────────────┘  │
│        └──────────────► Issue Queue                     │
└─────────────────────────────────────────────────────────┘
```

### Issue lifecycle

```
[webhook / chat / CLI] → pending → running → completed
                              │          │
                              │          ├── needs_human → approve → completed
                              │          │              → reject  → failed
                              │          │              → retry   → running
                              │          │
                              │          └── failed
                              │
                              └── (skipped)
```

### TUI Dashboard

```
uni-dev watch

┌─────────────┬──────────────────────────────────┐
│ Issue Queue │  Issue Detail                     │
│ ─────────── │  ─────────────                    │
│ #42 pending │  Title: Add avatar upload          │
│ #43 running │  Status: running                   │
│ #40 needs_h │  Sub-agent: code-generator         │
│ #39 done    │  Task runs: 4/5 completed          │
│ #38 failed  │                                   │
│             │  [Approve] [Reject] [Retry]       │
│─────────────│───────────────────────────────────│
│ Pipeline Log (scrolling)                        │
│ 12:03:21 Task domain-designer#abc: success       │
└──────────────────────────────────────────────────┘

Keyboard shortcuts:
  n     New Issue (opens LLM chat modal)
  r     Refresh
  q     Quit
```

### Chat Modal (press `n`)

Draft new issues using natural language. The LLM (deepseek-v4-flash) helps:
1. You describe what you need: *"Add user avatar upload with S3 storage, JPEG/PNG, max 5MB"*
2. The LLM drafts a structured title and body
3. You can iterate: *"Add JWT auth requirement"*
4. Click **Submit** → issue goes into the queue → runner picks it up

### Human-in-the-loop

When the orchestrator exhausts retries (escalate_to_human), the issue enters `needs_human` status. You can manage it via:

```bash
uni-dev approve <id>    # Accept the result, mark completed
uni-dev reject <id>     # Reject the result, mark failed
uni-dev retry <id>      # Reset to pending, try again
```

Or use the TUI buttons when the issue is selected.

### Headless mode

Run without the dashboard for CI/CD or servers:

```bash
uni-dev watch --no-tui --poll-interval 10
```

### Issue Queue database

```sql
-- .uni-dev/issues.db
issues (
    issue_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT,
    repo TEXT,
    sender TEXT,
    source TEXT,          -- "cli" | "github" | "codeberg" | "chat"
    status TEXT,           -- "pending" | "running" | "needs_human" | "completed" | "failed"
    classification TEXT,
    created_at REAL,
    updated_at REAL,
    started_at REAL,
    completed_at REAL,
    task_runs TEXT,        -- JSON array of TaskRun dicts
    error TEXT
)
```

### Programmatic access

```python
from uni_dev.store.issue_store import IssueStore

store = IssueStore(".uni-dev/issues.db")

# Insert from your own tooling
store.insert_issue({"title": "Fix timeout bug", "source": "custom"})

# Query status
pending = store.list_issues(status="pending")
needs_review = store.list_issues(status="needs_human")

# Get summary
summary = store.summary()
# {"total": 42, "pending": 3, "running": 1, "needs_human": 2, ...}
```

---

## Webhooks

### Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/webhook/github` | POST | HMAC-SHA256 (`X-Hub-Signature-256`) | GitHub issue/PR events |
| `/webhook/codeberg` | POST | HMAC-SHA256 (`X-Codeberg-Signature`) | Codeberg issue events |
| `/health` | GET | None | Server health check |

### GitHub Setup

1. Start the server: `uni-dev listen -p 8080 -s your-secret`
2. In your GitHub repo: Settings → Webhooks → Add webhook
3. Payload URL: `https://your-server:8080/webhook/github`
4. Content type: `application/json`
5. Secret: same as `-s` / `WEBHOOK_SECRET`
6. Events: "Issues" and "Pull requests"

### Codeberg Setup

1. Same server startup
2. In your Codeberg repo: Settings → Webhooks
3. Target URL: `https://your-server:8080/webhook/codeberg`
4. Secret: same as `WEBHOOK_SECRET`
5. Events: "Issues"

### How it works

When an issue is created or a PR is opened, the webhook handler:
1. Validates the HMAC-SHA256 signature
2. Extracts title, body, number, action, sender, and repo
3. Inserts the issue into the `IssueStore` queue (`.uni-dev/issues.db`, status=`pending`)
4. Returns `{status: "accepted", issue_id: "<id>"}`

The `uni-dev watch` runner picks up pending issues from the queue automatically.

---

## Monitoring

The monitor middleware records every sub-agent `task()` delegation with timing, status, and result metadata.

### Three output channels

| Channel | Location | Use |
|---------|----------|-----|
| **State** | `state["task_runs"]` | In-session querying via agent state |
| **SQLite** | `.uni-dev/monitor.db` | Multi-session history, queried by `uni-dev status` |
| **Logs/Streams** | Python logging + stream events | Real-time dashboards, debugging |

### Database schema

```sql
-- .uni-dev/monitor.db
task_runs (
    run_id TEXT PRIMARY KEY,
    subagent_type TEXT NOT NULL,     -- "domain-designer", "spec-writer", ...
    description TEXT,                 -- Task description
    parent_agent TEXT DEFAULT 'orchestrator',
    started_at REAL NOT NULL,
    completed_at REAL,
    duration_ms INTEGER,
    status TEXT DEFAULT 'running',    -- "running" | "success" | "error"
    error TEXT,
    result_length INTEGER
)
```

### Querying manually

```python
from uni_dev.monitoring.store import MonitorStore

store = MonitorStore(".uni-dev/monitor.db")

# All domain-designer runs
runs = store.query_runs(subagent_type="domain-designer")

# Failed tasks
errors = store.query_runs(status="error")

# Aggregate stats
summary = store.summary()
# {"total": 42, "success_count": 38, "error_count": 4, ...}
```

---

## Pipeline Methodology

uni-dev enforces three phases, each handled by a specialized agent:

### 1. DDD — Domain-Driven Design (`domain-designer`)

Before any code is written:
- Identify **bounded contexts** (module boundaries)
- Define **entities**, **aggregates**, **value objects**
- Map **relationships** and **invariants**

Output: domain model YAML consumed by the spec writer and code generator.

### 2. SDD — Specification-Driven Development (`spec-writer`)

Before any implementation:
- Generate a complete **OpenAPI 3.0 YAML** contract
- Define paths, request/response schemas, security schemes
- Include error responses (400, 401, 403, 404, 500)

The spec is the **source of truth** — code must conform.

### 3. TDD — Test-Driven Development (`test-generator` + `code-generator`)

**Red** → `test-generator` writes tests that **fail** (contract tests + unit tests).

**Green** → `code-generator` writes **minimal** code to pass tests, following existing patterns and conventions.

**Refactor** → after passing, the deterministic verification gate runs.

### Verification Gate (deterministic, zero LLM)

The pipeline controller is **pure Python** and cannot be overridden:
- Test exit code must pass (pytest exit 0)
- Contract must be valid (MCP `verify_contract()`)
- Max 3 retry attempts, then escalates to human review

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Issue Source                       │
│  CLI · GitHub Webhook · Codeberg Webhook · Chat     │
└───────────────────────┬──────────────────────────────┘
                        ▼
┌──────────────────────────────────────────────────────┐
│              Continuous Runner                        │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │IssueStore │  │ IssueRunner  │  │  TUI (watch) │  │
│  │ (SQLite)  │  │ (poll loop)  │  │ 3-panel dash │  │
│  └───────────┘  └──────┬───────┘  └──────────────┘  │
└────────────────────────┼──────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────┐
│  Orchestrator (deepagents create_deep_agent)          │
│  Model: deepseek-v4-pro (DeepSeek via langchain)     │
│  System prompt: DDD → SDD → TDD methodology           │
├──────────────────────────────────────────────────────┤
│  LLM Sub-Agents                                       │
│  ┌─────────────┐ ┌───────────┐ ┌──────────────┐     │
│  │ domain-     │ │ spec-     │ │ code-        │     │
│  │ designer    │ │ writer    │ │ generator    │     │
│  │ (v4-pro)    │ │ (v4-flash)│ │ (v4-flash)   │     │
│  └─────────────┘ └───────────┘ └──────────────┘     │
│  ┌─────────────┐ ┌───────────┐                       │
│  │ test-       │ │ reviewer  │                       │
│  │ generator   │ │ (v4-pro)  │                       │
│  │ (v4-flash)  │ └───────────┘                       │
│  └─────────────┘                                      │
├──────────────────────────────────────────────────────┤
│  Deterministic Core (pure Python, 0 LLM, ~50 LOC ea) │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌───────┐ │
│  │Verif.Gate│ │Retry Ctrl│ │Class.Router│ │Mig.Step│ │
│  │   ①      │ │   ②      │ │    ④      │ │  ③   │ │
│  └──────────┘ └──────────┘ └───────────┘ └───────┘ │
├──────────────────────────────────────────────────────┤
│  Middleware                                           │
│  ┌──────────────┐  ┌─────────────────┐               │
│  │ LogFilter    │  │ MonitorMiddleware│               │
│  │ (PII redact) │  │ (task tracking) │               │
│  └──────────────┘  └─────────────────┘               │
├──────────────────────────────────────────────────────┤
│  Knowledge Base (uni-kb)                              │
│  SQLite (8 tables) · ChromaDB (14 indexes) ·         │
│  NetworkX graph · MCP server (20 tools)              │
└──────────────────────────────────────────────────────┘
```

### Directory Structure

```
uni-dev/
├── pyproject.toml
├── config/default.yaml      # Model + pipeline settings
├── skills/backend-dev/       # Progressive disclosure skill
├── specs/                    # SDD specifications (per component)
├── src/uni_dev/
│   ├── main.py               # CLI entry point (click)
│   ├── orchestrator.py       # Main deepagent pipeline
│   ├── core/                 # Deterministic LangGraph nodes
│   │   ├── graph.py          # Compiled StateGraph
│   │   ├── verification_gate.py
│   │   ├── retry_controller.py
│   │   ├── classification_router.py
│   │   └── migration_stepper.py
│   ├── agents/               # LLM sub-agents
│   │   ├── domain_designer.py
│   │   ├── spec_writer.py
│   │   ├── code_generator.py
│   │   ├── test_generator.py
│   │   └── reviewer.py
│   ├── webhooks/             # Issue ingestion
│   │   ├── server.py
│   │   ├── github_handler.py
│   │   └── codeberg_handler.py
│   ├── store/                # Persistent storage
│   │   └── issue_store.py    # Issue lifecycle tracker
│   ├── tui/                  # Textual dashboard
│   │   ├── app.py            # Main TUI layout
│   │   └── chat.py           # LLM-powered issue draft
│   ├── security/             # PII/secret protection
│   │   └── log_filter.py
│   ├── monitoring/           # Pipeline observability
│   │   ├── monitor.py
│   │   └── store.py
│   └── runner.py             # Continuous pipeline loop
└── tests/                    # Mirroring src/uni_dev/
```

### Dependency Flow

```
uni-dev ──► imports ──► uni-kb (Knowledge Base)
   │                        │
│   deepagents            │   parsers/ (Java, Node.js)
│   langgraph             │   store/ (SQLite, ChromaDB, Graph)
│   langchain-openai      │   generators/ (6 spec generators)
│   click, fastapi        │   mcp_server.py (20 tools)
│   textual, textual-web  │
```

---

## Security

### Log filter

The `LogFilter` middleware redacts sensitive data from all tool call arguments and results before they reach logs or the knowledge base:

| Pattern | Replacement |
|---------|-------------|
| Bearer tokens | `Bearer <REDACTED>` |
| API keys (`api_key=...`, `api-key: ...`) | `api_key=<REDACTED>` |
| Passwords | `password=<REDACTED>` |
| Email addresses | `<EMAIL>` |
| PostgreSQL URLs | `postgresql://<CREDENTIALS>@...` |
| MongoDB URLs | `mongodb://<CREDENTIALS>@...` |
| Redis URLs | `REDIS_URL=<REDACTED>` |

### Webhook signature validation

Both GitHub and Codeberg webhook endpoints require HMAC-SHA256 signature validation. Without a valid `WEBHOOK_SECRET`, requests return `401 Unauthorized`.

### Credentials policy

- **Zero hardcoded credentials** — all secrets via environment variables (`DEEPSEEK_API_KEY`, `WEBHOOK_SECRET`)
- **`.env` files** — never committed (`.gitignore` excludes `*.env`)
- **API keys** — never logged, never stored in the knowledge base

---

## Running Tests

```bash
uv run pytest -v        # Run all 148 tests
uv run ruff check src/  # Lint
```
