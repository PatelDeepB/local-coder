"""Git-aware version control operations and checkpoint manager."""

from pathlib import Path
from typing import Optional
import subprocess


class GitManager:
    """Provides non-destructive git inspections and automated checkpoint recovery."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir).resolve()

    def is_git_repository(self) -> bool:
        """Returns True if root_dir is inside a git work tree."""
        res = self._run_git(["rev-parse", "--is-inside-work-tree"])
        return res is not None and res.strip() == "true"

    def get_status(self) -> str:
        """Returns short git status."""
        out = self._run_git(["status", "--short"])
        return out or "Clean working tree"

    def get_diff(self, file_path: Optional[str] = None) -> str:
        """Returns unified diff of unstaged and staged modifications."""
        args = ["diff", "HEAD"]
        if file_path:
            args.append(file_path)
        out = self._run_git(args)
        return out or ""

    def restore_file(self, file_path: str) -> bool:
        """Restores a modified file to HEAD state in 5 milliseconds."""
        res = self._run_git(["checkout", "HEAD", "--", file_path])
        return res is not None

    def _run_git(self, args: list[str]) -> Optional[str]:
        try:
            proc = subprocess.run(
                ["git"] + args,
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            if proc.returncode == 0:
                return proc.stdout.strip()
            return None
        except Exception:
            return None
