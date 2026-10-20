"""Strict Resident Set Size (RSS) memory watchdog for LOCAL-CODER."""

import os
import psutil

from local_coder.core.config import CONFIG


class MemoryBudgetExceededError(Exception):
    """Raised when process resident memory exceeds the safe budget ceiling."""

    def __init__(self, current_mb: float, limit_mb: float) -> None:
        super().__init__(
            f"Resident memory {current_mb:.2f} MB strictly exceeds safe budget {limit_mb:.2f} MB."
        )
        self.current_mb = current_mb
        self.limit_mb = limit_mb


class MemoryGuard:
    """Monitors process memory and guarantees compliance with the 2.0 GB limit."""

    def __init__(self, budget_mb: float = CONFIG.max_rss_mb) -> None:
        self.budget_mb = budget_mb
        self._process = psutil.Process(os.getpid())

    def get_resident_memory_mb(self) -> float:
        """Returns the current Resident Set Size (RSS) in megabytes."""
        bytes_used = self._process.memory_info().rss
        return float(bytes_used) / (1024.0 * 1024.0)

    def assert_within_budget(self) -> None:
        """Validates that current memory usage does not breach the budget limit."""
        current_mb = self.get_resident_memory_mb()
        if current_mb > self.budget_mb:
            raise MemoryBudgetExceededError(current_mb, self.budget_mb)

    def is_within_budget(self) -> bool:
        """Returns True if memory is within the safe limit."""
        return self.get_resident_memory_mb() <= self.budget_mb
