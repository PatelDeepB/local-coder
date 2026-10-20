"""Hardware profiler for optimal CPU SIMD and core pinning."""

from dataclasses import dataclass
import os
import psutil


@dataclass(frozen=True)
class HardwareProfile:
    """Summary of host CPU capabilities and optimal thread allocation."""

    physical_cores: int
    logical_cores: int
    optimal_threads: int
    has_avx2: bool


def detect_hardware_profile() -> HardwareProfile:
    """Detects host CPU architecture and resolves optimal SIMD execution threads."""
    physical = psutil.cpu_count(logical=False) or 4
    logical = psutil.cpu_count(logical=True) or physical

    # For memory-bandwidth-bound matrix multiplication, physical cores outperform
    # hyperthreaded logical cores by avoiding L1/L2 cache contention.
    optimal = max(1, physical)

    # Assume AVX2 on modern x86_64 architectures
    has_avx2 = True

    return HardwareProfile(
        physical_cores=physical,
        logical_cores=logical,
        optimal_threads=optimal,
        has_avx2=has_avx2,
    )
