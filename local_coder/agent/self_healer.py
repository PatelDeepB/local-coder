"""Automated triage of test failures with targeted repair proposals."""

from dataclasses import dataclass
from typing import Optional
import re

from local_coder.neural.llama_runner import LlamaModelRunner


@dataclass(frozen=True)
class HealingProposal:
    """Represents a proposed fix for a test or runtime failure."""

    target_file: str
    search_block: str
    replace_block: str
    explanation: str


class SelfHealer:
    """Diagnoses test failures and proposes surgical search-and-replace patches."""

    def __init__(self, runner: LlamaModelRunner) -> None:
        self.runner = runner

    def propose_fix(
        self,
        failing_file_content: str,
        failing_file_path: str,
        error_traceback: str,
    ) -> Optional[HealingProposal]:
        """Analyzes traceback against file content and proposes an exact patch."""
        prompt = (
            f"File '{failing_file_path}' content:\n```python\n{failing_file_content}\n```\n\n"
            f"Test / Runtime Error:\n{error_traceback}\n\n"
            f"Analyze the bug and propose a surgical patch.\n"
            f"Format strictly as:\n"
            f"SEARCH:\n<exact existing code block to replace>\n"
            f"REPLACE:\n<new replacement code block>\n"
        )

        res = self.runner.generate(prompt=prompt, max_tokens=300, temperature=0.1)
        content = res.content

        m_search = re.search(r"SEARCH:\s*\n(.*?)\nREPLACE:", content, flags=re.DOTALL)
        m_replace = re.search(r"REPLACE:\s*\n(.*)", content, flags=re.DOTALL)

        if m_search and m_replace:
            s_block = m_search.group(1).strip()
            r_block = m_replace.group(1).strip()
            # Clean possible markdown ticks
            s_block = s_block.replace("```python", "").replace("```", "").strip()
            r_block = r_block.replace("```python", "").replace("```", "").strip()

            return HealingProposal(
                target_file=failing_file_path,
                search_block=s_block,
                replace_block=r_block,
                explanation="Automated self-healing patch derived from traceback.",
            )

        return None
