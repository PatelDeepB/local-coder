"""Autonomous terminal test-repair loop for executing test suites and auto-healing failures."""

from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Any, Optional

from local_coder.verifier.test_runner import TestExecutionOutcome, TestRunner
from local_coder.workspace.shadow_workspace import ShadowWorkspace
from local_coder.workspace.terminal_runner import TerminalRunner

logger = logging.getLogger("test_healer")


@dataclass(frozen=True)
class TestRepairResult:
    """Outcome of iterative test execution and repair."""

    is_successful: bool
    iterations_used: int
    passed_count: int
    failed_count: int
    repaired_files: list[str]
    final_output: str


class AutonomousTestHealer:
    """Runs test suite via terminal runner and iteratively repairs implementation code on failure."""

    def __init__(
        self,
        runner: Any,
        workspace: ShadowWorkspace,
        terminal: TerminalRunner,
        max_iterations: int = 3,
    ) -> None:
        self.runner = runner
        self.workspace = workspace
        self.terminal = terminal
        self.test_runner = TestRunner(terminal)
        self.max_iterations = max_iterations

    def run_and_repair(
        self,
        test_path: str = "tests",
        target_file: Optional[str] = None,
    ) -> TestRepairResult:
        """Executes tests and iteratively repairs files until green or limit reached."""
        repaired: list[str] = []
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            outcome = self.test_runner.run_pytest(test_path=test_path)
            if outcome.is_all_passed:
                return TestRepairResult(
                    is_successful=True,
                    iterations_used=iteration,
                    passed_count=outcome.passed_count,
                    failed_count=0,
                    repaired_files=repaired,
                    final_output=outcome.raw_output,
                )

            # Resolve file to repair
            file_to_fix = target_file or self._detect_file_from_traceback(outcome.raw_output)
            current_code = self.workspace.get_staged_content(file_to_fix) if file_to_fix else None
            if not file_to_fix or current_code is None:
                logger.warning("Could not identify candidate source file to repair.")
                return TestRepairResult(
                    is_successful=False,
                    iterations_used=iteration,
                    passed_count=outcome.passed_count,
                    failed_count=outcome.failed_count,
                    repaired_files=repaired,
                    final_output=outcome.raw_output,
                )

            repair_prompt = self._format_repair_prompt(
                file_path=file_to_fix,
                current_code=current_code,
                error_summary=outcome.error_summary or outcome.raw_output[-600:],
            )

            res = self.runner.generate(prompt=repair_prompt, max_tokens=1500, temperature=0.1)
            raw_content = getattr(res, "content", "") if res else ""
            fixed_code = self._clean_code_fence(raw_content)
            if fixed_code:
                self.workspace.stage_edit(file_to_fix, fixed_code)
                self.workspace.commit_all()
                if file_to_fix not in repaired:
                    repaired.append(file_to_fix)

        # Final verification attempt
        final_outcome = self.test_runner.run_pytest(test_path=test_path)
        return TestRepairResult(
            is_successful=final_outcome.is_all_passed,
            iterations_used=iteration,
            passed_count=final_outcome.passed_count,
            failed_count=final_outcome.failed_count,
            repaired_files=repaired,
            final_output=final_outcome.raw_output,
        )

    def _detect_file_from_traceback(self, raw_output: str) -> Optional[str]:
        """Extracts source file involved in failure traceback."""
        matches = re.findall(r'File "([^"]+\.py)", line \d+', raw_output)
        for path_str in reversed(matches):
            p = Path(path_str)
            filename = p.name
            if not filename.startswith("test_") and not filename.startswith("conftest"):
                return filename
        return None

    def _format_repair_prompt(self, file_path: str, current_code: str, error_summary: str) -> str:
        """Constructs prompt focusing model on test failures."""
        return (
            f"File to fix: {file_path}\n"
            f"Test Suite Failure Diagnostic:\n```\n{error_summary}\n```\n"
            f"Current Implementation:\n```python\n{current_code}\n```\n"
            f"Task: Fix the bug causing the test failure. Output ONLY the corrected Python code inside a code block."
        )

    def _clean_code_fence(self, text: Any) -> str:
        """Extracts code block from model response."""
        content_str = str(text) if not isinstance(text, str) else text
        match = re.search(r"```(?:python|py)?\s*\n(.*?)```", content_str, flags=re.DOTALL)
        if match:
            return match.group(1).strip()
        return content_str.replace("```", "").strip()
