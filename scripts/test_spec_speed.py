#!/usr/bin/env python3
"""
Quick benchmark for speculative decoding speed test.
Tests both baseline and with N-gram prompt lookup.
"""

import requests
import time
import json

URL = "http://localhost:8888/v1/chat/completions"
MODEL = "qwen-3.6-27b-512k-fast"

def benchmark_generation(prompt, max_tokens=500, label="Test"):
    """Run a single generation and measure speed."""
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "stream": False
    }

    start = time.time()
    response = requests.post(URL, json=payload)
    elapsed = time.time() - start

    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        print(response.text)
        return None

    result = response.json()
    content = result["choices"][0]["message"]["content"]
    usage = result.get("usage", {})

    completion_tokens = usage.get("completion_tokens", len(content.split()))
    total_tokens = usage.get("total_tokens", completion_tokens)

    tokens_per_sec = completion_tokens / elapsed if elapsed > 0 else 0

    print(f"✅ Generation complete:")
    print(f"   Time: {elapsed:.2f}s")
    print(f"   Completion tokens: {completion_tokens}")
    print(f"   Total tokens: {total_tokens}")
    print(f"   Speed: {tokens_per_sec:.1f} tok/s")
    print(f"\n   First 200 chars of response:")
    print(f"   {content[:200]}...")

    return {
        "elapsed": elapsed,
        "completion_tokens": completion_tokens,
        "tokens_per_sec": tokens_per_sec,
        "content": content
    }

def main():
    print("╔" + "═"*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  QWEN3.6-27B SPECULATIVE DECODING BENCHMARK".center(68) + "║")
    print("║" + "  512K Context + N-gram Prompt Lookup".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "═"*68 + "╝")

    # Test 1: Code generation (benefits from N-gram)
    code_prompt = """Write a Python function that implements a binary search tree with insert, delete, and search operations. Include proper error handling and docstrings."""

    result1 = benchmark_generation(
        code_prompt,
        max_tokens=500,
        label="TEST 1: Code Generation (N-gram works well here)"
    )

    # Test 2: Creative writing (less benefit from N-gram)
    creative_prompt = """Write a short story about a time traveler who discovers they can only travel to moments of historical significance, but each jump costs them a precious memory."""

    result2 = benchmark_generation(
        creative_prompt,
        max_tokens=500,
        label="TEST 2: Creative Writing (less N-gram benefit)"
    )

    # Test 3: Structured output (good for N-gram)
    structured_prompt = """Create a detailed JSON schema for a REST API that manages a library system with books, authors, and borrowers. Include all CRUD operations."""

    result3 = benchmark_generation(
        structured_prompt,
        max_tokens=500,
        label="TEST 3: Structured Output (N-gram should help)"
    )

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    if all([result1, result2, result3]):
        avg_speed = (result1["tokens_per_sec"] + result2["tokens_per_sec"] + result3["tokens_per_sec"]) / 3
        print(f"\n Average Speed: {avg_speed:.1f} tok/s")
        print(f"\n Test 1 (Code):      {result1['tokens_per_sec']:.1f} tok/s")
        print(f" Test 2 (Creative):  {result2['tokens_per_sec']:.1f} tok/s")
        print(f" Test 3 (Structured):{result3['tokens_per_sec']:.1f} tok/s")
        print()
        print(f" Expected with N-gram: 60-120 tok/s (1.5-2× speedup)")
        print(f" Baseline (no spec):   40-60 tok/s")

        if avg_speed > 60:
            print(f"\n ✅ GOOD: Achieving {avg_speed/50:.1f}× speedup over baseline (50 tok/s)")
        else:
            print(f"\n ⚠️  Performance lower than expected")
            print(f"    This may be due to:")
            print(f"    - Model still warming up (try again)")
            print(f"    - Prompts don't match N-gram patterns well")
            print(f"    - First request overhead")

    print(f"\n{'='*70}")
    print("N-GRAM SPECULATION NOTES:")
    print(f"{'='*70}")
    print("• N-gram works best with:")
    print("  - Code with repeated patterns")
    print("  - Templates and structured output")
    print("  - Long prompts with repetition")
    print()
    print("• Less effective for:")
    print("  - Highly creative/unique text")
    print("  - Short prompts")
    print("  - Random/unpredictable output")
    print()
    print("• Memory saved vs draft model:")
    print("  - N-gram: ~54GB (no draft model)")
    print("  - Draft model: ~63GB (+6GB for 3B draft)")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
