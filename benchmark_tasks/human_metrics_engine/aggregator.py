"""High-performance sliding and tumbling window time-series aggregator."""

from __future__ import annotations

import math
import time
from typing import Optional

from benchmark_tasks.human_metrics_engine.models import MetricPoint, WindowStats


class TimeSeriesAggregator:
    """Buffers time-stamped metric samples and calculates windowed rollups."""

    def __init__(self) -> None:
        self._buffer: dict[str, list[MetricPoint]] = {}

    def ingest(self, point: MetricPoint) -> None:
        """Stores a metric point in memory."""
        self._buffer.setdefault(point.name, []).append(point)

    def get_window_stats(
        self,
        metric_name: str,
        window_seconds: float,
        end_time: Optional[float] = None,
        filter_tags: Optional[dict[str, str]] = None,
    ) -> WindowStats:
        """Computes count, sum, avg, min, max, and 95th percentile over window with tag filtering."""
        cutoff_end = end_time if end_time is not None else time.time()
        cutoff_start = cutoff_end - window_seconds

        all_points = self._buffer.get(metric_name, [])
        points_in_window = [
            p.value
            for p in all_points
            if cutoff_start <= p.timestamp <= cutoff_end
            and (not filter_tags or all(p.tags.get(k) == v for k, v in filter_tags.items()))
        ]

        if not points_in_window:
            return WindowStats(
                metric_name=metric_name,
                count=0,
                sum_val=0.0,
                avg_val=0.0,
                min_val=0.0,
                max_val=0.0,
                p95_val=0.0,
                window_duration_seconds=window_seconds,
            )

        count = len(points_in_window)
        sum_val = sum(points_in_window)
        avg_val = sum_val / count
        min_val = min(points_in_window)
        max_val = max(points_in_window)

        sorted_values = sorted(points_in_window)
        p95_index = max(0, math.ceil(0.95 * count) - 1)
        p95_val = sorted_values[p95_index]

        return WindowStats(
            metric_name=metric_name,
            count=count,
            sum_val=sum_val,
            avg_val=avg_val,
            min_val=min_val,
            max_val=max_val,
            p95_val=p95_val,
            window_duration_seconds=window_seconds,
        )
