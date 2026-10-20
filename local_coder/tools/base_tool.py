"""Abstract base class and parameter schemas for agent tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ToolResult:
    """Structured response from tool execution."""

    is_success: bool
    output: str
    error_message: Optional[str] = None


class BaseAgentTool(ABC):
    """Abstract interface that all agent tools must satisfy."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The tool identifier used by the model."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Clear instruction explaining what the tool does and when to call it."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema dictionary describing required arguments."""
        pass

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Performs the tool operation and returns structured result."""
        pass
