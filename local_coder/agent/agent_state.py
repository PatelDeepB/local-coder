"""Agent task execution state and step tracking models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    """Status of an autonomous agent task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentStep:
    """Represents a single step in the agent's reasoning loop."""

    step_number: int
    thought: str
    action_tool: str
    action_arguments: dict[str, Any]
    observation: str
    is_successful: bool
    elapsed_seconds: float = 0.0


@dataclass
class AgentSessionState:
    """Represents the complete state of an active coding session."""

    session_id: str
    user_goal: str
    plan_checklist: list[str] = field(default_factory=list)
    completed_steps: list[AgentStep] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    final_output: Optional[str] = None
    modified_files: list[str] = field(default_factory=list)
    output_directory: Optional[str] = None
