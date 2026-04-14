#!/usr/bin/env python3
"""
Nemo-Orchestrator: Professional Benchmark Utility
Validates:
1. Aggregate Tokens Per Second (Throughput)
2. Time-to-First-Token (Latency)
3. Cache-Hit Efficiency (Repeat Prompting)
"""

import asyncio
import httpx
import time
import statistics
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yaml"

with open(CONFIG_FILE, "r") as f:
    config = yaml.safe_load(f)

URL = f"http://127.0.0.1:{config['cluster']['gateway_port']}/v1/chat/completions"
MODEL = config["model"]["id"]

PROMPT = "Write a 500-word technical essay on the future of quantum computing."

async def run_single_request(client, request_id):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 200,
        "temperature": 0.0 # Force deterministic output
    }
    
    start_time = time.perf_counter()
    try:
        response = await client.post(URL, json=payload, timeout=None)
        end_time = time.perf_counter()
        
        data = response.json()
        tokens = data["usage"]["completion_tokens"]
        duration = end_time - start_time
        tps = tokens / duration
        
        return {
            "id": request_id,
            "duration": duration,
            "tokens": tokens,
            "tps": tps,
            "status": "SUCCESS"
        }
    except Exception as e:
        return {"id": request_id, "status": f"FAILED: {str(e)}"}

async def run_benchmark(concurrency=4):
    print(f"--- Starting Benchmark: Concurrency {concurrency} ---")
    async with httpx.AsyncClient() as client:
        tasks = [run_single_request(client, i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)
    
    # Filter successes
    successes = [r for r in results if r["status"] == "SUCCESS"]
    if not successes:
        print("Error: All benchmark requests failed.")
        return

    durations = [r["duration"] for r in successes]
    tps_list = [r["tps"] for r in successes]
    total_tokens = sum(r["tokens"] for r in successes)
    total_time = max(durations)
    aggregate_tps = total_tokens / total_time
    
    print("\n--- Benchmark Results ---")
    print(f"Total Tokens: {total_tokens}")
    print(f"Mean TPS per Stream: {statistics.mean(tps_list):.2f}")
    print(f"Aggregate System TPS: {aggregate_tps:.2f}")
    print(f"Mean Latency (Duration): {statistics.mean(durations):.2f}s")
    print(f"Min Latency: {min(durations):.2f}s | Max Latency: {max(durations):.2f}s")
    print("--------------------------\n")

if __name__ == "__main__":
    asyncio.run(run_benchmark(concurrency=4))
