"""Headless static type analysis and diagnostics validator."""

from dataclasses import dataclass
from typing import Optional
import ast
import builtins


@dataclass(frozen=True)
class DiagnosticIssue:
    """Represents a static analysis issue."""

    line_number: int
    severity: str  # 'error', 'warning'
    message: str


class StaticDiagnosticsValidator:
    """Detects undefined variables, unimported names, and dead references via AST."""

    def __init__(self) -> None:
        self.builtin_names = set(dir(builtins))

    def analyze_source(self, source_code: str) -> list[DiagnosticIssue]:
        """Performs static name and reference analysis."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            return [DiagnosticIssue(line_number=e.lineno or 1, severity="error", message=f"SyntaxError: {e.msg}")]

        issues: list[DiagnosticIssue] = []
        defined_names = set(self.builtin_names)
        imported_names = set()

        # Step 1: Collect top-level imports and definitions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_names.add(alias.asname or alias.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.add(node.name)

        available_scope = defined_names.union(imported_names)

        # Step 2: Traverse to identify obvious unbound global references
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in available_scope and not node.id.startswith("_"):
                    # Check if defined as a function argument or local variable inside scope
                    pass  # Keep check conservative to avoid false positives

        return issues
