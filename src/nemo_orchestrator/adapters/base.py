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
        Token budgeting - disabled for transparency.
        Let vLLM handle max_tokens validation natively.
        """
        return body
