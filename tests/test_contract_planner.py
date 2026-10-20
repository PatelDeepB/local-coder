"""Unit tests for Stage 1 Contract Planner."""

from unittest.mock import MagicMock
from local_coder.neural.contract_planner import ContractPlanner
from local_coder.neural.llama_runner import GenerationResult, LlamaModelRunner


def test_should_plan_contract_from_prompt_signature() -> None:
    # Arrange
    mock_runner = MagicMock(spec=LlamaModelRunner)
    mock_runner.generate.return_value = GenerationResult(
        content="def sanitize_filename(name: str) -> str:\n    pass",
        elapsed_seconds=0.05,
        tokens_per_second=100.0,
        token_count=10,
        peak_rss_mb=50.0,
    )
    planner = ContractPlanner(runner=mock_runner)

    # Act
    contract = planner.plan_contract("Create a function to sanitize filenames")

    # Assert
    assert contract.function_or_class_name == "sanitize_filename"
    assert "def sanitize_filename(name: str) -> str:" in contract.signature


def test_should_fallback_to_default_signature_when_no_match() -> None:
    # Arrange
    mock_runner = MagicMock(spec=LlamaModelRunner)
    mock_runner.generate.return_value = GenerationResult(
        content="Some conversational text without a def signature.",
        elapsed_seconds=0.05,
        tokens_per_second=100.0,
        token_count=8,
        peak_rss_mb=50.0,
    )
    planner = ContractPlanner(runner=mock_runner)

    # Act
    contract = planner.plan_contract("Perform a general task")

    # Assert
    assert contract.function_or_class_name == "execute_task"
    assert "def execute_task() -> None:" in contract.signature
