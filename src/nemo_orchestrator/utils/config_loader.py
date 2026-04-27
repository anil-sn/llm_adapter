"""
Configuration Loader for LLM Orchestrator

Implements a layered configuration system with deep merging:
1. Base config (config/config.yaml) - Hardware, cluster, common settings
2. Adapter config (config/config-adapter.yaml) - Adapter routing and settings
3. Model config (LLM_CONFIG env var) - Model-specific overrides

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import yaml


# Configure logging
logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Base exception for configuration errors."""
    pass


class ConfigFileNotFoundError(ConfigError):
    """Raised when a required config file is not found."""
    pass


class ConfigValidationError(ConfigError):
    """Raised when config validation fails."""
    pass


class ConfigMergeError(ConfigError):
    """Raised when config merging fails."""
    pass


def setup_logging(level: str = "INFO") -> None:
    """
    Setup logging for config loader.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries with override precedence.

    Recursively merges nested dictionaries. Non-dict values in override
    completely replace values in base.

    Args:
        base: Base dictionary
        override: Override dictionary (takes precedence)

    Returns:
        Merged dictionary (new dict, doesn't modify inputs)

    Raises:
        ConfigMergeError: If merge operation fails

    Examples:
        >>> base = {"a": {"b": 1, "c": 2}, "d": 3}
        >>> override = {"a": {"b": 10}, "e": 4}
        >>> deep_merge(base, override)
        {'a': {'b': 10, 'c': 2}, 'd': 3, 'e': 4}
    """
    if not isinstance(base, dict) or not isinstance(override, dict):
        raise ConfigMergeError(
            f"Cannot merge non-dict types: base={type(base)}, override={type(override)}"
        )

    try:
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = deep_merge(result[key], value)
            else:
                # Override value (or add new key)
                result[key] = value

        return result

    except Exception as e:
        raise ConfigMergeError(f"Failed to merge configs: {e}") from e


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """
    Load and parse a YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed YAML content as dictionary

    Raises:
        ConfigFileNotFoundError: If file doesn't exist
        ConfigValidationError: If YAML is invalid

    Examples:
        >>> config = load_yaml_file(Path("config/config.yaml"))
        >>> assert isinstance(config, dict)
    """
    if not file_path.exists():
        raise ConfigFileNotFoundError(
            f"Config file not found: {file_path}\n"
            f"Current directory: {Path.cwd()}\n"
            f"Searched path: {file_path.absolute()}"
        )

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)

        # Handle empty files
        if content is None:
            logger.warning(f"Config file is empty: {file_path}")
            return {}

        if not isinstance(content, dict):
            raise ConfigValidationError(
                f"Config file must contain a YAML dictionary, got {type(content)}: {file_path}"
            )

        logger.debug(f"Successfully loaded config: {file_path} ({len(content)} top-level keys)")
        return content

    except yaml.YAMLError as e:
        raise ConfigValidationError(
            f"Invalid YAML in {file_path}:\n{e}"
        ) from e
    except Exception as e:
        raise ConfigError(
            f"Failed to load config {file_path}: {e}"
        ) from e


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """
    Find project root by searching for config/ directory.

    Walks up from start_path until finding a directory with config/ subdirectory,
    or reaches filesystem root.

    Args:
        start_path: Directory to start search from (defaults to cwd)

    Returns:
        Project root path

    Raises:
        ConfigError: If project root cannot be found

    Examples:
        >>> root = find_project_root()
        >>> assert (root / "config").is_dir()
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.absolute()
    max_depth = 10  # Prevent infinite loops

    for _ in range(max_depth):
        if (current / "config").is_dir():
            logger.debug(f"Found project root: {current}")
            return current

        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    raise ConfigError(
        f"Could not find project root (directory with config/ subdirectory)\n"
        f"Searched from: {start_path}\n"
        f"Current directory: {Path.cwd()}\n"
        f"Hint: Run from project root or set PROJECT_ROOT environment variable"
    )


def validate_base_config(config: Dict[str, Any]) -> None:
    """
    Validate base configuration has required fields.

    Args:
        config: Configuration dictionary

    Raises:
        ConfigValidationError: If validation fails
    """
    required_sections = [
        "hardware",
        "inference",
        "cluster",
        "replicas",
    ]

    missing = [s for s in required_sections if s not in config]
    if missing:
        raise ConfigValidationError(
            f"Base config missing required sections: {missing}\n"
            f"Required: {required_sections}\n"
            f"Found: {list(config.keys())}"
        )

    # Validate hardware section
    hardware = config.get("hardware", {})
    if "tensor_parallel_size" not in hardware:
        raise ConfigValidationError(
            "hardware.tensor_parallel_size is required"
        )

    tp_size = hardware["tensor_parallel_size"]
    if not isinstance(tp_size, int) or tp_size < 1:
        raise ConfigValidationError(
            f"hardware.tensor_parallel_size must be positive integer, got: {tp_size}"
        )

    # Validate gpu_memory_utilization if present
    if "gpu_memory_utilization" in hardware:
        gpu_mem = hardware["gpu_memory_utilization"]
        if not isinstance(gpu_mem, (int, float)) or not (0.0 < gpu_mem <= 1.0):
            raise ConfigValidationError(
                f"hardware.gpu_memory_utilization must be in range (0.0, 1.0], got: {gpu_mem}"
            )

    logger.debug("Base config validation passed")


def validate_model_config(config: Dict[str, Any]) -> None:
    """
    Validate model configuration has required fields.

    Args:
        config: Configuration dictionary

    Raises:
        ConfigValidationError: If validation fails
    """
    if "model" not in config:
        raise ConfigValidationError("Model config must have 'model' section")

    model = config["model"]
    required_fields = ["id", "served_model_name"]

    missing = [f for f in required_fields if f not in model]
    if missing:
        raise ConfigValidationError(
            f"model section missing required fields: {missing}\n"
            f"Required: {required_fields}\n"
            f"Found: {list(model.keys())}"
        )

    logger.debug(f"Model config validation passed: {model.get('id')}")


def load_config(
    project_root: Optional[Path] = None,
    validate: bool = True,
    required_files: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Load and merge all configuration files.

    Loading order (each step deep merges into previous):
    1. config/config.yaml (base) - REQUIRED
    2. config/config-adapter.yaml (adapters) - REQUIRED
    3. LLM_CONFIG env var file (model-specific) - OPTIONAL

    Args:
        project_root: Project root directory (auto-detected if None)
        validate: Whether to validate config structure
        required_files: List of required config files (default: base + adapter)

    Returns:
        Merged configuration dictionary

    Raises:
        ConfigFileNotFoundError: If required config file missing
        ConfigValidationError: If config validation fails
        ConfigError: If any other config error occurs

    Environment Variables:
        LLM_CONFIG: Path to model-specific config file (relative or absolute)
        PROJECT_ROOT: Override project root directory (optional)

    Examples:
        >>> config = load_config()
        >>> assert "model" in config
        >>> assert "hardware" in config
    """
    # Setup logging from environment
    log_level = os.environ.get("CONFIG_LOG_LEVEL", "INFO")
    setup_logging(log_level)

    logger.info("=" * 80)
    logger.info("LLM Orchestrator - Configuration Loader v2.0")
    logger.info("=" * 80)

    # Determine project root
    if project_root is None:
        project_root_env = os.environ.get("PROJECT_ROOT")
        if project_root_env:
            project_root = Path(project_root_env)
            logger.info(f"Using PROJECT_ROOT from environment: {project_root}")
        else:
            project_root = find_project_root()

    project_root = Path(project_root).absolute()
    config_dir = project_root / "config"

    if not config_dir.is_dir():
        raise ConfigError(
            f"Config directory not found: {config_dir}\n"
            f"Project root: {project_root}\n"
            f"Hint: Ensure you're running from the correct directory"
        )

    logger.info(f"Project root: {project_root}")
    logger.info(f"Config directory: {config_dir}")

    # Define required config files
    if required_files is None:
        required_files = ["config.yaml", "config-adapter.yaml"]

    # Step 1: Load base config (REQUIRED)
    base_config_path = config_dir / "config.yaml"
    logger.info(f"\n[1/3] Loading base config: {base_config_path.name}")

    try:
        config = load_yaml_file(base_config_path)
        if validate:
            validate_base_config(config)
        logger.info(f"✓ Base config loaded ({len(config)} sections)")
    except Exception as e:
        logger.error(f"✗ Failed to load base config: {e}")
        raise

    # Step 2: Load adapter config (REQUIRED)
    adapter_config_path = config_dir / "config-adapter.yaml"
    logger.info(f"\n[2/3] Loading adapter config: {adapter_config_path.name}")

    try:
        adapter_config = load_yaml_file(adapter_config_path)
        config = deep_merge(config, adapter_config)
        logger.info(f"✓ Adapter config loaded and merged")
    except Exception as e:
        logger.error(f"✗ Failed to load adapter config: {e}")
        raise

    # Step 3: Load model-specific config (OPTIONAL)
    llm_config_env = os.environ.get("LLM_CONFIG")

    logger.info(f"\n[3/3] Loading model-specific config")

    if llm_config_env:
        model_config_path = Path(llm_config_env)

        # Try multiple resolution strategies
        search_paths = []

        if not model_config_path.is_absolute():
            # Strategy 1: Relative to project root
            search_paths.append(project_root / llm_config_env)
            # Strategy 2: Relative to config directory
            search_paths.append(config_dir / llm_config_env)
            # Strategy 3: Relative to current directory
            search_paths.append(Path.cwd() / llm_config_env)
        else:
            # Absolute path
            search_paths.append(model_config_path)

        # Find first existing path
        model_config_path = None
        for path in search_paths:
            if path.exists():
                model_config_path = path
                break

        if model_config_path:
            try:
                logger.info(f"LLM_CONFIG: {llm_config_env}")
                logger.info(f"Resolved to: {model_config_path}")

                model_config = load_yaml_file(model_config_path)
                config = deep_merge(config, model_config)

                if validate:
                    validate_model_config(config)

                logger.info(f"✓ Model config loaded and merged: {model_config_path.name}")

            except Exception as e:
                logger.error(f"✗ Failed to load model config: {e}")
                raise
        else:
            logger.warning(f"⚠ LLM_CONFIG file not found: {llm_config_env}")
            logger.warning(f"  Searched paths:")
            for path in search_paths:
                logger.warning(f"    - {path}")
            logger.warning(f"  Continuing with base + adapter config only")
    else:
        logger.warning(f"⚠ LLM_CONFIG environment variable not set")
        logger.warning(f"  Using base + adapter config only")
        logger.warning(f"  Hint: Set LLM_CONFIG=config/config-qwen.yaml for model-specific config")

    # Log final configuration summary
    logger.info("\n" + "=" * 80)
    logger.info("Configuration Summary")
    logger.info("=" * 80)

    if "model" in config:
        logger.info(f"Model ID: {config['model'].get('id', 'N/A')}")
        logger.info(f"Served Name: {config['model'].get('served_model_name', 'N/A')}")
    else:
        logger.info("Model: Not configured")

    if "inference" in config:
        max_len = config['inference'].get('max_model_len', 'N/A')
        if isinstance(max_len, int):
            logger.info(f"Context Length: {max_len:,}")
        else:
            logger.info(f"Context Length: {max_len}")
        logger.info(f"Thinking Enabled: {config['inference'].get('enable_thinking', 'N/A')}")

    if "hardware" in config:
        logger.info(f"Tensor Parallel Size: {config['hardware'].get('tensor_parallel_size', 'N/A')}")
        logger.info(f"GPU Memory Util: {config['hardware'].get('gpu_memory_utilization', 'N/A')}")

    if "model_rules" in config:
        logger.info(f"Adapter Rules: {len(config['model_rules'])} patterns")

    logger.info("=" * 80)

    return config


def get_config(
    project_root: Optional[Path] = None,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to load configuration.

    This is the main entry point for loading configuration.

    Args:
        project_root: Project root directory (auto-detected if None)
        validate: Whether to validate config structure

    Returns:
        Merged configuration dictionary

    Examples:
        >>> from nemo_orchestrator.utils.config_loader import get_config
        >>> config = get_config()
        >>> model_id = config["model"]["id"]
    """
    return load_config(project_root=project_root, validate=validate)


# CLI for testing
if __name__ == "__main__":
    import json
    import argparse

    parser = argparse.ArgumentParser(description="Test LLM Orchestrator config loader")
    parser.add_argument("--validate", action="store_true", help="Validate config structure")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--json", action="store_true", help="Output config as JSON")
    args = parser.parse_args()

    # Set log level
    if args.verbose:
        os.environ["CONFIG_LOG_LEVEL"] = "DEBUG"

    try:
        config = load_config(validate=args.validate)

        if args.json:
            print("\n" + json.dumps(config, indent=2))
        else:
            print("\n✓ Configuration loaded successfully!")

    except ConfigError as e:
        print(f"\n✗ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
