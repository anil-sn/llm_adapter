"""
LLM Tool Definitions and Implementations

This module provides tool definitions and implementations that can be used
with the LLM adapters for function calling / tool use.

Available Tools:
- web_search: Search the web using DuckDuckGo or other search engines
- calculator: Perform mathematical calculations
- datetime: Get current date and time information

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

from .web_search import web_search_tool, execute_web_search
from .builtin_tools import get_builtin_tools

__all__ = [
    "web_search_tool",
    "execute_web_search",
    "get_builtin_tools",
]
