"""Unit tests for FastAPI REST and OpenAI-compatible server."""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from local_coder.agent.agent_state import AgentSessionState, TaskStatus
import local_coder.server.api_server as api_module
from local_coder.server.api_server import app


def test_should_return_healthy_status() -> None:
    # Arrange
    client = TestClient(app)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "engine": "local-coder"}


def test_should_list_available_models() -> None:
    # Arrange
    client = TestClient(app)

    # Act
    response = client.get("/v1/models")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert any(m["id"] == "local-coder" for m in data["data"])


def test_should_process_openai_chat_completion_non_streaming() -> None:
    # Arrange
    mock_orch = MagicMock()
    mock_session = AgentSessionState(
        session_id="test1234",
        user_goal="write a hello world function",
        status=TaskStatus.COMPLETED,
        final_output="def hello(): return 'world'",
    )
    mock_orch.run_coding_task.return_value = mock_session
    api_module.orchestrator_instance = mock_orch

    client = TestClient(app)
    payload = {
        "model": "local-coder",
        "messages": [{"role": "user", "content": "write a hello world function"}],
        "stream": False,
    }

    # Act
    response = client.post("/v1/chat/completions", json=payload)

    # Assert
    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["object"] == "chat.completion"
    assert len(resp_data["choices"]) == 1
    assert "def hello():" in resp_data["choices"][0]["message"]["content"]


def test_should_serve_interactive_web_ui() -> None:
    # Arrange
    client = TestClient(app)

    # Act
    response = client.get("/")

    # Assert
    assert response.status_code == 200
    assert "LOCAL-CODER" in response.text
    assert "Autonomous Local Coding Studio" in response.text


def test_should_return_api_status_and_diff() -> None:
    # Arrange
    mock_orch = MagicMock()
    mock_orch.memory_guard.get_resident_memory_mb.return_value = 1450.0
    mock_orch.memory_guard.budget_mb = 1800.0
    mock_orch.root_dir = "/workspace"
    mock_orch.shadow_workspace.staged_files = []
    mock_orch.shadow_workspace._staged_edits = {}
    mock_orch.hdc_index = []
    api_module.orchestrator_instance = mock_orch

    client = TestClient(app)

    # Act
    status_resp = client.get("/api/v1/status")
    diff_resp = client.get("/api/v1/diff")

    # Assert
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "online"
    assert status_resp.json()["rss_mb"] == 1450.0
    assert diff_resp.status_code == 200
    assert diff_resp.json() == {"diff": ""}


def test_should_process_inline_edit_request() -> None:
    # Arrange
    mock_orch = MagicMock()
    mock_orch.runner.generate.return_value = MagicMock(content="```python\ndef greet(): return 'hi'\n```")
    api_module.orchestrator_instance = mock_orch

    client = TestClient(app)
    payload = {
        "file_path": "test.py",
        "selected_code": "def greet(): pass",
        "instruction": "return hi",
    }

    # Act
    resp = client.post("/api/v1/inline-edit", json=payload)

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert "replacement_code" in data
    assert "def greet(): return 'hi'" in data["replacement_code"]
    assert "diff" in data


def test_should_heal_diagnostics() -> None:
    # Arrange
    mock_orch = MagicMock()
    mock_orch.runner.generate.return_value = MagicMock(
        content="```python\ndef valid():\n    return 42\n```"
    )
    api_module.orchestrator_instance = mock_orch

    client = TestClient(app)
    payload = {
        "file_path": "valid.py",
        "content": "def broken(): return",
        "diagnostics": [
            {"file": "valid.py", "line": 1, "column": 1, "message": "invalid syntax", "severity": "error"}
        ],
    }

    # Act
    resp = client.post("/api/v1/diagnostics/heal", json=payload)

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert "is_repaired" in data
    assert data["is_repaired"] is True
    assert "return 42" in data["repaired_code"]


def test_should_set_active_workspace() -> None:
    # Arrange
    mock_orch = MagicMock()
    mock_orch.root_dir = "/tmp/my_project"
    api_module.orchestrator_instance = mock_orch

    client = TestClient(app)
    payload = {"workspace_root": "/tmp/my_project"}

    # Act
    resp = client.post("/api/v1/workspace/set", json=payload)

    # Assert
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    mock_orch.set_workspace.assert_called_once_with("/tmp/my_project")


def test_should_execute_task_with_output_directory() -> None:
    # Arrange
    mock_orch = MagicMock()
    mock_session = AgentSessionState(
        session_id="run999",
        user_goal="create api endpoint",
        status=TaskStatus.COMPLETED,
        output_directory="/tmp/my_project",
        modified_files=["app.py"],
    )
    mock_orch.run_coding_task.return_value = mock_session
    api_module.orchestrator_instance = mock_orch

    client = TestClient(app)
    payload = {
        "goal": "create api endpoint",
        "output_directory": "/tmp/my_project",
    }

    # Act
    resp = client.post("/api/v1/task", json=payload)

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["modified_files"] == ["app.py"]
    mock_orch.set_workspace.assert_called_once_with("/tmp/my_project")


