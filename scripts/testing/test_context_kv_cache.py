#!/usr/bin/env python3
"""
Enhanced Context Length & KV Cache Test Suite
Tests maximum context length with progressive scaling and memory monitoring.

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import httpx
import json
import sys
import time
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
API_BASE = "http://10.172.249.149:8888"
DEFAULT_MODEL = "qwen-3.5-122b"  # Updated for Qwen

def estimate_tokens(text: str) -> int:
    """
    Token estimation matching adapter logic.

    Uses 3.5 chars/token to align with adapter's estimation.
    This ensures test predictions match gateway behavior.

    Note: Real tokenization varies (3-8 chars/token depending on content),
    but we use consistent estimation for predictable testing.
    """
    return int(len(text) / 3.5)

def generate_test_prompt(target_tokens: int) -> str:
    """
    Generate a prompt of approximately target_tokens length.
    Uses varied content to avoid degenerate cases.
    """
    # Create diverse content blocks
    blocks = [
        "The quick brown fox jumps over the lazy dog. ",
        "Machine learning models process natural language efficiently. ",
        "Context windows enable long-form reasoning and analysis. ",
        "Distributed systems scale horizontally across multiple nodes. ",
        "Data structures optimize memory access patterns for performance. "
    ]

    # Each block averages ~10 words × ~5 chars/word = ~50 chars
    # Using 3.5 chars/token estimate → ~14 tokens per block
    # To generate N tokens, we need: N chars = target_tokens × 3.5
    target_chars = int(target_tokens * 3.5)

    # Average chars per block
    avg_block_chars = sum(len(b) for b in blocks) // len(blocks)
    blocks_needed = max(1, target_chars // avg_block_chars)

    # Cycle through blocks to create varied content
    result = []
    for i in range(blocks_needed):
        result.append(blocks[i % len(blocks)])

    return "".join(result)

def test_context_length(
    client: httpx.Client,
    tokens: int,
    model: str,
    max_output: int = 100,
    timeout: float = 600.0
) -> Dict:
    """Test a specific context length"""
    print(f"\n{'='*70}")
    print(f"Testing {tokens:,} token context...")
    print(f"{'='*70}")

    prompt = generate_test_prompt(tokens)
    actual_chars = len(prompt)
    estimated_tokens = estimate_tokens(prompt)

    print(f"Prompt: {actual_chars:,} chars (~{estimated_tokens:,} tokens estimated)")

    # Test via OpenAI-compatible endpoint
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_output,
        "temperature": 0.7
    }

    try:
        start = time.time()
        response = client.post(
            f"{API_BASE}/v1/chat/completions",
            json=payload,
            timeout=timeout
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            # Calculate throughput
            if elapsed > 0 and input_tokens > 0:
                prefill_tps = input_tokens / elapsed
                decode_tps = output_tokens / elapsed if output_tokens > 0 else 0
            else:
                prefill_tps = decode_tps = 0

            print(f"✅ SUCCESS ({elapsed:.2f}s)")
            print(f"   Input tokens:     {input_tokens:,}")
            print(f"   Output tokens:    {output_tokens:,}")
            print(f"   Total tokens:     {total_tokens:,}")
            print(f"   Prefill speed:    {prefill_tps:,.1f} tok/s")
            if decode_tps > 0:
                print(f"   Decode speed:     {decode_tps:,.1f} tok/s")

            return {
                "success": True,
                "tokens": tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "elapsed": elapsed,
                "prefill_tps": prefill_tps,
                "decode_tps": decode_tps
            }
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get("error", {}).get("message", response.text[:200])
            print(f"❌ FAILED (HTTP {response.status_code})")
            print(f"   Error: {error_msg}")

            return {
                "success": False,
                "tokens": tokens,
                "error": error_msg,
                "status_code": response.status_code
            }

    except httpx.TimeoutException:
        print(f"⏱️  TIMEOUT (>{timeout}s)")
        return {"success": False, "tokens": tokens, "error": "timeout"}

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return {"success": False, "tokens": tokens, "error": str(e)}

def check_model_info(client: httpx.Client) -> Dict:
    """Check reported model info"""
    print("\n" + "="*70)
    print("Checking Model Configuration...")
    print("="*70)

    try:
        response = client.get(f"{API_BASE}/v1/models")
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            if models:
                model = models[0]
                max_model_len = model.get("max_model_len", 0)
                model_id = model.get("id", "unknown")

                print(f"Model ID:         {model_id}")
                print(f"Max context:      {max_model_len:,} tokens")
                print(f"Owner:            {model.get('owned_by', 'unknown')}")

                # Detect model type for better estimations
                is_qwen = "qwen" in model_id.lower()
                is_nemotron = "nemotron" in model_id.lower()

                return {
                    "max_model_len": max_model_len,
                    "model_id": model_id,
                    "is_qwen": is_qwen,
                    "is_nemotron": is_nemotron
                }

        print("❌ Failed to get model info")
        return {}

    except Exception as e:
        print(f"❌ Exception: {e}")
        return {}

def generate_test_sizes(max_context: int, aggressive: bool = False) -> List[int]:
    """
    Generate progressive test sizes up to max_context.

    Args:
        max_context: Maximum context length to test
        aggressive: If True, test closer to the limit

    Returns:
        List of token counts to test
    """
    if max_context <= 0:
        return []

    # Leave safety margin for overhead (adapter adds 5% + reserves)
    # Use 90% of max as absolute limit to avoid rejection
    safe_max = int(max_context * 0.90)

    # Base progressive sizes (percentages of safe_max)
    if aggressive:
        # More aggressive - go up to 90% of actual max
        percentages = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 1.0]
    else:
        # Conservative - stay well below limit
        percentages = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90]

    sizes = []
    for pct in percentages:
        size = int(safe_max * pct)
        # Round to nice numbers
        if size < 1000:
            size = (size // 100) * 100
        elif size < 10000:
            size = (size // 1000) * 1000
        else:
            size = (size // 10000) * 10000

        if size > 0:
            sizes.append(size)

    # Remove duplicates and sort
    sizes = sorted(list(set(sizes)))

    return sizes

def estimate_kv_cache_memory(
    tokens: int,
    num_seqs: int,
    num_layers: int,
    hidden_size: int,
    num_heads: int,
    tensor_parallel_size: int = 1,
    dtype: str = "fp8"
) -> Dict[str, float]:
    """
    Estimate KV cache memory usage with tensor parallelism.

    Args:
        tokens: Number of tokens in context
        num_seqs: Number of concurrent sequences
        num_layers: Number of transformer layers
        hidden_size: Hidden dimension size
        num_heads: Number of attention heads
        tensor_parallel_size: Number of GPUs for tensor parallelism
        dtype: Data type (fp8, fp16, fp32)

    Returns:
        Dictionary with memory estimates in GB
    """
    # Bytes per element
    dtype_bytes = {
        "fp8": 1,
        "fp16": 2,
        "fp32": 4
    }
    bytes_per_elem = dtype_bytes.get(dtype, 1)

    # KV cache formula (per GPU with tensor parallelism):
    # 2 (K+V) * num_layers * tokens * (hidden_size / TP) * bytes_per_elem
    # Note: hidden_size is sharded across TP GPUs
    hidden_per_gpu = hidden_size // tensor_parallel_size
    bytes_per_token_per_gpu = 2 * num_layers * hidden_per_gpu * bytes_per_elem

    # Total for all sequences on one GPU
    total_bytes_per_gpu = bytes_per_token_per_gpu * tokens * num_seqs
    gb_per_gpu = total_bytes_per_gpu / (1024**3)

    # Total across all GPUs
    total_gb_all_gpus = gb_per_gpu * tensor_parallel_size

    return {
        "bytes_per_token_per_gpu": bytes_per_token_per_gpu,
        "gb_per_gpu": gb_per_gpu,
        "per_seq_gb_per_gpu": gb_per_gpu / num_seqs if num_seqs > 0 else 0,
        "total_gb_all_gpus": total_gb_all_gpus
    }

def main():
    parser = argparse.ArgumentParser(
        description="Test maximum context length and KV cache allocation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default settings
  python test_context_kv_cache.py

  # Aggressive testing (closer to limit)
  python test_context_kv_cache.py --aggressive

  # Test specific sizes
  python test_context_kv_cache.py --sizes 100000 250000 500000

  # Use different model
  python test_context_kv_cache.py --model nemotron-3-super
"""
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Model name to test (default: qwen-3.5-122b)"
    )

    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Test closer to the maximum context limit (default: conservative)"
    )

    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        help="Specific token sizes to test (overrides automatic sizing)"
    )

    parser.add_argument(
        "--max-output",
        type=int,
        default=100,
        help="Maximum output tokens per test (default: 100)"
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="Timeout in seconds per test (default: 600)"
    )

    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop testing on first failure (default: continue)"
    )

    args = parser.parse_args()

    print("""
╔═══════════════════════════════════════════════════════════════════╗
║   Enhanced Context Length & KV Cache Test Suite                  ║
║   Progressive scaling with memory monitoring                      ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    client = httpx.Client(timeout=args.timeout)

    # Step 1: Check model info
    model_info = check_model_info(client)
    max_context = model_info.get("max_model_len", 0)

    if max_context == 0:
        print("\n❌ Could not determine max context length. Is the server running?")
        sys.exit(1)

    # Step 2: Generate or use provided test sizes
    if args.sizes:
        test_sizes = sorted(args.sizes)
        print(f"\nUsing custom test sizes: {test_sizes}")
    else:
        test_sizes = generate_test_sizes(max_context, args.aggressive)

    # Filter sizes that exceed max_context
    test_sizes = [s for s in test_sizes if s <= max_context]

    if not test_sizes:
        print(f"\n❌ No valid test sizes for max_context={max_context:,}")
        sys.exit(1)

    print(f"\nTest plan: {len(test_sizes)} progressive tests")
    print(f"Range: {test_sizes[0]:,} → {test_sizes[-1]:,} tokens")
    print(f"Strategy: {'Aggressive' if args.aggressive else 'Conservative'}")

    results = []

    # Step 3: Run progressive tests
    for i, size in enumerate(test_sizes, 1):
        print(f"\n[Test {i}/{len(test_sizes)}]")

        result = test_context_length(
            client,
            size,
            args.model,
            max_output=args.max_output,
            timeout=args.timeout
        )
        results.append(result)

        # Stop on first failure if requested
        if not result["success"] and args.stop_on_failure:
            print(f"\n⚠️  Stopping tests - failure at {size:,} tokens")
            break

        # Brief pause between tests to allow system to stabilize
        if i < len(test_sizes):
            time.sleep(3)

    # Step 4: Summary
    print(f"\n{'='*70}")
    print("TEST SUMMARY")
    print(f"{'='*70}")

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    print(f"\n✅ Passed: {len(successful)}/{len(results)} tests")
    print(f"❌ Failed: {len(failed)}/{len(results)} tests")

    if successful:
        max_success = max(r["input_tokens"] for r in successful)
        max_success_target = max(r["tokens"] for r in successful)

        print(f"\n🎯 Maximum verified context: {max_success:,} tokens (actual)")
        print(f"   Target was: {max_success_target:,} tokens")
        print(f"   Utilization: {(max_success / max_context * 100):.1f}% of max ({max_context:,})")

        # Show performance metrics
        print("\n📊 Performance Metrics:")
        print(f"{'Target':>10}  {'Actual':>10}  {'Time':>8}  {'Prefill':>10}  {'Decode':>10}")
        print("-" * 70)

        for r in successful:
            target = r["tokens"]
            actual = r.get("input_tokens", 0)
            elapsed = r.get("elapsed", 0)
            prefill = r.get("prefill_tps", 0)
            decode = r.get("decode_tps", 0)

            print(f"{target:>10,}  {actual:>10,}  {elapsed:>7.2f}s  {prefill:>9.1f}/s  {decode:>9.1f}/s")

    if failed:
        print("\n❌ Failed tests:")
        for r in failed:
            error = r.get('error', 'unknown error')
            status = r.get('status_code', 'N/A')
            print(f"  {r['tokens']:>10,} tokens: HTTP {status} - {error}")

    # Step 5: KV Cache estimation
    if successful:
        max_tokens = max(r["input_tokens"] for r in successful)

        # Model-specific parameters
        is_qwen = model_info.get("is_qwen", False)
        is_nemotron = model_info.get("is_nemotron", False)

        if is_qwen:
            # Qwen 122B MoE parameters
            num_layers = 80
            hidden_size = 8192
            num_heads = 64
        elif is_nemotron:
            # Nemotron 120B parameters
            num_layers = 80
            hidden_size = 8192
            num_heads = 64
        else:
            # Generic large model
            num_layers = 80
            hidden_size = 8192
            num_heads = 64

        tensor_parallel_size = 4  # From config
        kv_mem = estimate_kv_cache_memory(
            tokens=max_tokens,
            num_seqs=2,  # From config
            num_layers=num_layers,
            hidden_size=hidden_size,
            num_heads=num_heads,
            tensor_parallel_size=tensor_parallel_size,
            dtype="fp8"
        )

        print(f"\n{'='*70}")
        print("KV CACHE MEMORY ESTIMATION")
        print(f"{'='*70}")
        print(f"Model:              {model_info.get('model_id', 'unknown')}")
        print(f"Max input tested:   {max_tokens:,} tokens")
        print(f"Config:             max_num_seqs = 2, kv_cache_dtype = fp8, TP = {tensor_parallel_size}")
        print(f"\nArchitecture:")
        print(f"  Layers:           {num_layers}")
        print(f"  Hidden size:      {hidden_size:,}")
        print(f"  Attention heads:  {num_heads}")
        print(f"  Tensor Parallel:  {tensor_parallel_size} GPUs")
        print(f"\nMemory estimates (FP8 KV cache with TP{tensor_parallel_size}):")
        print(f"  Per token/GPU:    {kv_mem['bytes_per_token_per_gpu']:,} bytes")
        print(f"  Per sequence:     {kv_mem['per_seq_gb_per_gpu']:.2f} GB per GPU")
        print(f"  Total (2 seqs):   {kv_mem['gb_per_gpu']:.2f} GB per GPU")
        print(f"  All {tensor_parallel_size} GPUs:       {kv_mem['total_gb_all_gpus']:.2f} GB (aggregate)")

        # Warning if approaching limits
        kv_per_gpu = kv_mem['gb_per_gpu']
        if kv_per_gpu > 10:
            print(f"\n⚠️  WARNING: KV cache using {kv_per_gpu:.2f} GB per GPU")
            print(f"   Consider reducing max_num_seqs or max_model_len if OOM occurs")

    print("\n" + "="*70)
    print("✅ Test suite complete!")
    print("="*70 + "\n")

    # Exit code
    sys.exit(0 if not failed else 1)

if __name__ == "__main__":
    main()
