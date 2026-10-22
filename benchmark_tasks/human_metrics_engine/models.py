"""Data models and enums for time-series metric collection, window rollups, and alerting."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Optional


class AlertSeverity(str, Enum):
    """Severity classification for metric alerts."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertState(str, Enum):
    """Lifecycle state of an alert condition."""

    RESOLVED = "RESOLVED"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"


@dataclass(frozen=True)
class MetricPoint:
    """Individual time-stamped metric sample."""

    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WindowStats:
    """Aggregated summary of metrics over a discrete temporal window."""

    metric_name: str
    count: int
    sum_val: float
    avg_val: float
    min_val: float
    max_val: float
    p95_val: float
    window_duration_seconds: float


@dataclass
class AlertRule:
    """Specification defining an alert trigger boundary."""

    rule_id: str
    metric_name: str
    threshold: float
    comparison_op: str = ">"
    severity: AlertSeverity = AlertSeverity.WARNING
    duration_seconds: float = 0.0


@dataclass
class AlertEvent:
    """Emitted notification when alert transitions between states."""

    rule_id: str
    metric_name: str
    state: AlertState
    triggered_at: float
    observed_value: float
    threshold: float
