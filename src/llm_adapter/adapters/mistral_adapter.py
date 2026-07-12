"""
Mistral Adapter for LLM Orchestrator

Adapter for Mistral Medium 3.5 128B with native vLLM parser support.
Enables dynamic reasoning effort control, tool calling, and agentic coding
via vLLM's MistralToolParser and MistralReasoningParser.

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

import json
import logging
from typing import Any

from .openai_adapter import OpenAIAdapter

logger = logging.getLogger("mistral-adapter")


class MistralAdapter(OpenAIAdapter):
    """
    Adapter for Mistral Medium 3.5 128B models with native vLLM parser support.

    Features:
    - Dynamic reasoning effort control per request (none/low/high)
    - Native tool calling via vLLM's MistralToolParser (--tool-call-parser mistral)
    - Native reasoning via vLLM's MistralReasoningParser (--reasoning-parser mistral)
    - Mistral-specific tokenizer mode (--tokenizer-mode mistral)
    - Optimized for agentic coding workloads (OpenHands, RooCode, Aider, Claude-code-style)

    vLLM Parser References:
    - Tool Parser: /vllm/tool_parsers/mistral_tool_parser.py
    - Reasoning Parser: /vllm/reasoning/mistral_reasoning_parser.py

    Notes:
    - reasoning_effort is first-class: dynamically configurable per request
    - Parser correctness matters enormously for this model
    - Context compaction recommended beyond ~168k tokens
    - Practical production target: 128k-192k effective context
    - Message ordering: Mistral enforces strict role transitions (user→assistant, assistant→tool, tool→assistant)
    """

    def __init__(
        self,
        max_context: int = 262144,
        default_max_tokens: int = 16384,
        max_output_tokens: int = 65536,
        autonomous_system_prompt: str = None,
        **kwargs
    ):
        """
        Initialize Mistral Medium 3.5 adapter.

        Args:
            max_context: Maximum context length (default 256K native)
            default_max_tokens: Default output tokens
            max_output_tokens: Maximum output tokens (64K for 256K context)
            autonomous_system_prompt: Optional system prompt to encourage autonomous behavior
        """
        super().__init__(max_context=max_context, default_max_tokens=default_max_tokens)
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = "none"  # Default: no reasoning overhead
        self.autonomous_system_prompt = autonomous_system_prompt
        logger.info(
            f"MistralAdapter initialized: max_context={max_context}, "
            f"default_max_tokens={default_max_tokens}, "
            f"max_output_tokens={max_output_tokens}, "
            f"autonomous_mode={'enabled' if autonomous_system_prompt else 'disabled'}"
        )

    def _validate_and_fix_message_order(self, messages: list) -> list:
        """
        Validate and fix message ordering for Mistral's strict role transition rules.

        Mistral enforces these role transitions:
        - user → assistant, system, user
        - assistant → assistant, user, tool
        - tool → assistant, tool, user
        - system → user, assistant, system

        Common issue: Claude format sends tool_result in a 'user' message, which gets
        converted to role='tool'. But if previous message was 'user', we get user→tool
        which is invalid.

        Fix: Insert a dummy assistant acknowledgment before tool messages if needed.

        Args:
            messages: List of messages with roles

        Returns:
            Fixed message list
        """
        if not messages:
            return messages

        fixed_messages = []
        prev_role = None

        for msg in messages:
            current_role = msg.get("role")

            # Check if this transition is invalid
            if prev_role == "user" and current_role == "tool":
                # Invalid: user → tool
                # Fix: Insert assistant acknowledgment
                logger.debug(f"Fixing invalid user→tool transition by inserting assistant message")
                fixed_messages.append({
                    "role": "assistant",
                    "content": ""  # Empty assistant message as acknowledgment
                })

            fixed_messages.append(msg)
            prev_role = current_role

        return fixed_messages

    def build_request(self, body: dict) -> dict:
        """
        Build Mistral Medium 3.5 request with reasoning effort control.

        Process:
        1. Call parent build_request (handles message conversion)
        2. Fix message ordering for Mistral's strict role transitions
        3. Apply default max_tokens if not specified
        4. Enforce max output limit
        5. Extract reasoning_effort (none/low/high)
        6. Apply token clamping
        7. Build request with Mistral-specific settings

        Args:
            body: Request body from client

        Returns:
            Modified request body for vLLM
        """
        # Step 1: Call parent build_request for message conversion
        # This handles Claude→OpenAI protocol conversion including tool_result→tool messages
        request = super().build_request(body)

        # Step 2: Fix message ordering for Mistral's strict validation
        if "messages" in request:
            request["messages"] = self._validate_and_fix_message_order(request["messages"])

        # Step 2.5: Inject autonomous system prompt if configured
        if self.autonomous_system_prompt and "messages" in request:
            messages = request["messages"]
            # Check if there's already a system message
            has_system = any(msg.get("role") == "system" for msg in messages)
            if not has_system:
                # Prepend autonomous system prompt
                messages.insert(0, {
                    "role": "system",
                    "content": self.autonomous_system_prompt
                })
                logger.debug("Injected autonomous system prompt")
            else:
                # Append to existing system message
                for msg in messages:
                    if msg.get("role") == "system":
                        existing = msg.get("content", "")
                        msg["content"] = f"{existing}\n\n{self.autonomous_system_prompt}".strip()
                        logger.debug("Appended autonomous prompt to existing system message")
                        break

        # Step 3: Apply default max_tokens if not specified
        if "max_tokens" not in request:
            request["max_tokens"] = self.default_max_tokens
            logger.debug(f"Applied default max_tokens: {self.default_max_tokens}")

        # Step 4: Enforce max output limit
        if request["max_tokens"] > self.max_output_tokens:
            logger.warning(
                f"max_tokens={request['max_tokens']} exceeds limit. "
                f"Clamping to {self.max_output_tokens}"
            )
            request["max_tokens"] = self.max_output_tokens

        # Step 5: Extract reasoning_effort (none/low/high)
        # Default: none (low latency for simple tasks)
        # Complex coding agents should set to "high"
        self.reasoning_effort = body.get("reasoning_effort", "none")

        # Step 6: Token clamping already done by parent, skip

        # Step 7: Build request with Mistral-specific settings
        # Initialize extra_body if not present
        if "extra_body" not in request:
            request["extra_body"] = {}

        # Pass reasoning_effort to vLLM for dynamic control
        request["extra_body"]["reasoning_effort"] = self.reasoning_effort

        logger.debug(
            f"Request built: reasoning_effort={self.reasoning_effort}, "
            f"max_tokens={request['max_tokens']}"
        )

        return request

    def normalize_response(self, resp: dict) -> dict:
        """
        Normalize Mistral Medium 3.5 response.

        vLLM's MistralReasoningParser handles reasoning token stripping automatically.
        vLLM's MistralToolParser handles tool call parsing automatically.

        Args:
            resp: Response from vLLM

        Returns:
            Normalized response
        """
        if "choices" in resp:
            for choice in resp["choices"]:
                msg = choice.get("message", {})

                # Fix tool call arguments if present
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    for tc in tool_calls:
                        try:
                            args_str = tc["function"]["arguments"]
                            args = json.loads(args_str)
                            # Ensure arguments are re-serialized cleanly
                            tc["function"]["arguments"] = json.dumps(args)
                        except (KeyError, json.JSONDecodeError, TypeError):
                            pass

                # NOTE: No need to strip reasoning tokens manually!
                # vLLM's MistralReasoningParser (--reasoning-parser mistral)
                # handles reasoning token stripping automatically

        return resp

    def normalize_stream_chunk(self, chunk: dict) -> dict:
        """
        Normalize Mistral Medium 3.5 streaming chunks.

        For streaming mode, vLLM's parsers handle token stripping in real-time.
        Tool call argument fixing happens in final accumulated chunks.

        Args:
            chunk: Streaming chunk from vLLM

        Returns:
            Normalized chunk
        """
        # vLLM parsers handle streaming automatically
        # Tool call argument fixing happens in final accumulated chunks
        return chunk
