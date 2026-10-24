"""Curated repository of clean architecture patterns, templates, and production idioms."""

from typing import Optional
import re

from local_coder.knowledge.backend_patterns import (
    CLI_DATA_ANALYSIS_PATTERN,
    DJANGO_CRUD_PATTERN,
)
from local_coder.knowledge.pattern_models import (
    ArchitecturalPattern,
    PatternFileBlueprint,
)
from local_coder.knowledge.web_patterns import (
    FASTAPI_REST_PATTERN,
    REACT_DASHBOARD_PATTERN,
)


class CleanPatternBank:
    """Provides instant architectural skeletons and clean-code guidance."""

    def __init__(self) -> None:
        self._patterns = [
            REACT_DASHBOARD_PATTERN,
            FASTAPI_REST_PATTERN,
            DJANGO_CRUD_PATTERN,
            CLI_DATA_ANALYSIS_PATTERN,
        ]

    def get_all_patterns(self) -> list[ArchitecturalPattern]:
        """Returns all registered architectural patterns."""
        return list(self._patterns)

    def match_pattern(self, goal: str) -> Optional[ArchitecturalPattern]:
        """Finds matching architectural pattern for user goal."""
        lower_goal = goal.lower()
        best_match: Optional[ArchitecturalPattern] = None
        max_hits = 0

        for pattern in self._patterns:
            hits = sum(
                1
                for kw in pattern.keywords
                if re.search(r"\b" + re.escape(kw) + r"\b", lower_goal)
            )
            if hits > max_hits:
                max_hits = hits
                best_match = pattern

        return best_match if max_hits > 0 else None

    def get_file_blueprint(
        self, pattern: ArchitecturalPattern, file_path: str
    ) -> Optional[PatternFileBlueprint]:
        """Finds specific file blueprint within matched pattern."""
        norm = file_path.replace("\\", "/").lower()
        for fb in pattern.files:
            if fb.file_path.lower() == norm or norm.endswith(fb.file_path.lower()):
                return fb
        return None

    def build_guidance_prompt(self, goal: str, target_file: str) -> str:
        """Injects clean architectural skeleton into prompt context."""
        pattern = self.match_pattern(goal)
        if not pattern:
            return ""

        blueprint = self.get_file_blueprint(pattern, target_file)
        if not blueprint:
            return f"Architectural Style: {pattern.name}\nDomain: {pattern.domain}\n"

        reqs = ", ".join(blueprint.key_requirements)
        return (
            f"=== VERIFIED ARCHITECTURAL PATTERN: {pattern.name} ===\n"
            f"Target: {blueprint.file_path}\n"
            f"Key Requirements: {reqs}\n"
            f"Production Skeleton (Use as reference for clean syntax and structure):\n"
            f"```\n{blueprint.boilerplate_skeleton}\n```\n"
        )
