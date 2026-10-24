"""Pydantic data schemas for API server request and response payloads."""

from typing import Any, Optional
from pydantic import BaseModel


class OpenAIMessage(BaseModel):
    """Represents a chat message in OpenAI format."""
    role: str
    content: str


class OpenAIChatRequest(BaseModel):
    """Chat completion request payload."""
    model: str = "local-coder"
    messages: list[OpenAIMessage]
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 1024
    stream: Optional[bool] = False


class OpenAIChoiceMessage(BaseModel):
    """Choice message item inside OpenAI response."""
    role: str = "assistant"
    content: str


class OpenAIChoice(BaseModel):
    """Choice object inside OpenAI response."""
    index: int = 0
    message: OpenAIChoiceMessage
    finish_reason: str = "stop"


class OpenAIChatResponse(BaseModel):
    """Standard OpenAI chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[OpenAIChoice]


class TaskRequest(BaseModel):
    """Request payload for autonomous agent coding tasks."""
    goal: str
    output_directory: Optional[str] = None


class TerminalRequest(BaseModel):
    """Request payload for executing sandboxed terminal commands."""
    command: str


class InlineEditRequest(BaseModel):
    """Request payload for scoped inline code edits."""
    file_path: str
    selected_code: str
    instruction: str
    prefix_context: str = ""
    suffix_context: str = ""


class FastApplyRequest(BaseModel):
    """Request payload for single-pass fast apply edits."""
    file_path: str
    instruction: str
    output_directory: Optional[str] = None


class AutocompleteRequest(BaseModel):
    """Request payload for predictive tab completions."""
    prefix: str
    suffix: str = ""
    max_tokens: int = 32
    single_line_only: bool = True


class DiagnosticsHealRequest(BaseModel):
    """Request payload for LSP diagnostics healing."""
    file_path: str
    content: str
    diagnostics: list[dict[str, Any]] = []


class TestRepairRequest(BaseModel):
    """Request payload for test execution and repair."""
    test_path: str = "tests"
    target_file: Optional[str] = None
    max_iterations: int = 3


class SingleFileRequest(BaseModel):
    """Request payload referencing a single file path."""
    file_path: str


class ProviderChangeRequest(BaseModel):
    """Request payload for changing LLM model provider dynamically."""
    provider: str
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
