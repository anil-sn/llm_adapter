"""
Base Adapter for LLM Orchestrator

Standard interface for all LLM provider adapters.
Ensures consistent request building and response normalization.

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

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
        Unified token budgeting with message truncation support.

        Uses consistent 2.0 chars/token ratio, 5% safety margin, and gracefully
        truncates messages if input is too large instead of failing.
        """
        import logging
        logger = logging.getLogger("base-adapter")

        RESERVE_TOKENS=100          # JSON overhead
        MIN_COMPLETION_TOKENS=256   # Minimum viable output
        CHARS_PER_TOKEN=3.5         # Balanced estimate: ~3.5 chars per token
                                      # (Conservative but not overly so)

        def estimate_tokens(text: str) -> int:
            """
            Estimate token count from text.

            Uses 3.5 chars/token as a balanced estimate:
            - Typical English: 4-5 chars/token
            - Code/technical: 3-4 chars/token
            - Repetitive text: 6-8 chars/token

            3.5 provides safety margin without excessive over-estimation.
            """
            if not text:
                return 0
            # Round up for safety
            return max(1, int((len(text) / CHARS_PER_TOKEN) + 0.5))

        def estimate_message_tokens(msg: dict) -> int:
            """Estimate tokens for one message including structure overhead."""
            total = 8  # Base overhead per message

            content = msg.get("content")
            if isinstance(content, str):
                total += estimate_tokens(content)
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        text = block.get("text", block.get("content", ""))
                        total += estimate_tokens(str(text))
                    else:
                        total += 2
            elif content is not None:
                total += estimate_tokens(str(content))

            # Account for tool calls
            tool_calls = msg.get("tool_calls")
            if isinstance(tool_calls, list):
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        func = tc.get("function", {})
                        total += estimate_tokens(tc.get("id", ""))
                        total += estimate_tokens(func.get("name", ""))
                        total += estimate_tokens(func.get("arguments", ""))
                    total += 8

            return total

        def truncate_messages(messages: list, max_prompt_tokens: int) -> list:
            """Keep system messages + newest conversation messages that fit."""
            if max_prompt_tokens <= 0:
                return messages

            total = sum(estimate_message_tokens(m) for m in messages)
            if total <= max_prompt_tokens:
                return messages

            # Separate system and conversation messages
            system_msgs = [m for m in messages if m.get("role") == "system"]
            rest = [m for m in messages if m.get("role") != "system"]

            system_tokens = sum(estimate_message_tokens(m) for m in system_msgs)
            budget_rest = max(0, max_prompt_tokens - system_tokens)

            # Keep newest messages that fit
            kept = []
            running = 0
            for m in reversed(rest):
                tokens = estimate_message_tokens(m)
                if running + tokens <= budget_rest:
                    kept.append(m)
                    running += tokens
                else:
                    break

            kept.reverse()
            return system_msgs + kept

        # 1. Estimate input tokens
        messages = body.get("messages", [])
        system_text = str(body.get("system", ""))

        prompt_tokens = sum(estimate_message_tokens(m) for m in messages)
        prompt_tokens += estimate_tokens(system_text)

        # 2. Add 5% safety margin
        prompt_tokens = int(prompt_tokens * 1.05)

        # 3. Extract tool overhead if present
        tool_overhead = body.pop("__tool_overhead_tokens__", 0)
        total_input_tokens = prompt_tokens + tool_overhead

        # 4. Get requested output tokens
        requested_max_tokens = body.get("max_tokens", 4096)

        # 5. Check if truncation needed
        available_completion = max_context - total_input_tokens - RESERVE_TOKENS
        message_count_before = len(messages)

        if available_completion <= 0:
            # Need to truncate messages
            target_completion = max(MIN_COMPLETION_TOKENS, max_context // 8)
            max_prompt_tokens = max(1, max_context - target_completion - tool_overhead - RESERVE_TOKENS)

            messages = truncate_messages(messages, max_prompt_tokens)
            body["messages"] = messages

            # Validate that at least one message remains after truncation
            if not messages:
                raise ValueError(
                    f"Input too large: truncation would remove all messages. "
                    f"Prompt estimated at {prompt_tokens:,} tokens, "
                    f"max context is {max_context:,} tokens. "
                    f"Consider reducing input size or increasing max_model_len."
                )

            # Recalculate after truncation
            prompt_tokens = sum(estimate_message_tokens(m) for m in messages)
            prompt_tokens += estimate_tokens(system_text)
            prompt_tokens = int(prompt_tokens * 1.05)
            total_input_tokens = prompt_tokens + tool_overhead
            available_completion = max_context - total_input_tokens - RESERVE_TOKENS

            logger.warning(
                f"TokenGuard: Truncated messages to fit context "
                f"(kept {len(messages)}/{message_count_before}, "
                f"input: {total_input_tokens}, context: {max_context})"
            )

        # 6. Clamp max_tokens to available space
        safe_max_tokens = max(MIN_COMPLETION_TOKENS, min(requested_max_tokens, available_completion))

        # 7. Log if clamping occurred
        if safe_max_tokens < requested_max_tokens:
            logger.info(
                f"TokenGuard: Clamping max_tokens from {requested_max_tokens} to {safe_max_tokens} "
                f"(input: {total_input_tokens}, tools: {tool_overhead}, context: {max_context})"
            )

        body["max_tokens"] = safe_max_tokens
        return body
