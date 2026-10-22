from __future__ import annotations
from task_queue import RetryPolicy, Task, TaskQueue
from concurrent.futures import ThreadPoolExecutor, as_completed
from models import TaskPriority, RetryPolicy
import json

class WorkerPool:
    def __init__(self, max_workers=5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def start(self):
        for task in self.tasks:
            self.executor.submit(task.execute)

    def shutdown(self):
        self.executor.shutdown()

class Worker:
    def __init__(self, priority_queue, retry_policy):
        self.priority_queue = priority_queue
        self.retry_policy = retry_policy

    def execute(self):
        while True:
            try:
                task = self.priority_queue.get()
                if not task:
                    break
                result = task.execute()
                print(f"Task {task.id} completed with result: {result}")
            except Exception as e:
                print(f"Task {task.id} failed with error: {e}")
                if self.retry_policy.is_retryable(e):
                    retry_count = self.retry_policy.get_retry_count(e)
                    if retry_count >= self.retry_policy.max_retries:
                        # Handle DLQ
                        print("Task failed too many times, moving to DLQ")
                        break
                    else:
                        delay = self.retry_policy.get_delay(retry_count)
                        print(f"Retrying task {task.id} in {delay} seconds")
                        import time
                        time.sleep(delay)
                else:
                    # Handle other exceptions
                    raise

class TaskQueue:
    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def get(self):
        if not self.tasks:
            return None
        return self.tasks.pop(0)
