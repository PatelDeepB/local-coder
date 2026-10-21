"""Unit tests for CompilerGate error detection and LSP diagnostic ingestion."""

from local_coder.agent.compiler_gate import CompilerGate, DiagnosticSeverity


def test_should_pass_valid_python_syntax() -> None:
    # Arrange
    gate = CompilerGate()
    code = "def add(a: int, b: int) -> int:\n    return a + b\n"

    # Act
    report = gate.check_file_content("math_utils.py", code)

    # Assert
    assert report.is_valid is True
    assert len(report.errors) == 0


def test_should_catch_invalid_python_syntax() -> None:
    # Arrange
    gate = CompilerGate()
    broken_code = "def add(a: int, b: int)\n    return a + b\n"

    # Act
    report = gate.check_file_content("broken.py", broken_code)

    # Assert
    assert report.is_valid is False
    assert len(report.errors) == 1
    assert report.errors[0].line == 1
    assert report.errors[0].source == "python_compiler"


def test_should_validate_and_catch_broken_json() -> None:
    # Arrange
    gate = CompilerGate()
    good_json = '{"name": "test-pkg", "version": "1.0.0"}'
    bad_json = '{"name": "test-pkg", "version": }'

    # Act
    good_report = gate.check_file_content("package.json", good_json)
    bad_report = gate.check_file_content("package.json", bad_json)

    # Assert
    assert good_report.is_valid is True
    assert bad_report.is_valid is False
    assert bad_report.errors[0].source == "json_validator"


def test_should_catch_unbalanced_brackets_in_jsx() -> None:
    # Arrange
    gate = CompilerGate()
    broken_jsx = "function App() { return (<div>Hello world; }"

    # Act
    report = gate.check_file_content("src/App.jsx", broken_jsx)

    # Assert
    assert report.is_valid is False
    assert len(report.errors) > 0


def test_should_ingest_lsp_diagnostics() -> None:
    # Arrange
    gate = CompilerGate()
    raw_lsp = [
        {
            "file": "src/App.tsx",
            "line": 15,
            "column": 4,
            "message": "Cannot find name 'useState'.",
            "severity": "error",
        },
        {
            "file": "src/App.tsx",
            "line": 22,
            "column": 8,
            "message": "'unusedVar' is declared but never read.",
            "severity": "warning",
        },
    ]

    # Act
    report = gate.ingest_lsp_diagnostics(raw_lsp)

    # Assert
    assert report.is_valid is False
    assert len(report.errors) == 1
    assert report.errors[0].message == "Cannot find name 'useState'."
    assert len(report.warnings) == 1
    assert report.warnings[0].severity == DiagnosticSeverity.WARNING


def test_should_format_repair_prompt_with_compiler_feedback() -> None:
    # Arrange
    gate = CompilerGate()
    broken_code = "def calc(): return 1 /"
    report = gate.check_file_content("calc.py", broken_code)

    # Act
    prompt = gate.format_repair_prompt(report, broken_code, "calc.py")

    # Assert
    assert "File: calc.py" in prompt
    assert "python_compiler" in prompt
    assert "def calc(): return 1 /" in prompt
