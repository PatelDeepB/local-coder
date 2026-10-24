"""Virtual shadow workspace for staging non-destructive multi-file edits."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os


@dataclass
class StagedFileEdit:
    """Represents a pending change to a file."""

    file_path: Path
    original_content: Optional[str]  # None if file is newly created
    staged_content: str
    is_deletion: bool = False


class ShadowWorkspace:
    """Maintains an isolated staging layer for safe multi-file edits."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir).resolve()
        self._staged_edits: dict[Path, StagedFileEdit] = {}

    def stage_edit(self, relative_path: str, new_content: str) -> None:
        """Stages an update or creation of a file."""
        target_path = (self.root_dir / relative_path).resolve()
        orig = None
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                orig = f.read()

        self._staged_edits[target_path] = StagedFileEdit(
            file_path=target_path,
            original_content=orig,
            staged_content=new_content,
            is_deletion=False,
        )

    def stage_deletion(self, relative_path: str) -> None:
        """Stages a file deletion."""
        target_path = (self.root_dir / relative_path).resolve()
        orig = None
        if target_path.exists():
            with open(target_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                orig = f.read()

        self._staged_edits[target_path] = StagedFileEdit(
            file_path=target_path,
            original_content=orig,
            staged_content="",
            is_deletion=True,
        )

    def get_staged_content(self, relative_path: str) -> Optional[str]:
        """Returns the staged content of a file if modified, or real disk content if untouched."""
        target_path = (self.root_dir / relative_path).resolve()
        if target_path in self._staged_edits:
            edit = self._staged_edits[target_path]
            return None if edit.is_deletion else edit.staged_content

        if target_path.exists():
            with open(target_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                return f.read()
        return None

    def commit_all(self) -> list[str]:
        """Atomically applies all staged edits to real disk files. Returns list of modified paths."""
        applied: list[str] = []
        for path, edit in self._staged_edits.items():
            if edit.is_deletion:
                if path.exists():
                    os.remove(path)
                    applied.append(str(path))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(edit.staged_content)
                applied.append(str(path))

        self._staged_edits.clear()
        return applied

    def commit_file(self, relative_path: str) -> bool:
        """Commits a single staged file to disk."""
        target_path = (self.root_dir / relative_path).resolve()
        edit = self._staged_edits.pop(target_path, None)
        if not edit:
            return False

        if edit.is_deletion:
            if target_path.exists():
                os.remove(target_path)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(edit.staged_content)
        return True

    def discard_file(self, relative_path: str) -> bool:
        """Discards a single staged file without affecting other files."""
        target_path = (self.root_dir / relative_path).resolve()
        edit = self._staged_edits.pop(target_path, None)
        if not edit:
            return False

        if edit.original_content is not None:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(edit.original_content)
        elif target_path.exists():
            os.remove(target_path)
        return True

    def discard_all(self) -> None:
        """Discards all staged edits in the shadow workspace, reverting files on disk."""
        for target_path, edit in list(self._staged_edits.items()):
            if edit.original_content is not None:
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(edit.original_content)
            elif target_path.exists():
                os.remove(target_path)
        self._staged_edits.clear()

    @property
    def has_staged_edits(self) -> bool:
        return len(self._staged_edits) > 0

    @property
    def staged_files(self) -> list[Path]:
        return list(self._staged_edits.keys())
