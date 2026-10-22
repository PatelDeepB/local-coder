"""Pytest verification suite for async priority task queue, backoff retry, and DLQ."""

import asyncio
import pytest

from benchmark_tasks.human_task_queue.models import (
    RetryPolicy,
    Task,
    TaskPriority,
    TaskStatus,
)
from benchmark_tasks.human_task_queue.task_queue import PriorityTaskQueue
from benchmark_tasks.human_task_queue.worker_pool import WorkerPool


@pytest.mark.asyncio
async def test_should_dequeue_tasks_in_priority_order() -> None:
    queue = PriorityTaskQueue()

    low_task = Task(name="low_task", payload="payload_low", priority=TaskPriority.LOW)
    high_task = Task(name="high_task", payload="payload_high", priority=TaskPriority.HIGH)
    crit_task = Task(name="crit_task", payload="payload_crit", priority=TaskPriority.CRITICAL)

    # Enqueue out of order
    await queue.enqueue(low_task)
    await queue.enqueue(high_task)
    await queue.enqueue(crit_task)

    first = await queue.dequeue()
    queue.task_done()
    second = await queue.dequeue()
    queue.task_done()
    third = await queue.dequeue()
    queue.task_done()

    assert first.name == "crit_task"
    assert second.name == "high_task"
    assert third.name == "low_task"


@pytest.mark.asyncio
async def test_should_retry_with_backoff_and_succeed() -> None:
    queue = PriorityTaskQueue()
    attempts = 0

    async def flaky_handler(task: Task) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("Transient connection blip")

    worker_pool = WorkerPool(queue=queue, handler=flaky_handler, concurrency=1)
    await worker_pool.start()

    policy = RetryPolicy(max_retries=2, base_delay_seconds=0.01, backoff_factor=1.5)
    task = Task(name="flaky_task", payload="retry_me", retry_policy=policy)
    await queue.enqueue(task)

    # Allow worker to execute, fail once, wait 0.01s, and succeed
    await asyncio.sleep(0.1)
    await worker_pool.stop()

    assert attempts == 2
    assert task.status == TaskStatus.COMPLETED
    assert queue.metrics.retried == 1
    assert queue.metrics.completed == 1


@pytest.mark.asyncio
async def test_should_route_to_dlq_when_max_retries_exceeded() -> None:
    queue = PriorityTaskQueue()

    async def always_failing_handler(task: Task) -> None:
        raise ValueError("Fatal payload corruption")

    worker_pool = WorkerPool(queue=queue, handler=always_failing_handler, concurrency=1)
    await worker_pool.start()

    policy = RetryPolicy(max_retries=2, base_delay_seconds=0.01, backoff_factor=1.0)
    task = Task(name="doomed_task", payload="bad_payload", retry_policy=policy)
    await queue.enqueue(task)

    # Let retries exhaust (attempt 1, attempt 2, then DLQ)
    await asyncio.sleep(0.15)
    await worker_pool.stop()

    assert task.status == TaskStatus.DEAD_LETTER
    assert len(queue.dead_letter_queue) == 1
    assert queue.dead_letter_queue[0].task_id == task.task_id
    assert queue.metrics.dead_lettered == 1


@pytest.mark.asyncio
async def test_should_process_tasks_concurrently_with_worker_pool() -> None:
    queue = PriorityTaskQueue()
    completed_task_names: list[str] = []

    async def quick_handler(task: Task) -> None:
        await asyncio.sleep(0.01)
        completed_task_names.append(task.name)

    worker_pool = WorkerPool(queue=queue, handler=quick_handler, concurrency=4)
    await worker_pool.start()

    for i in range(12):
        await queue.enqueue(Task(name=f"task-{i}", payload=i))

    await asyncio.sleep(0.1)
    await worker_pool.stop()

    assert len(completed_task_names) == 12
    assert queue.metrics.completed == 12
    assert queue.metrics.failed == 0


@pytest.mark.asyncio
async def test_should_reject_duplicate_task_by_dedup_key() -> None:
    queue = PriorityTaskQueue()

    task1 = Task(name="sync_user", payload={"uid": 42}, dedup_key="user-sync-42")
    task2 = Task(name="sync_user_duplicate", payload={"uid": 42}, dedup_key="user-sync-42")

    enqueued_first = await queue.enqueue(task1)
    enqueued_second = await queue.enqueue(task2)

    assert enqueued_first is True
    assert enqueued_second is False
    assert queue.qsize() == 1


@pytest.mark.asyncio
async def test_should_report_queue_statistics() -> None:
    queue = PriorityTaskQueue()
    await queue.enqueue(Task(name="task_a", payload=1))
    await queue.enqueue(Task(name="task_b", payload=2))

    t = await queue.dequeue()
    await queue.handle_success(t)
    queue.task_done()

    stats = queue.get_queue_stats()
    assert stats["enqueued"] == 2
    assert stats["completed"] == 1
    assert stats["pending"] == 1
