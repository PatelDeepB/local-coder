"""Core runtime, hardware detection, and memory supervision package."""

from local_coder.core.config import CONFIG, LocalCoderConfig
from local_coder.core.hardware_profiler import HardwareProfile, detect_hardware_profile
from local_coder.core.memory_guard import MemoryBudgetExceededError, MemoryGuard

__all__ = [
    "CONFIG",
    "LocalCoderConfig",
    "HardwareProfile",
    "detect_hardware_profile",
    "MemoryBudgetExceededError",
    "MemoryGuard",
]
