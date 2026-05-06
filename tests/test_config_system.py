"""
Comprehensive Test Suite for Configuration System

Tests layered config loading, merging, validation, and error handling.

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import os
import sys
import json
import tempfile
from pathlib import Path
import pytest

# Add src to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from llm_adapter.utils.config_loader import (
    load_config,
    deep_merge,
    ConfigError,
    ConfigFileNotFoundError,
    ConfigValidationError,
    load_yaml_file
)
from llm_adapter.utils.config_schema import validate_config, Config


class TestDeepMerge:
    """Test deep dictionary merging."""

    def test_simple_merge(self):
        """Test simple dictionary merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """Test nested dictionary merge."""
        base = {
            "hardware": {"gpu_mem": 0.85, "tp_size": 4},
            "inference": {"max_len": 192000}
        }
        override = {
            "hardware": {"gpu_mem": 0.80},
            "inference": {"max_len": 262144, "kv_cache": "fp8"}
        }
        result = deep_merge(base, override)

        assert result["hardware"]["gpu_mem"] == 0.80
        assert result["hardware"]["tp_size"] == 4
        assert result["inference"]["max_len"] == 262144
        assert result["inference"]["kv_cache"] == "fp8"

    def test_list_override(self):
        """Test that lists are replaced, not merged."""
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = deep_merge(base, override)

        assert result["items"] == [4, 5]

    def test_non_dict_types(self):
        """Test error handling for non-dict types."""
        with pytest.raises(Exception):
            deep_merge("not a dict", {"a": 1})


class TestConfigLoading:
    """Test configuration loading and merging."""

    def test_load_base_config(self):
        """Test loading base configuration."""
        config = load_config(project_root=PROJECT_ROOT, validate=False)

        assert "hardware" in config
        assert "inference" in config
        assert "cluster" in config
        assert "replicas" in config

    def test_load_with_env_var(self):
        """Test loading with LLM_CONFIG environment variable."""
        # Save original
        original = os.environ.get("LLM_CONFIG")

        try:
            # Test with Qwen config
            os.environ["LLM_CONFIG"] = "config/config-qwen.yaml"
            config = load_config(project_root=PROJECT_ROOT, validate=False)

            assert config["model"]["id"] == "Qwen/Qwen3.5-122B-A10B"
            assert config["model"]["served_model_name"] == "qwen-3.5-122b"

        finally:
            # Restore original
            if original:
                os.environ["LLM_CONFIG"] = original
            else:
                os.environ.pop("LLM_CONFIG", None)

    def test_config_merging(self):
        """Test that configs merge correctly."""
        original = os.environ.get("LLM_CONFIG")

        try:
            os.environ["LLM_CONFIG"] = "config/config-qwen.yaml"
            config = load_config(project_root=PROJECT_ROOT, validate=False)

            # Should have base settings
            assert config["hardware"]["tensor_parallel_size"] == 4

            # Should have Qwen overrides
            assert config["hardware"]["gpu_memory_utilization"] == 0.80

            # Should have adapter rules
            assert "model_rules" in config

        finally:
            if original:
                os.environ["LLM_CONFIG"] = original
            else:
                os.environ.pop("LLM_CONFIG", None)


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_valid_config(self):
        """Test validation of valid configuration."""
        config = load_config(project_root=PROJECT_ROOT, validate=True)
        # Should not raise exception
        assert config is not None

    def test_validate_with_schema(self):
        """Test Pydantic schema validation."""
        original = os.environ.get("LLM_CONFIG")

        try:
            os.environ["LLM_CONFIG"] = "config/config-qwen.yaml"
            config_dict = load_config(project_root=PROJECT_ROOT, validate=False)

            # Validate with Pydantic
            validated = validate_config(config_dict)

            assert isinstance(validated, Config)
            assert validated.hardware.tensor_parallel_size == 4
            assert validated.inference.max_model_len == 262144

        finally:
            if original:
                os.environ["LLM_CONFIG"] = original
            else:
                os.environ.pop("LLM_CONFIG", None)

    def test_invalid_gpu_memory(self):
        """Test validation of invalid GPU memory value."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
model:
  id: "test/model"
  served_model_name: "test"
hardware:
  tensor_parallel_size: 4
  gpu_memory_utilization: 1.5  # Invalid: > 1.0
inference:
  max_model_len: 100000
cluster:
  gateway_port: 8888
replicas:
  count: 1
  gpu_groups: ["0,1,2,3"]
""")
            temp_file = f.name

        try:
            config_dict = load_yaml_file(Path(temp_file))
            with pytest.raises(ValueError):
                validate_config(config_dict)
        finally:
            os.unlink(temp_file)


