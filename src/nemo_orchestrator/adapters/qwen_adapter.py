"""
QwenAdapter for LLM Orchestrator

Adapter for Qwen3.5-122B-A10B with advanced features:
- Thinking mode with <think>...</think> tags
- Profile-based sampling parameters
- Multi-turn history cleaning
- Extended context support (up to 512K with YaRN)

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import re
import logging
from typing import Any, Dict, Optional

from .nemotron_adapter import NemotronAdapter

logger = logging.getLogger("qwen-adapter")


class QwenAdapter(NemotronAdapter):
    """
    Adapter for Qwen3.5-122B-A10B models.

    Inherits base functionality from NemotronAdapter and adds:
    - Sampling profile selection (thinking_general, thinking_coding, etc.)
    - Multi-turn history cleaning (strips <think> tags from previous messages)
    - Qwen-specific thinking mode support
    - Default output token settings

    Args:
        max_context: Maximum context length in tokens
        sampling_profiles: Dictionary of sampling parameter profiles
        default_max_tokens: Default max tokens for completions
        max_output_tokens: Maximum output tokens allowed
    """

    def __init__(
        self,
        max_context: int = 262144,
        sampling_profiles: Optional[Dict[str, Any]] = None,
        default_max_tokens: int = 32768,
        max_output_tokens: int = 81920,
        **kwargs
    ):
        super().__init__(max_context=max_context)

        self.sampling_profiles = sampling_profiles or self._default_profiles()
        self.default_max_tokens = default_max_tokens
        self.max_output_tokens = max_output_tokens

        logger.info(
            f"QwenAdapter initialized: "
            f"max_context={max_context:,}, "
            f"default_max_tokens={default_max_tokens:,}, "
            f"profiles={len(self.sampling_profiles)}"
        )

    def _default_profiles(self) -> Dict[str, Dict[str, Any]]:
        """
        Default sampling profiles for Qwen3.5.

        Based on HuggingFace model card best practices.

        Returns:
            Dictionary of profile name to sampling parameters
        """
        return {
            "thinking_general": {
                "description": "General reasoning with thinking mode enabled",
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 20,
                "min_p": 0.0,
                "presence_penalty": 1.5,
                "repetition_penalty": 1.0,
            },
            "thinking_coding": {
                "description": "Precise coding tasks with thinking mode",
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "min_p": 0.0,
                "presence_penalty": 0.0,
                "repetition_penalty": 1.0,
            },
            "instruct_general": {
                "description": "General instruction following without thinking",
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 20,
                "min_p": 0.0,
                "presence_penalty": 1.5,
                "repetition_penalty": 1.0,
            },
            "instruct_reasoning": {
                "description": "Complex reasoning without thinking tags",
                "temperature": 1.0,
                "top_p": 1.0,
                "top_k": 40,
                "min_p": 0.0,
                "presence_penalty": 2.0,
                "repetition_penalty": 1.0,
            },
        }

    def _strip_thinking_from_content(self, content: str) -> str:
        """
        Remove <think>...</think> blocks from content.

        This is used for multi-turn history cleaning to prevent context pollution.
        According to Qwen documentation, thinking content should not be included
        in historical messages.

        Args:
            content: Text content potentially containing thinking tags

        Returns:
            Content with thinking tags removed

        Examples:
            >>> adapter = QwenAdapter()
            >>> text = "<think>Let me analyze...</think>The answer is 42."
            >>> adapter._strip_thinking_from_content(text)
            'The answer is 42.'
        """
        if not content or not isinstance(content, str):
            return content

        # Remove complete thinking blocks (greedy match)
        content = re.sub(r'<think>.*?</think>\s*', '', content, flags=re.DOTALL)

        # Remove orphaned closing tags
        content = re.sub(r'</think>\s*', '', content)

        # Remove orphaned opening tags
        content = re.sub(r'<think>\s*', '', content)

        return content.strip()

    def _select_sampling_profile(
        self,
        thinking_enabled: bool,
        profile_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Select appropriate sampling profile.

        Priority:
        1. Explicit profile hint from client
        2. Auto-select based on thinking mode:
           - thinking_general if thinking enabled
           - instruct_general if thinking disabled

        Args:
            thinking_enabled: Whether thinking mode is enabled
            profile_hint: Optional explicit profile name from client

        Returns:
            Dictionary of sampling parameters
        """
        # Explicit profile takes priority
        if profile_hint and profile_hint in self.sampling_profiles:
            logger.debug(f"Using explicit profile: {profile_hint}")
            return self.sampling_profiles[profile_hint]

        # Auto-select based on thinking mode
        if thinking_enabled:
            profile_name = "thinking_general"
        else:
            profile_name = "instruct_general"

        logger.debug(f"Auto-selected profile: {profile_name}")
        return self.sampling_profiles[profile_name]

    def _clean_message_history(self, messages: list) -> list:
        """
        Clean thinking tags from assistant messages in history.

        According to Qwen documentation, thinking content should not be
        included in multi-turn conversation history.

        Args:
            messages: List of message dictionaries

        Returns:
            List of cleaned messages (new list, doesn't modify input)
        """
        cleaned = []

        for msg in messages:
            # Create a copy to avoid modifying input
            msg_copy = msg.copy()

            # Clean assistant messages only
            if msg_copy.get("role") == "assistant":
                content = msg_copy.get("content", "")

                if isinstance(content, str) and "<think>" in content:
                    cleaned_content = self._strip_thinking_from_content(content)
                    msg_copy["content"] = cleaned_content
                    logger.debug("Cleaned thinking tags from assistant message")

            cleaned.append(msg_copy)

        return cleaned

    def build_request(self, body: dict) -> dict:
        """
        Build Qwen-specific request with sampling profiles and thinking mode.

        Process:
        1. Apply default max_tokens if not specified
        2. Clean multi-turn history (strip thinking from assistant messages)
        3. Determine thinking mode (client-controlled)
        4. Select and apply sampling profile
        5. Build request with Qwen-specific settings

        Args:
            body: Request body from client

        Returns:
            Modified request body for vLLM
        """
        # Step 1: Apply default max_tokens if not specified
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

        # Step 2: Clean multi-turn history
        if "messages" in body and isinstance(body["messages"], list):
            body["messages"] = self._clean_message_history(body["messages"])

        # Step 3: Determine thinking mode (CLIENT-CONTROLLED: default False)
        thinking = body.get("enable_thinking", False)

        # Step 4: Select sampling profile
        profile_hint = body.get("sampling_profile")  # Optional client hint
        sampling_params = self._select_sampling_profile(thinking, profile_hint)

        # Step 5: Apply token clamping from parent
        body = self.clamp_max_tokens(body, self.max_context)

        # Step 6: Build request with Qwen-specific settings
        request = body.copy()

        # Initialize extra_body if not present
        if "extra_body" not in request:
            request["extra_body"] = {}

        # Enable/disable thinking mode via chat_template_kwargs
        request["extra_body"]["chat_template_kwargs"] = {
            "enable_thinking": thinking
        }

        # Apply sampling parameters from profile
        # These override any client-provided values to ensure profile consistency
        request["temperature"] = sampling_params.get("temperature", 0.7)
        request["top_p"] = sampling_params.get("top_p", 0.95)

        # Add to extra_body for vLLM
        request["extra_body"]["top_k"] = sampling_params.get("top_k", 20)
        request["extra_body"]["min_p"] = sampling_params.get("min_p", 0.0)
        request["extra_body"]["presence_penalty"] = sampling_params.get("presence_penalty", 0.0)
        request["extra_body"]["repetition_penalty"] = sampling_params.get("repetition_penalty", 1.0)

        logger.debug(
            f"Request built: thinking={thinking}, "
            f"profile={profile_hint or 'auto'}, "
            f"max_tokens={request['max_tokens']}"
        )

        return request

    def normalize_response(self, resp: dict) -> dict:
        """
        Normalize Qwen response.

        Inherits base normalization from NemotronAdapter.
        Qwen-specific processing can be added here if needed.

        Args:
            resp: Response from vLLM

        Returns:
            Normalized response
        """
        # Use parent normalization
        resp = super().normalize_response(resp)

        # Qwen-specific normalization can be added here
        # For example: handling Qwen-specific reasoning field formats

        return resp

    def normalize_stream_chunk(self, chunk: dict) -> dict:
        """
        Normalize Qwen streaming chunk.

        Inherits base normalization from NemotronAdapter.
        Qwen-specific streaming processing can be added here if needed.

        Args:
            chunk: Stream chunk from vLLM

        Returns:
            Normalized chunk
        """
        # Use parent normalization
        chunk = super().normalize_stream_chunk(chunk)

        # Qwen-specific streaming normalization can be added here

        return chunk
