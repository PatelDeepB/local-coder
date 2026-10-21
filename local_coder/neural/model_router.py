"""Unified model routing supporting local CPU, Ollama, and OpenAI-compatible providers."""

from enum import Enum
import json
import os
from pathlib import Path
import time
from typing import Any, Generator, Optional
import urllib.request
import urllib.error

from local_coder.core.config import CONFIG
from local_coder.core.memory_guard import MemoryGuard
from local_coder.neural.llama_runner import GenerationResult, LlamaModelRunner


class ModelProvider(str, Enum):
    """Supported model provider backends."""

    LOCAL = "local"
    OLLAMA = "ollama"
    OPENAI = "openai"
    HYBRID = "hybrid"


class ModelRouter:
    """Dispatches generation requests to local GGUF or external LLM endpoints."""

    def __init__(
        self,
        provider: Optional[str] = None,
        local_runner: Optional[LlamaModelRunner] = None,
        memory_guard: Optional[MemoryGuard] = None,
    ) -> None:
        self.provider = ModelProvider(provider or CONFIG.model_provider)
        self.memory_guard = memory_guard or MemoryGuard()
        self.local_runner = local_runner or LlamaModelRunner(memory_guard=self.memory_guard)
        self.ollama_base_url = CONFIG.ollama_base_url.rstrip("/")
        self.ollama_model = CONFIG.ollama_model
        self.openai_base_url = CONFIG.openai_base_url.rstrip("/")
        self.openai_api_key = CONFIG.openai_api_key
        self.openai_model = CONFIG.openai_model

    def close(self) -> None:
        """Releases underlying resources."""
        self.local_runner.close()

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.2,
        stop_tokens: Optional[list[str]] = None,
        prefer_frontier: bool = False,
    ) -> GenerationResult:
        """Routes prompt to appropriate provider with fallback resilience."""
        active_provider = self._resolve_active_provider(prefer_frontier)
        if active_provider == ModelProvider.LOCAL:
            return self.local_runner.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop_tokens=stop_tokens,
            )

        if active_provider == ModelProvider.OLLAMA:
            return self._call_ollama(prompt, system_prompt, max_tokens, temperature)

        if active_provider == ModelProvider.OPENAI:
            return self._call_openai_compatible(prompt, system_prompt, max_tokens, temperature)

        return self.local_runner.generate(prompt=prompt, system_prompt=system_prompt)

    def stream_tokens(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.2,
        prefer_frontier: bool = False,
    ) -> Generator[str, None, None]:
        """Streams tokens from configured provider."""
        active_provider = self._resolve_active_provider(prefer_frontier)
        if active_provider == ModelProvider.LOCAL:
            yield from self.local_runner.stream_tokens(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return

        # Stream remote or fall back
        try:
            yield from self._stream_remote(prompt, system_prompt, max_tokens, temperature, active_provider)
        except Exception:
            yield from self.local_runner.stream_tokens(prompt=prompt, system_prompt=system_prompt)

    def _resolve_active_provider(self, prefer_frontier: bool) -> ModelProvider:
        """Selects provider based on mode and request complexity."""
        if self.provider == ModelProvider.HYBRID:
            if prefer_frontier and (self.openai_api_key or self._is_ollama_alive()):
                return ModelProvider.OPENAI if self.openai_api_key else ModelProvider.OLLAMA
            return ModelProvider.LOCAL
        return self.provider

    def _is_ollama_alive(self) -> bool:
        """Checks if local Ollama server is responding."""
        try:
            req = urllib.request.Request(f"{self.ollama_base_url}/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _call_ollama(
        self, prompt: str, system_prompt: str, max_tokens: int, temperature: float
    ) -> GenerationResult:
        """Executes request against Ollama OpenAI-compatible endpoint."""
        url = f"{self.ollama_base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        return self._send_http_chat_request(
            url=url,
            headers=headers,
            model=self.ollama_model,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _call_openai_compatible(
        self, prompt: str, system_prompt: str, max_tokens: int, temperature: float
    ) -> GenerationResult:
        """Executes request against OpenAI or DeepSeek remote endpoint."""
        url = f"{self.openai_base_url}/chat/completions"
        api_key = self.openai_api_key or ""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        return self._send_http_chat_request(
            url=url,
            headers=headers,
            model=self.openai_model,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def _send_http_chat_request(
        self,
        url: str,
        headers: dict[str, str],
        model: str,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> GenerationResult:
        """Dispatches HTTP chat completion with fallback to local model on error."""
        start_time = time.perf_counter()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data["choices"][0]["message"].get("content", "").strip()
            elapsed = time.perf_counter() - start_time
            tokens = len(content.split())
            tps = tokens / elapsed if elapsed > 0 else 0.0

            return GenerationResult(
                content=content,
                elapsed_seconds=elapsed,
                tokens_per_second=tps,
                token_count=tokens,
                peak_rss_mb=self.memory_guard.get_resident_memory_mb(),
            )
        except Exception:
            # Fall back to local CPU runner
            return self.local_runner.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )

    def _stream_remote(
        self,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
        provider: ModelProvider,
    ) -> Generator[str, None, None]:
        """Streams chunks from remote OpenAI/Ollama HTTP SSE endpoint."""
        url = (
            f"{self.ollama_base_url}/chat/completions"
            if provider == ModelProvider.OLLAMA
            else f"{self.openai_base_url}/chat/completions"
        )
        model = self.ollama_model if provider == ModelProvider.OLLAMA else self.openai_model
        headers = {"Content-Type": "application/json"}
        if provider == ModelProvider.OPENAI and self.openai_api_key:
            headers["Authorization"] = f"Bearer {self.openai_api_key}"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                try:
                    chunk = json.loads(line[6:])
                    delta = chunk["choices"][0].get("delta", {})
                    token = delta.get("content")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    continue
