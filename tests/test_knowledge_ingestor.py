"""Unit tests for ModernKnowledgeIngestor and high-throughput on-disk knowledge scaling."""

from pathlib import Path

from local_coder.knowledge.coding_knowledge_db import CodingKnowledgeDB
from local_coder.knowledge.knowledge_ingestor import ModernKnowledgeIngestor


def test_should_ingest_python_module(tmp_path: Path) -> None:
    # Arrange
    db_file = tmp_path / "test_knowledge.db"
    db = CodingKnowledgeDB(db_file)
    ingestor = ModernKnowledgeIngestor(db)

    # Act
    count = ingestor.ingest_python_module("json", category="stdlib")

    # Assert
    assert count > 0
    hit = db.lookup_topic("json.dumps")
    assert hit is not None
    assert "dumps" in hit.signature


def test_should_ingest_source_file_ast(tmp_path: Path) -> None:
    # Arrange
    db_file = tmp_path / "test_knowledge.db"
    db = CodingKnowledgeDB(db_file)
    ingestor = ModernKnowledgeIngestor(db)

    code_file = tmp_path / "models.py"
    code_file.write_text(
        "class Order:\n"
        "    '''Represents customer order.'''\n"
        "    pass\n\n"
        "def process_order(order_id: str) -> bool:\n"
        "    '''Processes pending order.'''\n"
        "    return True\n",
        encoding="utf-8",
    )

    # Act
    count = ingestor.ingest_source_file(code_file, category="orders")

    # Assert
    assert count == 2
    order_hit = db.lookup_topic("models.Order")
    assert order_hit is not None
    assert "class Order" in order_hit.signature

    func_hit = db.lookup_topic("models.process_order")
    assert func_hit is not None
    assert "def process_order" in func_hit.signature


def test_should_resolve_contracts_for_goal(tmp_path: Path) -> None:
    # Arrange
    db_file = tmp_path / "test_knowledge.db"
    db = CodingKnowledgeDB(db_file)
    ingestor = ModernKnowledgeIngestor(db)
    ingestor.ingest_python_module("pathlib", category="stdlib")

    # Act
    context_str = ingestor.resolve_contracts_for_goal("Read file with Path and resolve directory")

    # Assert
    assert len(context_str) > 0
    assert "pathlib" in context_str.lower()
    assert "VERIFIED CANONICAL API CONTRACTS" in context_str
