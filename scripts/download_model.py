"""Automatic GGUF model downloader with progress reporting."""

from pathlib import Path
import sys
import urllib.request

MODEL_URL = "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "qwen25_coder_15b"
MODEL_PATH = MODEL_DIR / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
EXPECTED_MIN_BYTES = 1_000_000_000  # ~1.04 GB


def download_progress_hook(block_num: int, block_size: int, total_size: int) -> None:
    downloaded = block_num * block_size
    if total_size > 0:
        percent = min(100.0, downloaded * 100.0 / total_size)
        mb_down = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        sys.stdout.write(f"\r[DOWNLOAD] {mb_down:.1f} MB / {mb_total:.1f} MB ({percent:.1f}%)")
        sys.stdout.flush()
    else:
        mb_down = downloaded / (1024 * 1024)
        sys.stdout.write(f"\r[DOWNLOAD] {mb_down:.1f} MB downloaded...")
        sys.stdout.flush()


def ensure_model_installed() -> Path:
    """Verifies or downloads the Qwen2.5-Coder-1.5B GGUF weights."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if MODEL_PATH.is_file() and MODEL_PATH.stat().st_size >= EXPECTED_MIN_BYTES:
        print(f"[INFO] Verified existing model weights at: {MODEL_PATH}")
        print(f"[INFO] File size: {MODEL_PATH.stat().st_size / (1024 * 1024):.1f} MB")
        return MODEL_PATH

    print("=" * 70)
    print("DOWNLOADING QWEN2.5-CODER-1.5B-INSTRUCT (GGUF Q4_K_M, ~1.04 GB)")
    print("=" * 70)
    print(f"Target destination: {MODEL_PATH}")
    print(f"Source URL: {MODEL_URL}")
    print("Downloading weights directly from Hugging Face...")

    temp_path = MODEL_PATH.with_suffix(".tmp")
    try:
        urllib.request.urlretrieve(MODEL_URL, temp_path, reporthook=download_progress_hook)
        print("\n[SUCCESS] Download completed. Finalizing file...")
        temp_path.replace(MODEL_PATH)
        print(f"[SUCCESS] Model ready at: {MODEL_PATH}")
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        print(f"\n[ERROR] Failed to download model: {exc}")
        sys.exit(1)

    return MODEL_PATH


if __name__ == "__main__":
    ensure_model_installed()
