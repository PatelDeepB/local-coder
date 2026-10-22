from typing import List, Optional, Dict, Any
import asyncio
import json

class TaskPriority:
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class RetryPolicy:
    def get_backoff_time(self, attempt):
        if attempt == 0:
            return 1  # First retry is immediate
        else:
            return 2 ** attempt  # Exponential backoff

class Task:
    def __init__(self, id: int, priority: TaskPriority, data: Any):
        self.id = id
        self.priority = priority
        self.data = data

class TaskQueue:
    def __init__(self, max_retries: int = 3):
        self.tasks = []
        self.max_retries = max_retries
        self.dead_letter_queue = []

    async def add_task(self, task: Task):
        if len(self.tasks) >= self.max_retries:
            self.dead_letter_queue.append(task)
            return
        self.tasks.append(task)

    async def execute_tasks(self):
        while self.tasks or self.dead_letter_queue:
            if self.tasks:
                task = self.tasks.pop(0)
                await self.execute_task(task)
            else:
                task = self.dead_letter_queue.pop(0)
                await self.execute_task(task)

    async def execute_task(self, task: Task):
        attempt = 0
        while attempt < self.max_retries:
            try:
                # Simulate task execution
                print(f"Executing task {task.id} with priority {task.priority}")
                return
            except Exception as e:
                print(f"Task {task.id} failed with error: {e}")
                attempt += 1
                backoff_time = RetryPolicy().get_backoff_time(attempt)
                await asyncio.sleep(backoff_time)

class WorkerPool:
    def __init__(self, max_workers: int):
        self.max_workers = max_workers
        self.workers = []

    async def start(self):
        for _ in range(self.max_workers):
            worker = Worker()
            worker.start()
            self.workers.append(worker)

    async def stop(self):
        for worker in self.workers:
            await worker.stop()

class Worker:
    def __init__(self):
        pass

    async def start(self):
        print("Worker started")

    async def stop(self):
        print("Worker stopped")