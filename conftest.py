from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import pytest

collect_ignore = ["src/**"]


# ── P0.3: FakeChatModel — deterministic mock LLM ──

_DOMAIN_YAML = """\
entities:
  - name: Pet
    fields:
      - name: id
        type: Long
      - name: name
        type: String
  - name: Owner
    fields:
      - name: id
        type: Long
      - name: name
        type: String
bounded_contexts:
  - clinic
  - inventory
aggregates:
  - Pet
relationships:
  - source: Owner
    target: Pet
    type: one_to_many
"""

_OPENAPI_YAML = """\
openapi: "3.0.3"
info:
  title: PetClinic
  version: "1.0.0"
paths:
  /pets:
    get:
      summary: List all pets
      operationId: listPets
      responses:
        "200":
          description: A list of pets
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: "#/components/schemas/Pet"
    post:
      summary: Create a pet
      operationId: createPet
      requestBody:
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/Pet"
      responses:
        "201":
          description: Pet created
components:
  schemas:
    Pet:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
"""

_TEST_CODE = """\
import pytest
from myapp.pet_service import PetService

class TestPetService:
    def test_create_pet(self):
        service = PetService()
        result = service.create_pet({"name": "Buddy"})
        assert result.name == "Buddy"

    def test_list_pets(self):
        service = PetService()
        pets = service.list_pets()
        assert isinstance(pets, list)
"""

_IMPL_CODE = """\
class PetService:
    def create_pet(self, data: dict) -> Pet:
        pet = Pet(name=data["name"])
        return pet

    def list_pets(self) -> list[Pet]:
        return []
"""

_REVIEW_JSON = """\
{"status": "pass", "gaps": [], "security": "clean", "notes": "Implementation matches spec"}
"""


class FakeChatModel:
    """Deterministic mock LLM that returns canned responses based on prompt content.

    Usage::

        from unittest.mock import patch

        model = FakeChatModel()
        with patch("langchain_core.language_models.chat_models.init_chat_model",
                   return_value=model):
            ...
    """

    model_name: str = "fake-chat-model"

    def invoke(self, messages: Sequence[Any], **kwargs: Any) -> Any:
        """Return deterministic response based on message content."""
        prompt = ""
        if messages:
            first = messages[0]
            prompt = getattr(first, "content", str(first)).lower()

        if "domain" in prompt or "bounded context" in prompt:
            content = _DOMAIN_YAML
        elif "openapi" in prompt or "spec" in prompt:
            content = _OPENAPI_YAML
        elif "test" in prompt:
            content = _TEST_CODE
        elif "implement" in prompt or "code" in prompt:
            content = _IMPL_CODE
        elif "review" in prompt:
            content = _REVIEW_JSON
        else:
            content = "ack"

        # Return a simple object with .content attribute
        return _FakeMessage(content=content)


class _FakeMessage:
    """Mock message object with content attribute."""

    def __init__(self, content: str) -> None:
        self.content = content


# ── FakeDeepAgent — mock sub-agent for pipeline integration tests ──

