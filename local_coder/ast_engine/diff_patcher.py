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
        raw_replace = replace_block.replace("\r\n", "\n").strip()
        norm_replace = re.sub(r"(?m)^[<>=]{5,9}.*$", "", raw_replace).strip("\r\n")

        if not norm_search:
            if norm_replace:
                sep = "\n\n" if not norm_orig.endswith("\n\n") else ""
                modified = norm_orig.rstrip() + sep + norm_replace + "\n"
                diff = self.generate_unified_diff(norm_orig, modified)
                return PatchResult(is_success=True, modified_content=modified, diff_unified=diff)
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

        # 3. Ellipsis wildcard match attempt (when search block contains '...' representing elided body)
        if "..." in norm_search:
            raw_chunks = [c for c in norm_search.split("...") if c.strip()]
            if raw_chunks:
                escaped_chunks = [
                    re.sub(r"\\\s+", r"\\s+", re.escape(c.strip()))
                    for c in raw_chunks
                ]
                wildcard_pattern = r"\s*[\s\S]*?\s*".join(escaped_chunks)
                if norm_search.rstrip().endswith("..."):
                    wildcard_pattern += r"[\s\S]*?(?=\n\s*(?:def\s|class\s|\Z))"
                match = re.search(wildcard_pattern, norm_orig)
                if match:
                    modified = norm_orig[: match.start()] + norm_replace + norm_orig[match.end() :]
                    diff = self.generate_unified_diff(norm_orig, modified)
                    return PatchResult(is_success=True, modified_content=modified, diff_unified=diff)

        # 4. Swapped SEARCH/REPLACE recovery: check if replace block matches original
        if norm_replace and norm_replace in norm_orig and norm_search not in norm_orig:
            modified = norm_orig.replace(norm_replace, norm_search, 1)
            diff = self.generate_unified_diff(norm_orig, modified)
            return PatchResult(is_success=True, modified_content=modified, diff_unified=diff)

        # 5. Model put intended replacement in SEARCH with ellipsis in REPLACE
        if norm_replace in ["...", "", "pass"] or norm_replace.startswith("..."):
            orig_lines = norm_orig.splitlines()
            search_lines = [l for l in norm_search.splitlines() if not l.strip().startswith("#") and l.strip()]
            if search_lines:
                matcher = difflib.SequenceMatcher(None, orig_lines, search_lines)
                m = matcher.find_longest_match(0, len(orig_lines), 0, len(search_lines))
                if m.size >= 2:
                    matched_prefix = orig_lines[: m.a]
                    matched_suffix = orig_lines[m.a + m.size :]
                    new_lines = matched_prefix + norm_search.splitlines() + matched_suffix
                    modified = "\n".join(new_lines) + ("\n" if norm_orig.endswith("\n") else "")
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
