"""
Gateway
========

The main traffic-shaping router for LLM Adapter.
Handles request routing, protocol adaptation, and response normalization.

Run directly: python src/llm_adapter/gateway/server.py

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

# Don't import server here to avoid circular imports
# Server is meant to be run as a script, not imported

__all__ = []
