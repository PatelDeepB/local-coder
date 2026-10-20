"""Unit tests for automated Micro-Repair Loop and Static Diagnostics."""

from local_coder.verifier.lsp_diagnostics import StaticDiagnosticsValidator
from local_coder.verifier.repair_loop import MicroRepairLoop


def test_should_pass_clean_syntax_without_repair() -> None:
    # Arrange
    repair_called = False

    def dummy_generator(prompt: str, ctx: str) -> str:
        nonlocal repair_called
        repair_called = True
        return ""

    loop = MicroRepairLoop(repair_generator=dummy_generator)
    valid_code = "def valid_fn():\n    return 42\n"

    # Act
    res = loop.verify_and_repair(valid_code)

    # Assert
    assert res.is_repaired is False
    assert repair_called is False
    assert res.repaired_code == valid_code


def test_should_trigger_repair_and_fix_syntax_error() -> None:
    # Arrange
    broken_code = "def broken():\n    return 42 +"
    fixed_code = "def broken():\n    return 42 + 1\n"

    def repair_generator(prompt: str, ctx: str) -> str:
        assert "SyntaxError" in prompt
        return fixed_code

    loop = MicroRepairLoop(repair_generator=repair_generator, max_attempts=1)

    # Act
    res = loop.verify_and_repair(broken_code)

    # Assert
    assert res.is_repaired is True
    assert res.repair_attempts == 1
    assert "return 42 + 1" in res.repaired_code


def test_static_diagnostics_should_flag_syntax_error() -> None:
    # Arrange
    validator = StaticDiagnosticsValidator()
    broken_code = "def func(\n"

    # Act
    issues = validator.analyze_source(broken_code)

    # Assert
    assert len(issues) > 0
    assert issues[0].severity == "error"
    assert "SyntaxError" in issues[0].message
