"""Dataset builder for extracting verified instruction and FIM pairs from pattern bank."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Optional

from local_coder.knowledge.pattern_bank import CleanPatternBank


@dataclass(frozen=True)
class InstructionSample:
    """Standard instruction fine-tuning sample."""

    instruction: str
    input: str
    output: str
    category: str


@dataclass(frozen=True)
class FIMTrainingSample:
    """Fill-in-the-Middle sample formatted with Qwen special tokens."""

    prompt: str
    completion: str


class SynapseDatasetBuilder:
    """Generates synthetic high-density instruction and FIM datasets for LoRA training."""

    def __init__(self, pattern_bank: Optional[CleanPatternBank] = None) -> None:
        self.bank = pattern_bank or CleanPatternBank()

    def build_instruction_dataset(self) -> list[InstructionSample]:
        """Constructs instruction samples from all verified architectural patterns."""
        samples: list[InstructionSample] = []
        for pattern in self.bank.get_all_patterns():
            for bp in pattern.files:
                reqs_str = "; ".join(bp.key_requirements) if bp.key_requirements else "Follow production standards."
                instruction = f"Implement {bp.file_path} for a {pattern.name} ({pattern.domain})."
                input_context = f"Purpose: {bp.purpose}\nRequirements: {reqs_str}\nDomain: {pattern.domain}"
                samples.append(
                    InstructionSample(
                        instruction=instruction,
                        input=input_context,
                        output=bp.boilerplate_skeleton.strip(),
                        category="pattern_synthesis",
                    )
                )
        return samples

    def build_fim_dataset(self, min_length: int = 40) -> list[FIMTrainingSample]:
        """Constructs FIM training samples by slicing function and module blocks."""
        fim_samples: list[FIMTrainingSample] = []
        for pattern in self.bank.get_all_patterns():
            for bp in pattern.files:
                text = bp.boilerplate_skeleton.strip()
                if len(text) < min_length:
                    continue
                slices = self._extract_natural_slices(text)
                for prefix, middle, suffix in slices:
                    prompt = f"<|fim_prefix|>{prefix}<|fim_suffix|>{suffix}<|fim_middle|>"
                    fim_samples.append(FIMTrainingSample(prompt=prompt, completion=middle))
        return fim_samples

    def _extract_natural_slices(self, code: str) -> list[tuple[str, str, str]]:
        """Splits code into prefix, middle, and suffix slices for infilling training."""
        lines = code.splitlines(keepends=True)
        if len(lines) < 4:
            return []

        mid_start = max(1, len(lines) // 3)
        mid_end = min(len(lines) - 1, 2 * len(lines) // 3)
        if mid_start >= mid_end:
            return []

        prefix = "".join(lines[:mid_start])
        middle = "".join(lines[mid_start:mid_end])
        suffix = "".join(lines[mid_end:])
        return [(prefix, middle, suffix)]

    def export_jsonl(self, samples: list[Any], output_file: str | Path) -> int:
        """Serializes samples to JSON Lines format."""
        target_path = Path(output_file).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(target_path, "w", encoding="utf-8") as f:
            for s in samples:
                payload = asdict(s) if hasattr(s, "__dataclass_fields__") else s
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
                count += 1
        return count
