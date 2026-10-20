"""Stage 2 Slot Coder: Generates scoped function body implementations from contracts."""

from dataclasses import dataclass
from typing import Optional
import re

from local_coder.ast_engine.cst_surgery import replace_function_body
from local_coder.neural.contract_planner import CodeContract
from local_coder.neural.llama_runner import LlamaModelRunner
from local_coder.verifier.syntax_validator import SyntaxValidator


@dataclass(frozen=True)
class SlotSynthesisResult:
    """Represents the outcome of a scoped slot body synthesis."""

    is_success: bool
    function_name: str
    complete_function_code: str
    body_code: str
    error_message: Optional[str] = None


class SlotCoder:
    """Synthesizes scope-restricted function bodies strictly constrained by interface contracts."""

    SLOT_CODER_SYSTEM_PROMPT = (
        "You are an expert Python implementation engine. Given a formal function signature and task description, "
        "emit ONLY the valid Python body statements indented by 4 spaces. Do not repeat the def line, do not include "
        "markdown formatting or backticks, and do not include conversational commentary."
    )

    def __init__(self, runner: LlamaModelRunner) -> None:
        self.runner = runner
        self.validator = SyntaxValidator()

    def clean_body_text(self, raw_text: str) -> str:
        """Removes markdown fences and ensures proper 4-space indentation."""
        lines = []
        for line in raw_text.splitlines():
            stripped = line.strip()
            # Skip markdown block markers or redundant def lines
            if stripped.startswith("```") or stripped.startswith("def ") or stripped.startswith("async def "):
                continue
            if stripped:
                # Ensure at least 4 spaces indentation
                if not line.startswith("    "):
                    lines.append("    " + stripped)
                else:
                    lines.append(line)
            else:
                lines.append("")

        result = "\n".join(lines).strip("\n")
        if not result:
            result = "    pass"
        return result

    def synthesize_body(self, contract: CodeContract, task_prompt: str) -> str:
        """Generates the inner statements for the given contract."""
        prompt = (
            f"Interface Contract:\n{contract.signature}\n"
            f"Task: {task_prompt}\n\n"
            f"Implement the function body (4 spaces indented):"
        )

        res = self.runner.generate(
            prompt=prompt,
            system_prompt=self.SLOT_CODER_SYSTEM_PROMPT,
            max_tokens=256,
            temperature=0.1,
        )

        return self.clean_body_text(res.content)

    def synthesize_slot(
        self,
        contract: CodeContract,
        task_prompt: str,
    ) -> SlotSynthesisResult:
        """Synthesizes and validates a complete function implementation."""
        body = self.synthesize_body(contract, task_prompt)
        full_code = f"{contract.signature}\n{body}\n"

        val = self.validator.validate_python(full_code)
        if not val.is_valid:
            # Fallback to safe pass if neural generation has syntax flaw
            fallback_body = "    pass"
            full_code = f"{contract.signature}\n{fallback_body}\n"
            return SlotSynthesisResult(
                is_success=False,
                function_name=contract.function_or_class_name,
                complete_function_code=full_code,
                body_code=fallback_body,
                error_message=f"Syntax validation failed: {val.error_message}",
            )

        return SlotSynthesisResult(
            is_success=True,
            function_name=contract.function_or_class_name,
            complete_function_code=full_code,
            body_code=body,
        )

    def inject_slot_into_file(
        self,
        source_code: str,
        function_name: str,
        body_code: str,
    ) -> tuple[str, bool]:
        """Surgically replaces the function body in source code via LibCST."""
        modified_code, is_replaced = replace_function_body(
            code=source_code,
            function_name=function_name,
            new_body_code=body_code,
        )
        if not is_replaced:
            return source_code, False

        val = self.validator.validate_python(modified_code)
        if not val.is_valid:
            return source_code, False

        return modified_code, True
