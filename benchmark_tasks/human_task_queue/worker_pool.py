"""Async worker pool for concurrent task consumption with error recovery."""

import asyncio
from typing import Awaitable, Callable, Optional

from benchmark_tasks.human_task_queue.models import Task
from benchmark_tasks.human_task_queue.task_queue import PriorityTaskQueue

TaskHandler = Callable[[Task], Awaitable[None]]


class WorkerPool:
    """Coordinates multiple async workers processing tasks from a priority queue."""

    def __init__(
        self,
        queue: PriorityTaskQueue,
        handler: TaskHandler,
        concurrency: int = 3,
    ) -> None:
        self.queue = queue
        self.handler = handler
        self.concurrency = concurrency
        self._workers: list[asyncio.Task[None]] = []
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Returns True if the worker pool is actively consuming."""
        return self._is_running

    async def start(self) -> None:
        """Launches worker coroutines up to the concurrency limit."""
        if self._is_running:
            return

        self._is_running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(f"worker-{i}"))
            for i in range(self.concurrency)
        ]

    async def stop(self) -> None:
        """Stops worker coroutines and cancels pending loops."""
        self._is_running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def _worker_loop(self, worker_id: str) -> None:
        """Continuous consumer loop executed by each worker coroutine."""
        while self._is_running:
            try:
                task = await self.queue.dequeue()
            except asyncio.CancelledError:
                break

            try:
                await self.handler(task)
                await self.queue.handle_success(task)
            except Exception as exc:
                await self.queue.handle_failure(task, exc)
            finally:
                self.queue.task_done()
