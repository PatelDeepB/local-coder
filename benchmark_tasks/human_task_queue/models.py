"""Data models and enums for priority task queue with retry and DLQ support."""

from dataclasses import dataclass, field
from enum import Enum, IntEnum
import time
from typing import Any, Optional
import uuid


class TaskPriority(IntEnum):
    """Priority levels for task execution, where lower integer indicates higher priority."""

    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class TaskStatus(str, Enum):
    """Lifecycle states of a task."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass(frozen=True)
class RetryPolicy:
    """Configures retry behavior and exponential backoff timing."""

    max_retries: int = 3
    base_delay_seconds: float = 0.05
    backoff_factor: float = 2.0
    max_delay_seconds: float = 2.0

    def compute_delay(self, attempt: int) -> float:
        """Calculates backoff delay in seconds for the given attempt index."""
        raw_delay = self.base_delay_seconds * (self.backoff_factor ** max(0, attempt - 1))
        return min(raw_delay, self.max_delay_seconds)


@dataclass
class Task:
    """Represents a discrete unit of work executed by workers."""

    name: str
    payload: Any
    priority: TaskPriority = TaskPriority.MEDIUM
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dedup_key: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    created_at: float = field(default_factory=time.time)
    last_error: Optional[str] = None

    def __lt__(self, other: "Task") -> bool:
        """Enables priority queue comparison by priority value and creation order."""
        if not isinstance(other, Task):
            return NotImplemented
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at


@dataclass
class QueueMetrics:
    """Telemetry counters for queue activity."""

    enqueued: int = 0
    completed: int = 0
    failed: int = 0
    retried: int = 0
    dead_lettered: int = 0
