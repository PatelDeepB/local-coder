"""Isolated test runner that executes pytest and parses structured test results."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re
import sys

from local_coder.workspace.terminal_runner import TerminalRunner


@dataclass(frozen=True)
class TestExecutionOutcome:
    """Outcome of a test suite run."""

    is_all_passed: bool
    passed_count: int
    failed_count: int
    error_summary: Optional[str] = None
    raw_output: str = ""


class TestRunner:
    """Runs pytest on test files or directories and parses test outcomes."""

    def __init__(self, terminal: TerminalRunner) -> None:
        self.terminal = terminal

    def run_pytest(
        self,
        test_path: str = "tests",
        timeout: float = 30.0,
    ) -> TestExecutionOutcome:
        """Runs pytest on target path and parses pass/fail metrics."""
        cmd = f'"{sys.executable}" -m pytest {test_path} -v --no-header -o pythonpath=.'
        res = self.terminal.run_command(cmd, timeout=timeout)
        combined = f"{res.stdout}\n{res.stderr}"

        # Match pytest summary line like '5 passed, 1 failed in 0.23s' or '3 passed in 0.10s'
        pass_match = re.search(r"(\d+)\s+passed", combined)
        fail_match = re.search(r"(\d+)\s+failed", combined)
        err_match = re.search(r"(\d+)\s+error", combined)

        passed = int(pass_match.group(1)) if pass_match else 0
        failed = int(fail_match.group(1)) if fail_match else (1 if err_match else 0)

        # Failure summary extraction
        error_summary = None
        if not res.is_success or failed > 0:
            lines = [l.strip() for l in combined.splitlines() if "FAILED" in l or "ERROR" in l]
            error_summary = "\n".join(lines[:5]) if lines else res.stderr[:300]

        return TestExecutionOutcome(
            is_all_passed=(res.exit_code == 0 and failed == 0),
            passed_count=passed,
            failed_count=failed,
            error_summary=error_summary,
            raw_output=combined,
        )
