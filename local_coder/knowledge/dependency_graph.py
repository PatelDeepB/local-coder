"""Multi-hop codebase dependency and import graph for contextual type awareness."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Optional


@dataclass(frozen=True)
class DependencyEdge:
    """Represents an import relationship between two files."""

    source_file: str
    target_file: str
    imported_symbols: tuple[str, ...] = ()


class CodebaseDependencyGraph:
    """Extracts and queries multi-file import graphs for Python, JS, and TS."""

    def __init__(self, root_dir: Optional[str | Path] = None) -> None:
        self.root_dir = Path(root_dir or os.getcwd()).resolve()
        self._imports: dict[str, set[str]] = {}
        self._imported_by: dict[str, set[str]] = {}
        self._contracts_cache: dict[str, str] = {}

    def scan_codebase(self) -> int:
        """Parses imports across all workspace files. Returns total edges discovered."""
        self._imports.clear()
        self._imported_by.clear()
        edge_count = 0

        for path in self.root_dir.rglob("*"):
            if not path.is_file() or any(p.startswith(".") or p == "node_modules" for p in path.parts):
                continue
            if path.suffix in (".py", ".js", ".jsx", ".ts", ".tsx"):
                rel_path = str(path.relative_to(self.root_dir)).replace("\\", "/")
                edges = self._extract_file_imports(path, rel_path)
                for edge in edges:
                    self._imports.setdefault(edge.source_file, set()).add(edge.target_file)
                    self._imported_by.setdefault(edge.target_file, set()).add(edge.source_file)
                    edge_count += 1

        return edge_count

    def _extract_file_imports(self, abs_path: Path, rel_source: str) -> list[DependencyEdge]:
        """Extracts import targets from a single source file."""
        try:
            content = abs_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        if abs_path.suffix == ".py":
            return self._parse_python_imports(content, rel_source, abs_path.parent)
        return self._parse_js_imports(content, rel_source, abs_path.parent)

    def _parse_python_imports(self, content: str, rel_source: str, parent: Path) -> list[DependencyEdge]:
        """Extracts Python from/import dependencies."""
        edges: list[DependencyEdge] = []
        for line in content.splitlines():
            line = line.strip()
            # Match: from .utils import foo or import os
            from_match = re.match(r"^from\s+([.\w]+)\s+import\s+(.+)$", line)
            if from_match:
                module_path, symbols_raw = from_match.groups()
                symbols = tuple(s.strip() for s in symbols_raw.split(","))
                target = self._resolve_python_module(module_path, parent)
                if target:
                    edges.append(DependencyEdge(rel_source, target, symbols))
        return edges

    def _resolve_python_module(self, module_str: str, parent: Path) -> Optional[str]:
        """Resolves Python module import to relative workspace path."""
        # Check relative import (.module or ..module)
        if module_str.startswith("."):
            dots = len(module_str) - len(module_str.lstrip("."))
            target_dir = parent
            for _ in range(dots - 1):
                target_dir = target_dir.parent
            subpath = module_str.lstrip(".")
            candidate = target_dir / f"{subpath}.py"
            if candidate.exists() and candidate.is_relative_to(self.root_dir):
                return str(candidate.relative_to(self.root_dir)).replace("\\", "/")
        return None

    def _parse_js_imports(self, content: str, rel_source: str, parent: Path) -> list[DependencyEdge]:
        """Extracts JS/TS ESM and CommonJS imports."""
        edges: list[DependencyEdge] = []
        # Match ESM: import { x } from './foo'
        esm_matches = re.finditer(r"""import\s+(?:\{([^}]+)\}|\*\s+as\s+(\w+)|\w+)?\s*from\s*['"]([^'"]+)['"]""", content)
        for m in esm_matches:
            target_str = m.group(3)
            target = self._resolve_js_path(target_str, parent)
            if target:
                edges.append(DependencyEdge(rel_source, target))

        # Match CJS: require('./foo')
        cjs_matches = re.finditer(r"""require\(['"]([^'"]+)['"]\)""", content)
        for m in cjs_matches:
            target_str = m.group(1)
            target = self._resolve_js_path(target_str, parent)
            if target:
                edges.append(DependencyEdge(rel_source, target))

        return edges

    def _resolve_js_path(self, target_str: str, parent: Path) -> Optional[str]:
        """Resolves JS/TS relative import path to relative workspace file."""
        if not target_str.startswith("."):
            return None

        base = (parent / target_str).resolve()
        for ext in ("", ".js", ".jsx", ".ts", ".tsx", "/index.js", "/index.jsx", "/index.ts"):
            candidate = Path(str(base) + ext)
            if candidate.is_file() and candidate.is_relative_to(self.root_dir):
                return str(candidate.relative_to(self.root_dir)).replace("\\", "/")
        return None

    def get_dependencies(self, rel_path: str) -> list[str]:
        """Returns direct dependencies imported by the specified file."""
        norm = rel_path.replace("\\", "/")
        return sorted(list(self._imports.get(norm, set())))

    def get_dependents(self, rel_path: str) -> list[str]:
        """Returns files that directly import the specified file."""
        norm = rel_path.replace("\\", "/")
        return sorted(list(self._imported_by.get(norm, set())))

    def extract_file_contracts(self, rel_path: str) -> str:
        """Extracts public function and class signatures for prompt injection context."""
        norm = rel_path.replace("\\", "/")
        if norm in self._contracts_cache:
            return self._contracts_cache[norm]

        abs_path = self.root_dir / norm
        if not abs_path.is_file():
            return ""

        try:
            content = abs_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""

        signatures: list[str] = []
        for line in content.splitlines():
            trimmed = line.strip()
            # Capture def, class, export function, export const
            if re.match(r"^(async\s+)?def\s+\w+\(.*\).*:", trimmed):
                signatures.append(trimmed)
            elif re.match(r"^class\s+\w+.*:", trimmed):
                signatures.append(trimmed)
            elif re.match(r"^export\s+(default\s+)?(function|const|class|interface|type)\s+\w+", trimmed):
                signatures.append(trimmed)

        contract_summary = "\n".join(signatures[:15])
        self._contracts_cache[norm] = contract_summary
        return contract_summary

    def build_enriched_context(self, rel_path: str) -> str:
        """Constructs concise prompt context containing signatures of imported files."""
        deps = self.get_dependencies(rel_path)
        if not deps:
            return ""

        context_parts = [f"Imported Contracts for {rel_path}:"]
        for dep in deps[:3]:
            contract = self.extract_file_contracts(dep)
            if contract:
                context_parts.append(f"--- File: {dep} ---\n{contract}")

        return "\n\n".join(context_parts)
