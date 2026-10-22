"""Unit tests for AutonomousTestHealer and autonomous test-repair loop."""

from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from local_coder.agent.autonomous_test_healer import AutonomousTestHealer
from local_coder.neural.llama_runner import GenerationResult
import local_coder.server.api_server as api_module
from local_coder.server.api_server import app
from local_coder.tools.test_tools import RunAutonomousTestRepairTool
from local_coder.verifier.test_runner import TestExecutionOutcome
from local_coder.workspace.shadow_workspace import ShadowWorkspace
from local_coder.workspace.terminal_runner import TerminalExecutionResult, TerminalRunner


def test_should_pass_immediately_when_tests_green(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    terminal = TerminalRunner(str(tmp_path))
    mock_runner = MagicMock()

    healer = AutonomousTestHealer(runner=mock_runner, workspace=workspace, terminal=terminal)
    mock_test_runner = MagicMock()
    mock_test_runner.run_pytest.return_value = TestExecutionOutcome(
        is_all_passed=True,
        passed_count=5,
        failed_count=0,
        raw_output="5 passed in 0.1s",
    )
    healer.test_runner = mock_test_runner

    # Act
    outcome = healer.run_and_repair(test_path="tests")

    # Assert
    assert outcome.is_successful is True
    assert outcome.iterations_used == 1
    assert outcome.passed_count == 5
    assert len(outcome.repaired_files) == 0


def test_should_repair_code_and_succeed_on_subsequent_run(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    terminal = TerminalRunner(str(tmp_path))
    workspace.stage_edit("calc.py", "def add(a, b): return a - b\n")

    mock_runner = MagicMock()
    mock_runner.generate.return_value = GenerationResult(
        content="```python\ndef add(a, b):\n    return a + b\n```",
        elapsed_seconds=0.01,
        tokens_per_second=100.0,
        token_count=10,
        peak_rss_mb=500.0,
    )

    healer = AutonomousTestHealer(runner=mock_runner, workspace=workspace, terminal=terminal)
    mock_test_runner = MagicMock()
    # First call fails, second call passes
    mock_test_runner.run_pytest.side_effect = [
        TestExecutionOutcome(
            is_all_passed=False,
            passed_count=0,
            failed_count=1,
            error_summary="assert -1 == 3",
            raw_output='File "calc.py", line 1 in add\nAssertionError',
        ),
        TestExecutionOutcome(
            is_all_passed=True,
            passed_count=1,
            failed_count=0,
            raw_output="1 passed in 0.05s",
        ),
    ]
    healer.test_runner = mock_test_runner

    # Act
    outcome = healer.run_and_repair(test_path="tests", target_file="calc.py")

    # Assert
    assert outcome.is_successful is True
    assert "calc.py" in outcome.repaired_files
    assert "return a + b" in (workspace.get_staged_content("calc.py") or "")


def test_should_execute_run_and_repair_tool(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    terminal = TerminalRunner(str(tmp_path))
    mock_runner = MagicMock()
    tool = RunAutonomousTestRepairTool(runner=mock_runner, workspace=workspace, terminal=terminal)

    mock_healer = MagicMock()
    mock_healer.run_and_repair.return_value = MagicMock(
        is_successful=True,
        passed_count=4,
        failed_count=0,
        iterations_used=1,
        repaired_files=[],
    )
    tool.healer = mock_healer

    # Act
    res = tool.execute(test_path="tests")

    # Assert
    assert res.is_success is True
    assert "PASSED" in res.output


def test_should_serve_test_and_repair_endpoint() -> None:
    # Arrange
    mock_orch = MagicMock()
    mock_orch.terminal_runner.run_command.return_value = TerminalExecutionResult(
        command="pytest",
        exit_code=0,
        stdout="2 passed in 0.05s",
        stderr="",
        elapsed_seconds=0.05,
    )
    api_module.orchestrator_instance = mock_orch

    client = TestClient(app)
    payload = {"test_path": "tests", "target_file": "app.py", "max_iterations": 2}

    # Act
    response = client.post("/api/v1/test-and-repair", json=payload)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "is_successful" in data
    assert "iterations_used" in data
