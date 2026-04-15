#!/usr/bin/env python3
"""
Test script to verify context length and KV cache allocation.
Tests 128K context window with progressively larger prompts.
"""

import httpx
import json
import sys
import time
from pathlib import Path

# Configuration
API_BASE = "http://10.172.249.149:8888"
MODEL = "nemotron-3-super"  # Use the served model name

def estimate_tokens(text: str) -> int:
    """Rough estimation: ~4 chars per token for English"""
    return len(text) // 4

def generate_test_prompt(target_tokens: int) -> str:
    """Generate a prompt of approximately target_tokens length"""
    # Use repetitive text pattern for predictable token count
    word = "test "  # ~1 token
    repeat_count = target_tokens
    return word * repeat_count

def test_context_length(client: httpx.Client, tokens: int) -> dict:
    """Test a specific context length"""
    print(f"\n{'='*60}")
    print(f"Testing {tokens:,} token context...")
    print(f"{'='*60}")

    prompt = generate_test_prompt(tokens)
    actual_chars = len(prompt)
    estimated_tokens = estimate_tokens(prompt)

    print(f"Prompt: {actual_chars:,} chars (~{estimated_tokens:,} tokens)")

    # Test via OpenAI-compatible endpoint
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
        "temperature": 0.7
    }

    try:
        start = time.time()
        response = client.post(
            f"{API_BASE}/v1/chat/completions",
            json=payload,
            timeout=300.0  # 5 minute timeout for large contexts
        )
        elapsed = time.time() - start

        if response.status_code == 200:
            data = response.json()
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            print(f"✅ SUCCESS ({elapsed:.2f}s)")
            print(f"   Input tokens:  {input_tokens:,}")
            print(f"   Output tokens: {output_tokens:,}")
            print(f"   Total tokens:  {total_tokens:,}")

            return {
                "success": True,
                "tokens": tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "elapsed": elapsed
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
        print(f"⏱️  TIMEOUT (>300s)")
        return {"success": False, "tokens": tokens, "error": "timeout"}

    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return {"success": False, "tokens": tokens, "error": str(e)}

def check_model_info(client: httpx.Client) -> dict:
    """Check reported model info"""
    print("\n" + "="*60)
    print("Checking Model Info...")
    print("="*60)

    try:
        response = client.get(f"{API_BASE}/v1/models")
        if response.status_code == 200:
            data = response.json()
            models = data.get("data", [])
            if models:
                model = models[0]
                max_model_len = model.get("max_model_len", 0)
                print(f"Model ID: {model.get('id')}")
                print(f"Max context: {max_model_len:,} tokens")
                print(f"Owner: {model.get('owned_by')}")
                return {"max_model_len": max_model_len}

        print("❌ Failed to get model info")
        return {}

    except Exception as e:
        print(f"❌ Exception: {e}")
        return {}

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║   Context Length & KV Cache Test Suite                   ║
║   Target: 128K (131,072 tokens)                           ║
╚═══════════════════════════════════════════════════════════╝
""")

    client = httpx.Client(timeout=300.0)

    # Step 1: Check model info
    model_info = check_model_info(client)
    max_context = model_info.get("max_model_len", 0)

    if max_context == 0:
        print("\n❌ Could not determine max context length. Is the server running?")
        sys.exit(1)

    # Step 2: Progressive context length tests
    # Test at: 10K, 32K, 64K, 96K, 120K, 128K
    test_sizes = [
        10_000,   # Baseline
        32_768,   # Previous limit
        65_536,   # Previous max (should now work)
        98_304,   # 96K (75% of new limit)
        120_000,  # Near limit
    ]

    # Only test up to configured max
    if max_context < 131_072:
        print(f"\n⚠️  WARNING: max_model_len ({max_context:,}) < 131,072")
        print(f"   Tests will be limited to {max_context:,} tokens")
        test_sizes = [s for s in test_sizes if s < max_context]
    else:
        test_sizes.append(128_000)  # Full 128K test

    results = []

    for size in test_sizes:
        result = test_context_length(client, size)
        results.append(result)

        # Stop on first failure
        if not result["success"]:
            print(f"\n⚠️  Stopping tests - first failure at {size:,} tokens")
            break

        # Brief pause between tests
        time.sleep(2)

    # Step 3: Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    print(f"\n✅ Passed: {len(successful)}/{len(results)} tests")
    print(f"❌ Failed: {len(failed)}/{len(results)} tests")

    if successful:
        max_success = max(r["tokens"] for r in successful)
        print(f"\n🎯 Maximum verified context: {max_success:,} tokens")

        # Show performance
        print("\nPerformance:")
        for r in successful:
            tokens = r["tokens"]
            elapsed = r.get("elapsed", 0)
            input_tokens = r.get("input_tokens", 0)

            if elapsed > 0 and input_tokens > 0:
                tokens_per_sec = input_tokens / elapsed
                print(f"  {tokens:>7,} tokens: {elapsed:>6.2f}s ({tokens_per_sec:>6.1f} tok/s)")

    if failed:
        print("\n❌ Failed tests:")
        for r in failed:
            print(f"  {r['tokens']:,} tokens: {r.get('error', 'unknown error')}")

    # Step 4: KV Cache estimation
    if successful:
        max_tokens = max(r["input_tokens"] for r in successful)

        print(f"\n{'='*60}")
        print("KV CACHE ESTIMATION")
        print(f"{'='*60}")
        print(f"Max input processed: {max_tokens:,} tokens")
        print(f"Config: max_num_seqs = 2")
        print(f"\nEstimated KV cache usage:")
        print(f"  Per token:  ~80 bytes (FP8, 80 layers)")
        print(f"  Per seq:    {max_tokens * 80 / (1024**3):.2f} GB")
        print(f"  Total (2):  {max_tokens * 80 * 2 / (1024**3):.2f} GB per GPU")
        print(f"  TP4 total:  {max_tokens * 80 * 2 / (1024**3):.2f} GB (distributed)")

    print("\n" + "="*60)
    print("Test complete!")
    print("="*60 + "\n")

    # Exit code
    sys.exit(0 if not failed else 1)

if __name__ == "__main__":
    main()
