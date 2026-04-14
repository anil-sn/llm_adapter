import json
import logging
from typing import Any, AsyncGenerator
from .base import BaseAdapter

logger = logging.getLogger("openai-adapter")

class OpenAIAdapter(BaseAdapter):
    """
    Standard OpenAI passthrough for vLLM and other compatible backends.
    """
    def __init__(self, max_context: int = 32768):
        self.max_context = max_context

    def build_request(self, body: dict) -> dict:
        return self.clamp_max_tokens(body, self.max_context)

    async def complete(self, client: Any, target_url: str, request: dict) -> dict:
        """Perform non-streaming call using the given AsyncClient."""
        headers = {"Content-Type": "application/json"}
        response = await client.request(
            method="POST",
            url=target_url,
            headers=headers,
            json=request,
            timeout=None
        )
        # Assuming we handle 200 OK only for simplification
        data = response.json()
        return self.normalize_response(data)

    async def stream(self, client: Any, target_url: str, request: dict) -> AsyncGenerator[bytes, None]:
        """Perform SSE streaming passthrough."""
        headers = {"Content-Type": "application/json"}
        logger.info(f"Connecting to upstream stream: {target_url}")
        async with client.stream(
            method="POST",
            url=target_url,
            headers=headers,
            json=request,
            timeout=None
        ) as response:
            logger.info(f"Upstream stream status: {response.status_code}")
            async for line in response.aiter_lines():
                if not line: continue
                logger.info(f"Stream line: {line}")
                if line.startswith("data: "):
                    if line == "data: [DONE]":
                        yield b"data: [DONE]\n\n"
                        break
                    try:
                        chunk = json.loads(line[6:])
                        normalized = self.normalize_stream_chunk(chunk)
                        yield f"data: {json.dumps(normalized)}\n\n".encode()
                    except Exception as e:
                        logger.warning(f"Parse error: {e} on line: {line}")
                        yield f"{line}\n\n".encode()
                else:
                    yield f"{line}\n".encode()

    def normalize_response(self, resp: dict) -> dict:
        return resp

    def normalize_stream_chunk(self, chunk: dict) -> dict:
        return chunk
