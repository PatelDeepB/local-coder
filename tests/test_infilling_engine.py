"""Unit tests for InfillingEngine and FIM tab autocomplete."""

from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from local_coder.neural.infilling_engine import InfillingEngine, InfillingResult
from local_coder.neural.llama_runner import GenerationResult
import local_coder.server.api_server as api_module
from local_coder.server.api_server import app


def test_should_generate_raw_fim_completion() -> None:
    # Arrange
    mock_runner = MagicMock()
    mock_runner.generate_raw.return_value = GenerationResult(
        content=" = True",
        elapsed_seconds=0.01,
        tokens_per_second=200.0,
        token_count=2,
        peak_rss_mb=500.0,
    )
    engine = InfillingEngine(mock_runner)

    # Act
    result = engine.complete(prefix="is_active", suffix=":\n    pass\n")

    # Assert
    assert isinstance(result, InfillingResult)
    assert result.completion == " = True"
    assert result.elapsed_ms > 0
    mock_runner.generate_raw.assert_called_once()


def test_should_strip_fim_tokens_from_completion() -> None:
    # Arrange
    mock_runner = MagicMock()
    mock_runner.generate_raw.return_value = GenerationResult(
        content="<|fim_middle|>return x + y<|endoftext|>",
        elapsed_seconds=0.01,
        tokens_per_second=200.0,
        token_count=4,
        peak_rss_mb=500.0,
    )
    engine = InfillingEngine(mock_runner)

    # Act
    result = engine.complete(prefix="def add(x, y):\n    ", suffix="\n")

    # Assert
    assert result.completion == "return x + y"


def test_should_serve_autocomplete_endpoint() -> None:
    # Arrange
    mock_orch = MagicMock()
    mock_runner = MagicMock()
    mock_runner.generate_raw.return_value = GenerationResult(
        content="def calculate():\n    return 42",
        elapsed_seconds=0.02,
        tokens_per_second=150.0,
        token_count=5,
        peak_rss_mb=500.0,
    )
    mock_orch.runner = mock_runner
    api_module.orchestrator_instance = mock_orch

    client = TestClient(app)
    payload = {
        "prefix": "import os\n",
        "suffix": "\nif __name__ == '__main__': pass",
        "max_tokens": 16,
        "single_line_only": False,
    }

    # Act
    response = client.post("/api/v1/autocomplete", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "completion" in data
    assert data["completion"] == "def calculate():\n    return 42"
    assert "elapsed_ms" in data
