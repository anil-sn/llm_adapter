"""
Model Alias Mapper - Multi-Client Compatibility
Maps incoming model names from various clients (OpenAI, Claude, Claude Code CLI, etc.)
to the actual served model names in vLLM.
"""

import logging
from typing import Optional

logger = logging.getLogger("model-alias")

# Comprehensive model alias mapping
# Maps ANY model name a client might send -> vLLM served model name
MODEL_ALIASES = {
    # Claude-style model names
    "claude-haiku-4-5-20251001": "nemotron-3-super",
    "claude-3-5-sonnet-20240620": "nemotron-3-super",
    "claude-3-5-sonnet": "nemotron-3-super",
    "claude-3-opus-20240229": "nemotron-3-super",
    "claude-opus-4-0-20250514": "nemotron-3-super",
    "claude-sonnet-4-0-20250514": "nemotron-3-super",
    "claude-haiku-4-5-20250714": "nemotron-3-super",
    
    # OpenAI-style model names
    "gpt-4": "nemotron-3-super",
    "gpt-4o": "nemotron-3-super",
    "gpt-4o-mini": "nemotron-3-super",
    "gpt-3.5-turbo": "nemotron-3-super",
    "o1": "nemotron-3-super",
    "o3": "nemotron-3-super",
    
    # Nemotron/NVIDIA model names
    "nvidia/nvidia-nemotron-3-super-120b-a12b-fp8": "nemotron-3-super",
    "nemotron-3-super-120b": "nemotron-3-super",
    "nemotron-120b": "nemotron-3-super",
    "nvidia-nemotron-3-super": "nemotron-3-super",
    
    # Qwen model names
    "qwen3-235b": "nemotron-3-super",
    "qwen3-30b": "nemotron-3-super",
    "qwen-plus": "nemotron-3-super",
    "qwen-turbo": "nemotron-3-super",
    
    # Generic aliases
    "default": "nemotron-3-super",
    "llm": "nemotron-3-super",
    "ai": "nemotron-3-super",
}


class ModelAliasMapper:
    """Maps incoming model names to vLLM served model names."""
    
    def __init__(self, served_model_names: list[str], primary_model: str):
        """
        Initialize the mapper.
        
        Args:
            served_model_names: List of model names vLLM is serving
            primary_model: The primary model ID from config
        """
        self.served_model_names = set(served_model_names)
        self.primary_model = primary_model
        self.alias_map = {}
        
        # Build alias map from static aliases
        for alias, target in MODEL_ALIASES.items():
            if target == primary_model or target in self.served_model_names:
                self.alias_map[alias.lower()] = target
        
        # Add served model names as aliases (identity mapping)
        for name in self.served_model_names:
            self.alias_map[name.lower()] = name
            self.alias_map[name] = name
        
        logger.info(f"ModelAliasMapper initialized with {len(self.alias_map)} aliases")
        logger.debug(f"Served model names: {self.served_model_names}")
    
    def resolve(self, model_name: str) -> str:
        """
        Resolve an incoming model name to a vLLM served model name.
        
        Args:
            model_name: The model name from the client request
            
        Returns:
            The vLLM served model name to use
        """
        if not model_name:
            return self.primary_model
        
        # Exact match
        if model_name in self.alias_map:
            return self.alias_map[model_name]
        
        # Case-insensitive match
        lower_name = model_name.lower()
        if lower_name in self.alias_map:
            return self.alias_map[lower_name]
        
        # If the model name is already a served model name, use it directly
        if model_name in self.served_model_names:
            return model_name
        
        # Fallback: return primary model
        logger.warning(f"Unknown model '{model_name}', falling back to '{self.primary_model}'")
        return self.primary_model
    
    def get_all_served_names(self) -> list[str]:
        """Get all model names that vLLM is serving."""
        return list(self.served_model_names)
