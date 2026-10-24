"""File reading, directory listing, and structural outline tools."""

from pathlib import Path
from typing import Any
import json
import os

from local_coder.ast_engine.smart_merger import SmartCodeMerger
from local_coder.ast_engine.symbol_extractor import SymbolExtractor
from local_coder.tools.base_tool import BaseAgentTool, ToolResult
from local_coder.verifier.syntax_validator import SyntaxValidator
from local_coder.workspace.shadow_workspace import ShadowWorkspace


class ReadFileTool(BaseAgentTool):
    """Reads content of a target file from shadow workspace or disk."""

    def __init__(self, workspace: ShadowWorkspace) -> None:
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Reads the full content of a file in the workspace."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to target file"}
            },
            "required": ["file_path"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        rel_path = kwargs.get("file_path", "")
        content = self.workspace.get_staged_content(rel_path)
        if content is None:
            return ToolResult(is_success=False, output="", error_message=f"File not found: {rel_path}")
        return ToolResult(is_success=True, output=content)


class ListDirectoryTool(BaseAgentTool):
    """Lists files and subdirectories in a workspace path."""

    def __init__(self, workspace: ShadowWorkspace) -> None:
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "Lists files and folders inside a directory path."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "relative_path": {"type": "string", "description": "Relative directory path (or empty for root)"}
            },
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        rel = kwargs.get("relative_path", "")
        target = (self.workspace.root_dir / rel).resolve()
        if not target.is_dir():
            return ToolResult(is_success=False, output="", error_message=f"Not a directory: {rel}")

        entries = []
        for item in sorted(os.listdir(target)):
            if item not in {".git", "__pycache__", ".venv", "node_modules"}:
                is_d = (target / item).is_dir()
                entries.append(f"{item}/" if is_d else item)

        return ToolResult(is_success=True, output="\n".join(entries))


class FileOutlineTool(BaseAgentTool):
    """Extracts high-level class and function signatures without full source body."""

    def __init__(self, workspace: ShadowWorkspace) -> None:
        self.workspace = workspace
        self.extractor = SymbolExtractor()

    @property
    def name(self) -> str:
        return "get_file_outline"

    @property
    def description(self) -> str:
        return "Extracts class names, method signatures, and docstrings from a Python file."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to target file"}
            },
            "required": ["file_path"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        rel = kwargs.get("file_path", "")
        content = self.workspace.get_staged_content(rel)
        if not content:
            return ToolResult(is_success=False, output="", error_message=f"File not found: {rel}")

        symbols = self.extractor.extract_from_source(content)
        if not symbols:
            return ToolResult(is_success=True, output=f"No symbols found in {rel}.")

        lines = [f"=== Outline for {rel} ==="]
        for s in symbols:
            doc_str = f" - {s.docstring.strip()}" if s.docstring else ""
            lines.append(f"Line {s.start_line}: {s.signature}{doc_str}")

        return ToolResult(is_success=True, output="\n".join(lines))


class WriteFileTool(BaseAgentTool):
    """Writes or overwrites a file in the virtual shadow workspace."""

    def __init__(self, workspace: ShadowWorkspace) -> None:
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Creates or updates a file in the workspace with given content."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to target file"},
                "content": {"type": "string", "description": "Complete new content to write to the file"},
            },
            "required": ["file_path", "content"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        rel_path = kwargs.get("file_path", "")
        content = kwargs.get("content", "")
        if not rel_path:
            return ToolResult(is_success=False, output="", error_message="file_path is required.")

        # Non-Destructive Merge Gate: Prevent clobbering existing features in existing files
        existing_content = self.workspace.get_staged_content(rel_path)
        if existing_content and existing_content.strip():
            content = SmartCodeMerger().merge_source_code(existing_content, content, rel_path)

        # AST Syntax Gate: Prevent saving broken Python code
        if rel_path.endswith(".py"):
            syntax_check = SyntaxValidator().validate_python(content)
            if not syntax_check.is_valid:
                return ToolResult(
                    is_success=False,
                    output="",
                    error_message=(
                        f"Syntax Error on line {syntax_check.error_line}: {syntax_check.error_message}. "
                        "The Python code has invalid syntax. Please correct the syntax and rewrite the file."
                    ),
                )

        # JSON Syntax Gate: Prevent saving invalid JSON configs (package.json, tsconfig.json, etc.)
        if rel_path.endswith(".json"):
            try:
                json.loads(content)
            except Exception as exc:
                return ToolResult(
                    is_success=False,
                    output="",
                    error_message=f"JSON Syntax Error in {rel_path}: {exc}. Please fix the JSON formatting.",
                )

        self.workspace.stage_edit(rel_path, content)
        return ToolResult(
            is_success=True,
            output=f"Successfully staged {len(content.splitlines())} lines to {rel_path} in shadow workspace.",
        )
