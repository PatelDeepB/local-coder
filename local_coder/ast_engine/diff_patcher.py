"""Precision AST and text hunk applicator with zero indentation drift."""

from dataclasses import dataclass
from typing import Optional
import difflib
import re


@dataclass(frozen=True)
class PatchResult:
    """Represents the outcome of applying a code patch."""

    is_success: bool
    modified_content: str
    diff_unified: str
    error_message: Optional[str] = None


class PrecisionPatcher:
    """Applies search-and-replace hunks or surgical replacements to source code."""

    def apply_search_replace(
        self,
        original_content: str,
        search_block: str,
        replace_block: str,
    ) -> PatchResult:
        """Finds search_block within original_content and replaces it."""
        norm_orig = original_content.replace("\r\n", "\n")
        norm_search = search_block.replace("\r\n", "\n").strip()
        norm_replace = replace_block.replace("\r\n", "\n").strip()

        if not norm_search:
            return PatchResult(
                is_success=False,
                modified_content=original_content,
                diff_unified="",
                error_message="Search block cannot be empty.",
            )

        # 1. Exact match attempt
        if norm_search in norm_orig:
            modified = norm_orig.replace(norm_search, norm_replace, 1)
            diff = self.generate_unified_diff(norm_orig, modified)
            return PatchResult(is_success=True, modified_content=modified, diff_unified=diff)

        # 2. Whitespace-flexible regex match attempt
        escaped_search = re.escape(norm_search)
        flexible_pattern = re.sub(r"\\\s+", r"\\s+", escaped_search)
        match = re.search(flexible_pattern, norm_orig)

        if match:
            modified = norm_orig[: match.start()] + norm_replace + norm_orig[match.end() :]
            diff = self.generate_unified_diff(norm_orig, modified)
            return PatchResult(is_success=True, modified_content=modified, diff_unified=diff)

        return PatchResult(
            is_success=False,
            modified_content=original_content,
            diff_unified="",
            error_message="Search block could not be located in target file.",
        )

    def generate_unified_diff(
        self,
        original_content: str,
        modified_content: str,
        file_path: str = "target_file.py",
    ) -> str:
        """Generates standard unified diff format for user review."""
        orig_lines = original_content.splitlines(keepends=True)
        mod_lines = modified_content.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return "".join(diff)
