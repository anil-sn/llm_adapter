"""
Comprehensive Test Suite for QwenAdapter

Tests Qwen-specific functionality:
- Thinking mode control
- Sampling profile selection
- Multi-turn history cleaning
- Token limits and defaults

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from nemo_orchestrator.adapters.qwen_adapter import QwenAdapter


class TestQwenAdapterInitialization:
    """Test QwenAdapter initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        adapter = QwenAdapter()

        assert adapter.max_context == 262144
        assert adapter.default_max_tokens == 32768
        assert adapter.max_output_tokens == 81920
        assert len(adapter.sampling_profiles) == 4

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        custom_profiles = {
            "custom_profile": {
                "temperature": 0.5,
                "top_p": 0.9
            }
        }

        adapter = QwenAdapter(
            max_context=524288,
            sampling_profiles=custom_profiles,
            default_max_tokens=16384
        )

        assert adapter.max_context == 524288
        assert adapter.default_max_tokens == 16384
        assert "custom_profile" in adapter.sampling_profiles


class TestThinkingContentStripping:
    """Test thinking tag removal from content."""

    def test_strip_complete_thinking_blocks(self):
        """Test stripping complete thinking blocks."""
        adapter = QwenAdapter()

        text = "<think>Let me analyze this...</think>The answer is 42."
        result = adapter._strip_thinking_from_content(text)

        assert result == "The answer is 42."
        assert "<think>" not in result
        assert "</think>" not in result

    def test_strip_multiple_thinking_blocks(self):
        """Test stripping multiple thinking blocks."""
        adapter = QwenAdapter()

        text = "<think>First thought</think>Text 1<think>Second thought</think>Text 2"
        result = adapter._strip_thinking_from_content(text)

        assert result == "Text 1Text 2"
        assert "<think>" not in result

    def test_strip_multiline_thinking(self):
        """Test stripping multiline thinking blocks."""
        adapter = QwenAdapter()

        text = """<think>
Let me think about this...
Step 1: Analyze
Step 2: Solve
</think>Here is my answer."""

        result = adapter._strip_thinking_from_content(text)

        assert "Here is my answer." in result
        assert "<think>" not in result
        assert "Let me think" not in result

    def test_strip_orphaned_tags(self):
        """Test stripping orphaned thinking tags."""
        adapter = QwenAdapter()

        # Orphaned closing tag
        text1 = "Some text</think> more text"
        result1 = adapter._strip_thinking_from_content(text1)
        assert "</think>" not in result1

        # Orphaned opening tag
        text2 = "Some text <think> more text"
        result2 = adapter._strip_thinking_from_content(text2)
        assert "<think>" not in result2

    def test_handle_empty_content(self):
        """Test handling of empty or None content."""
        adapter = QwenAdapter()

        assert adapter._strip_thinking_from_content("") == ""
        assert adapter._strip_thinking_from_content(None) is None


class TestSamplingProfileSelection:
    """Test sampling profile selection logic."""

    def test_explicit_profile_priority(self):
        """Test that explicit profile hint takes priority."""
        adapter = QwenAdapter()

        profile = adapter._select_sampling_profile(
            thinking_enabled=False,
            profile_hint="thinking_coding"
        )

        assert profile["temperature"] == 0.6  # thinking_coding temp

    def test_auto_select_thinking(self):
        """Test auto-selection with thinking enabled."""
        adapter = QwenAdapter()

        profile = adapter._select_sampling_profile(
            thinking_enabled=True,
            profile_hint=None
        )

        assert profile["temperature"] == 1.0  # thinking_general temp
        assert profile["top_p"] == 0.95

    def test_auto_select_no_thinking(self):
        """Test auto-selection with thinking disabled."""
        adapter = QwenAdapter()

        profile = adapter._select_sampling_profile(
            thinking_enabled=False,
            profile_hint=None
        )

        assert profile["temperature"] == 0.7  # instruct_general temp
        assert profile["top_p"] == 0.8

    def test_invalid_profile_hint(self):
        """Test handling of invalid profile hint."""
        adapter = QwenAdapter()

        profile = adapter._select_sampling_profile(
            thinking_enabled=False,
            profile_hint="nonexistent_profile"
        )

        # Should fall back to auto-selection
        assert profile["temperature"] == 0.7  # instruct_general


