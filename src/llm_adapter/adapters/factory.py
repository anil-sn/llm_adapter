"""
Adapter Factory for LLM Orchestrator

Dynamically selects and instantiates the appropriate adapter based on
model name patterns from configuration.

Supported Adapters:
- ClaudeAdapter: For Claude-style requests
- QwenAdapter: For Qwen models with thinking mode
- NemotronAdapter: For NVIDIA Nemotron models
- OpenAIAdapter: Fallback for standard OpenAI-compatible requests

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import logging
import re
from pathlib import Path
from typing import Union

from .claude_adapter import ClaudeAdapter
from .gemma_adapter import GemmaAdapter
from .openai_adapter import OpenAIAdapter
from .nemotron_adapter import NemotronAdapter
from .qwen_adapter import QwenAdapter
from .mistral_adapter import MistralAdapter
from .laguna_adapter import LagunaAdapter

from llm_adapter.utils.config_loader import load_config, ConfigError

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

logger = logging.getLogger("adapter-factory")

# Load configuration at module level
try:
    config = load_config(project_root=PROJECT_ROOT, validate=False)  # Skip validation for speed
    RULES = config.get("model_rules", [])
    MAX_CONTEXT = config.get("inference", {}).get("max_model_len", 900000)

    # Extract adapter-specific settings
    QWEN_ADAPTER_CONFIG = config.get("qwen_adapter", {})
    NEMOTRON_ADAPTER_CONFIG = config.get("nemotron_adapter", {})
    CLAUDE_ADAPTER_CONFIG = config.get("claude_adapter", {})
    GEMMA_ADAPTER_CONFIG = config.get("gemma_adapter", {})
    MISTRAL_ADAPTER_CONFIG = config.get("mistral_adapter", {})
    LAGUNA_ADAPTER_CONFIG = config.get("laguna_adapter", {})

    logger.info(f"Adapter factory initialized with {len(RULES)} routing rules")
    logger.info(f"Max context: {MAX_CONTEXT:,} tokens")

except ConfigError as e:
    logger.error(f"Failed to load config: {e}")
    # Fallback to defaults
    RULES = []
    MAX_CONTEXT = 32768
    QWEN_ADAPTER_CONFIG = {}
    NEMOTRON_ADAPTER_CONFIG = {}
    CLAUDE_ADAPTER_CONFIG = {}
    GEMMA_ADAPTER_CONFIG = {}
    MISTRAL_ADAPTER_CONFIG = {}
    LAGUNA_ADAPTER_CONFIG = {}
    logger.warning("Using default adapter configuration")


def get_adapter(
    model_id: str
) -> Union[ClaudeAdapter, NemotronAdapter, OpenAIAdapter]:
    """
    Dynamically select and instantiate the appropriate adapter.

    Pattern-based routing uses regex matching against model_id.
    First matching rule wins.

    Args:
        model_id: Model identifier from client request

    Returns:
        Instantiated adapter object

    Examples:
        >>> adapter = get_adapter("claude-opus-4")
        >>> assert isinstance(adapter, ClaudeAdapter)

        >>> adapter = get_adapter("qwen-3.5-122b")
        >>> assert isinstance(adapter, QwenAdapter)  # When implemented

        >>> adapter = get_adapter("nemotron-3-super")
        >>> assert isinstance(adapter, NemotronAdapter)
    """
    selected_type = "openai"  # Default fallback

    # Match against routing rules
    for rule in RULES:
        pattern = rule.get("pattern", "")
        if re.search(pattern, model_id, re.IGNORECASE):
            selected_type = rule.get("adapter", "openai")
            logger.debug(f"Model '{model_id}' matched pattern '{pattern}' → {selected_type}")
            break

    # Instantiate the selected adapter with configuration
    if selected_type == "claude":
        adapter = ClaudeAdapter(
            max_context=MAX_CONTEXT,
            **CLAUDE_ADAPTER_CONFIG  # Pass adapter-specific settings
        )

    elif selected_type == "qwen":
        # Extract Qwen-specific settings
        sampling_profiles = QWEN_ADAPTER_CONFIG.get("sampling_profiles")
        default_max_tokens = QWEN_ADAPTER_CONFIG.get("default_max_tokens", 32768)
        max_output_tokens = QWEN_ADAPTER_CONFIG.get("max_output_tokens", 81920)

        adapter = QwenAdapter(
            max_context=MAX_CONTEXT,
            sampling_profiles=sampling_profiles,
            default_max_tokens=default_max_tokens,
            max_output_tokens=max_output_tokens
        )

    elif selected_type == "gemma":
        # Extract Gemma-specific settings
        default_max_tokens = GEMMA_ADAPTER_CONFIG.get("default_max_tokens", 16384)
        max_output_tokens = GEMMA_ADAPTER_CONFIG.get("max_output_tokens", 65536)

        adapter = GemmaAdapter(
            max_context=MAX_CONTEXT,
            default_max_tokens=default_max_tokens,
            max_output_tokens=max_output_tokens
        )

    elif selected_type == "nemotron":
        adapter = NemotronAdapter(
            max_context=MAX_CONTEXT,
            **NEMOTRON_ADAPTER_CONFIG
        )

    elif selected_type == "mistral":
        default_max_tokens = MISTRAL_ADAPTER_CONFIG.get("default_max_tokens", 16384)
        max_output_tokens = MISTRAL_ADAPTER_CONFIG.get("max_output_tokens", 65536)
        autonomous_system_prompt = MISTRAL_ADAPTER_CONFIG.get("autonomous_system_prompt")

        adapter = MistralAdapter(
            max_context=MAX_CONTEXT,
            default_max_tokens=default_max_tokens,
            max_output_tokens=max_output_tokens,
            autonomous_system_prompt=autonomous_system_prompt
        )

    elif selected_type == "laguna":
        default_max_tokens = LAGUNA_ADAPTER_CONFIG.get("default_max_tokens", 16384)
        max_output_tokens = LAGUNA_ADAPTER_CONFIG.get("max_output_tokens", 65536)

        adapter = LagunaAdapter(
            max_context=MAX_CONTEXT,
            default_max_tokens=default_max_tokens,
            max_output_tokens=max_output_tokens
        )

    else:  # openai or unknown
        adapter = OpenAIAdapter(
            max_context=MAX_CONTEXT
        )

    logger.info(f"Request routed: '{model_id}' → {adapter.__class__.__name__}")
    return adapter


def reload_config() -> None:
    """
    Reload configuration from disk.

    Useful for dynamic config updates without restarting the gateway.

    Raises:
        ConfigError: If config reload fails
    """
    global config, RULES, MAX_CONTEXT
    global QWEN_ADAPTER_CONFIG, NEMOTRON_ADAPTER_CONFIG, CLAUDE_ADAPTER_CONFIG, GEMMA_ADAPTER_CONFIG, MISTRAL_ADAPTER_CONFIG, LAGUNA_ADAPTER_CONFIG

    logger.info("Reloading adapter factory configuration...")

    try:
        config = load_config(project_root=PROJECT_ROOT, validate=False)
        RULES = config.get("model_rules", [])
        MAX_CONTEXT = config.get("inference", {}).get("max_model_len", 32768)

        QWEN_ADAPTER_CONFIG = config.get("qwen_adapter", {})
        NEMOTRON_ADAPTER_CONFIG = config.get("nemotron_adapter", {})
        CLAUDE_ADAPTER_CONFIG = config.get("claude_adapter", {})
        GEMMA_ADAPTER_CONFIG = config.get("gemma_adapter", {})
        MISTRAL_ADAPTER_CONFIG = config.get("mistral_adapter", {})
        LAGUNA_ADAPTER_CONFIG = config.get("laguna_adapter", {})

        logger.info(f"Configuration reloaded: {len(RULES)} rules, {MAX_CONTEXT:,} max context")

    except ConfigError as e:
        logger.error(f"Failed to reload config: {e}")
        raise


# Expose public API
__all__ = [
    "get_adapter",
    "reload_config",
]
