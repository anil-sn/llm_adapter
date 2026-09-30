import requests
import json
import sys
import os
import time
import re

# ANSI color codes for better terminal rendering
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

def c(text, color):
    """Apply color to text"""
    return f"{color}{text}{Colors.RESET}"

def header(text):
    """Bold cyan header"""
    return c(text, Colors.CYAN + Colors.BOLD)

def success(text):
    """Green success text"""
    return c(text, Colors.GREEN)

def error(text):
    """Red error text"""
    return c(text, Colors.RED)

def warning(text):
    """Yellow warning text"""
    return c(text, Colors.YELLOW)

def info(text):
    """Blue info text"""
    return c(text, Colors.BLUE)

def dim(text):
    """Dimmed text"""
    return c(text, Colors.DIM)

def metric(text, value, unit=""):
    """Formatted metric line"""
    return f"  {dim(text)} {c(value, Colors.WHITE)}{unit}"

def extract_json_robust(text):
    """
    Robustly extracts a JSON object from text, handling think/reasoning blocks,
    markdown code fences, and any leading/trailing explanations.
    """
    if not text:
        return None
        
    # Strip think/reasoning block first (handles <think>...</think> if present)
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    cleaned = cleaned.strip()
    
    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
        cleaned = cleaned.strip()
        
    # Try to find JSON block by taking substring between first { and last }
    first_brace = cleaned.find('{')
    last_brace = cleaned.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        json_str = cleaned[first_brace:last_brace+1]
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass
            
    # Fallback to searching for JSON-like blocks using regex
    json_blocks = re.findall(r'\{[^{}]*"overall"[^{}]*\}', cleaned, re.DOTALL)
    for block in json_blocks:
        try:
            return json.loads(block)
        except (json.JSONDecodeError, ValueError):
            continue
            
    return None

def test_openai_compatibility(base_url, api_key, headers):
    """Test OpenAI SDK compatibility"""
    print()
    print(header("=" * 80))
    print(header("            OPENAI API COMPATIBILITY TEST"))
    print(header("=" * 80))

    try:
        # Try importing OpenAI SDK
        from openai import OpenAI
        print(f"  {success('[+]')} OpenAI SDK installed")

        # Initialize client
        client = OpenAI(api_key=api_key, base_url=f"{base_url}/v1")

        # Test 1: Models endpoint
        print(f"\n{info('[1/4] Testing /v1/models endpoint...')}")
        models = client.models.list()
        model_ids = [m.id for m in models.data]
        print(f"  {success('[+]')} Available models: {model_ids}")

        if not model_ids:
            print(f"  {error('[-]')} No models available")
            return False

        selected_model = model_ids[0]

        # Test 2: Chat completion
        print(f"\n{info('[2/4] Testing standard chat completion...')}")
        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": "Say 'hello' in 3 words"}],
            max_tokens=20
        )
        print(f"  {success('[+]')} Response: {response.choices[0].message.content}")
        print(f"  {success('[+]')} Tokens: {response.usage.total_tokens}")

        # Test 3: Streaming
        print(f"\n{info('[3/4] Testing streaming chat completion...')}")
        print(f"  {info('[*]')} Stream: ", end="")
        stream = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": "Count to 3"}],
            max_tokens=30,
            stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print()
        print(f"  {success('[+]')} Streaming working")

        # Test 4: Temperature and parameters
        print(f"\n{info('[4/4] Testing OpenAI parameters (temperature, top_p)...')}")
        response = client.chat.completions.create(
            model=selected_model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
            temperature=0.7,
            top_p=0.9
        )
        print(f"  {success('[+]')} Parameters accepted: temperature=0.7, top_p=0.9")

        print()
        print(header("=" * 80))
        print(f"  {success('[✓]')} OpenAI API Compatibility: FULLY COMPATIBLE")
        print(header("=" * 80))
        return True

    except ImportError:
        print(f"  {warning('[!]')} OpenAI SDK not installed (pip install openai)")
        print(f"  {info('[*]')} Skipping OpenAI SDK compatibility test")
        print(f"  {info('[*]')} Proceeding with raw HTTP tests...")
        return None
    except Exception as e:
        print(f"  {error('[-]')} OpenAI compatibility test failed: {e}")
        return False

