"""
Protocol Adapters
==================

Provider-specific normalization for different API protocols:
- ClaudeAdapter: Anthropic Messages API
- GemmaAdapter: Google Gemma 4 with native vLLM parsers
- NemotronAdapter: NVIDIA Nemotron-specific optimizations
- OpenAIAdapter: OpenAI Chat Completions API
- QwenAdapter: Qwen models with thinking mode support

Author: Anil Srirangapatna Nagesh
Version: 2.2
"""

from .claude_adapter import ClaudeAdapter
from .gemma_adapter import GemmaAdapter
from .mistral_adapter import MistralAdapter
from .nemotron_adapter import NemotronAdapter
from .openai_adapter import OpenAIAdapter
from .qwen_adapter import QwenAdapter

__all__ = [
    "ClaudeAdapter",
    "GemmaAdapter",
    "MistralAdapter",
    "NemotronAdapter",
    "OpenAIAdapter",
    "QwenAdapter",
]
