"""Task decomposition and action checklist planner."""

import re
from local_coder.agent.prompt_templates import PLANNER_SYSTEM_PROMPT
from local_coder.neural.llama_runner import LlamaModelRunner


class TaskPlanner:
    """Decomposes complex user goals into an ordered checklist of subtasks."""

    def __init__(self, runner: LlamaModelRunner) -> None:
        self.runner = runner

    def create_plan(self, user_goal: str, repo_summary: str = "") -> list[str]:
        """Generates a 2-4 step actionable plan for achieving the user goal."""
        prompt = (
            f"Repository Context:\n{repo_summary}\n\n"
            f"Goal: {user_goal}\n\n"
            f"Formulate a minimal, ordered execution checklist."
        )

        res = self.runner.generate(
            prompt=prompt,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            max_tokens=400,
            temperature=0.2,
        )

        lines = [l.strip() for l in res.content.splitlines() if l.strip()]
        steps: list[str] = []

        for line in lines:
            if line.startswith("-") or line.startswith("*") or re.match(r"^\d+\.", line):
                clean_step = re.sub(r"^[-*\d.]+\s*", "", line).strip()
                if clean_step:
                    steps.append(clean_step)

        if not steps:
            steps = [f"Inspect relevant files for: {user_goal}", f"Implement required edits for: {user_goal}", "Run test suite to verify changes"]

        return steps
