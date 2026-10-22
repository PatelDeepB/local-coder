"""Speculative Fill-in-the-Middle (FIM) autocomplete engine for sub-50ms tab completions."""

from dataclasses import dataclass
from typing import Any, Optional
import time

from local_coder.neural.speculative_drafter import SpeculativeDraftingEngine


@dataclass(frozen=True)
class InfillingResult:
    """Outcome of speculative tab completion."""

    completion: str
    elapsed_ms: float
    token_count: int


class InfillingEngine:
    """Formats FIM prompts and generates real-time inline tab completions."""

    def __init__(
        self,
        runner: Any,
        drafter: Optional[SpeculativeDraftingEngine] = None,
        enable_speculative: bool = True,
    ) -> None:
        self.runner = runner
        if drafter is not None:
            self.drafter: Optional[SpeculativeDraftingEngine] = drafter
        elif enable_speculative:
            self.drafter = SpeculativeDraftingEngine()
        else:
            self.drafter = None

    def complete(
        self,
        prefix: str,
        suffix: str,
        max_tokens: int = 32,
        single_line_only: bool = True,
    ) -> InfillingResult:
        """Executes FIM code completion ahead of cursor position."""
        start_time = time.perf_counter()

        # Keep recent context window for sub-second CPU latency
        trimmed_prefix = prefix[-1000:] if len(prefix) > 1000 else prefix
        trimmed_suffix = suffix[:500] if len(suffix) > 500 else suffix

        # Step 1: Sub-millisecond speculative drafting lookup
        if self.drafter:
            draft = self.drafter.draft_continuation(trimmed_prefix)
            if draft and draft.continuation.strip():
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return InfillingResult(
                    completion=draft.continuation,
                    elapsed_ms=elapsed_ms,
                    token_count=len(draft.continuation.split()),
                )

        # Step 2: Fall back to local neural runner FIM generation
        fim_prompt = f"<|fim_prefix|>{trimmed_prefix}<|fim_suffix|>{trimmed_suffix}<|fim_middle|>"
        
        stop_tokens = ["<|fim_pad|>", "<|fim_prefix|>", "<|endoftext|>", "<|file_sep|>"]
        if single_line_only:
            stop_tokens.append("\n")

        if hasattr(self.runner, "generate_raw"):
            res = self.runner.generate_raw(
                prompt=fim_prompt,
                max_tokens=max_tokens,
                temperature=0.1,
                stop_tokens=stop_tokens,
            )
            raw_text = res.content
        else:
            # Fallback to standard chat generation if raw not exposed
            res = self.runner.generate(
                prompt=f"Complete the code between PREFIX and SUFFIX.\nPREFIX:\n{trimmed_prefix}\nSUFFIX:\n{trimmed_suffix}\nOutput ONLY the middle code.",
                max_tokens=max_tokens,
                temperature=0.1,
            )
            raw_text = res.content

        # Clean any leakage of special tokens
        cleaned = self._clean_completion(raw_text)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return InfillingResult(
            completion=cleaned,
            elapsed_ms=elapsed_ms,
            token_count=len(cleaned.split()),
        )

    def _clean_completion(self, text: str) -> str:
        """Strips markdown fences and special tokens from completion output."""
        cleaned = text.replace("<|fim_prefix|>", "").replace("<|fim_suffix|>", "")
        cleaned = cleaned.replace("<|fim_middle|>", "").replace("<|fim_pad|>", "")
        cleaned = cleaned.replace("<|endoftext|>", "").replace("```", "")
        return cleaned
