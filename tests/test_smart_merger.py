"""Unit tests for non-destructive SmartCodeMerger."""

from pathlib import Path
from local_coder.ast_engine.smart_merger import SmartCodeMerger
from local_coder.tools.file_tools import WriteFileTool
from local_coder.workspace.shadow_workspace import ShadowWorkspace


def test_should_append_new_function_without_removing_existing_functions() -> None:
    # Arrange
    existing = (
        "def calculate_force(mass: float, acceleration: float) -> float:\n"
        "    return mass * acceleration\n"
    )
    incoming = (
        "def calculate_work(force: float, distance: float) -> float:\n"
        "    return force * distance\n"
    )
    merger = SmartCodeMerger()

    # Act
    merged = merger.merge_source_code(existing, incoming, file_path="calc.py")

    # Assert
    assert "def calculate_force" in merged
    assert "def calculate_work" in merged
    assert "return mass * acceleration" in merged
    assert "return force * distance" in merged


def test_should_update_existing_function_in_place_preserving_other_functions() -> None:
    # Arrange
    existing = (
        "# Calculation module\n"
        "def calculate_force(mass: float, acceleration: float) -> float:\n"
        "    return mass * acceleration\n\n"
        "def helper_constant() -> int:\n"
        "    return 42\n"
    )
    incoming = (
        "def calculate_force(mass: float, acceleration: float) -> float:\n"
        "    if mass <= 0:\n"
        "        raise ValueError('Invalid mass')\n"
        "    return mass * acceleration\n"
    )
    merger = SmartCodeMerger()

    # Act
    merged = merger.merge_source_code(existing, incoming, file_path="calc.py")

    # Assert
    assert "raise ValueError('Invalid mass')" in merged
    assert "def helper_constant" in merged
    assert "return 42" in merged
    assert "# Calculation module" in merged


def test_should_merge_new_imports_without_duplication() -> None:
    # Arrange
    existing = (
        "import math\n\n"
        "def area(r: float) -> float:\n"
        "    return math.pi * r * r\n"
    )
    incoming = (
        "import sys\n"
        "import math\n\n"
        "def log_msg(m: str) -> None:\n"
        "    sys.stdout.write(m)\n"
    )
    merger = SmartCodeMerger()

    # Act
    merged = merger.merge_source_code(existing, incoming, file_path="geom.py")

    # Assert
    assert "import math" in merged
    assert "import sys" in merged
    assert "def area" in merged
    assert "def log_msg" in merged


def test_should_deep_merge_json_without_clobbering_keys() -> None:
    # Arrange
    existing = '{\n  "name": "my-app",\n  "version": "1.0.0",\n  "scripts": {\n    "start": "node index.js"\n  }\n}'
    incoming = '{\n  "scripts": {\n    "build": "webpack"\n  },\n  "author": "Alice"\n}'
    merger = SmartCodeMerger()

    # Act
    merged = merger.merge_source_code(existing, incoming, file_path="package.json")

    # Assert
    assert '"name": "my-app"' in merged
    assert '"version": "1.0.0"' in merged
    assert '"start": "node index.js"' in merged
    assert '"build": "webpack"' in merged
    assert '"author": "Alice"' in merged


def test_write_file_tool_should_preserve_existing_file_contents_on_partial_edit(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "math_calc.py"
    target.write_text(
        "def calculate_force(mass: float, acceleration: float) -> float:\n"
        "    return mass * acceleration\n",
        encoding="utf-8",
    )
    workspace = ShadowWorkspace(tmp_path)
    tool = WriteFileTool(workspace)

    # Act
    tool.execute(
        file_path="math_calc.py",
        content="def calculate_work(force: float, distance: float) -> float:\n    return force * distance\n",
    )

    # Assert
    staged = workspace.get_staged_content("math_calc.py")
    assert staged is not None
    assert "def calculate_force" in staged
    assert "def calculate_work" in staged


def test_should_handle_utf8_bom_and_short_files_safely() -> None:
    # Arrange
    existing = "\ufeffdef add(a: int, b: int) -> int:\n    return a + b\n"
    incoming = "def sub(a: int, b: int) -> int:\n    return a - b\n"
    merger = SmartCodeMerger()

    # Act
    merged = merger.merge_source_code(existing, incoming, file_path="calc.py")

    # Assert
    assert "def add" in merged
    assert "def sub" in merged
    assert "\ufeff" not in merged

