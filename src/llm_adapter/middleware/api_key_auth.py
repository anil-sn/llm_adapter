"""
API Key Authentication Middleware for LLM Gateway.
Forces users to use valid API keys to access GPU resources.
"""
import logging
from pathlib import Path
from typing import Optional, Dict
import yaml
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("api-key-auth")


class APIKeyManager:
    """Manages API key validation and user mapping."""

    def __init__(self, config_path: Path):
        """Load API key configuration."""
        self.config_path = config_path
        self.api_keys: Dict[str, str] = {}
        self.enforce_api_keys = True
        self.allow_localhost_bypass = True
        self.require_prefix = "sk-"
        self.min_key_length = 16
        self._load_config()

    def _load_config(self):
        """Load API key configuration from YAML."""
        if not self.config_path.exists():
            logger.warning(f"API key config not found: {self.config_path}")
            return

        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f) or {}
                self.api_keys = config.get("api_keys", {})
                self.enforce_api_keys = config.get("enforce_api_keys", True)
                self.allow_localhost_bypass = config.get("allow_localhost_bypass", True)
                self.require_prefix = config.get("require_prefix", "sk-")
                self.min_key_length = config.get("min_key_length", 16)

            logger.info(f"Loaded {len(self.api_keys)} API keys")
        except Exception as e:
            logger.error(f"Failed to load API key config: {e}")

    def reload_config(self):
        """Reload configuration from file."""
        logger.info("Reloading API key configuration...")
        self._load_config()

    def validate_api_key(self, api_key: str) -> Optional[str]:
        """
        Validate API key and return the associated username.

        Args:
            api_key: The API key to validate

        Returns:
            Username if valid, None otherwise
        """
        if not api_key:
            return None

        # Validate key format
        if self.require_prefix and not api_key.startswith(self.require_prefix):
            logger.warning(f"API key rejected: missing prefix '{self.require_prefix}'")
            return None

        if len(api_key) < self.min_key_length:
            logger.warning(f"API key rejected: too short (min {self.min_key_length})")
            return None

        # Check if key exists in our mapping
        username = self.api_keys.get(api_key)

        if username:
            logger.debug(f"API key validated: {username}")
            return username
        else:
            logger.warning(f"API key rejected: not found in authorized keys")
            return None


# Global instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager(config_root: Path) -> APIKeyManager:
    """Get or create APIKeyManager singleton."""
    global _api_key_manager
    if _api_key_manager is None:
        config_path = config_root / "config" / "api_keys.yaml"
        _api_key_manager = APIKeyManager(config_path)
    return _api_key_manager


def extract_api_key(request: Request) -> Optional[str]:
    """
    Extract API key from request headers.

    Checks multiple header formats:
    1. Authorization: Bearer sk-xxx
    2. Authorization: sk-xxx
    3. X-API-Key: sk-xxx
    4. ANTHROPIC_API_KEY: sk-xxx

    Args:
        request: FastAPI Request object

    Returns:
        API key string or None
    """
    # Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header:
        # Handle "Bearer sk-xxx" format
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        # Handle direct "sk-xxx" format
        return auth_header.strip()

    # Check X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key.strip()

    # Check ANTHROPIC_API_KEY header (for compatibility)
    api_key = request.headers.get("ANTHROPIC_API_KEY")
    if api_key:
        return api_key.strip()

    return None


def require_api_key(request: Request, api_key_manager: APIKeyManager) -> str:
    """
    Require valid API key for GPU access.

    Args:
        request: FastAPI Request object
        api_key_manager: APIKeyManager instance

    Returns:
        Username associated with the API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    # Check if enforcement is enabled
    if not api_key_manager.enforce_api_keys:
        return "unauthenticated"

    # Check localhost bypass
    client_ip = request.client.host if request.client else None
    is_localhost = client_ip in ["127.0.0.1", "::1", "localhost"]

    if is_localhost and api_key_manager.allow_localhost_bypass:
        logger.debug(f"Localhost bypass: {client_ip}")
        return "localhost"

    # Extract API key from headers
    api_key = extract_api_key(request)

    if not api_key:
        logger.warning(f"Access denied: No API key provided from {client_ip}")
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "type": "authentication_required",
                    "message": "Valid API key required to access GPU resources",
                    "how_to_fix": {
                        "method_1": "Add Authorization header: 'Authorization: Bearer sk-your-key-here'",
                        "method_2": "Add X-API-Key header: 'X-API-Key: sk-your-key-here'",
                        "contact": "Request an API key from the administrator"
                    },
                    "example_curl": "curl -H 'Authorization: Bearer sk-your-key-here' ...",
                    "example_python": """
import os
from anthropic import Anthropic

client = Anthropic(
    base_url="http://10.172.249.149:8888",
    api_key="sk-your-key-here"  # Your assigned API key
)
""",
                    "your_ip": client_ip
                }
            }
        )

    # Validate API key
    username = api_key_manager.validate_api_key(api_key)

    if not username:
        # Log the failed API key (masked for security)
        masked_key = f"{api_key[:12]}..." if len(api_key) > 12 else api_key
        logger.warning(f"Access denied: Invalid API key '{masked_key}' from {client_ip}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "type": "invalid_api_key",
                    "message": "The provided API key is not valid",
                    "your_key_format": f"{api_key[:10]}..." if len(api_key) > 10 else api_key,
                    "contact": "Request a valid API key from the administrator",
                    "your_ip": client_ip
                }
            }
        )

    # Log successful authentication with API key
    masked_key = f"{api_key[:15]}..." if len(api_key) > 15 else api_key
    logger.info(f"✓ Auth: {username} (key: {masked_key}) from {client_ip}")
    return username
