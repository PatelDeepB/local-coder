from __future__ import annotations
from pydantic import BaseModel, Field

class TaskPriority(BaseModel):
    """
    Represents the priority level of a task.
    
    Attributes:
        name (str): The name of the priority level.
        value (int): The numeric value associated with the priority level.
    """
    name: str = Field(..., description="The name of the priority level.")
    value: int = Field(..., description="The numeric value associated with the priority level.")

class RetryPolicy(BaseModel):
    """
    Represents the retry policy for a task.
    
    Attributes:
        max_retries (int): The maximum number of retries allowed.
        backoff_factor (float): The factor by which to increase the delay between retries.
    """
    max_retries: int = Field(..., description="The maximum number of retries allowed.")
    backoff_factor: float = Field(..., description="The factor by which to increase the delay between retries.")
