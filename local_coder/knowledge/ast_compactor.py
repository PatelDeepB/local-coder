"""High-throughput AST Semantic Compactor for virtualizing 65,000+ token context."""

from __future__ import annotations

import ast
from pathlib import Path
import re
from typing import Optional


class ASTSemanticCompactor:
    """Strips implementation bodies while preserving public class and function interfaces."""

    def compact_python_code(self, code: str) -> str:
        """Compresses Python code into an interface outline with 90%+ token reduction."""
        if not code.strip():
            return ""

        try:
            tree = ast.parse(code)
        except Exception:
            return self._fallback_regex_compress(code)

        class BodyPruner(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
                return self._prune_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
                return self._prune_function(node)

            def _prune_function(
                self, node: ast.FunctionDef | ast.AsyncFunctionDef
            ) -> ast.AST:
                docstring = ast.get_docstring(node)
                new_body: list[ast.stmt] = []
                if docstring:
                    new_body.append(ast.Expr(value=ast.Constant(value=docstring)))
                new_body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
                node.body = new_body
                return node

        pruned_tree = BodyPruner().visit(tree)
        ast.fix_missing_locations(pruned_tree)

        try:
            return ast.unparse(pruned_tree)
        except Exception:
            return self._fallback_regex_compress(code)

    def _fallback_regex_compress(self, code: str) -> str:
        """Lightweight regex line filter for non-Python or unparseable source files."""
        lines = code.splitlines()
        kept: list[str] = []
        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith(("import ", "from ", "class ", "def ", "async def ", "export ", "interface ", "type "))
                or stripped.startswith(("@", "public ", "private ", "protected "))
                or stripped.startswith('"""')
            ):
                kept.append(line)
        return "\n".join(kept[:100])

    def compact_file(self, file_path: str, code: str) -> str:
        """Compacts a single file based on its file extension."""
        if file_path.endswith(".py"):
            return self.compact_python_code(code)
        return self._fallback_regex_compress(code)

    def build_virtual_workspace_schema(
        self,
        files: dict[str, str],
        active_file: Optional[str] = None,
        max_total_chars: int = 16000,
    ) -> str:
        """Combines multiple files into a compact virtual project schema under 4,000 tokens."""
        outlines: list[str] = []
        current_chars = 0

        for path, content in sorted(files.items()):
            if active_file and path == active_file:
                continue

            compacted = self.compact_file(path, content)
            if not compacted.strip():
                continue

            block = f"--- Interface: {path} ---\n{compacted}\n"
            if current_chars + len(block) > max_total_chars:
                outlines.append(f"--- Interface: {path} (truncated) ---")
                break

            outlines.append(block)
            current_chars += len(block)

        return "\n".join(outlines)

    def build_workspace_schema(
        self,
        root_dir: Path,
        file_reader: Optional[object] = None,
        max_total_chars: int = 12000,
    ) -> str:
        """Walks project workspace and compiles compact virtual interface schema."""
        ignored_dirs = {
            ".git",
            ".localcoder",
            ".pytest_cache",
            "venv",
            "__pycache__",
            "node_modules",
            "workspace_runs",
            "benchmark_tasks",
        }
        collected: dict[str, str] = {}
        for path in root_dir.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".ts", ".js"}:
                continue
            rel_parts = path.relative_to(root_dir).parts
            if any(part in ignored_dirs for part in rel_parts):
                continue
            try:
                rel = str(path.relative_to(root_dir)).replace("\\", "/")
                if file_reader and hasattr(file_reader, "get_file_content"):
                    content = file_reader.get_file_content(rel)
                else:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                collected[rel] = content
            except Exception:
                continue
        return self.build_virtual_workspace_schema(collected, max_total_chars=max_total_chars)
