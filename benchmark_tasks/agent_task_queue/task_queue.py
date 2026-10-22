from typing import List, Optional

class TaskPriority:
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class RetryPolicy:
    def get_backoff_time(self, attempt: int) -> float:
        # Implement exponential backoff logic here
        return 2 ** attempt * 1.0  # Example implementation

class Task:
    def __init__(self, id: str, priority: TaskPriority, data: dict):
        self.id = id
        self.priority = priority
        self.data = data

class TaskQueue:
    def __init__(self, max_retries: int = 3, dlq_enabled: bool = True):
        self.tasks = []
        self.max_retries = max_retries
        self.dlq_enabled = dlq_enabled

    async def enqueue(self, task: Task):
        if not isinstance(task, Task):
            raise ValueError("Task must be an instance of Task")
        self.tasks.append(task)

    async def process_tasks(self):
        while self.tasks:
            for i in range(len(self.tasks)):
                task = self.tasks[i]
                attempt = 0
                while attempt < self.max_retries:
                    try:
                        # Simulate task execution
                        await asyncio.sleep(1)
                        print(f"Task {task.id} executed successfully")
                        del self.tasks[i]
                        break
                    except Exception as e:
                        attempt += 1
                        if attempt == self.max_retries:
                            if self.dlq_enabled:
                                # Move to DLQ
                                dlq_task = Task(task.id, task.priority, task.data)
                                await asyncio.sleep(2)  # Simulate DLQ processing time
                                print(f"Task {task.id} moved to DLQ")
                else:
                    break

    async def start(self):
        await self.process_tasks()

# Example usage
async def main():
    queue = TaskQueue(max_retries=3, dlq_enabled=True)
    task1 = Task("1", TaskPriority.HIGH, {"name": "High Priority Task"})
    task2 = Task("2", TaskPriority.MEDIUM, {"name": "Medium Priority Task"})
    task3 = Task("3", TaskPriority.LOW, {"name": "Low Priority Task"})

    await queue.enqueue(task1)
    await queue.enqueue(task2)
    await queue.enqueue(task3)

    await queue.start()

if __name__ == "__main__":
    asyncio.run(main())