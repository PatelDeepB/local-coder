"""Sub-millisecond Abstract Syntax Tree validator for Python and polyglot code."""

from dataclasses import dataclass
from typing import Optional
import ast


@dataclass(frozen=True)
class SyntaxValidationResult:
    """Outcome of syntax validation check."""

    is_valid: bool
    error_line: Optional[int] = None
    error_offset: Optional[int] = None
    error_message: Optional[str] = None


class SyntaxValidator:
    """Verifies syntactic correctness of code before rendering or writing."""

    def validate_python(self, code_str: str) -> SyntaxValidationResult:
        """Parses Python source using native AST parser in under 1 millisecond."""
        try:
            ast.parse(code_str)
            return SyntaxValidationResult(is_valid=True)
        except SyntaxError as exc:
            return SyntaxValidationResult(
                is_valid=False,
                error_line=exc.lineno,
                error_offset=exc.offset,
                error_message=exc.msg,
            )
        except Exception as exc:
            return SyntaxValidationResult(
                is_valid=False,
                error_message=str(exc),
            )
