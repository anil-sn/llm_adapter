"""
Gateway
========

The main traffic-shaping router for Nemo Orchestrator.
Handles request routing, protocol adaptation, and response normalization.

Run directly: python src/nemo_orchestrator/gateway/server.py
"""

# Don't import server here to avoid circular imports
# Server is meant to be run as a script, not imported

__all__ = []
