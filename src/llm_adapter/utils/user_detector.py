"""User detection utility for request logging."""
import socket
import logging
from pathlib import Path
import yaml

logger = logging.getLogger("user-detector")

class UserDetector:
    def __init__(self, config_path: Path):
        """Load user mapping configuration."""
        self.config_path = config_path
        self.ip_mapping = {}
        self.hostname_mapping = {}
        self.default_user = "unknown"
        self._load_config()

    def _load_config(self):
        """Load or reload configuration from file."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                config = yaml.safe_load(f) or {}
                self.ip_mapping = config.get("ip_mapping", {})
                self.hostname_mapping = config.get("hostname_mapping", {})
                self.default_user = config.get("default_user", "unknown")
        else:
            logger.warning(f"User config not found: {self.config_path}")

    def reload_config(self):
        """Reload configuration from file (for hot-reload)."""
        logger.info("Reloading user configuration...")
        self._load_config()
        logger.info(f"Configuration reloaded: {len(self.ip_mapping)} IP mappings, {len(self.hostname_mapping)} hostname mappings")

    def detect_user(self, request) -> str:
        """
        Detect user from request using multiple strategies:
        1. X-User-Name header (if client sends it)
        2. IP mapping from config
        3. Reverse DNS + hostname mapping
        4. Raw hostname from reverse DNS
        5. Client IP address
        6. Default "unknown"
        """
        # Strategy 1: Check for header override
        if header_user := request.headers.get("X-User-Name"):
            return header_user.strip()

        # Get client IP
        client_ip = request.client.host if request.client else None
        if not client_ip:
            return self.default_user

        # Strategy 2: Direct IP mapping
        if client_ip in self.ip_mapping:
            return self.ip_mapping[client_ip]

        # Strategy 3 & 4: Reverse DNS lookup
        try:
            hostname, _, _ = socket.gethostbyaddr(client_ip)

            # Try hostname mapping
            if hostname in self.hostname_mapping:
                return self.hostname_mapping[hostname]

            # Use first part of hostname
            short_hostname = hostname.split('.')[0]
            if short_hostname in self.hostname_mapping:
                return self.hostname_mapping[short_hostname]

            # Return cleaned hostname
            return short_hostname
        except (socket.herror, socket.gaierror, OSError):
            pass  # DNS lookup failed, fall through

        # Strategy 5: Return IP address
        return client_ip

# Global instance (loaded once at startup)
_detector = None

def get_user_detector(config_root: Path):
    """Get or create UserDetector singleton."""
    global _detector
    if _detector is None:
        config_path = config_root / "config" / "users.yaml"
        _detector = UserDetector(config_path)
    return _detector
