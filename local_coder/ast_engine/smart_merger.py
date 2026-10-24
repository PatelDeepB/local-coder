"""Intelligent non-destructive code merger preventing file clobbering."""

from typing import Any, Optional
import ast
import json
import re


class SmartCodeMerger:
    """Merges incoming code updates into existing source files without overwriting untouched features."""

    def merge_source_code(self, existing_code: str, incoming_code: str, file_path: str = "") -> str:
        """Merges incoming updates into existing code, preserving all existing functions, classes, and comments."""
        if not existing_code or not existing_code.strip():
            return incoming_code.lstrip("\ufeff")

        existing_code = existing_code.lstrip("\ufeff")
        clean_incoming = incoming_code.lstrip("\ufeff").strip()
        if not clean_incoming:
            return existing_code

        if clean_incoming == existing_code.strip():
            return existing_code

        # Format 1: Python AST merge
        if file_path.endswith(".py"):
            merged_py = self._merge_python(existing_code, incoming_code)
            if merged_py is not None:
                return merged_py

        # Format 2: JSON deep merge
        if file_path.endswith(".json"):
            merged_json = self._merge_json(existing_code, incoming_code)
            if merged_json is not None:
                return merged_json

        # Format 3: Anchor comment replacement (// ... existing code ...)
        merged_anchors = self._merge_anchors(existing_code, incoming_code)
        if merged_anchors is not None:
            return merged_anchors

        # Format 4: Generic partial snippet append
        return self._merge_generic(existing_code, incoming_code)

    def _merge_python(self, existing_code: str, incoming_code: str) -> Optional[str]:
        try:
            tree_orig = ast.parse(existing_code)
            tree_new = ast.parse(incoming_code)
        except Exception:
            return None

        lines_orig = existing_code.splitlines(keepends=True)
        lines_new = incoming_code.splitlines(keepends=True)

        orig_defs = {}
        for node in tree_orig.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                orig_defs[node.name] = node

        new_defs = {}
        for node in tree_new.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                new_defs[node.name] = node

        # If incoming code already contains all existing definitions, it is a complete rewrite
        if orig_defs and set(orig_defs.keys()).issubset(set(new_defs.keys())):
            return incoming_code

        # If incoming code has no functions/classes, but existing code does, don't clobber
        if orig_defs and not new_defs:
            return existing_code.rstrip() + "\n\n" + incoming_code.strip() + "\n"

        # Collect existing imports to avoid duplicate imports
        orig_import_texts = set()
        for node in tree_orig.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                orig_import_texts.add("".join(lines_orig[node.lineno - 1 : node.end_lineno]).strip())

        new_imports = []
        for node in tree_new.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                txt = "".join(lines_new[node.lineno - 1 : node.end_lineno]).strip()
                if txt not in orig_import_texts:
                    new_imports.append(txt)

        # Apply surgical replacements for matching functions/classes in reverse order
        replaced_lines = list(lines_orig)
        matching_nodes = []
        for node in tree_new.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name in orig_defs:
                orig_node = orig_defs[node.name]
                new_text = "".join(lines_new[node.lineno - 1 : node.end_lineno])
                matching_nodes.append((orig_node.lineno, orig_node.end_lineno, new_text))

        matching_nodes.sort(key=lambda x: x[0], reverse=True)
        for s_line, e_line, replacement in matching_nodes:
            replaced_lines[s_line - 1 : e_line] = [replacement]

        # Collect completely new definitions to append
        append_defs = []
        for node in tree_new.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name not in orig_defs:
                append_defs.append("".join(lines_new[node.lineno - 1 : node.end_lineno]).strip())

        header = ("\n".join(new_imports) + "\n\n") if new_imports else ""
        body = "".join(replaced_lines).rstrip()
        footer = ("\n\n\n" + "\n\n\n".join(append_defs) + "\n") if append_defs else "\n"

        merged = header + body + footer
        try:
            ast.parse(merged)
            return merged
        except Exception:
            return None

    def _merge_json(self, existing_code: str, incoming_code: str) -> Optional[str]:
        try:
            orig_data = json.loads(existing_code)
            new_data = json.loads(incoming_code)
            if isinstance(orig_data, dict) and isinstance(new_data, dict):
                merged_dict = self._deep_merge_dict(orig_data, new_data)
                return json.dumps(merged_dict, indent=2) + "\n"
        except Exception:
            return None
        return None

    def _deep_merge_dict(self, base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        result = dict(base)
        for k, v in update.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._deep_merge_dict(result[k], v)
            else:
                result[k] = v
        return result

    def _merge_anchors(self, existing_code: str, incoming_code: str) -> Optional[str]:
        anchor_pattern = r"(?://|#|/\*)\s*\.{3}\s*(?:existing code|code)?\s*(?:\*/)?|\.{3}"
        if not re.search(anchor_pattern, incoming_code, flags=re.IGNORECASE):
            return None

        chunks = re.split(anchor_pattern, incoming_code, flags=re.IGNORECASE)
        valid_chunks = [c.strip() for c in chunks if c.strip()]
        if not valid_chunks:
            return None

        if re.match(r"^\s*" + anchor_pattern, incoming_code, flags=re.IGNORECASE):
            addition = "\n".join(valid_chunks)
            if addition not in existing_code:
                return existing_code.rstrip() + "\n\n" + addition + "\n"

        return None

    def _merge_generic(self, existing_code: str, incoming_code: str) -> str:
        if incoming_code.strip() in existing_code:
            return existing_code

        orig_lines = set(l.strip() for l in existing_code.splitlines() if l.strip())
        incoming_lines = set(l.strip() for l in incoming_code.splitlines() if l.strip())

        if orig_lines and not incoming_lines.issuperset(orig_lines):
            return existing_code.rstrip() + "\n\n" + incoming_code.strip() + "\n"

        return incoming_code
