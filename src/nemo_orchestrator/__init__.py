"""
Nemo Orchestrator - High-Performance LLM Inference Cluster
===========================================================

A production-ready inference orchestrator for Nemotron-3 Super 120B model,
featuring:
- Multi-protocol support (Anthropic, OpenAI, Nemotron)
- Pulse Scheduler for high-throughput batching
- TokenGuard for context safety
- Production-ready Claude Code integration

Author: asrirang
Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "asrirang"

# Avoid circular imports - don't import submodules here
# Use: from nemo_orchestrator.adapters import ClaudeAdapterV2
# Not: from nemo_orchestrator import ClaudeAdapterV2

__all__ = [
    "__version__",
    "__author__",
]
