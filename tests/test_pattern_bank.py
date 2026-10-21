"""Unit tests for CleanPatternBank architectural guidance."""

from local_coder.knowledge.pattern_bank import CleanPatternBank


def test_should_match_react_dashboard_pattern() -> None:
    # Arrange
    bank = CleanPatternBank()

    # Act
    pat = bank.match_pattern("Create a responsive React dashboard with task list")

    # Assert
    assert pat is not None
    assert pat.domain == "frontend"
    assert any(fb.file_path == "src/App.jsx" for fb in pat.files)


def test_should_match_fastapi_rest_pattern() -> None:
    # Arrange
    bank = CleanPatternBank()

    # Act
    pat = bank.match_pattern("Build a python fastapi rest service for managing products")

    # Assert
    assert pat is not None
    assert pat.domain == "backend"
    assert any(fb.file_path == "main.py" for fb in pat.files)


def test_should_build_guidance_prompt_with_skeleton() -> None:
    # Arrange
    bank = CleanPatternBank()

    # Act
    guidance = bank.build_guidance_prompt("Build React App", "src/App.jsx")

    # Assert
    assert "VERIFIED ARCHITECTURAL PATTERN" in guidance
    assert "src/App.jsx" in guidance
    assert "export default function App" in guidance
