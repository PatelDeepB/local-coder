"""Scans repositories and builds on-disk HDC and symbol graph indexes."""

import os
from pathlib import Path
from typing import Optional

from local_coder.ast_engine.symbol_extractor import SymbolExtractor
from local_coder.knowledge.hdc_code_index import HDCCodeIndex
from local_coder.knowledge.mmap_symbol_graph import MmapSymbolGraph, SymbolNode


class TreeIndexer:
    """Traverses repository files and populates zero-RAM indexing structures."""

    IGNORED_DIRS = {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        ".pytest_cache",
        "build",
        "dist",
        ".idea",
        ".vscode",
    }

    def __init__(
        self,
        hdc_index: Optional[HDCCodeIndex] = None,
        graph_store: Optional[MmapSymbolGraph] = None,
    ) -> None:
        self.hdc_index = hdc_index if hdc_index is not None else HDCCodeIndex()
        self.graph_store = graph_store
        self._extractor = SymbolExtractor()

    def index_directory(self, root_path: str | Path) -> int:
        """Walks project directory and indexes all Python symbols. Returns count of indexed symbols."""
        root = Path(root_path).resolve()
        count = 0

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in self.IGNORED_DIRS]

            for filename in filenames:
                if filename.endswith(".py"):
                    full_path = Path(dirpath) / filename
                    count += self.index_file(full_path, root)

        if self.graph_store:
            self.graph_store.save()

        return count

    def index_file(self, file_path: Path, root_path: Path) -> int:
        """Parses a single file and records its symbols in HDC and graph stores."""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
        except Exception:
            return 0

        rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")
        symbols = self._extractor.extract_from_source(source)

        for sym in symbols:
            # Register in HDC index for bitwise semantic search
            snippet = f"{sym.signature}\n{sym.docstring or ''}"
            self.hdc_index.add_symbol(
                symbol_id=f"{rel_path}:{sym.name}",
                file_path=rel_path,
                symbol_type=sym.symbol_type,
                code_snippet=snippet,
            )

            # Register in binary symbol graph
            if self.graph_store:
                self.graph_store.add_node(
                    SymbolNode(
                        symbol_id=f"{rel_path}:{sym.name}",
                        file_path=rel_path,
                        symbol_type=sym.symbol_type,
                        signature=sym.signature,
                        dependencies=sym.dependencies,
                    )
                )

        return len(symbols)

    def reindex_file(self, file_path: Path, root_path: Path) -> int:
        """Incrementally removes old symbols and re-indexes a single file."""
        rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")
        self.hdc_index.remove_file(rel_path)
        if not file_path.exists():
            return 0
        return self.index_file(file_path, root_path)

    def format_interface_contracts(self, symbols_or_files: list[str]) -> str:
        """Formats high-density interface signatures for prompt context injection."""
        lines = ["[Indexed Codebase Contracts]:"]
        for item in symbols_or_files:
            lines.append(f"- {item}")
        return "\n".join(lines)
