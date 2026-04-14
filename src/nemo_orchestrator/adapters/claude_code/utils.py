"""Utility functions for Claude Code adapter"""

import logging

# Simple logger
logger = logging.getLogger("claude-code-adapter")

def record_usage(provider="", model_name="", model="", input_tokens=0, output_tokens=0, cached_input_tokens=None, streaming=False):
    """Record token usage (stub for compatibility)"""
    pass

def record_error(error, message_id="", provider="", model="", streaming=False):
    """Record error (stub for compatibility)"""
    logger.error(f"Error: {error}")
