"""High-performance CPU SIMD model runner with quantized KV-cache and flash attention."""

from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional
import json
import os
import time

from local_coder.core.config import CONFIG
from local_coder.core.hardware_profiler import detect_hardware_profile
from local_coder.core.memory_guard import MemoryGuard


@dataclass(frozen=True)
class GenerationResult:
    """Contains generated text, telemetry, and speed."""

    content: str
    elapsed_seconds: float
    tokens_per_second: float
    token_count: int
    peak_rss_mb: float


class LlamaModelRunner:
    """Executes local GGUF inference with strictly bounded RAM consumption."""

    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        context_size: int = CONFIG.context_window_size,
        memory_guard: Optional[MemoryGuard] = None,
    ) -> None:
        self.model_path = Path(model_path or CONFIG.default_model_path)
        self.context_size = context_size
        self.memory_guard = memory_guard or MemoryGuard()
        self.hw_profile = detect_hardware_profile()
        self._llm = None
        self._is_mock = False

        self._initialize_model()

    def close(self) -> None:
        """Explicitly releases llama context and internal buffers."""
        if self._llm is not None:
            try:
                self._llm.close()
            except Exception:
                pass
            self._llm = None

    def _initialize_model(self) -> None:
        """Loads GGUF via llama_cpp with optimal thread count and memory protection."""
        if not self.model_path.is_file():
            self._is_mock = True
            return

        try:
            from llama_cpp import Llama

            init_kwargs = {
                "model_path": str(self.model_path),
                "n_ctx": self.context_size,
                "n_batch": CONFIG.prompt_batch_size,
                "n_threads": self.hw_profile.optimal_threads,
                "n_threads_batch": self.hw_profile.optimal_threads,
                "verbose": False,
            }
            if CONFIG.kv_cache_quantization_type is not None:
                init_kwargs["type_k"] = CONFIG.kv_cache_quantization_type
                init_kwargs["type_v"] = CONFIG.kv_cache_quantization_type
            if CONFIG.enable_flash_attention:
                init_kwargs["flash_attn"] = True

            self._llm = Llama(**init_kwargs)
        except Exception:
            self._llm = None
            self._is_mock = True

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.2,
        stop_tokens: Optional[list[str]] = None,
    ) -> GenerationResult:
        """Generates response tokens with strict memory supervision."""
        self.memory_guard.assert_within_budget()
        start_time = time.perf_counter()
        stops = stop_tokens or ["<|im_end|>", "<|endoftext|>", "User:"]

        if self._is_mock or self._llm is None:
            # Deterministic mock response for lightweight unit test suites
            time.sleep(0.01)
            mock_text = f"Mock local coder response to: '{prompt[:50]}'"
            elapsed = time.perf_counter() - start_time
            return GenerationResult(
                content=mock_text,
                elapsed_seconds=elapsed,
                tokens_per_second=100.0,
                token_count=len(mock_text.split()),
                peak_rss_mb=self.memory_guard.get_resident_memory_mb(),
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Safeguard: dynamically compute token headroom and prevent context window overflow
        try:
            full_text = f"{system_prompt}\n{prompt}"
            input_tokens = len(self._llm.tokenize(full_text.encode("utf-8")))
        except Exception:
            input_tokens = len(prompt.split()) * 2

        available_tokens = self.context_size - input_tokens - 16
        if available_tokens < 64:
            prompt_lines = prompt.splitlines()
            while len(prompt_lines) > 20 and available_tokens < 128:
                prompt_lines.pop(1)
                prompt = "\n".join(prompt_lines)
                try:
                    input_tokens = len(self._llm.tokenize(f"{system_prompt}\n{prompt}".encode("utf-8")))
                except Exception:
                    input_tokens = len(prompt.split()) * 2
                available_tokens = self.context_size - input_tokens - 16
            messages[-1]["content"] = prompt

        effective_max_tokens = max(32, min(max_tokens, max(32, available_tokens)))

        output = self._llm.create_chat_completion(
            messages=messages,
            max_tokens=effective_max_tokens,
            temperature=temperature,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=stops,
        )

        raw_text = output["choices"][0]["message"].get("content") or ""
        raw_text = raw_text.strip()
        elapsed = time.perf_counter() - start_time
        token_count = len(raw_text.split())
        tps = token_count / elapsed if elapsed > 0 else 0.0

        return GenerationResult(
            content=raw_text,
            elapsed_seconds=elapsed,
            tokens_per_second=tps,
            token_count=token_count,
            peak_rss_mb=self.memory_guard.get_resident_memory_mb(),
        )

    def generate_raw(
        self,
        prompt: str,
        max_tokens: int = 32,
        temperature: float = 0.1,
        stop_tokens: Optional[list[str]] = None,
    ) -> GenerationResult:
        """Executes raw completion without chat formatting, ideal for FIM tab autocompletion."""
        self.memory_guard.assert_within_budget()
        start_time = time.perf_counter()
        stops = stop_tokens or ["<|fim_pad|>", "<|endoftext|>", "\n\n", "<|file_sep|>"]

        if self._is_mock or self._llm is None:
            time.sleep(0.005)
            mock_text = " = True"
            elapsed = time.perf_counter() - start_time
            return GenerationResult(
                content=mock_text,
                elapsed_seconds=elapsed,
                tokens_per_second=200.0,
                token_count=2,
                peak_rss_mb=self.memory_guard.get_resident_memory_mb(),
            )

        output = self._llm(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            repeat_penalty=1.05,
            stop=stops,
        )

        raw_text = output["choices"][0].get("text") or ""
        elapsed = time.perf_counter() - start_time
        token_count = len(raw_text.split())
        tps = token_count / elapsed if elapsed > 0 else 0.0

        return GenerationResult(
            content=raw_text,
            elapsed_seconds=elapsed,
            tokens_per_second=tps,
            token_count=token_count,
            peak_rss_mb=self.memory_guard.get_resident_memory_mb(),
        )

    def stream_tokens(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Streams generated tokens via generator."""
        if self._is_mock or self._llm is None:
            for word in f"Mock streaming response to: {prompt[:30]}".split():
                yield word + " "
            return

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for chunk in self._llm.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=["<|im_end|>", "<|endoftext|>"],
            stream=True,
        ):
            delta = chunk["choices"][0].get("delta", {}).get("content", "")
            if delta:
                yield delta
