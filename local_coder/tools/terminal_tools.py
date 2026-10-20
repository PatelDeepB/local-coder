"""Terminal execution tool for running tests, compilers, and shell commands."""

from typing import Any
from local_coder.tools.base_tool import BaseAgentTool, ToolResult
from local_coder.workspace.terminal_runner import TerminalRunner


class RunTerminalCommandTool(BaseAgentTool):
    """Executes a command string in a managed shell subprocess."""

    def __init__(self, runner: TerminalRunner) -> None:
        self.runner = runner

    @property
    def name(self) -> str:
        return "run_terminal_command"

    @property
    def description(self) -> str:
        return "Executes shell command (e.g. pytest, python script.py, git status) and returns output."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The exact shell command line string to run"},
                "timeout": {"type": "number", "description": "Optional timeout in seconds", "default": 30.0},
            },
            "required": ["command"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        cmd = kwargs.get("command", "")
        timeout = kwargs.get("timeout", 30.0)
        res = self.runner.run_command(cmd, timeout=timeout)

        out_summary = f"Exit code: {res.exit_code} (took {res.elapsed_seconds:.2f}s)\n"
        if res.stdout:
            out_summary += f"[stdout]:\n{res.stdout.strip()}\n"
        if res.stderr:
            out_summary += f"[stderr]:\n{res.stderr.strip()}\n"

        return ToolResult(is_success=res.is_success, output=out_summary, error_message=res.stderr if not res.is_success else None)