class TestMessageHistoryCleaning:
    """Test multi-turn message history cleaning."""

    def test_clean_assistant_thinking(self):
        """Test cleaning thinking tags from assistant messages."""
        adapter = QwenAdapter()

        messages = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "<think>2+2=4</think>The answer is 4."},
            {"role": "user", "content": "Now multiply by 3"}
        ]

        cleaned = adapter._clean_message_history(messages)

        assert cleaned[1]["content"] == "The answer is 4."
        assert "<think>" not in cleaned[1]["content"]

    def test_preserve_user_messages(self):
        """Test that user messages are not modified."""
        adapter = QwenAdapter()

        messages = [
            {"role": "user", "content": "User message with <think> tag"},
            {"role": "assistant", "content": "Response"}
        ]

        cleaned = adapter._clean_message_history(messages)

        # User message should be unchanged (we don't clean user messages)
        assert cleaned[0]["content"] == "User message with <think> tag"

    def test_no_modification_without_thinking(self):
        """Test that messages without thinking tags are unchanged."""
        adapter = QwenAdapter()

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        cleaned = adapter._clean_message_history(messages)

        assert cleaned == messages

    def test_original_not_modified(self):
        """Test that original messages list is not modified."""
        adapter = QwenAdapter()

        original = [
            {"role": "assistant", "content": "<think>test</think>Response"}
        ]
        original_content = original[0]["content"]

        cleaned = adapter._clean_message_history(original)

        # Original should be unchanged
        assert original[0]["content"] == original_content
        # Cleaned should be different
        assert cleaned[0]["content"] != original_content


class TestRequestBuilding:
    """Test request building with Qwen-specific settings."""

    def test_apply_default_max_tokens(self):
        """Test that default max_tokens is applied."""
        adapter = QwenAdapter(default_max_tokens=16384)

        body = {
            "model": "qwen-3.5-122b",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        request = adapter.build_request(body)

        assert request["max_tokens"] == 16384

    def test_preserve_client_max_tokens(self):
        """Test that client-provided max_tokens is preserved."""
        adapter = QwenAdapter(default_max_tokens=16384)

        body = {
            "model": "qwen-3.5-122b",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 8192
        }

        request = adapter.build_request(body)

        assert request["max_tokens"] == 8192

    def test_enforce_max_output_limit(self):
        """Test that max_output_tokens limit is enforced."""
        adapter = QwenAdapter(max_output_tokens=10000)

        body = {
            "model": "qwen-3.5-122b",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 20000  # Exceeds limit
        }

        request = adapter.build_request(body)

        assert request["max_tokens"] == 10000  # Clamped

    def test_thinking_mode_disabled_by_default(self):
        """Test that thinking mode is disabled by default."""
        adapter = QwenAdapter()

        body = {
            "model": "qwen-3.5-122b",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        request = adapter.build_request(body)

        assert request["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False

    def test_thinking_mode_enabled(self):
        """Test enabling thinking mode."""
        adapter = QwenAdapter()

        body = {
            "model": "qwen-3.5-122b",
            "messages": [{"role": "user", "content": "Solve this"}],
            "enable_thinking": True
        }

        request = adapter.build_request(body)

        assert request["extra_body"]["chat_template_kwargs"]["enable_thinking"] is True

    def test_sampling_profile_applied(self):
        """Test that sampling profile parameters are applied."""
        adapter = QwenAdapter()

        body = {
            "model": "qwen-3.5-122b",
            "messages": [{"role": "user", "content": "Hello"}],
            "enable_thinking": False
        }

        request = adapter.build_request(body)

        # Should use instruct_general profile
        assert request["temperature"] == 0.7
        assert request["top_p"] == 0.8
        assert request["extra_body"]["top_k"] == 20

    def test_explicit_profile_selection(self):
        """Test explicit sampling profile selection."""
        adapter = QwenAdapter()

        body = {
            "model": "qwen-3.5-122b",
            "messages": [{"role": "user", "content": "Write code"}],
            "sampling_profile": "thinking_coding"
        }

        request = adapter.build_request(body)

        # Should use thinking_coding profile
        assert request["temperature"] == 0.6
        assert request["top_p"] == 0.95

    def test_history_cleaning_applied(self):
        """Test that message history is cleaned."""
        adapter = QwenAdapter()

        body = {
            "model": "qwen-3.5-122b",
            "messages": [
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "<think>reasoning</think>Answer"},
                {"role": "user", "content": "Follow-up"}
            ]
        }

        request = adapter.build_request(body)

        # Assistant message should be cleaned
        assert request["messages"][1]["content"] == "Answer"
        assert "<think>" not in request["messages"][1]["content"]


class TestDefaultProfiles:
    """Test default sampling profiles."""

    def test_all_default_profiles_present(self):
        """Test that all expected default profiles are present."""
        adapter = QwenAdapter()

        expected_profiles = [
            "thinking_general",
            "thinking_coding",
            "instruct_general",
            "instruct_reasoning"
        ]

        for profile in expected_profiles:
            assert profile in adapter.sampling_profiles

    def test_profile_structure(self):
        """Test that profiles have correct structure."""
        adapter = QwenAdapter()

        for profile_name, profile in adapter.sampling_profiles.items():
            # Check required parameters
            assert "temperature" in profile
            assert "top_p" in profile
            assert "top_k" in profile

            # Check value ranges
            assert 0.0 <= profile["temperature"] <= 2.0
            assert 0.0 <= profile["top_p"] <= 1.0
            assert profile["top_k"] >= 0


# Run tests if executed directly
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
