"""Atomic transaction supervisor for multi-file workspace modifications."""

from pathlib import Path
from typing import Optional
import os

from local_coder.workspace.shadow_workspace import ShadowWorkspace


class WorkspaceTransactionManager:
    """Manages transactional execution boundaries with instant rollback on failure."""

    def __init__(self, shadow_workspace: ShadowWorkspace) -> None:
        self.workspace = shadow_workspace
        self._journal: list[tuple[str, Optional[str]]] = []
        self._committed_snapshots: list[list[tuple[str, Optional[str]]]] = []

    def record_backup(self, relative_path: str) -> None:
        """Records file state prior to modification for rollback recovery."""
        target_path = (self.workspace.root_dir / relative_path).resolve()
        orig = None
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                orig = f.read()
        self._journal.append((relative_path, orig))

    def rollback(self) -> None:
        """Restores files in active journal (or most recent committed snapshot) to original state."""
        self.workspace.discard_all()
        target_entries = self._journal if self._journal else (self._committed_snapshots.pop() if self._committed_snapshots else [])

        for rel_path, orig_content in reversed(target_entries):
            target = (self.workspace.root_dir / rel_path).resolve()
            if orig_content is None:
                if target.exists():
                    os.remove(target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(orig_content)

        self._journal.clear()

    def commit(self) -> list[str]:
        """Applies staged edits and moves the active journal into committed snapshot history."""
        applied = self.workspace.commit_all()
        if self._journal:
            self._committed_snapshots.append(list(self._journal))
            self._journal.clear()
        return applied
