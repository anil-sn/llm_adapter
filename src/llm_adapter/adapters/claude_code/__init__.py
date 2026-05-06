"""
Claude Code adapter - production-ready converters

Production-ready converters for Claude Code CLI integration.
Handles streaming, response conversion, and tool calling.

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

from .streaming import convert_stream_to_anthropic, StreamState
from .response import convert_response_to_anthropic, create_error_response
from .tools import convert_tools_to_openai, convert_tool_choice_to_openai, generate_tool_use_id

__all__ = [
    "convert_stream_to_anthropic",
    "StreamState",
    "convert_response_to_anthropic",
    "create_error_response",
    "convert_tools_to_openai",
    "convert_tool_choice_to_openai",
    "generate_tool_use_id",
]
