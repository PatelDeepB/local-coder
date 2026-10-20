"""Unit tests for strict memory guard."""

import pytest
from local_coder.core.memory_guard import MemoryGuard, MemoryBudgetExceededError


def test_should_measure_current_resident_memory_under_budget() -> None:
    # Arrange
    guard = MemoryGuard(budget_mb=2000.0)

    # Act
    current_mb = guard.get_resident_memory_mb()

    # Assert
    assert current_mb > 0.0
    assert current_mb < 2000.0
    assert guard.is_within_budget() is True


def test_should_raise_exception_when_budget_is_exceeded() -> None:
    # Arrange
    guard = MemoryGuard(budget_mb=0.01)  # Tiny artificial budget to trigger guard

    # Act & Assert
    with pytest.raises(MemoryBudgetExceededError) as exc_info:
        guard.assert_within_budget()

    assert "strictly exceeds safe budget" in str(exc_info.value)
