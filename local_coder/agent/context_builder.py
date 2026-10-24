"""Builds workspace context rules and compressed repository schemas for the agent."""

from pathlib import Path
from typing import Optional

from local_coder.knowledge.ast_compactor import ASTSemanticCompactor
from local_coder.workspace.shadow_workspace import ShadowWorkspace


class WorkspaceContextBuilder:
    """Discovers project structure and compresses schema context for LLM prompts."""

    @staticmethod
    def build_context_rules(
        root_dir: Path,
        shadow_workspace: ShadowWorkspace,
        ast_compactor: ASTSemanticCompactor,
        base_rules: Optional[str] = None,
    ) -> str:
        """Assembles repository file inventory and compressed virtual schema rules."""
        existing_files = [
            str(p.relative_to(root_dir)).replace("\\", "/")
            for p in root_dir.glob("**/*")
            if p.is_file()
            and not any(
                part.startswith(".")
                or part in ["venv", "__pycache__", "node_modules", "workspace_runs", "dist", "build"]
                for part in p.parts
            )
        ]
        repo_inv = (
            "Existing Project Files in Workspace:\n" + "\n".join(f"- {f}" for f in existing_files[:30])
            if existing_files
            else "Existing Project Files in Workspace: (None - new or empty project)"
        )

        schema = ast_compactor.build_workspace_schema(root_dir, shadow_workspace)
        if schema and len(schema) > 1800:
            schema = schema[:1800] + "\n... [truncated schema]"
        schema_block = f"\n\nVirtual Workspace Schema (64K token context compressed):\n{schema}" if schema else ""
        mod_rules = (
            f"{repo_inv}{schema_block}\n\n"
            f"CRITICAL RULES:\n"
            f"1. To modify an existing file, use <patch file=\"path\"> or <write_file path=\"path\"> at its exact path.\n"
            f"2. To create a new file or add a new module/test requested by the user, use <write_file path=\"path\">.\n"
            f"3. NEVER use write_file with '# Existing code...' stubs. Always provide complete working code or precision patches.\n"
            f"4. Preserve all existing classes and functions when updating files."
        )
        return f"{base_rules}\n\n{mod_rules}" if base_rules else mod_rules
