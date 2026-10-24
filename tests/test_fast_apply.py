"""Unit tests for FastApplyEngine."""

from pathlib import Path
from unittest.mock import MagicMock
from local_coder.agent.fast_apply import FastApplyEngine
from local_coder.workspace.shadow_workspace import ShadowWorkspace


def test_should_apply_new_function_in_single_pass(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "math_calc.py"
    target.write_text("def calculate_force(m, a):\n    return m * a\n", encoding="utf-8")
    workspace = ShadowWorkspace(tmp_path)

    mock_runner = MagicMock()
    mock_runner.generate.return_value = MagicMock(
        content="<update>\ndef calculate_work(f, d):\n    return f * d\n</update>"
    )

    engine = FastApplyEngine(runner=mock_runner, workspace=workspace)

    # Act
    res = engine.apply_update("math_calc.py", "Add calculate_work function")

    # Assert
    assert res.is_success is True
    assert "def calculate_force" in res.staged_content
    assert "def calculate_work" in res.staged_content
    assert "+def calculate_work" in res.diff
    assert res.elapsed_seconds < 1.0


def test_should_update_existing_function_in_single_pass(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "math_calc.py"
    target.write_text(
        "def calculate_force(m, a):\n    return m * a\n\ndef helper():\n    return 1\n",
        encoding="utf-8",
    )
    workspace = ShadowWorkspace(tmp_path)

    mock_runner = MagicMock()
    mock_runner.generate.return_value = MagicMock(
        content="<update>\ndef calculate_force(m, a):\n    if m <= 0:\n        raise ValueError()\n    return m * a\n</update>"
    )

    engine = FastApplyEngine(runner=mock_runner, workspace=workspace)

    # Act
    res = engine.apply_update("math_calc.py", "Add validation to calculate_force")

    # Assert
    assert res.is_success is True
    assert "raise ValueError()" in res.staged_content
    assert "def helper():" in res.staged_content


def test_should_fail_when_syntax_is_broken(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "math_calc.py"
    target.write_text("def foo():\n    return 1\n", encoding="utf-8")
    workspace = ShadowWorkspace(tmp_path)

    mock_runner = MagicMock()
    mock_runner.generate.return_value = MagicMock(
        content="<update>\ndef broken_func(\n</update>"
    )

    engine = FastApplyEngine(runner=mock_runner, workspace=workspace)

    # Act
    res = engine.apply_update("math_calc.py", "Add broken func")

    # Assert
    assert res.is_success is False
    assert "Syntax Error" in (res.error_message or "")
