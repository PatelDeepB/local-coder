"""System-wide configuration and path constants for LOCAL-CODER."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional


def _resolve_default_model_path(models_dir: Path) -> Path:
    """Selects specialized Qwen2.5-Coder model if present, otherwise fallbacks to DeepSeek-R1."""
    coder_path = models_dir / "qwen25_coder_15b" / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
    if coder_path.is_file():
        return coder_path
    return models_dir / "deepseek_r1_15b" / "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"


@dataclass(frozen=True)
class LocalCoderConfig:
    """Holds all paths, memory ceilings, and execution parameters."""

    repo_root: Path = Path(__file__).resolve().parent.parent.parent
    models_dir: Path = repo_root / "models"
    default_model_path: Path = _resolve_default_model_path(
        Path(__file__).resolve().parent.parent.parent / "models"
    )
    max_rss_mb: float = 2000.0  # Safe ceiling strictly under 2.0 GB RAM limit (2048 MB)
    context_window_size: int = 4608
    prompt_batch_size: int = 512
    terminal_timeout_seconds: float = 30.0
    enable_flash_attention: bool = False
    kv_cache_quantization_type: Optional[int] = None
    # Provider Settings (local, ollama, openai, hybrid)
    model_provider: str = os.getenv("LOCAL_CODER_PROVIDER", "local")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY", os.getenv("DEEPSEEK_API_KEY", None))
    openai_model: str = os.getenv("OPENAI_MODEL", "deepseek-chat")


CONFIG = LocalCoderConfig()
