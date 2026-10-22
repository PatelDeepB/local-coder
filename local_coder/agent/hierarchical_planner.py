"""Hierarchical multi-file dependency-ordered synthesis planner with cross-file contract propagation."""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from local_coder.agent.compiler_gate import CompilerGate
from local_coder.agent.manifest_synthesizer import FileManifestItem, ManifestSynthesizer
from local_coder.knowledge.coding_knowledge_db import CodingKnowledgeDB
from local_coder.workspace.shadow_workspace import ShadowWorkspace


@dataclass(frozen=True)
class SynthesizedFileResult:
    """Outcome of synthesizing a single file in the hierarchy."""

    file_path: str
    code: str
    is_valid: bool
    exported_contracts: str


class HierarchicalPlanner:
    """Sequences project files by architectural hierarchy and propagates type contracts forward."""

    HIERARCHY_WEIGHTS = {
        "models.py": 10,
        "types.ts": 10,
        "schemas.py": 15,
        "forms.py": 20,
        "serializers.py": 20,
        "services.py": 30,
        "views.py": 40,
        "controllers.ts": 40,
        "urls.py": 50,
        "routes.ts": 50,
        "main.py": 60,
        "app.py": 60,
        "index.js": 60,
        "test_": 90,
        "tests": 90,
    }

    def __init__(
        self,
        synthesizer: ManifestSynthesizer,
        workspace: ShadowWorkspace,
        compiler_gate: Optional[CompilerGate] = None,
        knowledge_db: Optional[CodingKnowledgeDB] = None,
    ) -> None:
        self.synthesizer = synthesizer
        self.workspace = workspace
        self.compiler_gate = compiler_gate or CompilerGate()
        self.knowledge_db = knowledge_db or CodingKnowledgeDB()

    def sort_manifest_by_dependency_order(
        self, manifest: list[FileManifestItem]
    ) -> list[FileManifestItem]:
        """Orders files so fundamental foundations (models, schemas) are synthesized before consumers."""
        def get_file_priority(item: FileManifestItem) -> int:
            fp_lower = item.file_path.lower()
            for pattern, weight in self.HIERARCHY_WEIGHTS.items():
                if pattern in fp_lower:
                    return weight
            # Config / requirements first
            if any(ext in fp_lower for ext in ("package.json", "requirements.txt", "settings.py")):
                return 5
            return 35

        return sorted(manifest, key=get_file_priority)

    def extract_ast_contracts(self, file_path: str, code: str) -> str:
        """Parses newly synthesized file and extracts public classes, functions, and attributes."""
        if not file_path.endswith(".py"):
            return ""

        try:
            tree = ast.parse(code)
        except Exception:
            return ""

        contracts: list[str] = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                contracts.append(f"class {node.name}:")
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef) and not sub.name.startswith("_"):
                        args_str = ", ".join(arg.arg for arg in sub.args.args)
                        contracts.append(f"    def {sub.name}({args_str})")
                    elif isinstance(sub, ast.Assign):
                        for target in sub.targets:
                            if isinstance(target, ast.Name):
                                contracts.append(f"    {target.id}: Field")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    args_str = ", ".join(arg.arg for arg in node.args.args)
                    contracts.append(f"def {node.name}({args_str})")

        return "\n".join(contracts[:20])

    def synthesize_hierarchy(
        self,
        manifest: list[FileManifestItem],
        user_goal: str,
        on_file_progress: Optional[Any] = None,
    ) -> list[SynthesizedFileResult]:
        """Sequentially synthesizes files while propagating live interface contracts across files."""
        ordered = self.sort_manifest_by_dependency_order(manifest)
        accumulated_contracts: list[str] = []
        results: list[SynthesizedFileResult] = []

        total_files = len(ordered)
        for idx, item in enumerate(ordered, 1):
            if on_file_progress:
                on_file_progress(item.file_path, idx, total_files)

            # Build enriched goal with upstream contracts
            enriched_goal = user_goal
            if accumulated_contracts:
                contracts_summary = "\n".join(accumulated_contracts[-4:])
                enriched_goal += (
                    f"\n\n=== UPSTREAM CONTRACTS (Already Synthesized & Frozen) ===\n"
                    f"{contracts_summary}\n"
                    f"CRITICAL: Match the exact class names, methods, and field names defined above."
                )

            # Synthesize single file
            code = self.synthesizer.synthesize_file(item, enriched_goal)

            # Validate with CompilerGate
            diag = self.compiler_gate.check_file_content(item.file_path, code)

            # Stage to workspace
            self.workspace.stage_edit(item.file_path, code)

            # Extract contracts to propagate to downstream files
            extracted = self.extract_ast_contracts(item.file_path, code)
            if extracted:
                accumulated_contracts.append(f"--- File: {item.file_path} ---\n{extracted}")

            results.append(
                SynthesizedFileResult(
                    file_path=item.file_path,
                    code=code,
                    is_valid=diag.is_valid,
                    exported_contracts=extracted,
                )
            )

        return results
