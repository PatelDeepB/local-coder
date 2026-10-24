"""Syntax balancing and framework import validation helpers for CompilerGate."""

import ast
from local_coder.agent.compiler_types import DiagnosticItem, DiagnosticReport


def check_missing_common_imports(
    file_path: str, content: str, tree: ast.AST
) -> list[DiagnosticItem]:
    """Detects commonly missing framework imports before disk commits."""
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name)
                imported_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.name)
                imported_names.add(alias.asname or alias.name)

    errors = []
    if "redirect(" in content and "redirect" not in imported_names:
        errors.append(DiagnosticItem(
            file_path=file_path, line=1, column=1,
            message="Missing import: 'from django.shortcuts import redirect'",
            source="import_gate",
        ))
    if "TaskForm" in content and "TaskForm" not in imported_names and "class TaskForm" not in content:
        errors.append(DiagnosticItem(
            file_path=file_path, line=1, column=1,
            message="Missing import: 'from tasks.forms import TaskForm'",
            source="import_gate",
        ))

    for sym in ("Dict", "List", "Optional", "Tuple", "Any", "Union"):
        if (f"{sym}[" in content or f": {sym}" in content or f"-> {sym}" in content) and sym not in imported_names:
            errors.append(DiagnosticItem(
                file_path=file_path, line=1, column=1,
                message=f"Missing import: 'from typing import {sym}'",
                source="import_gate",
            ))

    return errors


def check_bracket_balance(file_path: str, content: str) -> DiagnosticReport:
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
