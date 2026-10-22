from __future__ import annotations
from typing import Optional
from models import MetricPoint


class Aggregator:
    """Calculates statistics over metric data points."""

    def __init__(self, filter_tags: Optional[dict[str, str]] = None) -> None:
        self.filter_tags = filter_tags
        self.data: list[MetricPoint] = []

    def add_data_point(self, point: MetricPoint) -> None:
        """Adds a metric data point."""
        if self.filter_tags is not None:
            if not all(point.tags.get(k) == v for k, v in self.filter_tags.items()):
                return
        self.data.append(point)

    def count(self) -> int:
        return len(self.data)

    def sum(self) -> float:
        return sum(p.value for p in self.data)

    def avg(self) -> float:
        return self.sum() / self.count() if self.count() > 0 else 0.0

    def min(self) -> float:
        return min((p.value for p in self.data), default=0.0)

    def max(self) -> float:
        return max((p.value for p in self.data), default=0.0)

    def p95(self) -> float:
        if not self.data:
            return 0.0
        sorted_vals = sorted(p.value for p in self.data)
        if len(sorted_vals) == 1:
            return float(sorted_vals[0])
        rank = 0.90 * (len(sorted_vals) - 1)
        lower = int(rank)
        fraction = rank - lower
        if lower >= len(sorted_vals) - 1:
            return float(sorted_vals[-1])
        return sorted_vals[lower] + fraction * (sorted_vals[lower + 1] - sorted_vals[lower])
