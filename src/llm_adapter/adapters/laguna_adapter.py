"""
LagunaAdapter for LLM Orchestrator

Adapter for poolside/Laguna-S-2.1 models with advanced features:
- Native thinking mode using chat_template_kwargs
- Intact reasoning preservation in history for long-horizon planning
- Standard tool calling support

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

import logging
from typing import Any, Dict, Optional

from .openai_adapter import OpenAIAdapter

logger = logging.getLogger("laguna-adapter")


class LagunaAdapter(OpenAIAdapter):
    """
    Adapter for poolside/Laguna-S-2.1 models.

    Inherits base functionality from OpenAIAdapter and adds:
    - Native thinking/reasoning control (enable_thinking=True by default)
    - Preserve prior thinking blocks in history for agentic reasoning quality
    """

    def __init__(
        self,
        max_context: int = 1048576,
        default_max_tokens: int = 16384,
        max_output_tokens: int = 65536,
        **kwargs
    ):
        super().__init__(max_context=max_context, default_max_tokens=default_max_tokens)
        self.max_output_tokens = max_output_tokens

        logger.info(
            f"LagunaAdapter initialized: "
            f"max_context={max_context:,}, "
            f"default_max_tokens={default_max_tokens:,}"
        )

    def build_request(self, body: dict) -> dict:
        """
        Build Laguna-specific request with thinking mode template kwargs.

        Args:
            body: Request body from client

        Returns:
            Modified request body for vLLM
        """
        # Apply default max_tokens if not specified
        if "max_tokens" not in body:
            body["max_tokens"] = self.default_max_tokens
            logger.debug(f"Applied default max_tokens: {self.default_max_tokens}")

        # Enforce max output limit
        if body["max_tokens"] > self.max_output_tokens:
            logger.warning(
                f"max_tokens={body['max_tokens']} exceeds limit. "
                f"Clamping to {self.max_output_tokens}"
            )
            body["max_tokens"] = self.max_output_tokens

        # Apply token clamping from parent to stay within max context boundaries
        body = self.clamp_max_tokens(body, self.max_context)

        # Build request dict
        request = body.copy()

        # Laguna recommends enabling thinking by default for agentic coding.
        # Allow client override via enable_thinking or include_thinking.
        thinking = True
        if "enable_thinking" in body:
            thinking = bool(body["enable_thinking"])
        elif "include_thinking" in body:
            thinking = bool(body["include_thinking"])

        # Initialize extra_body if not present
        if "extra_body" not in request:
            request["extra_body"] = {}

        # Set Laguna-specific chat_template_kwargs
        if "chat_template_kwargs" not in request["extra_body"]:
            request["extra_body"]["chat_template_kwargs"] = {}
        
        request["extra_body"]["chat_template_kwargs"]["enable_thinking"] = thinking

        # Passthrough tools and tool_choice for vLLM native tool calling
        if "tools" in body:
            request["tools"] = body["tools"]

        if "tool_choice" in body:
            request["tool_choice"] = body["tool_choice"]
            logger.debug(f"Tool choice passed: {body['tool_choice']}")

        logger.debug(
            f"Laguna request built: thinking={thinking}, "
            f"max_tokens={request['max_tokens']}"
        )

        return request

    def normalize_response(self, resp: dict) -> dict:
        """
        Normalize response to OpenAI format.

        Args:
            resp: Raw response from vLLM

        Returns:
            Normalized response
        """
        # Laguna outputs are already OpenAI-compatible when served with poolside_v1 parser,
        # but we use parent normalization for absolute standard compliance.
        return super().normalize_response(resp)

    def normalize_stream_chunk(self, chunk: dict) -> dict:
        """
        Normalize streaming chunk to OpenAI format.

        Args:
            chunk: Raw stream chunk from vLLM

        Returns:
            Normalized chunk
        """
        return super().normalize_stream_chunk(chunk)
