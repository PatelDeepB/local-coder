from enum import Enum

class TaskPriority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class RetryPolicy:
    def __init__(self, max_retries: int, backoff_factor: float):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

    def get_backoff_time(self, attempt: int) -> float:
        return self.backoff_factor * (2 ** attempt)