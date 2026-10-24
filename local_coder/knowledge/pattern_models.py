"""Data models representing architectural blueprints and verified patterns."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PatternFileBlueprint:
    """Blueprint for a single file in a clean architecture pattern."""

    file_path: str
    purpose: str
    boilerplate_skeleton: str
    key_requirements: tuple[str, ...] = ()


@dataclass(frozen=True)
class ArchitecturalPattern:
    """A complete verified architectural template."""

    name: str
    domain: str
    keywords: tuple[str, ...]
    description: str
    files: tuple[PatternFileBlueprint, ...]
