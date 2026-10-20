"""Hierarchical context compressor for multi-turn dialogue history."""

from typing import Sequence
from local_coder.memory.episodic_ring import DialogueTurn


class HierarchicalEpisodicCompressor:
    """Summarizes conversational turns into a high-density compact prompt prefix."""

    def __init__(self, max_tokens: int = 150) -> None:
        self.max_tokens = max_tokens

    def build_context_summary(
        self,
        turns: Sequence[DialogueTurn],
        current_query: str = "",
    ) -> str:
        """Constructs an information-dense summary of recent user instructions and edits."""
        if not turns:
            return ""

        summary_lines = ["[Active Session Context]:"]
        for turn in turns:
            short_prompt = turn.user_prompt.strip().replace("\n", " ")
            if len(short_prompt) > 80:
                short_prompt = short_prompt[:77] + "..."

            short_resp = turn.assistant_response.strip().replace("\n", " ")
            if len(short_resp) > 80:
                short_resp = short_resp[:77] + "..."

            summary_lines.append(f"- Turn {turn.turn_id}: User '{short_prompt}' -> Assistant '{short_resp}'")

        full_summary = "\n".join(summary_lines)
        words = full_summary.split()
        if len(words) > self.max_tokens:
            return " ".join(words[: self.max_tokens]) + "..."
        return full_summary
