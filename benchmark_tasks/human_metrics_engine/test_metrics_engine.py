"""Pytest verification suite for metrics aggregation, p95 calculation, and alerting."""

from __future__ import annotations

import pytest

from benchmark_tasks.human_metrics_engine.aggregator import TimeSeriesAggregator
from benchmark_tasks.human_metrics_engine.alert_engine import AlertEngine
from benchmark_tasks.human_metrics_engine.models import (
    AlertRule,
    AlertSeverity,
    AlertState,
    MetricPoint,
)


def test_should_calculate_accurate_window_statistics() -> None:
    aggregator = TimeSeriesAggregator()
    base_time = 1000.0

    # Ingest 10 points: values 10, 20, 30, ..., 100
    for i in range(1, 11):
        aggregator.ingest(
            MetricPoint(name="cpu_load", value=float(i * 10), timestamp=base_time + i)
        )

    stats = aggregator.get_window_stats(
        metric_name="cpu_load",
        window_seconds=60.0,
        end_time=base_time + 15,
    )

    assert stats.count == 10
    assert stats.sum_val == 550.0
    assert stats.avg_val == 55.0
    assert stats.min_val == 10.0
    assert stats.max_val == 100.0
    assert stats.p95_val == 100.0


def test_should_handle_empty_window_gracefully() -> None:
    aggregator = TimeSeriesAggregator()
    stats = aggregator.get_window_stats(metric_name="unknown_metric", window_seconds=60.0)

    assert stats.count == 0
    assert stats.sum_val == 0.0
    assert stats.avg_val == 0.0
    assert stats.min_val == 0.0
    assert stats.max_val == 0.0
    assert stats.p95_val == 0.0


def test_should_trigger_and_resolve_alert_lifecycle() -> None:
    aggregator = TimeSeriesAggregator()
    engine = AlertEngine(evaluation_window_seconds=60.0)

    rule = AlertRule(
        rule_id="cpu_high",
        metric_name="cpu_load",
        threshold=80.0,
        comparison_op=">",
        severity=AlertSeverity.CRITICAL,
    )
    engine.register_rule(rule)

    t = 1000.0
    # Step 1: Normal load (50.0)
    aggregator.ingest(MetricPoint(name="cpu_load", value=50.0, timestamp=t))
    events1 = engine.evaluate_all(aggregator, evaluation_time=t)
    assert len(events1) == 0
    assert "cpu_high" not in engine.active_alerts

    # Step 2: High load breach (120.0, avg becomes 85.0 > 80.0)
    t += 10.0
    aggregator.ingest(MetricPoint(name="cpu_load", value=120.0, timestamp=t))
    events2 = engine.evaluate_all(aggregator, evaluation_time=t)
    assert len(events2) == 1
    assert events2[0].state == AlertState.ACTIVE
    assert "cpu_high" in engine.active_alerts

    # Step 3: Metric recovers (10.0), bringing 60s avg below 80.0
    t += 10.0
    for _ in range(5):
        aggregator.ingest(MetricPoint(name="cpu_load", value=10.0, timestamp=t))
    events3 = engine.evaluate_all(aggregator, evaluation_time=t)
    assert len(events3) == 1
    assert events3[0].state == AlertState.RESOLVED
    assert "cpu_high" not in engine.active_alerts


def test_should_filter_metrics_by_tags() -> None:
    aggregator = TimeSeriesAggregator()
    base_t = 1000.0

    aggregator.ingest(
        MetricPoint(name="latency", value=100.0, timestamp=base_t, tags={"env": "prod", "region": "us-east"})
    )
    aggregator.ingest(
        MetricPoint(name="latency", value=20.0, timestamp=base_t + 1, tags={"env": "dev", "region": "us-east"})
    )
    aggregator.ingest(
        MetricPoint(name="latency", value=300.0, timestamp=base_t + 2, tags={"env": "prod", "region": "eu-west"})
    )

    prod_east = aggregator.get_window_stats(
        metric_name="latency",
        window_seconds=60.0,
        end_time=base_t + 5,
        filter_tags={"env": "prod", "region": "us-east"},
    )
    assert prod_east.count == 1
    assert prod_east.avg_val == 100.0

    all_prod = aggregator.get_window_stats(
        metric_name="latency",
        window_seconds=60.0,
        end_time=base_t + 5,
        filter_tags={"env": "prod"},
    )
    assert all_prod.count == 2
    assert all_prod.avg_val == 200.0


def test_should_enforce_alert_cooldown_and_prevent_flapping() -> None:
    aggregator = TimeSeriesAggregator()
    engine = AlertEngine(evaluation_window_seconds=60.0, cooldown_seconds=30.0)

    rule = AlertRule(rule_id="mem_high", metric_name="memory_mb", threshold=500.0)
    engine.register_rule(rule)

    t = 1000.0
    # 1. Breach
    aggregator.ingest(MetricPoint(name="memory_mb", value=600.0, timestamp=t))
    e1 = engine.evaluate_all(aggregator, evaluation_time=t)
    assert len(e1) == 1
    assert e1[0].state == AlertState.ACTIVE

    # 2. Resolve at t + 10
    t += 10.0
    for _ in range(5):
        aggregator.ingest(MetricPoint(name="memory_mb", value=100.0, timestamp=t))
    e2 = engine.evaluate_all(aggregator, evaluation_time=t)
    assert len(e2) == 1
    assert e2[0].state == AlertState.RESOLVED

    # 3. Flap / re-breach at t + 5 (within 30s cooldown of resolution!)
    t += 5.0
    aggregator.ingest(MetricPoint(name="memory_mb", value=2000.0, timestamp=t))
    e3 = engine.evaluate_all(aggregator, evaluation_time=t)
    # Must be suppressed by cooldown!
    assert len(e3) == 0
    assert "mem_high" not in engine.active_alerts

    # 4. Re-breach after 35s (> 30s cooldown)
    t += 35.0
    aggregator.ingest(MetricPoint(name="memory_mb", value=2000.0, timestamp=t))
    e4 = engine.evaluate_all(aggregator, evaluation_time=t)
    assert len(e4) == 1
    assert e4[0].state == AlertState.ACTIVE
