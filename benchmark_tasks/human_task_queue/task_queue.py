"""Asynchronous thread-safe priority task queue with retry and DLQ routing."""

import asyncio
from typing import Optional

from benchmark_tasks.human_task_queue.models import (
    QueueMetrics,
    Task,
    TaskStatus,
)


class PriorityTaskQueue:
    """Manages ordered task storage, retry scheduling, and dead-letter queues."""

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[Task] = asyncio.PriorityQueue()
        self._dead_letter_queue: list[Task] = []
        self._metrics = QueueMetrics()
        self._seen_keys: set[str] = set()
        self._lock = asyncio.Lock()

    @property
    def metrics(self) -> QueueMetrics:
        """Returns the current queue activity metrics."""
        return self._metrics

    def get_queue_stats(self) -> dict[str, int]:
        """Returns structured dictionary of current queue operational counters."""
        return {
            "enqueued": self._metrics.enqueued,
            "completed": self._metrics.completed,
            "failed": self._metrics.failed,
            "retried": self._metrics.retried,
            "dead_lettered": self._metrics.dead_lettered,
            "pending": self.qsize(),
        }

    @property
    def dead_letter_queue(self) -> list[Task]:
        """Returns the list of dead-lettered tasks."""
        return list(self._dead_letter_queue)

    def qsize(self) -> int:
        """Returns current pending queue size."""
        return self._queue.qsize()

    async def enqueue(self, task: Task) -> bool:
        """Places a task into the queue, enforcing deduplication.

        Returns True if enqueued, False if rejected as duplicate.
        """
        async with self._lock:
            if task.dedup_key:
                if task.dedup_key in self._seen_keys:
                    return False
                self._seen_keys.add(task.dedup_key)

            task.status = TaskStatus.PENDING
            await self._queue.put(task)
            self._metrics.enqueued += 1
            return True

    async def dequeue(self) -> Task:
        """Pulls the highest priority available task."""
        task = await self._queue.get()
        task.status = TaskStatus.RUNNING
        return task

    def task_done(self) -> None:
        """Signals completion of a retrieved task."""
        self._queue.task_done()

    async def handle_success(self, task: Task) -> None:
        """Marks a task as successfully completed."""
        async with self._lock:
            task.status = TaskStatus.COMPLETED
            self._metrics.completed += 1

    async def handle_failure(self, task: Task, error: Exception) -> bool:
        """Routes task to retry with exponential backoff or into DLQ if retries exhausted.

        Returns True if task was scheduled for retry, False if routed to DLQ.
        """
        async with self._lock:
            task.retry_count += 1
            task.last_error = str(error)

            if task.retry_count <= task.retry_policy.max_retries:
                task.status = TaskStatus.RETRYING
                self._metrics.retried += 1
                delay = task.retry_policy.compute_delay(task.retry_count)
                asyncio.create_task(self._delayed_requeue(task, delay))
                return True

            task.status = TaskStatus.DEAD_LETTER
            self._dead_letter_queue.append(task)
            self._metrics.dead_lettered += 1
            self._metrics.failed += 1
            return False

    async def _delayed_requeue(self, task: Task, delay_seconds: float) -> None:
        """Waits for backoff delay before re-inserting task into queue."""
        await asyncio.sleep(delay_seconds)
        await self.enqueue(task)
