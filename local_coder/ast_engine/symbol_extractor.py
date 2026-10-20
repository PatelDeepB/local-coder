"""Extracts code symbols, signatures, and type contracts using AST."""

from dataclasses import dataclass
import ast
from typing import Optional


@dataclass(frozen=True)
class ExtractedSymbol:
    """Represents a discovered symbol in a code file."""

    name: str
    symbol_type: str  # 'function', 'class', 'method', 'async_function'
    signature: str
    docstring: Optional[str]
    start_line: int
    end_line: int
    dependencies: tuple[str, ...]


class SymbolExtractor:
    """Walks Python AST to discover and index code contracts."""

    def extract_from_source(self, source_code: str) -> list[ExtractedSymbol]:
        """Parses source code string and extracts all top-level and method symbols."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []

        symbols: list[ExtractedSymbol] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(self._extract_function(node))
            elif isinstance(node, ast.ClassDef):
                symbols.append(self._extract_class(node))
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append(self._extract_function(item, parent_class=node.name))

        return symbols

    def _extract_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        parent_class: Optional[str] = None,
    ) -> ExtractedSymbol:
        name = f"{parent_class}.{node.name}" if parent_class else node.name
        stype = "async_function" if isinstance(node, ast.AsyncFunctionDef) else (
            "method" if parent_class else "function"
        )
        sig = self._format_signature(node)
        doc = ast.get_docstring(node)
        deps = self._find_called_functions(node)

        return ExtractedSymbol(
            name=name,
            symbol_type=stype,
            signature=sig,
            docstring=doc,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            dependencies=tuple(deps),
        )

    def _extract_class(self, node: ast.ClassDef) -> ExtractedSymbol:
        bases = [ast.unparse(b) for b in node.bases]
        sig = f"class {node.name}({', '.join(bases)}):" if bases else f"class {node.name}:"
        doc = ast.get_docstring(node)

        return ExtractedSymbol(
            name=node.name,
            symbol_type="class",
            signature=sig,
            docstring=doc,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            dependencies=tuple(bases),
        )

    def _format_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        prefix = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
        params: list[str] = []

        for arg in node.args.args:
            if arg.annotation:
                params.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
            else:
                params.append(arg.arg)

        ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        return f"{prefix}{node.name}({', '.join(params)}){ret}"

    def _find_called_functions(self, node: ast.AST) -> set[str]:
        calls = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                if isinstance(sub.func, ast.Name):
                    calls.add(sub.func.id)
                elif isinstance(sub.func, ast.Attribute):
                    calls.add(sub.func.attr)
        return calls
