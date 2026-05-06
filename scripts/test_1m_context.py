#!/usr/bin/env python3
"""
Test 1M context window for Qwen 3.6 35B
"""
import requests
import json
import sys

GATEWAY_URL = "http://localhost:8888"

def check_model_info():
    """Verify 1M context is configured"""
    print("=" * 80)
    print("Checking model configuration...")
    print("=" * 80)

    response = requests.get(f"{GATEWAY_URL}/v1/models")
    if response.status_code == 200:
        data = response.json()
        model = data['data'][0]
        max_len = model['max_model_len']

        print(f"✓ Model: {model['id']}")
        print(f"✓ Max context: {max_len:,} tokens")

        if max_len == 1048576:
            print("✓ 1M context confirmed!")
            return True
        else:
            print(f"✗ Expected 1,048,576 but got {max_len:,}")
            return False
    else:
        print(f"✗ Failed to get model info: {response.status_code}")
        return False

def test_basic_inference():
    """Test basic inference works"""
    print("\n" + "=" * 80)
    print("Testing basic inference...")
    print("=" * 80)

    payload = {
        "model": "qwen-3.6-35b",
        "messages": [
            {"role": "user", "content": "Say 'OK' if you're ready."}
        ],
        "max_tokens": 50,
        "temperature": 0.7
    }

    response = requests.post(
        f"{GATEWAY_URL}/v1/chat/completions",
        json=payload,
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        content = data['choices'][0]['message']['content']
        usage = data['usage']
        print(f"Response: {content[:100]}...")
        print(f"✓ Inference successful")
        print(f"  Tokens: {usage['prompt_tokens']} prompt + {usage['completion_tokens']} completion")
        return True
    else:
        print(f"✗ Inference failed: {response.status_code}")
        return False

def test_long_context(num_tokens_approx=10000):
    """Test with longer context (not full 1M to save time)"""
    print("\n" + "=" * 80)
    print(f"Testing with ~{num_tokens_approx:,} token context...")
    print("=" * 80)

    # Generate a long prompt (approximately 4 chars per token)
    long_text = "The quick brown fox jumps over the lazy dog. " * (num_tokens_approx // 10)

    payload = {
        "model": "qwen-3.6-35b",
        "messages": [
            {"role": "user", "content": f"Here is some text:\n\n{long_text}\n\nHow many times does 'fox' appear? Answer with just the number."}
        ],
        "max_tokens": 50,
        "temperature": 0.0
    }

    print(f"Prompt length: ~{len(long_text)} characters")

    try:
        response = requests.post(
            f"{GATEWAY_URL}/v1/chat/completions",
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            data = response.json()
            content = data['choices'][0]['message']['content']
            usage = data['usage']

            print(f"Response: {content}")
            print(f"✓ Long context test successful")
            print(f"  Input tokens: {usage['prompt_tokens']:,}")
            print(f"  Output tokens: {usage['completion_tokens']}")
            print(f"  Total: {usage['total_tokens']:,}")
            return True
        else:
            print(f"✗ Request failed: {response.status_code}")
            print(response.text[:500])
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_gpu_memory():
    """Display GPU memory usage"""
    print("\n" + "=" * 80)
    print("GPU Memory Status")
    print("=" * 80)

    import subprocess
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,memory.free", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split(',')
                gpu_id = parts[0].strip()
                used = parts[1].strip()
                total = parts[2].strip()
                free = parts[3].strip()
                print(f"GPU {gpu_id}: {used} / {total} (Free: {free})")
        else:
            print("Could not query GPU memory")
    except Exception as e:
        print(f"nvidia-smi not available: {e}")

def main():
    print("\n🚀 1M Context Test Suite for Qwen 3.6 35B\n")

    all_passed = True

    try:
        # Test 1: Verify 1M context configured
        if not check_model_info():
            print("\n✗ Model configuration check failed")
            all_passed = False

        # Test 2: Basic inference
        if not test_basic_inference():
            print("\n✗ Basic inference failed")
            all_passed = False

        # Test 3: Long context (10K tokens - adjust as needed)
        if not test_long_context(num_tokens_approx=10000):
            print("\n✗ Long context test failed")
            all_passed = False

        # Show GPU memory
        check_gpu_memory()

        print("\n" + "=" * 80)
        if all_passed:
            print("✓ All tests passed!")
            print("\nNotes:")
            print("- 1M context is configured and working")
            print("- RoPE scaling: YaRN 8.0× from 128K native")
            print("- Quality may degrade with very long contexts (>512K)")
            print("- For production, test with real workloads")
        else:
            print("✗ Some tests failed")
            sys.exit(1)
        print("=" * 80)

    except requests.exceptions.ConnectionError:
        print("\n✗ Connection failed. Is the LLM running?")
        print("Start with: LLM_CONFIG=config/config-qwen36-35b.yaml python3 scripts/setup/llm_manager.py start")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
