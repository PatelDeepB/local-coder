"""Unit tests for HierarchicalPlanner and cross-file contract propagation."""

from pathlib import Path
from unittest.mock import MagicMock

from local_coder.agent.hierarchical_planner import HierarchicalPlanner
from local_coder.agent.manifest_synthesizer import FileManifestItem, ManifestSynthesizer
from local_coder.workspace.shadow_workspace import ShadowWorkspace


def test_should_order_manifest_foundation_first(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    synth = MagicMock()
    planner = HierarchicalPlanner(synthesizer=synth, workspace=workspace)

    items = [
        FileManifestItem("tests/test_app.py", "Test suite", "Tests"),
        FileManifestItem("tasks/views.py", "View logic", "Views"),
        FileManifestItem("tasks/models.py", "Model definitions", "Models"),
        FileManifestItem("tasks/forms.py", "Form definitions", "Forms"),
    ]

    # Act
    ordered = planner.sort_manifest_by_dependency_order(items)
    file_order = [it.file_path for it in ordered]

    # Assert
    assert file_order[0] == "tasks/models.py"
    assert file_order[1] == "tasks/forms.py"
    assert file_order[2] == "tasks/views.py"
    assert file_order[3] == "tests/test_app.py"


def test_should_extract_ast_contracts(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    synth = MagicMock()
    planner = HierarchicalPlanner(synthesizer=synth, workspace=workspace)

    code = (
        "class Task:\n"
        "    title = Field()\n"
        "    def mark_done(self) -> None: pass\n\n"
        "def create_task(title: str) -> Task:\n"
        "    return Task()\n"
    )

    # Act
    contracts = planner.extract_ast_contracts("models.py", code)

    # Assert
    assert "class Task:" in contracts
    assert "def mark_done" in contracts
    assert "def create_task" in contracts


def test_should_propagate_contracts_through_hierarchy(tmp_path: Path) -> None:
    # Arrange
    workspace = ShadowWorkspace(tmp_path)
    synth = MagicMock()
    synth.synthesize_file.side_effect = [
        "class Order: pass",  # models.py
        "from .models import Order\ndef view(): pass",  # views.py
    ]
    planner = HierarchicalPlanner(synthesizer=synth, workspace=workspace)

    manifest = [
        FileManifestItem("views.py", "Views", "Use Order"),
        FileManifestItem("models.py", "Models", "Define Order"),
    ]

    # Act
    results = planner.synthesize_hierarchy(manifest, user_goal="Build order system")

    # Assert
    assert len(results) == 2
    # Verify models synthesized first, then views
    assert results[0].file_path == "models.py"
    assert results[1].file_path == "views.py"

    # Verify views synthesis received models contract in its prompt
    second_call_goal = synth.synthesize_file.call_args_list[1][0][1]
    assert "=== UPSTREAM CONTRACTS" in second_call_goal
    assert "class Order:" in second_call_goal
