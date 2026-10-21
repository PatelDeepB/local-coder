"""Unit tests for CodebaseDependencyGraph multi-hop import resolution."""

from pathlib import Path
import pytest

from local_coder.knowledge.dependency_graph import CodebaseDependencyGraph


def test_should_parse_python_imports_and_build_graph(tmp_path: Path) -> None:
    # Arrange
    utils_py = tmp_path / "utils.py"
    utils_py.write_text(
        "def format_name(name: str) -> str:\n    return name.title()\n\n"
        "class Helper:\n    pass\n",
        encoding="utf-8",
    )

    main_py = tmp_path / "main.py"
    main_py.write_text(
        "from .utils import format_name, Helper\n\ndef run():\n    return format_name('alice')\n",
        encoding="utf-8",
    )

    # Act
    graph = CodebaseDependencyGraph(root_dir=tmp_path)
    edge_count = graph.scan_codebase()

    # Assert
    assert edge_count >= 1
    deps = graph.get_dependencies("main.py")
    assert "utils.py" in deps

    dependents = graph.get_dependents("utils.py")
    assert "main.py" in dependents

    contracts = graph.extract_file_contracts("utils.py")
    assert "def format_name" in contracts
    assert "class Helper" in contracts

    enriched = graph.build_enriched_context("main.py")
    assert "Imported Contracts for main.py:" in enriched
    assert "utils.py" in enriched


def test_should_parse_javascript_imports(tmp_path: Path) -> None:
    # Arrange
    src = tmp_path / "src"
    src.mkdir()
    api_js = src / "api.js"
    api_js.write_text(
        "export function fetchData() { return []; }\nexport const API_URL = 'http://localhost';\n",
        encoding="utf-8",
    )

    app_jsx = src / "App.jsx"
    app_jsx.write_text(
        "import { fetchData } from './api';\nexport default function App() { return null; }\n",
        encoding="utf-8",
    )

    # Act
    graph = CodebaseDependencyGraph(root_dir=tmp_path)
    graph.scan_codebase()

    # Assert
    deps = graph.get_dependencies("src/App.jsx")
    assert "src/api.js" in deps
    dependents = graph.get_dependents("src/api.js")
    assert "src/App.jsx" in dependents
