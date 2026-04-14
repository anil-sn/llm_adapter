from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator

class BaseAdapter(ABC):
    """
    Standard interface for all LLM provider adapters.
    Ensures consistent request building and response normalization.
    """
    
    def __init__(self, max_context: int = 32768):
        self.max_context = max_context
        self.original_model_name = None  # Track original model name from client

    @abstractmethod
    def build_request(self, body: dict) -> dict:
        """Transform incoming OpenAI-style body into provider-specific request."""
        pass

    @abstractmethod
    async def complete(self, client: Any, target_url: str, request: dict) -> dict:
        """Perform a non-streaming request and return normalized JSON."""
        pass

    @abstractmethod
    async def stream(self, client: Any, target_url: str, request: dict) -> AsyncGenerator[bytes, None]:
        """Perform a streaming request and yield normalized SSE chunks."""
        pass

    @abstractmethod
    def normalize_response(self, resp: dict) -> dict:
        """Transform provider-specific response JSON into standard OpenAI format."""
        pass

    @abstractmethod
    def normalize_stream_chunk(self, chunk: dict) -> dict:
        """Transform provider-specific stream chunk into standard OpenAI format."""
        pass

    def clamp_max_tokens(self, body: dict, max_context: int = 32768) -> dict:
        """
        Token budgeting: Ensure input + output tokens don't exceed context window.

        Rough estimation: ~4 characters per token for English text.
        Safety margin: Reserve 10% for JSON overhead and underestimation.
        """
        # Extract text content for estimation
        messages_text = ""
        for msg in body.get("messages", []):
            content = msg.get("content", "")
            if isinstance(content, str):
                messages_text += content + " "
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        messages_text += str(block.get("text", block.get("content", ""))) + " "

        system_text = str(body.get("system", ""))
        total_text = messages_text + system_text

        # Estimate input tokens (conservative: 3.5 chars/token for safety)
        estimated_input_tokens = int(len(total_text) / 3.5)

        # Add 10% safety margin
        estimated_input_tokens = int(estimated_input_tokens * 1.1)

        # Get requested output tokens
        requested_max_tokens = body.get("max_tokens", 4096)

        # Calculate safe max_tokens
        available_tokens = max_context - estimated_input_tokens

        # Ensure minimum viable output (at least 100 tokens)
        if available_tokens < 100:
            # Input is too large - reduce to emergency minimum
            safe_max_tokens = 100
            import logging
            logger = logging.getLogger("base-adapter")
            logger.warning(
                f"Input very large (~{estimated_input_tokens} tokens). "
                f"Clamping max_tokens to emergency minimum: {safe_max_tokens}"
            )
        else:
            # Normal clamping
            safe_max_tokens = min(requested_max_tokens, available_tokens - 100)  # Keep 100 token buffer

        # Apply clamping
        if safe_max_tokens < requested_max_tokens:
            import logging
            logger = logging.getLogger("base-adapter")
            logger.info(
                f"TokenGuard: Clamping max_tokens from {requested_max_tokens} to {safe_max_tokens} "
                f"(estimated input: {estimated_input_tokens}, context: {max_context})"
            )
            body["max_tokens"] = safe_max_tokens

        return body
