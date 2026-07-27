"""
Comprehensive Test Suite for LagunaAdapter

Tests Laguna-specific functionality:
- Default initialization limits
- Native thinking/reasoning activation via chat_template_kwargs
- Intact reasoning preservation in history (unlike Qwen)
- Correct tool call and tool choice passthrough
- Routing and factory instantiation

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pytest
from llm_adapter.adapters.laguna_adapter import LagunaAdapter
from llm_adapter.adapters.factory import get_adapter, reload_config


class TestLagunaAdapterInitialization:
    """Test LagunaAdapter initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        adapter = LagunaAdapter()

        assert adapter.max_context == 1048576
        assert adapter.default_max_tokens == 16384
        assert adapter.max_output_tokens == 65536

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        adapter = LagunaAdapter(
            max_context=524288,
            default_max_tokens=4096,
            max_output_tokens=32768
        )

        assert adapter.max_context == 524288
        assert adapter.default_max_tokens == 4096
        assert adapter.max_output_tokens == 32768


class TestLagunaAdapterBuildRequest:
    """Test request construction and option mapping."""

    def test_default_thinking_mode(self):
        """Test that thinking defaults to enabled in extra_body."""
        adapter = LagunaAdapter()
        body = {
            "messages": [{"role": "user", "content": "Help me refactor this code."}]
        }

        request = adapter.build_request(body)

        assert "extra_body" in request
        assert "chat_template_kwargs" in request["extra_body"]
        assert request["extra_body"]["chat_template_kwargs"].get("enable_thinking") is True
        assert request["max_tokens"] == adapter.default_max_tokens

    def test_explicit_thinking_mode(self):
        """Test client-specified thinking mode (enabled/disabled)."""
        adapter = LagunaAdapter()

        # Disabled
        body_off = {
            "messages": [{"role": "user", "content": "Tell me a joke."}],
            "enable_thinking": False
        }
        request_off = adapter.build_request(body_off)
        assert request_off["extra_body"]["chat_template_kwargs"].get("enable_thinking") is False

        # Alternate include_thinking key (enabled)
        body_on = {
            "messages": [{"role": "user", "content": "Solve this equation."}],
            "include_thinking": True
        }
        request_on = adapter.build_request(body_on)
        assert request_on["extra_body"]["chat_template_kwargs"].get("enable_thinking") is True

    def test_history_preservation(self):
        """Test that history is left intact and prior thinking blocks are NOT stripped (unlike Qwen)."""
        adapter = LagunaAdapter()
        messages = [
            {"role": "user", "content": "First prompt"},
            {"role": "assistant", "content": "<thought>Analyzing original code...</thought>Refactored version."},
            {"role": "user", "content": "Explain the refactoring."}
        ]
        body = {"messages": messages}

        request = adapter.build_request(body)

        # The message history must remain exactly intact for Laguna's long-horizon planning
        assert request["messages"][1]["content"] == "<thought>Analyzing original code...</thought>Refactored version."

    def test_tool_calling_passthrough(self):
        """Test tool calling and tool choice passthrough to vLLM engine."""
        adapter = LagunaAdapter()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read file contents",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        body = {
            "messages": [{"role": "user", "content": "Read files."}],
            "tools": tools,
            "tool_choice": "auto"
        }

        request = adapter.build_request(body)

        assert "tools" in request
        assert request["tools"] == tools
        assert "tool_choice" in request
        assert request["tool_choice"] == "auto"


class TestLagunaRouting:
    """Test factory routing to LagunaAdapter."""

    def test_routing_and_factory_instantiation(self):
        """Test that models containing 'laguna' get routed to LagunaAdapter."""
        reload_config()
        adapter = get_adapter("poolside/Laguna-S-2.1-INT4")

        assert isinstance(adapter, LagunaAdapter)
        # Verify the maximum context matches our config-adapter system (which is loaded at setup)
        assert adapter.max_context > 0


class TestLagunaAdapterNormalization:
    """Test LagunaAdapter response and stream normalization (mock-free)."""

    def test_normalize_response(self):
        """Test standard response JSON normalization."""
        adapter = LagunaAdapter()
        raw_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1677649420,
            "model": "poolside/Laguna-S-2.1-FP8",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Normalized output text"
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 4,
                "total_tokens": 16
            }
        }

        normalized = adapter.normalize_response(raw_response)
        assert normalized == raw_response  # Invariants are identical

    def test_normalize_stream_chunk(self):
        """Test streaming chunk normalization."""
        adapter = LagunaAdapter()
        chunk = {
            "id": "chatcmpl-123",
            "object": "chat.completion.chunk",
            "created": 1677649420,
            "model": "poolside/Laguna-S-2.1-FP8",
            "choices": [
                {
                    "index": 0,
                    "delta": {
                        "content": "text chunk"
                    },
                    "finish_reason": None
                }
            ]
        }

        normalized = adapter.normalize_stream_chunk(chunk)
        assert normalized == chunk  # Invariants are identical
