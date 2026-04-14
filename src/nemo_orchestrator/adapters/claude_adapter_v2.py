"""
Claude Adapter V2 - Using production-ready claude-adapter-py converters
Integrates battle-tested streaming and response conversion logic
"""

import json
import logging
import httpx
from typing import AsyncIterator

# Import production-ready converters
from .claude_code import (
    convert_stream_to_anthropic,
    convert_response_to_anthropic,
    convert_tools_to_openai,
    convert_tool_choice_to_openai,
)
from .claude_code.models.openai import OpenAIChatResponse

logger = logging.getLogger("claude-adapter-v2")


class ClaudeAdapterV2:
    """
    Claude Adapter V2 with production-ready streaming and response conversion
    Based on claude-adapter-py (https://github.com/XuYan-Breeze/claude-adapter-py)
    """

    def __init__(self, backend_url: str = "http://127.0.0.1:8000", max_context: int = 32768):
        self.backend_url = backend_url.rstrip("/")
        self.max_context = max_context
        self.message_id = "msg-local"
        self.estimated_input_tokens = 0
        self.thinking_requested = False
        self.incoming_protocol = "anthropic"

    def build_request(self, anthropic_body: dict) -> dict:
        """
        Convert Anthropic Messages API request to OpenAI Chat Completions format
        """
        messages = []

        # Convert system messages
        system_content = anthropic_body.get("system")
        if system_content:
            if isinstance(system_content, str):
                messages.append({"role": "system", "content": system_content})
            elif isinstance(system_content, list):
                text_parts = [block.get("text", "") for block in system_content if block.get("type") == "text"]
                if text_parts:
                    messages.append({"role": "system", "content": " ".join(text_parts)})

        # Convert conversation messages
        for msg in anthropic_body.get("messages", []):
            role = msg.get("role")
            content = msg.get("content")

            if isinstance(content, str):
                messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Handle structured content blocks
                text_parts = []
                tool_calls = []

                for block in content:
                    block_type = block.get("type")

                    if block_type == "text":
                        text_parts.append(block.get("text", ""))

                    elif block_type == "tool_use":
                        # Convert Anthropic tool_use to OpenAI tool_calls format
                        tool_calls.append({
                            "id": block.get("id"),
                            "type": "function",
                            "function": {
                                "name": block.get("name"),
                                "arguments": json.dumps(block.get("input", {}))
                            }
                        })

                    elif block_type == "tool_result":
                        # Add tool result as separate tool message
                        messages.append({
                            "role": "tool",
                            "tool_call_id": block.get("tool_use_id"),
                            "content": str(block.get("content", ""))
                        })

                # Add message with text and/or tool_calls
                if text_parts or tool_calls:
                    msg_dict = {"role": role}
                    if text_parts:
                        msg_dict["content"] = " ".join(text_parts)
                    if tool_calls:
                        msg_dict["tool_calls"] = tool_calls
                    messages.append(msg_dict)

        # Convert tools
        openai_request = {
            "model": anthropic_body.get("model", "default"),
            "messages": messages,
            "max_tokens": min(anthropic_body.get("max_tokens", 4096), self.max_context),
            "temperature": anthropic_body.get("temperature", 1.0),
        }

        # Add tools if present
        if "tools" in anthropic_body and anthropic_body["tools"]:
            # Use production-ready tool converter
            openai_request["tools"] = convert_tools_to_openai(anthropic_body["tools"])

            # Convert tool_choice
            tool_choice = anthropic_body.get("tool_choice", {"type": "auto"})
            openai_request["tool_choice"] = convert_tool_choice_to_openai(tool_choice)

        # Add streaming flag
        if "stream" in anthropic_body:
            openai_request["stream"] = anthropic_body["stream"]

        return openai_request

    async def stream(self, request: dict) -> AsyncIterator[str]:
        """
        Stream response using production-ready claude-adapter-py streaming logic
        """
        backend_request = self.build_request(request)
        backend_request["stream"] = True

        target_url = f"{self.backend_url}/v1/chat/completions"

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", target_url, json=backend_request) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Backend error {response.status_code}: {error_text.decode()[:200]}")
                    yield f'event: error\ndata: {{"type":"error","error":{{"type":"api_error","message":"Backend error"}}}}\n\n'
                    return

                # Use production-ready streaming converter
                async for event in convert_stream_to_anthropic(
                    openai_stream=response.aiter_lines(),
                    request_id=self.message_id,
                    model=request.get("model", "default"),
                    provider="vllm"
                ):
                    yield event

    def normalize_response(self, openai_response: dict) -> dict:
        """
        Convert OpenAI response to Anthropic format using production-ready converter
        """
        # Use production-ready response converter
        try:
            # Parse into OpenAIChatResponse model
            response_obj = OpenAIChatResponse(**openai_response)

            # Convert to Anthropic format
            anthropic_response = convert_response_to_anthropic(
                openai_response=response_obj,
                original_model_requested=openai_response.get("model", "default")
            )

            # Convert Pydantic model to dict
            return anthropic_response.model_dump(exclude_none=True)

        except Exception as e:
            logger.error(f"Response conversion error: {e}")
            # Fallback to basic conversion
            return {
                "id": self.message_id,
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": str(openai_response)}],
                "model": openai_response.get("model", "default"),
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 0, "output_tokens": 0}
            }
