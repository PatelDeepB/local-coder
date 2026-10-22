"""Unit tests for SpeculativeDraftingEngine and sub-millisecond completions."""

from pathlib import Path
from unittest.mock import MagicMock

from local_coder.neural.infilling_engine import InfillingEngine
from local_coder.neural.speculative_drafter import SpeculativeDraftingEngine


def test_should_learn_and_draft_continuation(tmp_path: Path) -> None:
    # Arrange
    db_file = tmp_path / "test_ngrams.db"
    drafter = SpeculativeDraftingEngine(db_path=db_file)
    snippet = "def calculate_total_price(items: list[dict]) -> float:\n    return sum(i['price'] for i in items)"
    drafter.learn_snippet(snippet)

    # Act
    draft = drafter.draft_continuation("def calculate_total")

    # Assert
    assert draft is not None
    assert "price" in draft.continuation
    assert draft.is_speculative is True
    assert draft.elapsed_ms < 5.0  # Sub-millisecond on warm disk


def test_should_return_none_for_unknown_prefix(tmp_path: Path) -> None:
    # Arrange
    db_file = tmp_path / "test_ngrams.db"
    drafter = SpeculativeDraftingEngine(db_path=db_file)

    # Act
    draft = drafter.draft_continuation("xyz_completely_unknown_token_prefix_123")

    # Assert
    assert draft is None


def test_should_accelerate_infilling_engine_without_neural_pass(tmp_path: Path) -> None:
    # Arrange
    db_file = tmp_path / "test_ngrams.db"
    drafter = SpeculativeDraftingEngine(db_path=db_file)
    drafter.learn_snippet("class TaskListView(ListView):\n    model = Task")

    mock_runner = MagicMock()
    engine = InfillingEngine(runner=mock_runner, drafter=drafter)

    # Act
    result = engine.complete(prefix="class TaskListView", suffix="\n")

    # Assert
    assert "ListView" in result.completion
    # Neural model runner should NOT have been called due to speculative hit!
    mock_runner.generate_raw.assert_not_called()
    mock_runner.generate.assert_not_called()
