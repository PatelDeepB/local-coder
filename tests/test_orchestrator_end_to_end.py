"""End-to-end integration tests for LOCAL-CODER orchestrator."""

from pathlib import Path
from local_coder.orchestrator import LocalCoderOrchestrator


def test_should_initialize_workspace_and_index_codebase(tmp_path: Path) -> None:
    # Arrange: Create sample multi-file project in tmp_path
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "models.py").write_text(
        "class UserModel:\n    def __init__(self, name: str):\n        self.name = name\n",
        encoding="utf-8",
    )
    (tmp_path / "app" / "services.py").write_text(
        "from app.models import UserModel\ndef create_user(name: str) -> UserModel:\n    return UserModel(name)\n",
        encoding="utf-8",
    )

    orch = LocalCoderOrchestrator(workspace_root=tmp_path)

    # Act
    count = orch.initialize_codebase()

    # Assert
    assert count >= 2
    assert len(orch.hdc_index) >= 2

    # Query HDC search
    hits = orch.hdc_index.search("create user model", limit=2)
    assert len(hits) > 0
    assert any("create_user" in h.symbol_id or "UserModel" in h.symbol_id for h in hits)

    orch.symbol_graph.close()


def test_should_execute_deterministic_refactor_and_commit(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "api.py"
    target.write_text("def fetch_user(uid: int):\n    return {'uid': uid}\n", encoding="utf-8")
    orch = LocalCoderOrchestrator(workspace_root=tmp_path)

    # Act: Stage LibCST transformation directly via orchestrator tool
    tool = next(t for t in orch.tools if t.name == "cst_transform")
    res = tool.execute(file_path="api.py", transform_type="make_async", function_name="fetch_user")

    # Assert
    assert res.is_success is True
    assert orch.shadow_workspace.has_staged_edits is True

    # Commit to disk
    applied = orch.commit_changes()
    assert len(applied) == 1
    assert "async def fetch_user" in target.read_text(encoding="utf-8")

    orch.symbol_graph.close()
