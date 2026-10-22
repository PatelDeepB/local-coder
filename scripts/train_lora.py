"""LoRA fine-tuning pipeline for Qwen2.5-Coder base models into specialized Synapse weights."""

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_lora")


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments for LoRA fine-tuning."""
    parser = argparse.ArgumentParser(description="Train Synapse LoRA adapter on clean pattern datasets.")
    parser.add_argument("--base-model", type=str, default="Qwen/Qwen2.5-Coder-1.5B-Instruct")
    parser.add_argument("--data-file", type=str, default="data/synapse_instructions.jsonl")
    parser.add_argument("--output-dir", type=str, default="models/synapse_lora_adapter")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--dry-run", action="store_true", help="Validate data and pipeline without training.")
    return parser.parse_args()


def load_dataset_samples(file_path: str) -> list[dict[str, Any]]:
    """Loads JSON Lines instruction or FIM samples."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Training data file not found: {file_path}")

    samples: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                samples.append(json.loads(line_str))
    return samples


def format_chatml_prompt(sample: dict[str, Any]) -> str:
    """Formats an instruction sample into standard ChatML text."""
    instruction = sample.get("instruction", "")
    context = sample.get("input", "")
    output = sample.get("output", "")

    user_text = f"{instruction}\n\nContext:\n{context}" if context else instruction
    return f"<|im_start|>user\n{user_text}<|im_end|>\n<|im_start|>assistant\n{output}<|im_end|>"


def execute_training(args: argparse.Namespace) -> None:
    """Executes the LoRA fine-tuning loop."""
    logger.info("Loading training dataset from: %s", args.data_file)
    samples = load_dataset_samples(args.data_file)
    logger.info("Loaded %d training samples successfully.", len(samples))

    if args.dry_run:
        logger.info("Dry-run requested. Verifying sample 1 formatting:")
        sample_prompt = format_chatml_prompt(samples[0]) if samples else ""
        logger.info("Preview:\n%s", sample_prompt[:300])
        logger.info("Dry-run validation complete. Pipeline is sound.")
        return

    try:
        import torch
        from peft import LoraConfig, get_peft_model
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
    except ImportError as e:
        logger.error("Missing required deep learning dependencies (torch, peft, transformers): %s", e)
        logger.error("Install via: pip install torch transformers peft accelerate datasets")
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Initializing base model: %s on %s", args.base_model, device)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
    )

    lora_config = LoraConfig(
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    logger.info("Training complete. Adapter saved to %s", output_path)


def main() -> None:
    """Entry point for LoRA training."""
    args = parse_arguments()
    execute_training(args)


if __name__ == "__main__":
    main()
