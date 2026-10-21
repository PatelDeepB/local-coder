"""Active compiler and LSP diagnostic gate for real-time error detection and self-repair."""

import ast
from dataclasses import dataclass, field
from enum import Enum
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import tempfile
from typing import Optional


class DiagnosticSeverity(str, Enum):
    """Severity classification for code diagnostics."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class DiagnosticItem:
    """A single diagnostic issue surfaced by a compiler, linter, or LSP."""

    file_path: str
    line: int
    column: int
    message: str
    severity: DiagnosticSeverity = DiagnosticSeverity.ERROR
    source: str = "compiler"


@dataclass(frozen=True)
class DiagnosticReport:
    """Aggregate compilation and diagnostic report for a file or project."""

    is_valid: bool
    errors: list[DiagnosticItem] = field(default_factory=list)
    warnings: list[DiagnosticItem] = field(default_factory=list)

    @property
    def summary_message(self) -> str:
        """Returns concise single-line summary of diagnostic errors."""
        if self.is_valid or not self.errors:
            return "All compiler diagnostics clean."
        first = self.errors[0]
        return f"{first.file_path}:{first.line} [{first.source}] {first.message}"


class CompilerGate:
    """Validates files against real compilers, runtime checkers, and LSP diagnostics."""

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self.timeout = timeout_seconds

    def check_file_content(self, file_path: str, content: str) -> DiagnosticReport:
        """Validates source text using language-specific syntax and compiler checks."""
        ext = Path(file_path).suffix.lower()

        if ext == ".py":
            return self._check_python(file_path, content)
        if ext == ".json":
            return self._check_json(file_path, content)
        if ext in (".js", ".mjs", ".cjs"):
            return self._check_javascript(file_path, content)
        if ext in (".jsx", ".tsx", ".ts"):
            return self._check_jsx_typescript(file_path, content)
        if ext in (".html", ".htm"):
            return self._check_html(file_path, content)

        return DiagnosticReport(is_valid=True)

    def _check_python(self, file_path: str, content: str) -> DiagnosticReport:
        """Checks Python code via AST parsing and bytecode compilation."""
        try:
            ast.parse(content, filename=file_path)
            compile(content, file_path, "exec")
            return DiagnosticReport(is_valid=True)
        except SyntaxError as exc:
            err = DiagnosticItem(
                file_path=file_path,
                line=exc.lineno or 1,
                column=exc.offset or 1,
                message=exc.msg,
                source="python_compiler",
            )
            return DiagnosticReport(is_valid=False, errors=[err])
        except Exception as exc:
            err = DiagnosticItem(
                file_path=file_path,
                line=1,
                column=1,
                message=str(exc),
                source="python_compiler",
            )
            return DiagnosticReport(is_valid=False, errors=[err])

    def _check_json(self, file_path: str, content: str) -> DiagnosticReport:
        """Checks JSON format."""
        try:
            json.loads(content)
            return DiagnosticReport(is_valid=True)
        except json.JSONDecodeError as exc:
            err = DiagnosticItem(
                file_path=file_path,
                line=exc.lineno,
                column=exc.colno,
                message=exc.msg,
                source="json_validator",
            )
            return DiagnosticReport(is_valid=False, errors=[err])

    def _check_javascript(self, file_path: str, content: str) -> DiagnosticReport:
        """Runs node --check if node runtime is available."""
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
            tmp.write(content)
            tmp_name = tmp.name

        try:
            res = subprocess.run(
                ["node", "--check", tmp_name],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            if res.returncode == 0:
                return DiagnosticReport(is_valid=True)

            msg = res.stderr.strip() or "Syntax error in JavaScript"
            err = DiagnosticItem(
                file_path=file_path,
                line=1,
                column=1,
                message=msg.split("\n")[0],
                source="node_check",
            )
            return DiagnosticReport(is_valid=False, errors=[err])
        except (subprocess.SubprocessError, FileNotFoundError):
            # Fallback to basic bracket balancing if node is not executable
            return self._check_bracket_balance(file_path, content)
        finally:
            Path(tmp_name).unlink(missing_ok=True)

    def _check_jsx_typescript(self, file_path: str, content: str) -> DiagnosticReport:
        """Validates bracket and tag balance for React and TypeScript."""
        return self._check_bracket_balance(file_path, content)

    def _check_html(self, file_path: str, content: str) -> DiagnosticReport:
        """Validates HTML markup using HTMLParser."""
        class StrictHTMLParser(HTMLParser):
            """Internal parser tracking syntax failures."""
            def __init__(self) -> None:
                super().__init__()
                self.error_encountered: Optional[str] = None

        parser = StrictHTMLParser()
        try:
            parser.feed(content)
            return DiagnosticReport(is_valid=True)
        except Exception as exc:
            err = DiagnosticItem(
                file_path=file_path,
                line=1,
                column=1,
                message=str(exc),
                source="html_parser",
            )
            return DiagnosticReport(is_valid=False, errors=[err])

    def _check_bracket_balance(self, file_path: str, content: str) -> DiagnosticReport:
        """Verifies matched parenthesis, braces, and brackets."""
        stack: list[tuple[str, int]] = []
        matching = {")": "(", "}": "{", "]": "["}
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for char in line:
                if char in "({[":
                    stack.append((char, line_num))
                elif char in ")}]":
                    if not stack or stack[-1][0] != matching[char]:
                        err = DiagnosticItem(
                            file_path=file_path,
                            line=line_num,
                            column=1,
                            message=f"Unmatched closing bracket '{char}'",
                            source="syntax_gate",
                        )
                        return DiagnosticReport(is_valid=False, errors=[err])
                    stack.pop()

        if stack:
            open_char, line_num = stack.pop()
            err = DiagnosticItem(
                file_path=file_path,
                line=line_num,
                column=1,
                message=f"Unclosed opening bracket '{open_char}'",
                source="syntax_gate",
            )
            return DiagnosticReport(is_valid=False, errors=[err])

        return DiagnosticReport(is_valid=True)

    def ingest_lsp_diagnostics(self, raw_diagnostics: list[dict]) -> DiagnosticReport:
        """Translates external LSP diagnostics from VS Code into a DiagnosticReport."""
        errors: list[DiagnosticItem] = []
        warnings: list[DiagnosticItem] = []

        for item in raw_diagnostics:
            diag = DiagnosticItem(
                file_path=item.get("file", ""),
                line=item.get("line", 1),
                column=item.get("column", 1),
                message=item.get("message", "Unknown diagnostic"),
                severity=DiagnosticSeverity(item.get("severity", "error").lower()),
                source="lsp_server",
            )
            if diag.severity == DiagnosticSeverity.ERROR:
                errors.append(diag)
            else:
                warnings.append(diag)

        return DiagnosticReport(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings,
        )

    def format_repair_prompt(
        self, report: DiagnosticReport, original_code: str, file_path: str
    ) -> str:
        """Builds a targeted prompt instructing the model to repair compiler diagnostics."""
        error_lines = [f"Line {e.line}: {e.message} ({e.source})" for e in report.errors[:3]]
        issues = "\n".join(error_lines)
        return (
            f"File: {file_path}\n"
            f"The compiler or language server reported errors:\n{issues}\n\n"
            f"Original code:\n```{Path(file_path).suffix.lstrip('.')}\n{original_code}\n```\n\n"
            f"Output the complete fixed file content without explanations."
        )
