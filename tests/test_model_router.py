"""Unit tests for ModelRouter supporting local, ollama, and openai providers."""

from unittest.mock import MagicMock, patch
import pytest

from local_coder.neural.llama_runner import GenerationResult, LlamaModelRunner
from local_coder.neural.model_router import ModelProvider, ModelRouter


def test_should_default_to_local_provider() -> None:
    # Arrange
    mock_runner = MagicMock(spec=LlamaModelRunner)
    mock_runner.generate.return_value = GenerationResult(
        content="def hello(): pass",
        elapsed_seconds=0.05,
        tokens_per_second=80.0,
        token_count=4,
        peak_rss_mb=50.0,
    )

    # Act
    router = ModelRouter(provider="local", local_runner=mock_runner)
    result = router.generate("Write hello world")

    # Assert
    assert router.provider == ModelProvider.LOCAL
    assert "def hello" in result.content
    mock_runner.generate.assert_called_once()


def test_should_route_to_mock_remote_and_fallback_on_unreachable() -> None:
    # Arrange
    mock_runner = MagicMock(spec=LlamaModelRunner)
    mock_runner.generate.return_value = GenerationResult(
        content="fallback response",
        elapsed_seconds=0.01,
        tokens_per_second=100.0,
        token_count=2,
        peak_rss_mb=40.0,
    )

    # Act: Request against unreachable endpoint
    router = ModelRouter(provider="openai", local_runner=mock_runner)
    result = router.generate("Test prompt")

    # Assert: Should gracefully fall back to local runner without throwing
    assert result.content == "fallback response"
    mock_runner.generate.assert_called_once()


def test_should_dispatch_hybrid_mode_correctly() -> None:
    # Arrange
    mock_runner = MagicMock(spec=LlamaModelRunner)
    router = ModelRouter(provider="hybrid", local_runner=mock_runner)

    # Act & Assert
    assert router._resolve_active_provider(prefer_frontier=False) == ModelProvider.LOCAL

    with patch.object(router, "_is_ollama_alive", return_value=True):
        assert router._resolve_active_provider(prefer_frontier=True) == ModelProvider.OLLAMA


def test_should_stream_tokens_locally() -> None:
    # Arrange
    mock_runner = MagicMock(spec=LlamaModelRunner)
    mock_runner.stream_tokens.return_value = iter(["token1 ", "token2 "])
    router = ModelRouter(provider="local", local_runner=mock_runner)

    # Act
    tokens = list(router.stream_tokens("Stream please"))

    # Assert
    assert tokens == ["token1 ", "token2 "]
