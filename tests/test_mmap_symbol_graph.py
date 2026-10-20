"""Unit tests for memory-mapped binary symbol graph (.hkg)."""

from pathlib import Path
from local_coder.knowledge.mmap_symbol_graph import MmapSymbolGraph, SymbolNode


def test_should_persist_and_reload_symbol_graph_with_caller_lookup(tmp_path: Path) -> None:
    # Arrange
    db_file = str(tmp_path / "test_graph.hkg")
    graph = MmapSymbolGraph(db_file)

    n1 = SymbolNode(
        symbol_id="services/user.py:get_user",
        file_path="services/user.py",
        symbol_type="function",
        signature="def get_user(uid: int) -> User:",
        dependencies=(),
    )
    n2 = SymbolNode(
        symbol_id="routes/auth.py:login",
        file_path="routes/auth.py",
        symbol_type="function",
        signature="def login(req: Request) -> Token:",
        dependencies=("services/user.py:get_user",),
    )

    # Act
    graph.add_node(n1)
    graph.add_node(n2)
    graph.save()

    # Reopen graph from disk
    reloaded = MmapSymbolGraph(db_file)

    # Assert
    assert len(reloaded) == 2
    queried = reloaded.get_node("services/user.py:get_user")
    assert queried is not None
    assert queried.signature == "def get_user(uid: int) -> User:"

    callers = reloaded.get_callers("services/user.py:get_user")
    assert len(callers) == 1
    assert callers[0].symbol_id == "routes/auth.py:login"

    reloaded.close()
