"""Unit tests for terminal command runner."""

import sys
from local_coder.workspace.terminal_runner import TerminalRunner


def test_should_execute_command_and_capture_exit_code() -> None:
    # Arrange
    runner = TerminalRunner()
    cmd = f'"{sys.executable}" -c "print(\'LOCAL_CODER_OK\')"'

    # Act
    res = runner.run_command(cmd, timeout=5.0)

    # Assert
    assert res.is_success is True
    assert res.exit_code == 0
    assert "LOCAL_CODER_OK" in res.stdout


def test_should_capture_command_timeout_gracefully() -> None:
    # Arrange
    runner = TerminalRunner()
    cmd = f'"{sys.executable}" -c "import time; time.sleep(2.0)"'

    # Act
    res = runner.run_command(cmd, timeout=0.2)

    # Assert
    assert res.is_timed_out is True
    assert res.is_success is False
