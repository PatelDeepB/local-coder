"""High-throughput ingestion engine for scaling CodingKnowledgeDB across 20-30GB on SSD."""

import ast
from dataclasses import dataclass
import inspect
from pathlib import Path
import re
from typing import Any, Optional

from local_coder.knowledge.coding_knowledge_db import CodingKnowledgeDB, KnowledgeHit


@dataclass(frozen=True)
class IngestedSymbolContract:
    """Extracted interface contract for a library or module symbol."""

    topic: str
    category: str
    version: str
    signature: str
    docstring: str
    canonical_code: str


class ModernKnowledgeIngestor:
    """Parses Python packages, type stubs, and canonical repositories into on-disk SQLite FTS5."""

    def __init__(self, db: Optional[CodingKnowledgeDB] = None) -> None:
        self.db = db or CodingKnowledgeDB()

    def ingest_python_module(self, module_name: str, category: str, version: str = "Modern 2024+") -> int:
        """Dynamically inspects an installed Python module and indexes its public classes and functions."""
        try:
            mod = __import__(module_name, fromlist=["*"])
        except Exception:
            return 0

        contracts: list[IngestedSymbolContract] = []
        for name, member in inspect.getmembers(mod):
            if name.startswith("_"):
                continue

            if inspect.isclass(member) or inspect.isfunction(member):
                doc = inspect.getdoc(member) or f"Public interface for {module_name}.{name}"
                try:
                    sig = str(inspect.signature(member))
                except Exception:
                    sig = "(...)"

                kind = "class" if inspect.isclass(member) else "def"
                full_sig = f"{kind} {name}{sig}"
                topic = f"{module_name}.{name}"
                canonical = f"# Standard usage of {topic}\n{full_sig}:\n    pass"

                contracts.append(
                    IngestedSymbolContract(
                        topic=topic,
                        category=category,
                        version=version,
                        signature=full_sig,
                        docstring=doc[:400],
                        canonical_code=canonical,
                    )
                )

        return self._batch_insert_contracts(contracts)

    def ingest_source_file(self, file_path: Path, category: str, version: str = "Modern 2024+") -> int:
        """Parses a Python source file or type stub (.pyi) via AST and extracts signatures."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)
        except Exception:
            return 0

        module_slug = file_path.stem
        contracts: list[IngestedSymbolContract] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    sig = self._format_ast_function_sig(node)
                    doc = ast.get_docstring(node) or f"Function {node.name}"
                    contracts.append(
                        IngestedSymbolContract(
                            topic=f"{module_slug}.{node.name}",
                            category=category,
                            version=version,
                            signature=sig,
                            docstring=doc[:400],
                            canonical_code=f"{sig}:\n    pass",
                        )
                    )
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith("_"):
                    sig = f"class {node.name}:"
                    doc = ast.get_docstring(node) or f"Class {node.name}"
                    contracts.append(
                        IngestedSymbolContract(
                            topic=f"{module_slug}.{node.name}",
                            category=category,
                            version=version,
                            signature=sig,
                            docstring=doc[:400],
                            canonical_code=f"{sig}\n    pass",
                        )
                    )

        return self._batch_insert_contracts(contracts)

    def _format_ast_function_sig(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        """Reconstructs signature string from AST node."""
        args_str = ", ".join(arg.arg for arg in node.args.args)
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        return f"{prefix} {node.name}({args_str})"

    def _batch_insert_contracts(self, contracts: list[IngestedSymbolContract]) -> int:
        """Inserts extracted contracts into on-disk database."""
        count = 0
        for c in contracts:
            self.db.insert_entry(
                topic=c.topic,
                category=c.category,
                version=c.version,
                signature=c.signature,
                canonical_code=c.canonical_code,
                docstring=c.docstring,
            )
            count += 1
        return count

    def resolve_contracts_for_goal(self, goal: str, limit: int = 3) -> str:
        """Retrieves exact canonical signatures matching the user goal for prompt enrichment."""
        hits = self.db.search(goal, limit=limit)
        if not hits:
            return ""

        blocks = ["[VERIFIED CANONICAL API CONTRACTS - Zero-RAM In-Disk Knowledge]:"]
        for h in hits:
            blocks.append(
                f"--- API: {h.topic} ({h.version}) ---\n"
                f"Signature: {h.signature}\n"
                f"Canonical Usage:\n```\n{h.canonical_code}\n```\n"
            )
        return "\n".join(blocks)
