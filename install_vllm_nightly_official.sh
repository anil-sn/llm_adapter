#!/bin/bash
# Install vLLM nightly/official wheels from official wheels repository
# Source: https://docs.vllm.ai/en/latest/contributing/ci/nightly_builds/
# Includes PR #55063 K2-Horizon support merged Sept 3, 2026
#
# Usage: ./install_vllm_nightly_official.sh [main]
#   main  : install the official wheels matching the `main` branch (default)

set -e

BRANCH="${1:-main}"

echo "========================================="
echo "vLLM Nightly Installation (Official)"
echo "========================================="
echo "Target branch/URL: $BRANCH"
echo

# Show current version
echo "Current vLLM version:"
uv pip show vllm | grep Version || echo "Not installed"

# Check CUDA version
echo
echo "Checking CUDA version..."
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $5}' | cut -d',' -f1)
    echo "CUDA version: $CUDA_VERSION"
else
    echo "nvcc not found, using default variant"
    CUDA_VERSION="unknown"
fi

echo
echo "Installing vLLM from official wheels..."
echo "URL: https://wheels.vllm.ai/nightly"
echo

# Uninstall current version
echo "Uninstalling current vLLM..."
uv pip uninstall -y vllm || true

# Install from nightly wheels (uv auto-detects CUDA variant)
echo "Installing vLLM..."
uv pip install -U vllm --extra-index-url https://wheels.vllm.ai/nightly

echo
echo "========================================="
echo "Installation complete!"
echo "========================================="
uv pip show vllm

echo
echo "Next steps:"
echo "1. Update config parsers to k2_horizon (native support available)"
echo "2. Test: LLM_CONFIG=config/config-k2-horizon-mova-36b.yaml uv run python scripts/setup/llm_manager.py start"
