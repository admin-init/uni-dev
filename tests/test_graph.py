"""Tests for core/graph.py — compiled StateGraph wiring and LLM agent nodes."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from uni_dev.core.graph import (
    UniDevState,
    _code_generator_node,
    _create_node_model,
    _domain_designer_node,
    _extract_code_block,
    _parse_file_paths,
    _reviewer_node,
    _spec_writer_node,
    _test_generator_node,
    build_graph,
)


def test_uni_dev_state_typed_dict():
    """UniDevState can be instantiated with all fields including new optional ones."""
    state: UniDevState = {
        "messages": [],
        "classification": "add_feature",
        "attempt_count": 0,
        "test_results": {"pass": False, "failures": [], "output": ""},
        "migration_idx": 0,
        "migration_plan": [],
        "current_phase": "ddd",
        "kb_path": "/tmp/.uni-dev",
        "domain_model": {},
        "api_spec": "",
        "test_files": [],
        "modified_files": [],
        "review_report": {},
    }
    assert state["classification"] == "add_feature"
    assert state["attempt_count"] == 0
    assert state["current_phase"] == "ddd"


def test_uni_dev_state_minimal_fields():
    """UniDevState with only required fields (optional ones omitted)."""
    state: UniDevState = {
        "messages": [],
        "classification": "refactor",
        "attempt_count": 0,
        "test_results": {"pass": True, "failures": [], "output": ""},
        "migration_idx": 0,
        "migration_plan": [],
        "current_phase": "sdd",
        "kb_path": "",
    }
    assert state["classification"] == "refactor"


def test_build_graph_returns_compiled_graph():
    """build_graph returns a compiled graph with expected attributes."""
    graph = build_graph()
    assert graph is not None


def test_build_graph_has_required_nodes():
    """The compiled graph contains all 4 deterministic core nodes."""
    graph = build_graph()
    graph_dict = graph.get_graph()
    node_names = set(graph_dict.nodes)
    required = {
        "classification_router",
        "verification_gate",
        "retry_controller",
        "migration_stepper",
    }
    assert required.issubset(node_names), f"Missing nodes: {required - node_names}"


def test_build_graph_has_llm_agent_nodes():
    """The compiled graph contains all 5 LLM agent nodes."""
    graph = build_graph()
    graph_dict = graph.get_graph()
    node_names = set(graph_dict.nodes)
    required = {
        "DomainDesigner",
        "SpecWriter",
        "TestGenerator",
        "CodeGenerator",
        "Reviewer",
    }
    assert required.issubset(node_names), f"Missing nodes: {required - node_names}"


def test_extract_code_block_yaml():
    """Extract YAML content from a markdown code fence."""
    raw = "Some text\n```yaml\nkey: value\n```\nMore text"
    result = _extract_code_block(raw, "yaml")
    assert result == "key: value"


def test_extract_code_block_json():
    """Extract JSON content from a markdown code fence."""
    raw = '```json\n{"approved": true}\n```'
    result = _extract_code_block(raw, "json")
    assert result == '{"approved": true}'


def test_extract_code_block_no_language():
    """Extract content from a code fence without language tag."""
    raw = "```\nsome code\n```"
    result = _extract_code_block(raw)
    assert result == "some code"


def test_extract_code_block_no_fence():
    """Return raw content when no code fence is present."""
    raw = "plain text output"
    result = _extract_code_block(raw)
    assert result == "plain text output"


def test_parse_file_paths_extracts_source_paths():
    """Parse file paths from text with various prefixes."""
    text = (
        "### Files\n"
        "- src/app/routes.py\n"
        "* tests/test_routes.py\n"
        "  - src/models/user.py\n"
        "  * src/services/auth.py\n"
    )
    paths = _parse_file_paths(text)
    assert "src/app/routes.py" in paths
    assert "tests/test_routes.py" in paths
    assert "src/models/user.py" in paths
    assert "src/services/auth.py" in paths


def test_parse_file_paths_ignores_non_paths():
    """Non-file-path lines are excluded."""
    text = "This is a description\n- src/main.py\nAnother sentence"
    paths = _parse_file_paths(text)
    assert paths == ["src/main.py"]


def test_domain_designer_node_returns_domain_model():
    """DDD node invokes LLM and returns domain_model state update."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="""\
```yaml
bounded_contexts:
  - name: UserManagement
entities:
  - name: User
    attributes:
      - id
      - name
```""")
    with patch("uni_dev.core.graph._create_node_model", return_value=mock_model):
        state: UniDevState = {
            "messages": [HumanMessage(content="Add user avatar upload endpoint")],
            "classification": "add_feature",
            "attempt_count": 0,
            "test_results": {},
            "migration_idx": 0,
            "migration_plan": [],
            "current_phase": "ddd",
            "kb_path": "",
        }
        result = _domain_designer_node(state)
    assert "domain_model" in result
    assert result["domain_model"]["bounded_contexts"][0]["name"] == "UserManagement"
    assert result["current_phase"] == "sdd"
    assert len(result["messages"]) == 1


def test_spec_writer_node_returns_api_spec():
    """SDD node invokes LLM and returns api_spec state update."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="""\
