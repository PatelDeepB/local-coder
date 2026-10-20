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

