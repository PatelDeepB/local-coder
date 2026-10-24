"""Fast Apply single-pass precision code editor mimicking Cursor Fast Apply."""

from dataclasses import dataclass
from typing import Optional
import re
import time

from local_coder.ast_engine.diff_patcher import PrecisionPatcher
from local_coder.ast_engine.smart_merger import SmartCodeMerger
from local_coder.neural.llama_runner import LlamaModelRunner
from local_coder.verifier.syntax_validator import SyntaxValidator
from local_coder.workspace.shadow_workspace import ShadowWorkspace


@dataclass(frozen=True)
class FastApplyResult:
    """Telemetry and outcome of a fast apply edit."""

    is_success: bool
    file_path: str
    staged_content: str
    diff: str
    elapsed_seconds: float
    error_message: Optional[str] = None


class FastApplyEngine:
    """Executes sub-3-second single-pass code updates using AST non-destructive splicing."""

    def __init__(
        self,
        runner: LlamaModelRunner,
        workspace: ShadowWorkspace,
        merger: Optional[SmartCodeMerger] = None,
        patcher: Optional[PrecisionPatcher] = None,
        validator: Optional[SyntaxValidator] = None,
    ) -> None:
        self.runner = runner
        self.workspace = workspace
        self.merger = merger or SmartCodeMerger()
        self.patcher = patcher or PrecisionPatcher()
        self.validator = validator or SyntaxValidator()

    def apply_update(
        self,
        file_path: str,
        instruction: str,
        additional_context: str = "",
    ) -> FastApplyResult:
        """Applies an update to target file in a single fast model generation pass."""
        start_time = time.perf_counter()
        existing_content = self.workspace.get_staged_content(file_path) or ""

        # Step 1: Format Kortix / Cursor style Fast Apply prompt
        prompt = self._format_prompt(file_path, existing_content, instruction, additional_context)
        system_prompt = (
            "You are a precision code editor. Apply the requested modification cleanly. "
            "Output only the updated code or new functions inside <update> ... </update> tags."
        )

        res = self.runner.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=640,
            temperature=0.1,
        )

        raw_output = res.content.strip()
        update_snippet = self._extract_snippet(raw_output)

        if not update_snippet:
            elapsed = time.perf_counter() - start_time
            return FastApplyResult(
                is_success=False,
                file_path=file_path,
                staged_content=existing_content,
                diff="",
                elapsed_seconds=elapsed,
                error_message="Could not extract valid code update from model output.",
            )

        # Step 2: Non-destructive AST merge
        merged_code = self.merger.merge_source_code(existing_content, update_snippet, file_path)

        # Step 3: Syntax validation gate
        if file_path.endswith(".py"):
            syntax_check = self.validator.validate_python(merged_code)
            if not syntax_check.is_valid:
                # If merged failed, attempt with raw snippet if valid
                raw_check = self.validator.validate_python(update_snippet)
                if raw_check.is_valid and len(update_snippet) >= len(existing_content) * 0.8:
                    merged_code = update_snippet
                else:
                    elapsed = time.perf_counter() - start_time
                    return FastApplyResult(
                        is_success=False,
                        file_path=file_path,
                        staged_content=existing_content,
                        diff="",
                        elapsed_seconds=elapsed,
                        error_message=f"Syntax Error: {syntax_check.error_message}",
                    )

        # Step 4: Stage in shadow workspace and generate unified diff
        self.workspace.stage_edit(file_path, merged_code)
        diff = self.patcher.generate_unified_diff(existing_content, merged_code, file_path=file_path)
        elapsed = time.perf_counter() - start_time

        return FastApplyResult(
            is_success=True,
            file_path=file_path,
            staged_content=merged_code,
            diff=diff,
            elapsed_seconds=elapsed,
        )

    def _format_prompt(
        self,
        file_path: str,
        existing_content: str,
        instruction: str,
        additional_context: str,
    ) -> str:
        ctx_block = f"\nContext:\n{additional_context}\n" if additional_context else ""
        compact_code = existing_content if len(existing_content) <= 3000 else existing_content[:3000] + "\n... [remaining code truncated]"
        return (
            f"File: {file_path}{ctx_block}\n"
            f"<code>\n{compact_code}\n</code>\n\n"
            f"Instruction: {instruction}\n\n"
            f"Provide the exact updated code or new functions inside <update> and </update> tags:"
        )

    def _extract_snippet(self, raw_text: str) -> str:
        m_tag = re.search(r"<update>(.*?)(?:</update>|$)", raw_text, flags=re.DOTALL)
        if m_tag:
            return self._strip_fences(m_tag.group(1))

        m_xml = re.search(r'<write_file\s+[^>]*>(.*?)(?:</write_file>|$)', raw_text, flags=re.DOTALL)
        if m_xml:
            return self._strip_fences(m_xml.group(1))

        m_code = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*[\r\n]+(.*?)```", raw_text, flags=re.DOTALL)
        if m_code:
            return m_code.group(1).strip()

        return self._strip_fences(raw_text)

    def _strip_fences(self, text: str) -> str:
        clean = text.strip()
        clean = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", clean)
        clean = re.sub(r"\n```$", "", clean)
        return clean.strip()
