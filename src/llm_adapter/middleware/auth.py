"""
Simple authentication middleware for LLM Gateway.
Requires users to provide X-User-Name header to access the GPU.
"""
import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("auth-middleware")


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


def require_user_identification(request: Request) -> str:
    """
    Require X-User-Name header for all API requests.

    Args:
        request: FastAPI Request object

    Returns:
        str: The username from the header

    Raises:
        HTTPException: If header is missing or invalid
    """
    # Check for X-User-Name header
    user_name = request.headers.get("X-User-Name")

    if not user_name:
        # Also check alternative header names
        user_name = (
            request.headers.get("X-User-ID") or
            request.headers.get("User-Name") or
            request.headers.get("User-ID")
        )

    if not user_name:
        logger.warning(f"Access denied: No user identification from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "authentication_required",
                "message": "GPU access requires user identification. Please provide X-User-Name header.",
                "example": "curl -H 'X-User-Name: your-name' ...",
                "documentation": "Add X-User-Name header to all requests"
            }
        )

    # Validate username (basic sanitization)
    user_name = user_name.strip()

    if len(user_name) < 2:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_username",
                "message": "Username must be at least 2 characters"
            }
        )

    if len(user_name) > 50:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_username",
                "message": "Username must be less than 50 characters"
            }
        )

    # Optional: Block certain usernames
    blocked_names = ["unknown", "anonymous", "test", "admin", "root"]
    if user_name.lower() in blocked_names:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_username",
                "message": f"Username '{user_name}' is not allowed. Please use your real name."
            }
        )

    logger.info(f"Access granted: {user_name} from {request.client.host if request.client else 'unknown'}")
    return user_name


def create_auth_error_response(client_ip: str) -> JSONResponse:
    """
    Create a user-friendly error response for missing authentication.

    Args:
        client_ip: Client IP address

    Returns:
        JSONResponse with authentication error
    """
    return JSONResponse(
        status_code=401,
        content={
            "type": "error",
            "error": {
                "type": "authentication_required",
                "message": "GPU access requires user identification",
                "details": {
                    "your_ip": client_ip,
                    "required_header": "X-User-Name",
                    "example_curl": f"curl -H 'X-User-Name: john' -X POST http://your-server:8888/v1/chat/completions ...",
                    "example_python": """
import requests
headers = {"X-User-Name": "john"}
response = requests.post("http://your-server:8888/v1/chat/completions", headers=headers, json=...)
""",
                    "example_claude_code": """
Add to ~/.claude/settings.json:
{
  "llm": {
    "anthropic": {
      "baseURL": "http://your-server:8888",
      "headers": {
        "X-User-Name": "john"
      }
    }
  }
}
"""
                }
            }
        }
    )
