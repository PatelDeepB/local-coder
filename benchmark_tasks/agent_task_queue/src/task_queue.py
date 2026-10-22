class Task:
    def __init__(self, name, dedup_key=None):
        self.name = name
        self.dedup_key = dedup_key

    def run(self):
        # Implementation of task execution
        pass

class TaskQueue:
    def __init__(self):
        self.tasks = []
        self.seen_dedup_keys = set()

    def add_task(self, task):
        if task.dedup_key in self.seen_dedup_keys:
            return False
        self.tasks.append(task)
        self.seen_dedup_keys.add(task.dedup_key)
        return True

    def get_queue_stats(self):
        return {
            'enqueued': len(self.tasks),
            'completed': 0,  # Placeholder for completed tasks
            'failed': 0,   # Placeholder for failed tasks
            'dlq': 0      # Placeholder for dead-letter queue tasks
        }