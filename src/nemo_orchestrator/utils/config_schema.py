"""
Configuration Schema for LLM Orchestrator

Pydantic models for validating configuration structure and values.
Provides strong typing, validation, and helpful error messages.

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class AttentionBackend(str, Enum):
    """Supported attention backends."""
    TRITON_ATTN = "TRITON_ATTN"
    FLASH_ATTN = "FLASH_ATTN"
    XFORMERS = "XFORMERS"


class RoutingStrategy(str, Enum):
    """Supported routing strategies."""
    PREFIX_HASH = "prefix_hash"
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"


class ReasoningParser(str, Enum):
    """Supported reasoning parsers."""
    SUPER_V3 = "super_v3"
    QWEN3 = "qwen3"
    NEMOTRON_V3 = "nemotron_v3"


# ============================================================================
# Cluster Configuration
# ============================================================================

class SpilloverConfig(BaseModel):
    """Spillover configuration for load balancing."""
    enabled: bool = Field(default=True, description="Enable spillover")
    queue_threshold: int = Field(default=4, ge=1, description="Queue threshold for spillover")


class ClusterConfig(BaseModel):
    """Cluster-level configuration."""
    gateway_port: int = Field(default=8888, ge=1024, le=65535, description="Gateway port")
    routing_strategy: RoutingStrategy = Field(
        default=RoutingStrategy.PREFIX_HASH,
        description="Request routing strategy"
    )
    spillover: SpilloverConfig = Field(default_factory=SpilloverConfig)


# ============================================================================
# Replica Configuration
# ============================================================================

class ReplicaConfig(BaseModel):
    """Replica configuration for vLLM instances."""
    count: int = Field(default=1, ge=1, description="Number of replicas")
    base_port: int = Field(default=8000, ge=1024, le=65535, description="Base port for replicas")
    gpu_groups: List[str] = Field(
        default_factory=lambda: ["0,1,2,3"],
        description="GPU groups for each replica"
    )
    core_ranges: List[str] = Field(
        default_factory=lambda: ["0-55,56-111"],
        description="CPU core ranges for each replica"
    )


# ============================================================================
# Hardware Configuration
# ============================================================================

class HardwareConfig(BaseModel):
    """Hardware configuration for model deployment."""
    tensor_parallel_size: int = Field(
        ...,  # Required
        ge=1,
        le=8,
        description="Number of GPUs for tensor parallelism"
    )
    gpu_memory_utilization: float = Field(
        default=0.85,
        gt=0.0,
        le=1.0,
        description="Fraction of GPU memory to use (0.0, 1.0]"
    )
    device: str = Field(default="cuda", description="Device type (cuda/cpu)")
    dtype: str = Field(default="auto", description="Data type (auto/float16/bfloat16)")
    attention_backend: AttentionBackend = Field(
        default=AttentionBackend.TRITON_ATTN,
        description="Attention implementation backend"
    )
    disable_custom_all_reduce: bool = Field(
        default=True,
        description="Disable custom all-reduce (required for PCIe)"
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for vLLM"
    )

    @field_validator("gpu_memory_utilization")
    @classmethod
    def validate_gpu_memory(cls, v: float) -> float:
        """Validate GPU memory utilization is reasonable."""
        if v > 0.95:
            raise ValueError(
                f"gpu_memory_utilization={v} is too high (>0.95). "
                "Recommended: 0.75-0.85 for stability."
            )
        if v < 0.5:
            raise ValueError(
                f"gpu_memory_utilization={v} is too low (<0.5). "
                "This wastes GPU memory. Recommended: 0.75-0.85."
            )
        return v


# ============================================================================
# Model Configuration
# ============================================================================

class ModelConfig(BaseModel):
    """Model identity and tokenizer configuration."""
    id: str = Field(..., description="HuggingFace model ID")
    served_model_name: str = Field(..., description="Model name exposed via API")
    tokenizer_mode: str = Field(default="auto", description="Tokenizer mode (auto/slow/fast)")
    trust_remote_code: bool = Field(
        default=False,
        description="Trust remote code for model loading"
    )

    @field_validator("id")
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        """Validate model ID is not empty."""
        if not v or not v.strip():
            raise ValueError("model.id cannot be empty")
        return v.strip()


# ============================================================================
# Inference Configuration
# ============================================================================

class RoPEScalingConfig(BaseModel):
    """RoPE scaling configuration for extended context."""
    type: Literal["yarn", "linear", "dynamic"] = Field(..., description="RoPE scaling type")
    factor: float = Field(..., gt=1.0, le=8.0, description="Scaling factor")
    original_max_position_embeddings: int = Field(
        ...,
        gt=0,
        description="Original max position embeddings"
    )

    @field_validator("factor")
    @classmethod
    def validate_factor(cls, v: float) -> float:
        """Warn about aggressive scaling."""
        if v > 4.0:
            print(
                f"WARNING: RoPE scaling factor={v} is very aggressive (>4.0). "
                "This may impact quality. Recommended: 1.5-2.0 for YaRN."
            )
        return v


class InferenceConfig(BaseModel):
    """Inference engine configuration."""
    # Context and memory
    max_model_len: int = Field(
        ...,  # Required
        gt=0,
        le=2_000_000,
        description="Maximum context length in tokens"
    )
    kv_cache_dtype: Literal["auto", "fp8", "fp16", "bf16"] = Field(
        default="fp8",
        description="KV cache data type"
    )
    rope_scaling: Optional[RoPEScalingConfig] = Field(
        default=None,
        description="RoPE scaling for extended context"
    )

    # Batching and sequences
    max_num_seqs: int = Field(
        default=2,
        ge=1,
        le=256,
        description="Maximum number of sequences to batch"
    )
    max_num_batched_tokens: int = Field(
        default=16384,
        ge=1024,
        le=131072,
        description="Maximum tokens to batch"
    )
    enable_prefix_caching: bool = Field(
        default=True,
        description="Enable prefix caching for repeated prompts"
    )
    enable_chunked_prefill: bool = Field(
        default=True,
        description="Process long prompts in chunks"
    )

    # Reasoning and thinking
    enable_thinking: bool = Field(
        default=False,
        description="Enable thinking/reasoning mode"
    )
    reasoning_parser: Optional[ReasoningParser] = Field(
        default=None,
        description="Reasoning parser to use"
    )
    reasoning_parser_plugin: Optional[str] = Field(
        default=None,
        description="Path to custom reasoning parser plugin"
    )

    # Tool calling
    enable_auto_tool_choice: bool = Field(
        default=True,
        description="Enable automatic tool choice"
    )
    tool_call_parser: Optional[str] = Field(
        default=None,
        description="Tool call parser to use"
    )

    # Output settings
    default_max_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Default max tokens for completions"
    )
    max_output_tokens: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum output tokens"
    )

    @model_validator(mode='after')
    def validate_context_and_memory(self) -> 'InferenceConfig':
        """Validate context length is reasonable for hardware."""
        max_len = self.max_model_len

        # Warn about extreme context lengths
        if max_len > 500_000:
            print(
                f"WARNING: max_model_len={max_len:,} is very large (>500K). "
                "Ensure sufficient GPU memory. Monitor for OOM errors."
            )

        # Validate rope_scaling consistency
        if self.rope_scaling and max_len:
            original = self.rope_scaling.original_max_position_embeddings
            expected = int(original * self.rope_scaling.factor)
            tolerance = 0.1  # 10% tolerance

            if abs(max_len - expected) / expected > tolerance:
                print(
                    f"WARNING: max_model_len={max_len:,} doesn't match RoPE scaling.\n"
                    f"  Expected: ~{expected:,} ({original:,} * {self.rope_scaling.factor})\n"
                    f"  Consider adjusting max_model_len or RoPE factor."
                )

        return self


# ============================================================================
# Adapter Configuration
# ============================================================================

class ModelRule(BaseModel):
    """Model routing rule for adapter selection."""
    pattern: str = Field(..., description="Regex pattern to match model name")
    adapter: str = Field(..., description="Adapter to route to")


class SamplingProfile(BaseModel):
    """Sampling parameter profile."""
    description: Optional[str] = Field(None, description="Profile description")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: int = Field(default=20, ge=0, le=100)
    min_p: float = Field(default=0.0, ge=0.0, le=1.0)
    presence_penalty: float = Field(default=0.0, ge=0.0, le=2.0)
    repetition_penalty: float = Field(default=1.0, ge=1.0, le=2.0)


# ============================================================================
# Observability Configuration
# ============================================================================

class ObservabilityConfig(BaseModel):
    """Logging and metrics configuration."""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Prometheus metrics port"
    )


# ============================================================================
# Root Configuration Schema
# ============================================================================

class Config(BaseModel):
    """Root configuration schema for LLM Orchestrator."""

    # Core sections
    cluster: ClusterConfig
    replicas: ReplicaConfig
    hardware: HardwareConfig
    model: ModelConfig
    inference: InferenceConfig
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)

    # Adapter sections
    model_rules: List[ModelRule] = Field(default_factory=list)
    qwen_adapter: Optional[Dict[str, Any]] = Field(default=None)
    nemotron_adapter: Optional[Dict[str, Any]] = Field(default=None)
    claude_adapter: Optional[Dict[str, Any]] = Field(default=None)
    openai_adapter: Optional[Dict[str, Any]] = Field(default=None)

    @model_validator(mode='after')
    def validate_consistency(self) -> 'Config':
        """Cross-field validation."""

        # Validate GPU count matches GPU groups
        tp_size = self.hardware.tensor_parallel_size
        gpu_groups = self.replicas.gpu_groups

        if gpu_groups:
            first_group = gpu_groups[0]
            num_gpus = len(first_group.split(','))

            if num_gpus != tp_size:
                raise ValueError(
                    f"Mismatch: tensor_parallel_size={tp_size} but "
                    f"gpu_groups[0] has {num_gpus} GPUs: {first_group}\n"
                    f"These must match for correct deployment."
                )

        return self

    class Config:
        """Pydantic model configuration."""
        extra = "allow"  # Allow extra fields for forward compatibility
        validate_assignment = True
        use_enum_values = True


def validate_config(config_dict: Dict[str, Any]) -> Config:
    """
    Validate configuration dictionary against schema.

    Args:
        config_dict: Configuration dictionary to validate

    Returns:
        Validated Config object

    Raises:
        ValueError: If validation fails

    Examples:
        >>> from nemo_orchestrator.utils.config_loader import load_config
        >>> from nemo_orchestrator.utils.config_schema import validate_config
        >>> config_dict = load_config()
        >>> validated = validate_config(config_dict)
        >>> assert validated.hardware.tensor_parallel_size > 0
    """
    try:
        return Config(**config_dict)
    except Exception as e:
        raise ValueError(f"Config validation failed: {e}") from e


# CLI for testing
if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Add parent directory to path for imports
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from nemo_orchestrator.utils.config_loader import load_config

    print("=" * 80)
    print("Testing Configuration Schema Validation")
    print("=" * 80)

    try:
        # Load config
        config_dict = load_config(validate=False)  # Skip basic validation

        # Validate against schema
        print("\nValidating against Pydantic schema...")
        validated = validate_config(config_dict)

        print("✓ Configuration is valid!")
        print(f"\nModel: {validated.model.id}")
        print(f"Context: {validated.inference.max_model_len:,} tokens")
        print(f"GPUs: {validated.hardware.tensor_parallel_size}")
        print(f"Memory Util: {validated.hardware.gpu_memory_utilization:.2%}")

    except ValueError as e:
        print(f"\n✗ Validation Error:\n{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected Error:\n{e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
