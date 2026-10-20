"""Unit tests for AST syntax validator."""

from local_coder.verifier.syntax_validator import SyntaxValidator


def test_should_pass_valid_python_syntax() -> None:
    # Arrange
    validator = SyntaxValidator()
    code = "def add(a: int, b: int) -> int:\n    return a + b\n"

    # Act
    res = validator.validate_python(code)

    # Assert
    assert res.is_valid is True
    assert res.error_message is None


def test_should_identify_syntax_error_line_and_message() -> None:
    # Arrange
    validator = SyntaxValidator()
    code = "def broken(\n    return 42\n"

    # Act
    res = validator.validate_python(code)

    # Assert
    assert res.is_valid is False
    assert res.error_line is not None
    assert res.error_message is not None
