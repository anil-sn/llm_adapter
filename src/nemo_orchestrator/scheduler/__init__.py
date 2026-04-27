"""
Pulse Scheduler
===============

Temporal coalescing engine for high-throughput request batching.
Implements smart batching with configurable pulse windows (5ms-30ms).

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

from .pulse_scheduler import PulseScheduler

__all__ = ["PulseScheduler"]