def test_connectivity():
    base_url = os.getenv("LLM_BASE_URL", "http://10.172.249.149:8888").rstrip('/')
    api_key = os.getenv("LLM_API_KEY", "EDGE-AI-ADMIN")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print()
    print(header("=" * 80))
    print(header("            LLM GATEWAY ADVANCED DOMAIN & LATENCY BENCHMARK"))
    print(f"  {dim('Target Endpoint:')} {base_url}")
    print(header("=" * 80))

    # Run OpenAI compatibility test first
    test_openai_compatibility(base_url, api_key, headers)

    # 1. Detect API Type & Active Models Dynamically
    api_type = "unknown"
    active_models = []
    
    try:
        print(f"\n{info('[1/3] Querying active endpoints (/v1/models)...')}")
        r = requests.get(f"{base_url}/v1/models", headers=headers, timeout=5)
        if r.status_code == 200:
            api_type = "openai"
            models_data = r.json().get("data", [])
            active_models = [m.get("id") for m in models_data if m.get("id")]
            print(f"  {success('[+]')} OpenAI-compatible API discovered.")
            print(f"  {success('[+]')} Active served endpoints: {active_models}")
        else:
            print(f"  {error('[-]')} Models query returned status: {r.status_code}")
    except Exception as e:
        print(f"  {error('[-]')} Models endpoint check failed: {e}")

    # Check for Ollama fallback
    if api_type == "unknown":
        try:
            print(f"{info('Checking fallback to Ollama API (/api/tags)...')}")
            r = requests.get(f"{base_url}/api/tags", timeout=5)
            if r.status_code == 200:
                print(f"  {success('[+]')} Detected Ollama API")
                api_type = "ollama"
        except Exception as e:
            print(f"  {error('[-]')} Ollama fallback check failed: {e}")

    if not active_models and api_type == "openai":
        print(f"  {warning('[-]')} WARNING: Gateway is online but reporting 0 active vLLM replicas — using default model.")

    # Pick active endpoint
    selected_model = active_models[0] if active_models else "gpt-3.5-turbo"

    # Define the 3 benchmark test cases
    PROFILES = {
        "1": {
            "name": "Creative Generation & Speed",
            "prompt": "Write a 120-word cohesive story about a quantum computer that gains consciousness.",
            "max_tokens": 512
        },
        "2": {
            "name": "Quality of Reasoning (Algorithm & Proof)",
            "prompt": (
                "Design a highly optimized, memory-safe O(log N) algorithm to find the single element "
                "in a sorted array where every other element appears exactly twice. Provide a strict proof "
                "of its correctness and analyze any edge cases (e.g. element at index 0 or index N-1) with "
                "step-by-step logic."
            ),
            "max_tokens": 1024
        },
        "3": {
            "name": "Advanced Networking Knowledge (Subnetting & BGP)",
            "prompt": (
                "A network administrator is troubleshooting an issue where a branch office router (AS 65001) "
                "cannot establish an eBGP peering session with the corporate data center router (AS 65000). "
                "The branch WAN port is assigned the subnet 10.144.12.0/27, and the local interface IP is 10.144.12.1. "
                "Calculate: 1. The valid host IP range of the subnet. 2. The subnet mask and wildcard mask. "
                "Then, explain step-by-step how to troubleshoot the BGP peering issue, and explain what happens "
                "to the BGP peering state machine if an MTU mismatch is present on the path."
            ),
            "max_tokens": 1024
        }
    }

    # Determine which profiles to run
    choices_to_run = []
    
    # 2. Check if specific choices were passed as arguments (e.g., verify_llm.py 3)
    for arg in sys.argv[1:]:
        if arg in ["1", "2", "3"]:
            choices_to_run.append(arg)
        elif arg == "all":
            choices_to_run = ["1", "2", "3"]
            break

    # If no specific arguments are passed, default to running ALL tests sequentially
    if not choices_to_run:
        print(f"  {info('[*]')} No specific profile selected. Defaulting to run ALL tests sequentially.")
        choices_to_run = ["1", "2", "3"]
    else:
        print(f"  {info('[*]')} Custom test profile execution sequence: {choices_to_run}")

    benchmark_results = []
    url = f"{base_url}/v1/chat/completions"

    # Execute selected benchmarks sequentially
    for idx, choice in enumerate(choices_to_run, 1):
        prof = PROFILES[choice]
        test_name = prof["name"]
        prompt = prof["prompt"]
        max_tokens = prof["max_tokens"]

        print()
        print(header("=" * 80))
        print(f"  {header('PROFILE [{}/{}]:'.format(idx, len(choices_to_run)))} {test_name}")
        print(header("=" * 80))
        print(f"  {info('[*]')} Target Endpoint: {selected_model}")
        print(f"  {info('[*]')} Sending streaming request...")
        print(f"  {info('[*]')} Max tokens: {max_tokens}")
        print(f"  {info('[*]')} Streaming output text: \n" + "-" * 80)

        payload = {
            "model": selected_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "top_p": 0.95,
            "stream": True,
            "stream_options": {"include_usage": True}
        }

        start_time = time.time()
        ttft_time = None
        completion_tokens = 0
        text_generated = ""
        prompt_tokens = 0

        try:
            resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
            
            if resp.status_code != 200:
                print(f"\nError: Endpoint returned status {resp.status_code}")
                print(resp.text)
                continue

            for line in resp.iter_lines():
                if line:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data_str)
                            choices = chunk.get("choices", [])
                            
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    if ttft_time is None:
                                        ttft_time = time.time()
                                    
                                    sys.stdout.write(content)
                                    sys.stdout.flush()
                                    text_generated += content
                            
                            if "usage" in chunk and chunk["usage"]:
                                usage = chunk["usage"]
                                completion_tokens = usage.get("completion_tokens", completion_tokens)
                                prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                        except json.JSONDecodeError:
                            continue
                            
            end_time = time.time()
            print("\n" + "-" * 80)
            
            # Performance metrics
            total_time = end_time - start_time
            if ttft_time:
                ttft_ms = (ttft_time - start_time) * 1000
                generation_time = end_time - ttft_time
                tokens_per_sec = completion_tokens / generation_time if generation_time > 0 else 0
            else:
                ttft_ms = 0
                generation_time = total_time
                tokens_per_sec = 0

            print()
            print(f"  {success('[+]')} Performance Metrics:")
            print(metric("Speed:", f"{tokens_per_sec:.2f}", " tokens/sec"))
            print(metric("TTFT:", f"{ttft_ms:.2f}", " ms"))
            print(metric("Latency:", f"{total_time:.2f}", " s"))
            print(metric("Tokens:", f"{completion_tokens}", " generated"))
            print(metric("Input Tokens:", f"{prompt_tokens}", ""))
            print()

            # Collect results for scoreboard
            benchmark_results.append({
                "name": test_name,
                "ttft_ms": ttft_ms,
                "t_s": tokens_per_sec,
                "latency": total_time,
                "tokens": completion_tokens,
                "input_tokens": prompt_tokens
            })

        except Exception as e:
            print(f"\n{error('[-]')} Request failed or timed out: {e}")

    # 3. Consolidated Scoreboard Display
    print()
    print(header("=" * 80))
    print(f"  {header('CONSOLIDATED BENCHMARK SCOREBOARD')}")
    print(header("=" * 80))
    print(f"  {dim('PROFILE')}{' ' * 35} | {dim('TTFT')}{' ' * 6} | {dim('SPEED')}{' ' * 7} | {dim('TOKENS')}")
    print("-" * 80)
    for res in benchmark_results:
        print(f" {res['name']:<42} | {res['ttft_ms']:>6.0f} ms | {res['t_s']:>6.1f} T/S | {res['tokens']:>4} tok")
    print(header("=" * 80))
    if not benchmark_results:
        print(f"  {error('[-]')} All benchmarks failed — no results to display.")
        sys.exit(1)
    print(f"  {success('[+]')} All benchmarks completed successfully!\n")

if __name__ == "__main__":
    test_connectivity()
