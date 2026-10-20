"""Cross-platform sandboxed terminal execution engine for test suites and shell commands."""

from dataclasses import dataclass
from typing import Optional
import os
import re
import subprocess
import sys
import time

from local_coder.core.config import CONFIG


@dataclass(frozen=True)
class TerminalExecutionResult:
    """Encapsulates outcome of a terminal command execution."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    is_timed_out: bool = False

    @property
    def is_success(self) -> bool:
        """Returns True if command exited with code 0."""
        return self.exit_code == 0 and not self.is_timed_out


def strip_ansi_codes(text: str) -> str:
    """Strips terminal ANSI escape sequences for clean logging and parsing."""
    ansi_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_pattern.sub("", text)


class TerminalRunner:
    """Executes shell commands in a managed subprocess with timeout supervision."""

    def __init__(
        self,
        working_directory: Optional[str] = None,
        default_timeout: float = CONFIG.terminal_timeout_seconds,
    ) -> None:
        self.working_directory = working_directory or os.getcwd()
        self.default_timeout = default_timeout

    def run_command(
        self,
        command_str: str,
        timeout: Optional[float] = None,
    ) -> TerminalExecutionResult:
        """Runs a command string using system shell with timeout enforcement."""
        effective_timeout = timeout or self.default_timeout
        start_time = time.perf_counter()

        try:
            proc = subprocess.run(
                command_str,
                shell=True,
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            elapsed = time.perf_counter() - start_time
            return TerminalExecutionResult(
                command=command_str,
                exit_code=proc.returncode,
                stdout=strip_ansi_codes(proc.stdout),
                stderr=strip_ansi_codes(proc.stderr),
                elapsed_seconds=elapsed,
                is_timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed = time.perf_counter() - start_time
            out = strip_ansi_codes(exc.stdout.decode("utf-8", errors="ignore")) if exc.stdout else ""
            err = strip_ansi_codes(exc.stderr.decode("utf-8", errors="ignore")) if exc.stderr else ""
            return TerminalExecutionResult(
                command=command_str,
                exit_code=-1,
                stdout=out,
                stderr=err + f"\nCommand timed out after {effective_timeout}s.",
                elapsed_seconds=elapsed,
                is_timed_out=True,
            )
        except Exception as exc:
            elapsed = time.perf_counter() - start_time
            return TerminalExecutionResult(
                command=command_str,
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {exc}",
                elapsed_seconds=elapsed,
                is_timed_out=False,
            )
