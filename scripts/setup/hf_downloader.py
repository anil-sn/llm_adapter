#!/usr/bin/env python3
"""
Nemo-Orchestrator: High-Performance Hugging Face Downloader
Uses hf-transfer for maximum throughput on large LLM models.
"""

import os
import sys
import yaml
import shutil
import argparse
from pathlib import Path
from huggingface_hub import snapshot_download

# Project Constants
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yaml"

def load_config():
    if not CONFIG_FILE.exists():
        print(f"Error: {CONFIG_FILE} not found.")
        sys.exit(1)
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)

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
    # Enable hf-transfer for parallel multi-threaded downloading
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
    
    print(f"--- Starting Download: {model_id} ---")
    print(f"Engine: hf-transfer (Multi-threaded)")
    
    try:
        path = snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            token=token,
            max_workers=16, # Optimized for high-bandwidth connections
            resume_download=True,
            # Ignore files that aren't needed for vLLM/SGLang if necessary
            ignore_patterns=["*.msgpack", "*.h5", "*.ot", "onnx/*"],
        )
        print(f"\nSuccess! Model stored at: {path}")
        return path
    except Exception as e:
        print(f"\nError downloading model: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="High-Speed HF Downloader")
    parser.add_argument("--model", help="Hugging Face model ID (overrides config.yaml)")
    parser.add_argument("--token", help="HF Access Token (or set HF_TOKEN env var)")
    parser.add_argument("--path", help="Local download path (overrides config.yaml)")
    parser.add_argument("--force", action="store_true", help="Skip disk space check")

    args = parser.parse_args()
    config = load_config()

    # Priority: CLI Arg > Config YAML
    model_id = args.model or config["model"]["id"]
    local_path = args.path or config["model"].get("path")
    token = args.token or os.environ.get("HF_TOKEN")

    # Safety check
    download_root = local_path if local_path else os.path.expanduser("~/.cache/huggingface")
    if not args.force:
        check_disk_space(download_root)

    download_model(model_id, local_dir=local_path, token=token)

if __name__ == "__main__":
    main()
