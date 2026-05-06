#!/usr/bin/env python3
"""
Quick test script for Qwen 3.6 35B
"""
import requests
import json
import sys

GATEWAY_URL = "http://localhost:8888"

def test_models():
    """Check available models"""
    print("=" * 80)
    print("Checking available models...")
    print("=" * 80)

    response = requests.get(f"{GATEWAY_URL}/v1/models")
    if response.status_code == 200:
        data = response.json()
        for model in data['data']:
            print(f"✓ Model: {model['id']}")
            print(f"  Root: {model['root']}")
            print(f"  Max context: {model['max_model_len']:,} tokens")
    else:
        print(f"✗ Failed: {response.status_code}")
        return False
    return True

def test_chat(prompt: str = "Explain quantum entanglement in one sentence."):
    """Test chat completion"""
    print("\n" + "=" * 80)
    print(f"Testing chat completion...")
    print("=" * 80)
    print(f"Prompt: {prompt}")
    print("-" * 80)

    payload = {
        "model": "qwen-3.6-35b",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.7,
        "stream": False
    }

    response = requests.post(
        f"{GATEWAY_URL}/v1/chat/completions",
        json=payload,
        timeout=60
    )

    if response.status_code == 200:
        data = response.json()
        content = data['choices'][0]['message']['content']
        usage = data['usage']

        print(f"Response: {content}")
        print("-" * 80)
        print(f"Usage: {usage['prompt_tokens']} prompt + {usage['completion_tokens']} completion = {usage['total_tokens']} total tokens")
        return True
    else:
        print(f"✗ Failed: {response.status_code}")
        print(response.text)
        return False

def test_streaming(prompt: str = "Count from 1 to 5."):
    """Test streaming response"""
    print("\n" + "=" * 80)
    print("Testing streaming...")
    print("=" * 80)
    print(f"Prompt: {prompt}")
    print("-" * 80)

    payload = {
        "model": "qwen-3.6-35b",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 200,
        "temperature": 0.7,
        "stream": True
    }

    response = requests.post(
        f"{GATEWAY_URL}/v1/chat/completions",
        json=payload,
        stream=True,
        timeout=60
    )

    if response.status_code == 200:
        print("Streaming response: ", end="", flush=True)
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str.strip() == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data['choices'][0]['delta']
                        if 'content' in delta:
                            print(delta['content'], end="", flush=True)
                    except json.JSONDecodeError:
                        pass
        print("\n" + "-" * 80)
        return True
    else:
        print(f"✗ Failed: {response.status_code}")
        return False

def main():
    print("\n🚀 Qwen 3.6 35B Test Suite\n")

    try:
        # Test 1: Check models
        if not test_models():
            print("\n✗ Model check failed. Is the LLM running?")
            sys.exit(1)

        # Test 2: Simple chat
        if not test_chat():
            print("\n✗ Chat test failed")
            sys.exit(1)

        # Test 3: Streaming
        if not test_streaming():
            print("\n✗ Streaming test failed")
            sys.exit(1)

        print("\n" + "=" * 80)
        print("✓ All tests passed!")
        print("=" * 80)

    except requests.exceptions.ConnectionError:
        print("\n✗ Connection failed. Is the LLM running?")
        print("Start with: LLM_CONFIG=config/config-qwen36-35b.yaml python3 scripts/setup/llm_manager.py start")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
