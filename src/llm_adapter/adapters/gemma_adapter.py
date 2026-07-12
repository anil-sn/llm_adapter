"""
Gemma 4 Adapter for LLM Orchestrator

Adapter for Google Gemma 4 models with native vLLM parser support.
Enables tool calling and thinking mode via vLLM's Gemma4ToolParser and
Gemma4ReasoningParser.

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

import json
import logging
from typing import Any

from .openai_adapter import OpenAIAdapter

logger = logging.getLogger("gemma-adapter")


class GemmaAdapter(OpenAIAdapter):
    """
    Adapter for Google Gemma 4 models with native vLLM parser support.

    Features:
    - Native tool calling via vLLM's Gemma4ToolParser (--tool-call-parser gemma4)
    - Native thinking mode via vLLM's Gemma4ReasoningParser (--reasoning-parser gemma4)
    - Gemma-specific JSON escaping fixes for tool call arguments
    - Extended context support (up to 512K tokens via YaRN RoPE scaling)

    vLLM Parser References:
    - Tool Parser: /vllm/tool_parsers/gemma4_tool_parser.py
    - Reasoning Parser: /vllm/reasoning/gemma4_reasoning_parser.py

    Notes:
    - Tool calling format: <|tool_call>call:func_name{key:<|"|>value<|"|>}<tool_call|>
    - Thinking format: <|channel>thought\n...reasoning...<channel|>
    - Parsers configured at vLLM server startup, not per-request
    """

    def __init__(
        self,
        max_context: int = 524288,
        default_max_tokens: int = 16384,
        max_output_tokens: int = 65536,
        **kwargs
    ):
        """
        Initialize Gemma 4 adapter.

        Args:
            max_context: Maximum context length (default 512K for YaRN scaling)
            default_max_tokens: Default output tokens (conservative for large context)
            max_output_tokens: Maximum output tokens (64K for 512K context)
        """
        super().__init__(max_context=max_context, default_max_tokens=default_max_tokens)
        self.max_output_tokens = max_output_tokens
        self.thinking_requested = False
        logger.info(
            f"GemmaAdapter initialized: max_context={max_context}, "
            f"default_max_tokens={default_max_tokens}, "
            f"max_output_tokens={max_output_tokens}"
        )

    def _fix_escaped_newlines(self, obj):
        """
        Fix Gemma 4 tool calling JSON escaping issues.

        Gemma 4 has a known issue where it outputs literal \\n (backslash-n)
        instead of proper JSON escape \\n in tool call arguments. This method
        recursively fixes these issues in nested objects/arrays.

        Issues fixed:
        1. Unescape literal \\n → \\n in string values
        2. Unescape literal \\t → \\t in string values
        3. Unescape literal \\r → \\r in string values
        4. Strip extra quotes from string values (e.g., "\\"path\\"" → "path")

        Args:
            obj: Object to fix (can be dict, list, str, or primitive)

        Returns:
            Fixed object with proper escaping

        Examples:
            >>> fix_escaped_newlines({"patch": "line1\\\\nline2"})
            {"patch": "line1\\nline2"}

            >>> fix_escaped_newlines({"path": "\\\\"src/file.py\\\\""})
            {"path": "src/file.py"}
        """
        if isinstance(obj, dict):
            return {k: self._fix_escaped_newlines(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._fix_escaped_newlines(item) for item in obj]
        elif isinstance(obj, str):
            # Replace literal escaped characters with actual characters
            fixed = obj.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')

            # Fix: Strip surrounding quotes if Gemma added extra escaping
            # e.g., "\\"src/ari/file.py\\"" -> "src/ari/file.py"
            if fixed.startswith('"') and fixed.endswith('"') and len(fixed) > 2:
                fixed = fixed[1:-1]

            return fixed
        return obj

    def build_request(self, body: dict) -> dict:
        """
        Build Gemma 4 request with proper token budgeting.

        Notes:
        - vLLM parsers are configured at server startup via llm_manager.py
        - No need to set extra_body for tool/thinking parsers
        - Client can control thinking mode via extra_body.enable_thinking

        Args:
            body: Request body from client

        Returns:
            Request with clamped max_tokens
        """
        # Track if client requested thinking mode (for future use)
        self.thinking_requested = body.get("enable_thinking", False)

        # Apply token clamping based on context window
        return self.clamp_max_tokens(body, self.max_context)

    def normalize_response(self, resp: dict) -> dict:
        """
        Normalize Gemma 4 response with tool call argument fixing.

        vLLM's Gemma4ToolParser handles token parsing (<|tool_call>...<tool_call|>),
        but we still need to fix the JSON escaping issues in tool call arguments.

        vLLM's Gemma4ReasoningParser handles thinking token stripping automatically,
        so no manual regex filtering needed here.

        Args:
            resp: Response from vLLM

        Returns:
            Normalized response with fixed tool arguments
        """
        if "choices" in resp:
            for choice in resp["choices"]:
                msg = choice.get("message", {})

                # Fix tool call arguments (Gemma 4 double-escaping issue)
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    for tc in tool_calls:
                        try:
                            # Parse the arguments JSON string
                            args_str = tc["function"]["arguments"]
                            args = json.loads(args_str)

                            # Fix escaped newlines recursively
                            args = self._fix_escaped_newlines(args)

                            # Update with fixed version
                            tc["function"]["arguments"] = json.dumps(args)

                            logger.debug(f"Fixed tool call arguments for {tc['function']['name']}")
                        except (KeyError, json.JSONDecodeError, TypeError) as e:
                            logger.warning(f"Could not fix tool call arguments: {e}")
                            pass

                # NOTE: No need to strip thinking tokens manually!
                # vLLM's Gemma4ReasoningParser (--reasoning-parser gemma4)
                # handles <|channel>thought...<channel|> token stripping automatically
                # when reasoning_parser is configured at server startup

        return resp

    def normalize_stream_chunk(self, chunk: dict) -> dict:
        """
        Normalize Gemma 4 streaming chunks.

        For streaming mode, vLLM's parsers handle token stripping in real-time.
        We may need to fix tool call arguments if they arrive in streaming chunks.

        Args:
            chunk: Streaming chunk from vLLM

        Returns:
            Normalized chunk
        """
        # DEBUG: Log streaming chunks to investigate Claude Code loop
        if "choices" in chunk and chunk["choices"]:
            delta = chunk["choices"][0].get("delta", {})
            if "tool_calls" in delta:
                logger.debug(f"[GEMMA STREAM] Tool call delta: {delta.get('tool_calls')}")
            if "content" in delta:
                logger.debug(f"[GEMMA STREAM] Content delta: {delta.get('content')[:100] if delta.get('content') else 'None'}")

        # vLLM parsers handle streaming automatically
        # Tool call argument fixing happens in final accumulated chunks
        # For now, passthrough - can add streaming tool fix if needed
        return chunk
