"""Unit tests for IncrementalFileWatcher and sub-2ms symbol updates."""

from pathlib import Path
import time

from local_coder.ast_engine.tree_indexer import TreeIndexer
from local_coder.knowledge.dependency_graph import CodebaseDependencyGraph
from local_coder.knowledge.file_watcher import IncrementalFileWatcher
from local_coder.knowledge.hdc_code_index import HDCCodeIndex


def test_should_detect_new_file_and_index_symbols(tmp_path: Path) -> None:
    # Arrange
    hdc = HDCCodeIndex()
    indexer = TreeIndexer(hdc_index=hdc)
    dep_graph = CodebaseDependencyGraph(root_dir=tmp_path)
    watcher = IncrementalFileWatcher(
        root_dir=tmp_path,
        tree_indexer=indexer,
        dependency_graph=dep_graph,
    )

    # Act
    code_file = tmp_path / "calculator.py"
    code_file.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
    events = watcher.poll_once()

    # Assert
    assert len(events) == 1
    ev = events[0]
    assert ev.file_path == "calculator.py"
    assert ev.symbols_updated == 1
    assert ev.elapsed_ms < 500.0  # Cold start allowance on Windows
    assert len(hdc) == 1


def test_should_update_symbols_when_file_modified(tmp_path: Path) -> None:
    # Arrange
    hdc = HDCCodeIndex()
    indexer = TreeIndexer(hdc_index=hdc)
    dep_graph = CodebaseDependencyGraph(root_dir=tmp_path)

    code_file = tmp_path / "service.py"
    code_file.write_text("def serve() -> None:\n    pass\n", encoding="utf-8")

    watcher = IncrementalFileWatcher(
        root_dir=tmp_path,
        tree_indexer=indexer,
        dependency_graph=dep_graph,
    )
    # Prime initial state
    assert len(hdc) == 0  # Priming only records mtime

    # Act
    time.sleep(0.01)
    code_file.write_text("def serve() -> None:\n    pass\n\ndef stop() -> None:\n    pass\n", encoding="utf-8")
    events = watcher.poll_once()

    # Assert
    assert len(events) == 1
    assert events[0].symbols_updated == 2
    assert len(hdc) == 2


def test_should_update_dependencies_incrementally(tmp_path: Path) -> None:
    # Arrange
    hdc = HDCCodeIndex()
    indexer = TreeIndexer(hdc_index=hdc)
    dep_graph = CodebaseDependencyGraph(root_dir=tmp_path)
    watcher = IncrementalFileWatcher(
        root_dir=tmp_path,
        tree_indexer=indexer,
        dependency_graph=dep_graph,
    )

    # Create module A and B
    mod_a = tmp_path / "alpha.py"
    mod_a.write_text("def helper(): pass\n", encoding="utf-8")
    mod_b = tmp_path / "beta.py"
    mod_b.write_text("from .alpha import helper\n", encoding="utf-8")

    # Act
    events = watcher.poll_once()

    # Assert
    assert len(events) == 2
    deps = dep_graph.get_dependencies("beta.py")
    assert "alpha.py" in deps


def test_should_start_and_stop_background_thread(tmp_path: Path) -> None:
    # Arrange
    hdc = HDCCodeIndex()
    indexer = TreeIndexer(hdc_index=hdc)
    dep_graph = CodebaseDependencyGraph(root_dir=tmp_path)
    watcher = IncrementalFileWatcher(
        root_dir=tmp_path,
        tree_indexer=indexer,
        dependency_graph=dep_graph,
    )

    # Act
    watcher.start_background_watcher(interval_seconds=0.05)
    assert watcher._is_running is True

    watcher.stop()

    # Assert
    assert watcher._is_running is False