class FakeDeepAgent:
    """Mock deep agent that returns deterministic responses.

    Used via `unittest.mock.patch("deepagents.create_deep_agent")`
    to avoid real LLM API calls during pipeline integration tests.
    """

    def __init__(self, response: str = "") -> None:
        self._response = response

    def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Return fake agent output with canned response as AIMessage."""
        content = self._response
        if not content:
            # Auto-detect response from input messages
            msg = input_data.get("messages", [])
            if msg:
                first = msg[0]
                prompt = getattr(first, "content", str(first)).lower()
                model = FakeChatModel()
                fake_msg = model.invoke(msg)
                content = fake_msg.content

        from langchain_core.messages import AIMessage

        return {"messages": [AIMessage(content=content)]}


@pytest.fixture
def mock_create_deep_agent():
    """Patch deepagents.create_deep_agent to return FakeDeepAgent."""
    from unittest.mock import patch

    with patch("deepagents.create_deep_agent") as mock:
        mock.side_effect = lambda **kwargs: FakeDeepAgent()
        yield mock


# ── P0.4: Pipeline test harness fixtures ──

@pytest.fixture
def pipeline_config():
    """PipelineConfig with fake API key for testing."""
    from uni_dev.core.factory import PipelineConfig

    return PipelineConfig(
        api_key="fake-test-key",
        base_url="https://fake.api",
        test_command="pytest",
    )


@pytest.fixture
def compiled_pipeline(pipeline_config):
    """Compiled SOP graph with fake config."""
    from uni_dev.core.graph import compile_pipeline

    return compile_pipeline(config=pipeline_config)


@pytest.fixture
def base_state():
    """Minimal initial pipeline state."""
    return {
        "issue": "Add pet owner avatar upload endpoint",
        "project_path": ".",
        "classification": "add_feature",
        "attempt_count": 0,
    }


@pytest.fixture
def state_after_ddd(base_state):
    """State after successful DDD phase."""
    s = dict(base_state)
    s["domain_model"] = _DOMAIN_YAML
    return s


@pytest.fixture
def state_after_sdd(state_after_ddd):
    """State after successful SDD phase."""
    s = dict(state_after_ddd)
    s["api_spec"] = _OPENAPI_YAML
    return s


@pytest.fixture
def state_after_test_gen(state_after_sdd):
    """State after successful test generation."""
    s = dict(state_after_sdd)
    s["test_files"] = ["test_pet_service.py"]
    return s


@pytest.fixture
def state_with_tests_passing(state_after_test_gen):
    """State with tests passing."""
    s = dict(state_after_test_gen)
    s["modified_files"] = ["pet_service.py"]
    s["test_results"] = {"pass": True, "failures": [], "exit_code": 0, "output": "2 passed"}
    return s


@pytest.fixture
def state_with_tests_failing(state_after_test_gen):
    """State with tests failing."""
    s = dict(state_after_test_gen)
    s["modified_files"] = ["pet_service.py"]
    s["test_results"] = {
        "pass": False,
        "exit_code": 1,
        "output": "FAILED test_pet_service.py::test_create_pet",
        "failures": ["FAILED test_create_pet - AssertionError"],
    }
    return s


# ── P0.5: State assertion helpers ──

def assert_gate_passed(state: dict) -> None:
    """Assert gate returned pass."""
    assert state.get("_gate_result") == "pass", (
        f"Expected gate pass, got {state.get('_gate_result')}"
    )


def assert_gate_failed(state: dict) -> None:
    """Assert gate returned fail."""
    assert state.get("_gate_result") == "fail", (
        f"Expected gate fail, got {state.get('_gate_result')}"
    )


def assert_has_domain_model(state: dict) -> None:
    """Assert domain_model is present and non-empty."""
    dm = state.get("domain_model", "")
    assert dm, "Expected domain_model in state"


def assert_has_api_spec(state: dict) -> None:
    """Assert api_spec is present and non-empty."""
    spec = state.get("api_spec", "")
    assert spec, "Expected api_spec in state"


def assert_test_passed(state: dict) -> None:
    """Assert test_results indicate passing tests."""
    results = state.get("test_results", {})
    assert results.get("pass") is True, f"Expected tests to pass, got: {results}"
    assert not results.get("failures", []), (
        f"Expected no failures, got: {results.get('failures')}"
    )


def assert_test_failed(state: dict) -> None:
    """Assert test_results indicate failing tests."""
    results = state.get("test_results", {})
    assert results.get("pass") is not True or results.get("failures", []), (
        f"Expected tests to fail, got: {results}"
    )


def assert_retry_attempt(state: dict, expected: int) -> None:
    """Assert attempt_count matches expected value."""
    actual = state.get("attempt_count")
    assert actual == expected, f"Expected attempt_count={expected}, got {actual}"


def assert_human_decision(state: dict, expected: str) -> None:
    """Assert _human_decision matches expected value."""
    actual = state.get("_human_decision")
    assert actual == expected, f"Expected _human_decision={expected}, got {actual}"


# ── P0.7: Sample project fixture ──

@pytest.fixture
def petclinic_path():
    """Path to spring-petclinic-rest test fixture project."""
    p = (
        Path(__file__).resolve().parent.parent
        / "tests" / "spring-petclinic-rest"
    )
    if not p.exists():
        pytest.skip("spring-petclinic-rest fixture not found")
    return str(p)
