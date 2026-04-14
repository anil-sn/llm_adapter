"""
Pulse Scheduler
===============

Temporal coalescing engine for high-throughput request batching.
Implements smart batching with configurable pulse windows (5ms-30ms).
"""

from .pulse_scheduler import PulseScheduler

__all__ = ["PulseScheduler"]
