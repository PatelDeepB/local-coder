"""Alert rule evaluation and lifecycle state management."""

from __future__ import annotations

import time
from typing import Optional

from benchmark_tasks.human_metrics_engine.aggregator import TimeSeriesAggregator
from benchmark_tasks.human_metrics_engine.models import (
    AlertEvent,
    AlertRule,
    AlertState,
)


class AlertEngine:
    """Evaluates rules against metric window statistics and tracks active alerts."""

    def __init__(
        self,
        evaluation_window_seconds: float = 60.0,
        cooldown_seconds: float = 30.0,
    ) -> None:
        self.evaluation_window_seconds = evaluation_window_seconds
        self.cooldown_seconds = cooldown_seconds
        self._rules: dict[str, AlertRule] = {}
        self._active_alerts: dict[str, AlertEvent] = {}
        self._last_resolved_time: dict[str, float] = {}

    def register_rule(self, rule: AlertRule) -> None:
        """Adds an alert rule to the active evaluation registry."""
        self._rules[rule.rule_id] = rule

    @property
    def active_alerts(self) -> dict[str, AlertEvent]:
        """Returns mapping of currently active alert events."""
        return dict(self._active_alerts)

    def evaluate_all(
        self,
        aggregator: TimeSeriesAggregator,
        evaluation_time: Optional[float] = None,
    ) -> list[AlertEvent]:
        """Evaluates all registered rules and returns list of transition events."""
        current_t = evaluation_time if evaluation_time is not None else time.time()
        emitted_events: list[AlertEvent] = []

        for rule in self._rules.values():
            stats = aggregator.get_window_stats(
                metric_name=rule.metric_name,
                window_seconds=self.evaluation_window_seconds,
                end_time=current_t,
            )

            is_breached = False
            if stats.count > 0:
                if rule.comparison_op == ">" and stats.avg_val > rule.threshold:
                    is_breached = True
                elif rule.comparison_op == "<" and stats.avg_val < rule.threshold:
                    is_breached = True

            current_active = self._active_alerts.get(rule.rule_id)

            if is_breached and current_active is None:
                # Check cooldown to prevent alert flapping
                last_resolved = self._last_resolved_time.get(rule.rule_id, 0.0)
                if (current_t - last_resolved) < self.cooldown_seconds:
                    continue

                # Transition to ACTIVE
                event = AlertEvent(
                    rule_id=rule.rule_id,
                    metric_name=rule.metric_name,
                    state=AlertState.ACTIVE,
                    triggered_at=current_t,
                    observed_value=stats.avg_val,
                    threshold=rule.threshold,
                )
                self._active_alerts[rule.rule_id] = event
                emitted_events.append(event)
            elif not is_breached and current_active is not None:
                # Transition to RESOLVED
                event = AlertEvent(
                    rule_id=rule.rule_id,
                    metric_name=rule.metric_name,
                    state=AlertState.RESOLVED,
                    triggered_at=current_t,
                    observed_value=stats.avg_val,
                    threshold=rule.threshold,
                )
                del self._active_alerts[rule.rule_id]
                self._last_resolved_time[rule.rule_id] = current_t
                emitted_events.append(event)

        return emitted_events
