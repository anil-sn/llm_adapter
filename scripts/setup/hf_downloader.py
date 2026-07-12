#!/usr/bin/env python3
"""
LLM Orchestrator: High-Performance Hugging Face Downloader

Uses hf-transfer for maximum throughput on large LLM models.

Author: Anil Srirangapatna Nagesh
Version: 1.0
Created: 2026-04-27
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# Enable hf-transfer for parallel multi-threaded downloading BEFORE importing huggingface_hub
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

from huggingface_hub import snapshot_download

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from llm_adapter.utils.config_loader import load_config, ConfigError

def get_config():
    """Load configuration using the config loader."""
    try:
        return load_config(project_root=PROJECT_ROOT, validate=False)
    except ConfigError as e:
        print(f"Error loading config: {e}")
        print("\nTip: Set LLM_CONFIG environment variable to specify model config:")
        print("  LLM_CONFIG=config/config-qwen.yaml python3 scripts/setup/hf_downloader.py")
        sys.exit(1)

def check_disk_space(path, required_gb=100):
    """Ensure there's enough space before starting a 70GB+ download."""
    stat = shutil.disk_usage(path)
    free_gb = stat.free / (1024**3)
    if free_gb < required_gb:
        print(f"Warning: Only {free_gb:.1f}GB free. Model may require ~{required_gb}GB.")
        return False
    return True

def download_model(model_id, local_dir=None, token=None):
    """
    Downloads the model using hf-transfer for maximum speed.
    """
    print(f"--- Starting Download ---")
    print(f"Model: {model_id}")
    print(f"Engine: hf-transfer (Multi-threaded, 16 workers)")
    print(f"Resume: Enabled (safe to interrupt and restart)")

    # Estimate size
    size_estimates = {
        "Qwen/Qwen3.5-122B-A10B": "~200GB",
        "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8": "~70GB",
    }
    estimated_size = size_estimates.get(model_id, "Large")
    print(f"Estimated Size: {estimated_size}")
    print(f"\nThis may take 30-60 minutes depending on network speed...")
    print(f"Download location: {local_dir or '~/.cache/huggingface/hub'}")
    print()

    try:
        path = snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            token=token,
            max_workers=16,  # Optimized for high-bandwidth connections
            resume_download=True,
            # Ignore files that aren't needed for vLLM
            ignore_patterns=["*.msgpack", "*.h5", "*.ot", "onnx/*"],
        )
        print(f"\n{'='*70}")
        print(f"✓ Success! Model downloaded to: {path}")
        print(f"{'='*70}\n")
        print("You can now start the model with:")
        print(f"  LLM_CONFIG=config/config-qwen.yaml python3 scripts/setup/llm_manager.py start")
        print()
        return path
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"✗ Error downloading model: {e}")
        print(f"{'='*70}\n")

        if "401" in str(e) or "403" in str(e):
            print("Authentication error. Try setting HF_TOKEN:")
            print("  export HF_TOKEN=hf_your_token_here")
            print("  python3 scripts/setup/hf_downloader.py --model \"Qwen/Qwen3.5-122B-A10B\"")
        elif "LocalEntryNotFoundError" in str(type(e)):
            print("Model not found locally. Download may have been interrupted.")
            print("Resume with the same command - downloads will continue from where they stopped.")

        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="High-Speed HF Model Downloader for LLM Orchestrator",
        epilog="""
Examples:
  # Download model from current config (uses LLM_CONFIG env var):
  LLM_CONFIG=config/config-qwen.yaml python3 scripts/setup/hf_downloader.py

  # Download specific model (override config):
  python3 scripts/setup/hf_downloader.py --model "Qwen/Qwen3.5-122B-A10B"

  # Download with HF token:
  HF_TOKEN=hf_xxx python3 scripts/setup/hf_downloader.py --model "Qwen/Qwen3.5-122B-A10B"
        """
    )
    parser.add_argument("--model", help="Hugging Face model ID (overrides config)")
    parser.add_argument("--token", help="HF Access Token (or set HF_TOKEN env var)")
    parser.add_argument("--path", help="Local download path (default: ~/.cache/huggingface)")
    parser.add_argument("--force", action="store_true", help="Skip disk space check")

    args = parser.parse_args()
    config = get_config()

    # Priority: CLI Arg > Config
    model_id = args.model or config["model"]["id"]
    local_path = args.path or config["model"].get("path")
    token = args.token or os.environ.get("HF_TOKEN")

    print(f"\n{'='*70}")
    print("LLM Orchestrator - Model Downloader")
    print(f"{'='*70}")
    print(f"Model: {model_id}")
    if os.environ.get("LLM_CONFIG"):
        print(f"Config: {os.environ.get('LLM_CONFIG')}")
    print(f"{'='*70}\n")

    # Safety check
    download_root = local_path if local_path else os.path.expanduser("~/.cache/huggingface")
    if not args.force:
        check_disk_space(download_root, required_gb=200)  # Qwen is ~200GB

    download_model(model_id, local_dir=local_path, token=token)

if __name__ == "__main__":
    main()
