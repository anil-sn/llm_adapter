"""Middleware for LLM Gateway authentication and authorization."""

from .auth import require_user_identification, create_auth_error_response

__all__ = ["require_user_identification", "create_auth_error_response"]
