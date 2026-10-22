"""Unit tests for SynapseDatasetBuilder and LoRA data generation."""

from pathlib import Path
import json

from local_coder.training.dataset_builder import SynapseDatasetBuilder
from scripts.train_lora import format_chatml_prompt


def test_should_build_instruction_dataset() -> None:
    # Arrange
    builder = SynapseDatasetBuilder()

    # Act
    samples = builder.build_instruction_dataset()

    # Assert
    assert len(samples) > 0
    first = samples[0]
    assert first.instruction
    assert first.output
    assert first.category == "pattern_synthesis"


def test_should_build_fim_dataset() -> None:
    # Arrange
    builder = SynapseDatasetBuilder()

    # Act
    fim_samples = builder.build_fim_dataset()

    # Assert
    assert len(fim_samples) > 0
    first = fim_samples[0]
    assert "<|fim_prefix|>" in first.prompt
    assert "<|fim_suffix|>" in first.prompt
    assert "<|fim_middle|>" in first.prompt
    assert first.completion


def test_should_export_jsonl_file(tmp_path: Path) -> None:
    # Arrange
    builder = SynapseDatasetBuilder()
    samples = builder.build_instruction_dataset()[:3]
    output_path = tmp_path / "instructions.jsonl"

    # Act
    count = builder.export_jsonl(samples, output_path)

    # Assert
    assert count == 3
    assert output_path.exists()
    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    parsed = json.loads(lines[0])
    assert "instruction" in parsed
    assert "output" in parsed


def test_should_format_chatml_for_lora() -> None:
    # Arrange
    sample = {
        "instruction": "Build user auth model",
        "input": "Framework: Django",
        "output": "class User(models.Model): pass",
    }

    # Act
    formatted = format_chatml_prompt(sample)

    # Assert
    assert "<|im_start|>user" in formatted
    assert "Build user auth model" in formatted
    assert "<|im_start|>assistant" in formatted
    assert "class User(models.Model): pass" in formatted
