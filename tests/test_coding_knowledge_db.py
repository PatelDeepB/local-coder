"""Unit tests for CodingKnowledgeDB zero-RAM on-disk knowledge substrate."""

from pathlib import Path
from unittest.mock import MagicMock

from local_coder.agent.manifest_synthesizer import FileManifestItem, ManifestSynthesizer
from local_coder.knowledge.coding_knowledge_db import CodingKnowledgeDB, KnowledgeHit
from local_coder.knowledge.seed_modern_knowledge import seed_knowledge_database
from local_coder.neural.llama_runner import GenerationResult
from local_coder.workspace.shadow_workspace import ShadowWorkspace


def test_should_insert_and_lookup_topic(tmp_path: Path) -> None:
    # Arrange
    db_file = tmp_path / "test_knowledge.db"
    db = CodingKnowledgeDB(db_file)

    # Act
    db.insert_entry(
        topic="fastapi.Depends",
        category="fastapi",
        version="0.115+",
        signature="Annotated[T, Depends(...)]",
        canonical_code="async def get_db(): pass",
        docstring="FastAPI modern dependency injection.",
    )
    hit = db.lookup_topic("fastapi.Depends")

    # Assert
    assert hit is not None
    assert hit.topic == "fastapi.Depends"
    assert hit.version == "0.115+"
    assert "Annotated" in hit.signature


def test_should_search_with_bm25_full_text(tmp_path: Path) -> None:
    # Arrange
    db_file = tmp_path / "test_knowledge.db"
    db = CodingKnowledgeDB(db_file)
    seed_knowledge_database(db)

    # Act
    hits = db.search("django pagination list view", limit=2)

    # Assert
    assert len(hits) > 0
    top_hit = hits[0]
    assert "django" in top_hit.category.lower()
    assert "ListView" in top_hit.topic


def test_should_inject_canonical_idioms_into_synthesizer(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    mock_runner = MagicMock()
    mock_runner.generate.return_value = GenerationResult(
        content="```python\nfrom django.views.generic import ListView\nclass ItemList(ListView): pass\n```",
        elapsed_seconds=0.01,
        tokens_per_second=100.0,
        token_count=10,
        peak_rss_mb=500.0,
    )

    db_file = tmp_path / "test_knowledge.db"
    db = CodingKnowledgeDB(db_file)
    seed_knowledge_database(db)

    synth = ManifestSynthesizer(runner=mock_runner, workspace=workspace, coding_knowledge=db)
    item = FileManifestItem("views.py", "Display list of tasks with pagination", "Use ListView")

    # Act
    code = synth.synthesize_file(item, "Build a Django task list")

    # Assert
    assert "ListView" in code
    call_args = mock_runner.generate.call_args
    prompt_used = call_args[1].get("prompt", "")
    assert "CANONICAL MODERN IDIOM" in prompt_used
