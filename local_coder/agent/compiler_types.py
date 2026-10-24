"""Type definitions and data models for compiler gates and LSP diagnostics."""

from dataclasses import dataclass, field
from enum import Enum


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
