""".cursorrules and .localcoder_rules compatibility loader."""

from pathlib import Path
from typing import Optional


class RulesEngine:
    """Discovers and parses repository-specific coding rules and conventions."""

    RULE_FILENAMES = (
        ".cursorrules",
        ".localcoder_rules",
        ".localcoderrules",
        "CODING_STANDARDS.md",
    )

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir).resolve()

    def discover_rules(self) -> Optional[str]:
        """Scans project root for rule files and returns unified instructions."""
        collected: list[str] = []

        for fname in self.RULE_FILENAMES:
            candidate = self.root_dir / fname
            if candidate.is_file():
                try:
                    with open(candidate, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().strip()
                        if content:
                            collected.append(f"[{fname} Guidelines]:\n{content}")
                except Exception:
                    continue

        if not collected:
            return None
        return "\n\n".join(collected)
