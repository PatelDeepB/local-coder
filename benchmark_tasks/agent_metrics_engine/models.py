from __future__ import annotations
from typing import Optional


class MetricPoint:
    """Represents a time-series data point with optional metadata tags."""

    def __init__(self, timestamp: int | float, value: float, tags: Optional[dict[str, str]] = None) -> None:
        self.timestamp = timestamp
        self.value = value
        self.tags = tags or {}
