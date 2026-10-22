"""Autonomous test execution and repair tool for agent loop."""

from typing import Any

from local_coder.agent.autonomous_test_healer import AutonomousTestHealer
from local_coder.tools.base_tool import BaseAgentTool, ToolResult
from local_coder.workspace.shadow_workspace import ShadowWorkspace
from local_coder.workspace.terminal_runner import TerminalRunner


class RunAutonomousTestRepairTool(BaseAgentTool):
    """Executes tests and iteratively heals broken files until all pass."""

    def __init__(
        self,
        runner: Any,
        workspace: ShadowWorkspace,
        terminal: TerminalRunner,
    ) -> None:
        self.healer = AutonomousTestHealer(runner=runner, workspace=workspace, terminal=terminal)

    @property
    def name(self) -> str:
        return "run_and_repair_tests"

    @property
    def description(self) -> str:
        return "Executes pytest test suite and autonomously heals failing code files until all tests pass."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "test_path": {
                    "type": "string",
                    "description": "Test file or directory to run",
                    "default": "tests",
                },
                "target_file": {
                    "type": "string",
                    "description": "Optional specific source file to repair",
                    "default": "",
                },
            },
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        test_path = kwargs.get("test_path", "tests")
        target_file = kwargs.get("target_file") or None
        outcome = self.healer.run_and_repair(test_path=test_path, target_file=target_file)

        status_text = "PASSED" if outcome.is_successful else "FAILED"
        repaired_str = ", ".join(outcome.repaired_files) if outcome.repaired_files else "None"
        summary = (
            f"Test Suite Outcome: {status_text}\n"
            f"Passed: {outcome.passed_count}, Failed: {outcome.failed_count}, Iterations: {outcome.iterations_used}\n"
            f"Repaired Files: {repaired_str}"
        )
        return ToolResult(
            is_success=outcome.is_successful,
            output=summary,
            error_message=None if outcome.is_successful else outcome.final_output,
        )