class TestErrorHandling:
    """Test error handling and messages."""

    def test_missing_config_file(self):
        """Test error when config file is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ConfigFileNotFoundError):
                load_config(project_root=Path(tmpdir), validate=False)

    def test_invalid_yaml(self):
        """Test error when YAML is invalid."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("{ invalid yaml [")
            temp_file = f.name

        try:
            with pytest.raises(ConfigValidationError):
                load_yaml_file(Path(temp_file))
        finally:
            os.unlink(temp_file)

    def test_helpful_error_messages(self):
        """Test that error messages are helpful."""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                load_config(project_root=Path(tmpdir), validate=False)
            except ConfigFileNotFoundError as e:
                error_msg = str(e)
                # Should mention the missing file
                assert "config.yaml" in error_msg
                # Should mention current directory
                assert tmpdir in error_msg


class TestModelConfigs:
    """Test model-specific configurations."""

    def test_qwen_config_structure(self):
        """Test Qwen config has correct structure."""
        original = os.environ.get("LLM_CONFIG")

        try:
            os.environ["LLM_CONFIG"] = "config/config-qwen.yaml"
            config = load_config(project_root=PROJECT_ROOT, validate=False)

            # Model settings
            assert config["model"]["id"] == "Qwen/Qwen3.5-122B-A10B"
            assert config["model"]["trust_remote_code"] is True

            # Context length
            assert config["inference"]["max_model_len"] == 262144

            # Thinking mode default
            assert config["inference"]["enable_thinking"] is False

        finally:
            if original:
                os.environ["LLM_CONFIG"] = original
            else:
                os.environ.pop("LLM_CONFIG", None)

    def test_nemotron_config_structure(self):
        """Test Nemotron config has correct structure."""
        original = os.environ.get("LLM_CONFIG")

        try:
            os.environ["LLM_CONFIG"] = "config/config-nemotron.yaml"
            config = load_config(project_root=PROJECT_ROOT, validate=False)

            # Model settings
            assert "NVIDIA-Nemotron" in config["model"]["id"]
            assert config["model"]["served_model_name"] == "nemotron-3-super"

            # Context length
            assert config["inference"]["max_model_len"] == 196608

            # Reasoning parser
            assert config["inference"]["reasoning_parser"] == "super_v3"

        finally:
            if original:
                os.environ["LLM_CONFIG"] = original
            else:
                os.environ.pop("LLM_CONFIG", None)


class TestAdapterConfig:
    """Test adapter configuration."""

    def test_adapter_rules_loaded(self):
        """Test that adapter rules are loaded."""
        config = load_config(project_root=PROJECT_ROOT, validate=False)

        assert "model_rules" in config
        assert len(config["model_rules"]) > 0

        # Check rule structure
        for rule in config["model_rules"]:
            assert "pattern" in rule
            assert "adapter" in rule

    def test_qwen_adapter_settings(self):
        """Test Qwen adapter settings are loaded."""
        config = load_config(project_root=PROJECT_ROOT, validate=False)

        assert "qwen_adapter" in config

        if "sampling_profiles" in config["qwen_adapter"]:
            profiles = config["qwen_adapter"]["sampling_profiles"]
            assert "thinking_general" in profiles
            assert "thinking_coding" in profiles
            assert "instruct_general" in profiles


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
