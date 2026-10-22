from __future__ import annotations
from typing import Optional


class AlertRule:
    """Evaluates threshold conditions on metric values."""

    def __init__(self, severity: str, threshold: float) -> None:
        self.severity = severity
        self.threshold = threshold

    def evaluate(self, val: float) -> bool:
        """Returns True if metric value exceeds threshold."""
        return val > self.threshold


class AlertEngine:
    """Manages alert rules and triggers notifications."""

    def __init__(self, cooldown_seconds: float = 30.0) -> None:
        self.rules: list[AlertRule] = []
        self.cooldown_seconds = cooldown_seconds
        self.last_triggered: dict[str, float] = {}

    def add_rule(self, rule: AlertRule) -> None:
        self.rules.append(rule)
