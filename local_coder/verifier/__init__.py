"""Automated compiler verification, static analysis, and micro-repair package."""

from local_coder.verifier.lsp_diagnostics import DiagnosticIssue, StaticDiagnosticsValidator
from local_coder.verifier.repair_loop import MicroRepairLoop, RepairResult
from local_coder.verifier.syntax_validator import SyntaxValidationResult, SyntaxValidator
from local_coder.verifier.test_runner import TestExecutionOutcome, TestRunner

__all__ = [
    "SyntaxValidator",
    "SyntaxValidationResult",
    "StaticDiagnosticsValidator",
    "DiagnosticIssue",
    "TestRunner",
    "TestExecutionOutcome",
    "MicroRepairLoop",
    "RepairResult",
]
