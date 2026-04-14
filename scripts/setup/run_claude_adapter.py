#!/usr/bin/env python3
"""
Run claude-adapter-py with Nemotron backend
Uses the production-ready claude-adapter-py implementation
"""

import sys
import asyncio
from pathlib import Path

# Add claude-adapter-py to path
sys.path.insert(0, str(Path.home() / "coding/claude-adapter-py/src"))

from claude_adapter.models.config import AdapterConfig, ModelConfig
from claude_adapter.server import run_server


async def main():
    """Run adapter with custom Nemotron configuration"""

    # Configuration for Nemotron backend
    config = AdapterConfig(
        provider="custom",
        base_url="http://127.0.0.1:8000/v1",  # Your vLLM endpoint
        api_key="dummy-key",  # vLLM doesn't require auth
        models=ModelConfig(
            # Map all Claude model tiers to Nemotron
            opus="nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8",
            sonnet="nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8",
            haiku="nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8",
        ),
        tool_format="native",  # vLLM supports native tool calling
        port=3080,  # Different from your gateway (8888)
        max_context_window=32768,
    )

    print("=" * 70)
    print("  Claude Adapter for Nemotron-3 Super 120B")
    print("=" * 70)
    print(f"Backend: {config.base_url}")
    print(f"Model: {config.models.haiku}")
    print(f"Tool Format: {config.tool_format}")
    print(f"Listening: http://0.0.0.0:{config.port}")
    print(f"Max Context: {config.max_context_window} tokens")
    print("=" * 70)
    print()
    print("Configure Claude Code CLI to use:")
    print(f"  URL: http://localhost:{config.port}")
    print(f"  API Key: {config.api_key}")
    print(f"  Model: claude-haiku-4-5-20251001")
    print("=" * 70)
    print()

    await run_server(config, port=config.port)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        sys.exit(0)
