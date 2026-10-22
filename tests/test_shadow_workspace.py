"""Unit tests for virtual shadow workspace and transactional rollback."""

from pathlib import Path
from local_coder.tools.file_tools import WriteFileTool
from local_coder.workspace.shadow_workspace import ShadowWorkspace
from local_coder.workspace.transaction_manager import WorkspaceTransactionManager


def test_should_stage_and_commit_edits_without_premature_disk_write(tmp_path: Path) -> None:
    # Arrange
    test_file = tmp_path / "hello.py"
    test_file.write_text("x = 1\n", encoding="utf-8")
    workspace = ShadowWorkspace(tmp_path)
    tx_mgr = WorkspaceTransactionManager(workspace)

    # Act
    tx_mgr.record_backup("hello.py")
    workspace.stage_edit("hello.py", "x = 99\n")

    # Assert: Real disk file remains untouched before commit
    assert test_file.read_text(encoding="utf-8") == "x = 1\n"
    assert workspace.get_staged_content("hello.py") == "x = 99\n"

    # Commit
    tx_mgr.commit()
    assert test_file.read_text(encoding="utf-8") == "x = 99\n"


def test_should_rollback_changes_cleanly(tmp_path: Path) -> None:
    # Arrange
    test_file = tmp_path / "data.py"
    test_file.write_text("val = 100\n", encoding="utf-8")
    workspace = ShadowWorkspace(tmp_path)
    tx_mgr = WorkspaceTransactionManager(workspace)

    # Act
    tx_mgr.record_backup("data.py")
    workspace.stage_edit("data.py", "val = 200\n")
    tx_mgr.commit()

    # Simulate subsequent failing transaction
    tx_mgr.record_backup("data.py")
    workspace.stage_edit("data.py", "val = 99999\n")
    tx_mgr.commit()

    # Rollback
    tx_mgr.rollback()

    # Assert
    assert test_file.read_text(encoding="utf-8") == "val = 200\n"


def test_should_stage_valid_python_via_write_file_tool(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    tool = WriteFileTool(workspace)

    # Act
    res = tool.execute(file_path="service.py", content="def add(a: int, b: int) -> int:\n    return a + b\n")

    # Assert
    assert res.is_success is True
    assert "Successfully staged" in res.output
    assert workspace.get_staged_content("service.py") is not None


def test_should_reject_invalid_python_syntax_via_write_file_tool(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    tool = WriteFileTool(workspace)

    # Act
    res = tool.execute(file_path="service.py", content="def add(a: int, b: int) -> int:\n    return a + b}\n")

    # Assert
    assert res.is_success is False
    assert "Syntax Error on line 2" in res.error_message
    assert workspace.get_staged_content("service.py") is None


def test_should_stage_valid_json_and_reject_invalid_json_via_write_file_tool(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    tool = WriteFileTool(workspace)

    # Act & Assert: Valid JSON
    valid_res = tool.execute(file_path="package.json", content='{"name": "my-react-app", "version": "1.0.0"}')
    assert valid_res.is_success is True
    assert workspace.get_staged_content("package.json") is not None

    # Act & Assert: Invalid JSON
    invalid_res = tool.execute(file_path="package.json", content='{"name": "broken-json", "version": }')
    assert invalid_res.is_success is False
    assert "JSON Syntax Error" in invalid_res.error_message


def test_should_discard_file_and_revert_disk_to_original(tmp_path: Path) -> None:
    # Arrange
    target = tmp_path / "module.py"
    target.write_text("x = 10\n", encoding="utf-8")
    workspace = ShadowWorkspace(tmp_path)
    workspace.stage_edit("module.py", "x = 999\n")
    # Simulate writing staged to disk
    target.write_text("x = 999\n", encoding="utf-8")

    # Act
    discarded = workspace.discard_file("module.py")

    # Assert
    assert discarded is True
    assert target.read_text(encoding="utf-8") == "x = 10\n"
    assert workspace.get_staged_content("module.py") == "x = 10\n"


def test_should_discard_all_and_revert_disk(tmp_path: Path) -> None:
    # Arrange
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("a = 1\n", encoding="utf-8")
    f2.write_text("b = 2\n", encoding="utf-8")
    workspace = ShadowWorkspace(tmp_path)
    workspace.stage_edit("a.py", "a = 100\n")
    workspace.stage_edit("b.py", "b = 200\n")
    f1.write_text("a = 100\n", encoding="utf-8")
    f2.write_text("b = 200\n", encoding="utf-8")

    # Act
    workspace.discard_all()

    # Assert
    assert f1.read_text(encoding="utf-8") == "a = 1\n"
    assert f2.read_text(encoding="utf-8") == "b = 2\n"
