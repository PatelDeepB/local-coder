"""Unit tests for Stage 2 Slot Coder scoped body synthesis."""

from unittest.mock import MagicMock
from local_coder.neural.contract_planner import CodeContract
from local_coder.neural.llama_runner import GenerationResult, LlamaModelRunner
from local_coder.neural.slot_coder import SlotCoder


def test_should_clean_body_text_and_enforce_indentation() -> None:
    # Arrange
    mock_runner = MagicMock(spec=LlamaModelRunner)
    coder = SlotCoder(runner=mock_runner)

    raw_response = (
        "```python\n"
        "def compute_interest(principal, rate):\n"
        "return principal * rate\n"
        "```\n"
    )

    # Act
    cleaned = coder.clean_body_text(raw_response)

    # Assert
    assert "```" not in cleaned
    assert "def compute_interest" not in cleaned
    assert cleaned.startswith("    ")
    assert "return principal * rate" in cleaned


def test_should_synthesize_and_validate_slot_function() -> None:
    # Arrange
    mock_runner = MagicMock(spec=LlamaModelRunner)
    mock_runner.generate.return_value = GenerationResult(
        content="return x + y",
        elapsed_seconds=0.1,
        tokens_per_second=100.0,
        token_count=4,
        peak_rss_mb=50.0,
    )
    coder = SlotCoder(runner=mock_runner)
    contract = CodeContract(
        function_or_class_name="add_numbers",
        signature="def add_numbers(x: int, y: int) -> int:",
        docstring="Adds two numbers.",
        preconditions=(),
        return_type="int",
    )

    # Act
    result = coder.synthesize_slot(contract, "Add two numbers")

    # Assert
    assert result.is_success is True
    assert "def add_numbers(x: int, y: int) -> int:" in result.complete_function_code
    assert "    return x + y" in result.complete_function_code


def test_should_surgically_inject_slot_into_file() -> None:
    # Arrange
    mock_runner = MagicMock(spec=LlamaModelRunner)
    coder = SlotCoder(runner=mock_runner)

    source = (
        "def calculate_tax(income: float) -> float:\n"
        "    pass\n"
        "\n"
        "def helper():\n"
        "    return 1\n"
    )
    new_body = "    return income * 0.2"

    # Act
    modified, ok = coder.inject_slot_into_file(source, "calculate_tax", new_body)

    # Assert
    assert ok is True
    assert "return income * 0.2" in modified
    assert "def helper():" in modified
