"""Tools for surgical code editing via AST transformations and search/replace patches."""

from typing import Any
from local_coder.ast_engine.cst_surgery import (
    make_function_async,
    replace_function_body,
    wrap_function_error_handler,
)
from local_coder.ast_engine.diff_patcher import PrecisionPatcher
from local_coder.tools.base_tool import BaseAgentTool, ToolResult
from local_coder.workspace.shadow_workspace import ShadowWorkspace


class ApplySearchReplacePatchTool(BaseAgentTool):
    """Applies exact search-and-replace block to a target file in shadow workspace."""

    def __init__(self, workspace: ShadowWorkspace) -> None:
        self.workspace = workspace
        self.patcher = PrecisionPatcher()

    @property
    def name(self) -> str:
        return "apply_search_replace_patch"

    @property
    def description(self) -> str:
        return "Applies a targeted search-and-replace edit block to a file."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to target file"},
                "search_block": {"type": "string", "description": "Exact existing code snippet to locate"},
                "replace_block": {"type": "string", "description": "New replacement code snippet"},
            },
            "required": ["file_path", "search_block", "replace_block"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        rel = kwargs.get("file_path", "")
        search_b = kwargs.get("search_block", "")
        replace_b = kwargs.get("replace_block", "")

        curr_content = self.workspace.get_staged_content(rel)
        if curr_content is None:
            return ToolResult(is_success=False, output="", error_message=f"Target file not found: {rel}")

        result = self.patcher.apply_search_replace(curr_content, search_b, replace_b)
        if not result.is_success:
            return ToolResult(is_success=False, output="", error_message=result.error_message)

        self.workspace.stage_edit(rel, result.modified_content)
        return ToolResult(
            is_success=True,
            output=f"Successfully patched {rel}.\nUnified Diff:\n{result.diff_unified}",
        )


class LibCSTTransformTool(BaseAgentTool):
    """Executes deterministic LibCST transformations in under 50ms."""

    def __init__(self, workspace: ShadowWorkspace) -> None:
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "cst_transform"

    @property
    def description(self) -> str:
        return "Executes deterministic AST transforms: 'make_async', 'replace_body', or 'wrap_error_handler'."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to target file"},
                "transform_type": {
                    "type": "string",
                    "enum": ["make_async", "replace_body", "wrap_error_handler"],
                    "description": "Type of deterministic transform to apply",
                },
                "function_name": {"type": "string", "description": "Name of function to transform"},
                "extra_code": {"type": "string", "description": "Replacement body code if using replace_body", "default": ""},
            },
            "required": ["file_path", "transform_type", "function_name"],
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        rel = kwargs.get("file_path", "")
        t_type = kwargs.get("transform_type", "")
        fn_name = kwargs.get("function_name", "")
        extra = kwargs.get("extra_code", "")

        curr = self.workspace.get_staged_content(rel)
        if curr is None:
            return ToolResult(is_success=False, output="", error_message=f"File not found: {rel}")

        if t_type == "make_async":
            new_code, ok = make_function_async(curr, fn_name)
        elif t_type == "replace_body":
            new_code, ok = replace_function_body(curr, fn_name, extra)
        elif t_type == "wrap_error_handler":
            new_code, ok = wrap_function_error_handler(curr, fn_name)
        else:
            return ToolResult(is_success=False, output="", error_message=f"Unknown transform: {t_type}")

        if not ok:
            return ToolResult(is_success=False, output="", error_message=f"Transform '{t_type}' failed on '{fn_name}'.")

        self.workspace.stage_edit(rel, new_code)
        return ToolResult(is_success=True, output=f"Successfully applied {t_type} to {fn_name} in {rel}.")
