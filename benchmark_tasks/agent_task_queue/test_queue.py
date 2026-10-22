from typing import List, Optional

class TaskPriority:
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class RetryPolicy:
    def get_backoff_time(self, attempt: int) -> float:
        # Implement exponential backoff logic here
        return 0.1 * (2 ** attempt)

class Task:
    def __init__(self, id: str, priority: TaskPriority, data: dict):
        self.id = id
        self.priority = priority
        self.data = data

class TaskQueue:
    def __init__(self):
        self.tasks = []
        self.retry_policy = RetryPolicy()

    def add_task(self, task: Task):
        self.tasks.append(task)

    def execute_tasks(self):
        for task in sorted(self.tasks, key=lambda x: x.priority):
            attempt = 0
            while True:
                try:
                    # Execute the task here
                    print(f"Executing task {task.id}")
                    break
                except Exception as e:
                    attempt += 1
                    if attempt >= self.retry_policy.get_backoff_time(attempt):
                        print(f"Failed to execute task {task.id} after {attempt} attempts")
                        # Add to DLQ here
                        continue

class WorkerPool:
    def __init__(self, max_workers: int):
        self.max_workers = max_workers
        self.workers = []

    def add_worker(self, worker: Worker):
        self.workers.append(worker)

    def execute_tasks(self):
        for task in sorted(self.tasks, key=lambda x: x.priority):
            attempt = 0
            while True:
                try:
                    # Execute the task here
                    print(f"Executing task {task.id}")
                    break
                except Exception as e:
                    attempt += 1
                    if attempt >= self.retry_policy.get_backoff_time(attempt):
                        print(f"Failed to execute task {task.id} after {attempt} attempts")
                        # Add to DLQ here
                        continue

class Worker:
    def __init__(self, id: str):
        self.id = id

# Unit tests for the task queue and worker pool
def test_task_queue():
    task_queue = TaskQueue()
    task1 = Task("task1", TaskPriority.HIGH, {"data": "test1"})
    task2 = Task("task2", TaskPriority.MEDIUM, {"data": "test2"})
    task3 = Task("task3", TaskPriority.LOW, {"data": "test3"})

    task_queue.add_task(task1)
    task_queue.add_task(task2)
    task_queue.add_task(task3)

    task_queue.execute_tasks()

def test_worker_pool():
    worker_pool = WorkerPool(2)
    worker1 = Worker("worker1")
    worker2 = Worker("worker2")

    worker_pool.add_worker(worker1)
    worker_pool.add_worker(worker2)

    # Add more tasks to the queue and execute them