```yaml
openapi: 3.0.0
info:
  title: Test API
paths:
  /users:
    get:
      summary: List users
```""")
    with patch("uni_dev.core.graph._create_node_model", return_value=mock_model):
        state: UniDevState = {
            "messages": [],
            "classification": "add_feature",
            "attempt_count": 0,
            "test_results": {},
            "migration_idx": 0,
            "migration_plan": [],
            "current_phase": "sdd",
            "kb_path": "",
            "domain_model": {"bounded_contexts": [{"name": "UserManagement"}]},
        }
        result = _spec_writer_node(state)
    assert result["api_spec"].startswith("openapi: 3.0.0")
    assert result["current_phase"] == "tdd"


def test_test_generator_node_returns_test_files():
    """TDD test generator node invokes LLM and returns test_files list."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="""\
### Test Files
- tests/test_users.py
- tests/test_auth.py
- tests/test_profiles.py
""")
    with patch("uni_dev.core.graph._create_node_model", return_value=mock_model):
        state: UniDevState = {
            "messages": [],
            "classification": "add_feature",
            "attempt_count": 0,
            "test_results": {},
            "migration_idx": 0,
            "migration_plan": [],
            "current_phase": "tdd",
            "kb_path": "",
            "api_spec": "openapi: 3.0.0\npaths: {}",
        }
        result = _test_generator_node(state)
    assert len(result["test_files"]) == 3
    assert "tests/test_users.py" in result["test_files"]


def test_code_generator_node_returns_modified_files():
    """TDD code generator node invokes LLM and returns modified_files and test_results."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="""\
### Files
- src/routes/users.py
- src/services/user_service.py
""")
    with patch("uni_dev.core.graph._create_node_model", return_value=mock_model):
        state: UniDevState = {
            "messages": [],
            "classification": "add_feature",
            "attempt_count": 0,
            "test_results": {},
            "migration_idx": 0,
            "migration_plan": [],
            "current_phase": "tdd",
            "kb_path": "",
            "api_spec": "openapi: 3.0.0",
            "test_files": ["tests/test_users.py"],
        }
        result = _code_generator_node(state)
    assert len(result["modified_files"]) == 2
    assert result["test_results"]["pass"] is True


def test_reviewer_node_returns_review_report():
    """Reviewer node invokes LLM and returns review_report state update."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="""\
```json
{"approved": true, "issues": [], "recommendations": [], "doc_updates": []}
```""")
    with patch("uni_dev.core.graph._create_node_model", return_value=mock_model):
        state: UniDevState = {
            "messages": [],
            "classification": "add_feature",
            "attempt_count": 0,
            "test_results": {"pass": True, "failures": []},
            "migration_idx": 0,
            "migration_plan": [],
            "current_phase": "done",
            "kb_path": "",
            "api_spec": "openapi: 3.0.0",
            "modified_files": ["src/routes/users.py"],
        }
        result = _reviewer_node(state)
    assert result["review_report"]["approved"] is True


def test_domain_designer_node_fallback_on_bad_yaml():
    """DDD node stores raw_output when YAML parsing fails."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="Just some unstructured text")
    with patch("uni_dev.core.graph._create_node_model", return_value=mock_model):
        state: UniDevState = {
            "messages": [HumanMessage(content="Fix bug in login")],
            "classification": "add_feature",
            "attempt_count": 0,
            "test_results": {},
            "migration_idx": 0,
            "migration_plan": [],
            "current_phase": "ddd",
            "kb_path": "",
        }
        result = _domain_designer_node(state)
    assert "domain_model" in result
    assert "raw_output" in result["domain_model"]


def test_reviewer_node_fallback_on_bad_json():
    """Reviewer node returns default approved=True on JSON parse failure."""
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="Not JSON at all")
    with patch("uni_dev.core.graph._create_node_model", return_value=mock_model):
        state: UniDevState = {
            "messages": [],
            "classification": "add_feature",
            "attempt_count": 0,
            "test_results": {"pass": True, "failures": []},
            "migration_idx": 0,
            "migration_plan": [],
            "current_phase": "done",
            "kb_path": "",
            "api_spec": "openapi: 3.0.0",
            "modified_files": [],
        }
        result = _reviewer_node(state)
    assert result["review_report"]["approved"] is True
    assert "raw_output" in result["review_report"]


def test_create_node_model_v4_pro():
    """_create_node_model for domain_designer sets reasoning_effort and thinking."""
    with patch("uni_dev.core.graph._get_api_key", return_value="sk-test"):
        with patch("uni_dev.core.graph.ChatOpenAI") as mock_chat:
            _create_node_model("domain_designer")
    call_kwargs = mock_chat.call_args.kwargs
    assert call_kwargs["model"] == "deepseek-v4-pro"
    assert call_kwargs["temperature"] == 0.3
    assert call_kwargs["reasoning_effort"] == "high"
    assert call_kwargs["extra_body"] == {"thinking": {"type": "enabled"}}


def test_create_node_model_v4_flash():
    """_create_node_model for spec_writer uses flash model without extras."""
    with patch("uni_dev.core.graph._get_api_key", return_value="sk-test"):
        with patch("uni_dev.core.graph.ChatOpenAI") as mock_chat:
            _create_node_model("spec_writer")
    call_kwargs = mock_chat.call_args.kwargs
    assert call_kwargs["model"] == "deepseek-v4-flash"
    assert call_kwargs["temperature"] == 0.1
    assert "reasoning_effort" not in call_kwargs
    assert "extra_body" not in call_kwargs
