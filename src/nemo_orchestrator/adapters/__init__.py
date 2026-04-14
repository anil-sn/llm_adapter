"""
Protocol Adapters
==================

Provider-specific normalization for different API protocols:
- ClaudeAdapter: Anthropic Messages API (legacy)
- ClaudeAdapterV2: Production-ready Claude Code integration
- NemotronAdapter: NVIDIA Nemotron-specific optimizations
- OpenAIAdapter: OpenAI Chat Completions API
"""

from .claude_adapter_v2 import ClaudeAdapterV2
from .nemotron_adapter import NemotronAdapter
from .openai_adapter import OpenAIAdapter

__all__ = [
    "ClaudeAdapterV2",
    "NemotronAdapter",
    "OpenAIAdapter",
]
