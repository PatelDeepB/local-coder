"""Stage 1 Contract Planner: Generates interface specifications and invariants."""

from dataclasses import dataclass
from typing import Optional
import re

from local_coder.neural.llama_runner import LlamaModelRunner


@dataclass(frozen=True)
class CodeContract:
    """Represents a planned interface contract before implementation."""

    function_or_class_name: str
    signature: str
    docstring: str
    preconditions: tuple[str, ...]
    return_type: str


class ContractPlanner:
    """Produces formal interface signatures and contracts from user requirements."""

    PLANNER_SYSTEM_PROMPT = (
        "You are an expert software architect. Given a programming task, emit ONLY the formal "
        "function signature with complete type hints, docstring, and preconditions. Do not implement the body."
    )

    def __init__(self, runner: LlamaModelRunner) -> None:
        self.runner = runner

    def plan_contract(self, task_description: str, context_signatures: str = "") -> CodeContract:
        """Generates a structured interface contract for the requested feature or fix."""
        prompt = (
            f"Context Interfaces:\n{context_signatures}\n\n"
            f"Task: {task_description}\n\n"
            f"Output the exact Python function signature, type annotations, and docstring."
        )

        res = self.runner.generate(prompt=prompt, system_prompt=self.PLANNER_SYSTEM_PROMPT, max_tokens=150)
        content = res.content

        # Extract function signature via regex
        match = re.search(r"(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*(?:->\s*[^:]+)?:", content)
        if match:
            fn_name = match.group(1)
            sig = match.group(0)
        else:
            fn_name = "execute_task"
            sig = "def execute_task() -> None:"

        return CodeContract(
            function_or_class_name=fn_name,
            signature=sig,
            docstring="Generated interface specification.",
            preconditions=(),
            return_type="Any",
        )
