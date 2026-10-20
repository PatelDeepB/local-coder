"""Sub-second automated micro-repair feedback loop for code errors."""

from dataclasses import dataclass
from typing import Callable, Optional
import re

from local_coder.verifier.syntax_validator import SyntaxValidator


@dataclass(frozen=True)
class RepairResult:
    """Outcome of micro-repair loop."""

    is_repaired: bool
    repaired_code: str
    repair_attempts: int
    error_message: Optional[str] = None


class MicroRepairLoop:
    """Catches compilation and syntax issues and prompts the model for targeted one-line fixes."""

    def __init__(
        self,
        repair_generator: Callable[[str, str], str],
        max_attempts: int = 1,
    ) -> None:
        self.repair_generator = repair_generator
        self.max_attempts = max_attempts
        self.validator = SyntaxValidator()

    def verify_and_repair(self, code_str: str, file_context: str = "") -> RepairResult:
        """Checks code syntax and triggers micro-repair if syntax or indentation is broken."""
        curr = code_str
        attempts = 0

        while attempts <= self.max_attempts:
            val_res = self.validator.validate_python(curr)
            if val_res.is_valid:
                return RepairResult(
                    is_repaired=(attempts > 0),
                    repaired_code=curr,
                    repair_attempts=attempts,
                )

            attempts += 1
            if attempts > self.max_attempts:
                return RepairResult(
                    is_repaired=False,
                    repaired_code=curr,
                    repair_attempts=attempts,
                    error_message=val_res.error_message,
                )

            # Generate targeted micro-repair prompt
            err_line = val_res.error_line or 1
            repair_prompt = (
                f"File: {file_context}\n"
                f"The following code produced SyntaxError at line {err_line}: '{val_res.error_message}'.\n"
                f"Broken Code:\n```python\n{curr}\n```\n"
                f"Provide ONLY the fixed Python code without explanations."
            )

            raw_repair = self.repair_generator(repair_prompt, file_context)
            # Strip markdown fences if present
            cleaned = self._clean_code(raw_repair)
            if cleaned:
                curr = cleaned

        return RepairResult(is_repaired=False, repaired_code=curr, repair_attempts=attempts)

    def _clean_code(self, text: str) -> str:
        pattern = r"```(?:python|py)?\s*\n(.*?)```"
        match = re.search(pattern, text, flags=re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
