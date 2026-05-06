#!/usr/bin/env python3
"""
DeepSeek V4 Phase 0 Stress Test
Controlled experiment to validate basic stability

Test Protocol:
- 100 iterations, batch size 1
- 512-1K token prompts
- ≤128 token outputs
- Deterministic seed
- Monitor for memory creep, CUDA errors, routing failures

Author: Claude Code (controlled experiment design)
"""

import os
import sys
import time
import json
import subprocess
import signal
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

try:
    import requests
    import numpy as np
except ImportError:
    print("Error: Required packages not found. Install with:")
    print("  pip install requests numpy")
    sys.exit(1)


class GPUMonitor:
    """Monitor GPU memory usage via nvidia-smi"""

    @staticmethod
    def get_memory_usage() -> List[Dict[str, int]]:
        """Get memory usage for all GPUs in MB"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return []

            gpus = []
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) == 3:
                    gpus.append({
                        'index': int(parts[0]),
                        'used_mb': int(parts[1]),
                        'total_mb': int(parts[2]),
                        'utilization': int(parts[1]) / int(parts[2]) * 100
                    })
            return gpus
        except Exception as e:
            print(f"Warning: GPU monitoring failed: {e}")
            return []


class Phase0Tester:
    """Phase 0 stress test orchestrator"""

    def __init__(self, base_url: str = "http://127.0.0.1:8888/v1"):
        self.base_url = base_url
        self.results = []
        self.gpu_monitor = GPUMonitor()
        self.test_start = None
        self.baseline_memory = None

        # Test prompts (512-1K tokens)
        self.prompts = [
            # Code analysis prompt (~600 tokens)
            """Analyze this Python function and explain its time complexity:

```python
def find_duplicates(arr):
    seen = set()
    duplicates = []
    for item in arr:
        if item in seen:
            duplicates.append(item)
        else:
            seen.add(item)
    return duplicates
```

Consider:
1. Best case scenario
2. Worst case scenario
3. Average case
4. Space complexity
5. Possible optimizations

Be concise but thorough.""",

            # Math reasoning prompt (~700 tokens)
            """Solve this problem step by step:

A train travels from City A to City B at 80 km/h. After reaching City B, it returns to City A at 120 km/h. The total journey takes 5 hours.

Questions:
1. What is the distance between City A and City B?
2. How long did each leg of the journey take?
3. What is the average speed for the entire round trip?
4. If the train had traveled at a constant 100 km/h for the entire journey, how much time would it have saved?

Show your work for each step.""",

            # Natural language prompt (~800 tokens)
            """Explain the concept of recursion in programming to a beginner.

Your explanation should include:
1. A clear definition
2. A simple example (like calculating factorial)
3. The difference between recursion and iteration
4. When to use recursion vs iteration
5. Common pitfalls (like stack overflow)
6. Best practices

Use simple language and practical examples. Aim for clarity over technical precision.""",

            # Mixed domain prompt (~650 tokens)
            """Compare and contrast these data structures:

1. Array/List
2. Linked List
3. Hash Table/Dictionary
4. Binary Search Tree

For each, discuss:
- Time complexity for insertion, deletion, search
- Space complexity
- Best use cases
- Trade-offs

Then recommend which structure to use for:
- A phone book application
- A task scheduler
- An LRU cache
- A spell checker

Justify your choices."""
        ]

    def wait_for_server(self, timeout: int = 120) -> bool:
        """Wait for vLLM server to become ready"""
        print(f"Waiting for server at {self.base_url}...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                response = requests.get(f"{self.base_url}/models", timeout=5)
                if response.status_code == 200:
                    models = response.json()
                    print(f"Server ready. Models: {models}")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
            print(".", end="", flush=True)
        print("\nTimeout waiting for server")
        return False

    def record_baseline_memory(self):
        """Record baseline GPU memory before testing"""
        self.baseline_memory = self.gpu_monitor.get_memory_usage()
        if self.baseline_memory:
            print("\nBaseline GPU Memory:")
            for gpu in self.baseline_memory:
                print(f"  GPU {gpu['index']}: {gpu['used_mb']} MB / {gpu['total_mb']} MB "
                      f"({gpu['utilization']:.1f}%)")

    def run_iteration(self, iteration: int, prompt: str) -> Dict:
        """Run single inference iteration"""
        start_time = time.time()
        gpu_before = self.gpu_monitor.get_memory_usage()

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": "deepseek-v4-flash",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 128,
                    "temperature": 0.0,  # Deterministic
                    "seed": 0,           # Deterministic
                    "stream": False
                },
                timeout=60
            )

            latency = time.time() - start_time
            gpu_after = self.gpu_monitor.get_memory_usage()

            if response.status_code == 200:
                data = response.json()
                output_tokens = data['usage']['completion_tokens']
                prompt_tokens = data['usage']['prompt_tokens']

                # Calculate memory delta
                memory_delta = 0
                if gpu_before and gpu_after:
                    memory_delta = sum(g['used_mb'] for g in gpu_after) - \
                                   sum(g['used_mb'] for g in gpu_before)

                result = {
                    'iteration': iteration,
                    'success': True,
                    'latency': latency,
                    'prompt_tokens': prompt_tokens,
                    'output_tokens': output_tokens,
                    'memory_delta_mb': memory_delta,
                    'timestamp': datetime.now().isoformat()
                }

                # Print progress
                status = "✓" if memory_delta < 100 else "⚠"
                print(f"{status} Iter {iteration:3d}: {latency:6.2f}s | "
                      f"Tokens: {prompt_tokens:4d} → {output_tokens:3d} | "
                      f"Mem Δ: {memory_delta:+6.0f} MB")

                return result
            else:
                print(f"✗ Iter {iteration:3d}: HTTP {response.status_code}")
                return {
                    'iteration': iteration,
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text[:200]}",
                    'latency': latency,
                    'timestamp': datetime.now().isoformat()
                }

        except Exception as e:
            latency = time.time() - start_time
            print(f"✗ Iter {iteration:3d}: {type(e).__name__}: {str(e)[:100]}")
            return {
                'iteration': iteration,
                'success': False,
                'error': f"{type(e).__name__}: {str(e)}",
                'latency': latency,
                'timestamp': datetime.now().isoformat()
            }

    def run_test(self, num_iterations: int = 100) -> Dict:
        """Run full Phase 0 test"""
        print("=" * 80)
        print("DeepSeek V4 Phase 0 Stress Test")
        print("=" * 80)
        print(f"Iterations: {num_iterations}")
        print(f"Prompts: {len(self.prompts)} variants (rotating)")
        print(f"Max output: 128 tokens")
        print(f"Deterministic: seed=0, temperature=0.0")
        print()

        if not self.wait_for_server():
            print("ERROR: Server not available")
            return {'success': False, 'error': 'Server timeout'}

        self.record_baseline_memory()
        self.test_start = time.time()
        self.results = []

        print("\nStarting stress test...")
        print("-" * 80)

        for i in range(1, num_iterations + 1):
            # Rotate through prompts
            prompt = self.prompts[(i - 1) % len(self.prompts)]
            result = self.run_iteration(i, prompt)
            self.results.append(result)

            # Check for critical failures
            if not result['success']:
                if 'CUDA' in result.get('error', '').upper():
                    print(f"\n!!! CRITICAL: CUDA error detected at iteration {i}")
                    print(f"!!! Error: {result['error']}")
                    break
                if 'OOM' in result.get('error', '').upper() or 'memory' in result.get('error', '').lower():
                    print(f"\n!!! CRITICAL: Memory error detected at iteration {i}")
                    print(f"!!! Error: {result['error']}")
                    break

            # Periodic full status
            if i % 25 == 0:
                self.print_intermediate_stats(i)

        total_time = time.time() - self.test_start
        return self.generate_report(total_time)

    def print_intermediate_stats(self, iteration: int):
        """Print intermediate statistics"""
        recent = [r for r in self.results[-25:] if r['success']]
        if not recent:
            return

        latencies = [r['latency'] for r in recent]
        memory_deltas = [r.get('memory_delta_mb', 0) for r in recent]

        print(f"\n--- Stats (last 25) ---")
        print(f"  Latency: {np.mean(latencies):.2f}s ± {np.std(latencies):.2f}s "
              f"[{np.min(latencies):.2f}, {np.max(latencies):.2f}]")
        print(f"  Memory Δ: {np.mean(memory_deltas):+.0f} MB ± {np.std(memory_deltas):.0f} MB")

        # Check for memory creep
        if len(self.results) >= 50:
            early = [r.get('memory_delta_mb', 0) for r in self.results[:25] if r['success']]
            late = [r.get('memory_delta_mb', 0) for r in self.results[-25:] if r['success']]
            if early and late:
                creep = np.mean(late) - np.mean(early)
                if abs(creep) > 50:
                    print(f"  ⚠ Memory creep detected: {creep:+.0f} MB over {len(self.results)} iterations")

        print("-" * 80)

    def generate_report(self, total_time: float) -> Dict:
        """Generate final test report"""
        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]

        report = {
            'test': 'DeepSeek V4 Phase 0',
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': total_time,
            'total_iterations': len(self.results),
            'successful': len(successful),
            'failed': len(failed),
            'success_rate': len(successful) / len(self.results) * 100 if self.results else 0,
        }

        if successful:
            latencies = [r['latency'] for r in successful]
            memory_deltas = [r.get('memory_delta_mb', 0) for r in successful]
            tokens_per_sec = [r.get('output_tokens', 0) / r['latency'] for r in successful if r['latency'] > 0]

            report['latency'] = {
                'mean': float(np.mean(latencies)),
                'std': float(np.std(latencies)),
                'min': float(np.min(latencies)),
                'max': float(np.max(latencies)),
                'p50': float(np.percentile(latencies, 50)),
                'p95': float(np.percentile(latencies, 95)),
                'p99': float(np.percentile(latencies, 99)),
            }

            report['memory'] = {
                'mean_delta_mb': float(np.mean(memory_deltas)),
                'std_delta_mb': float(np.std(memory_deltas)),
                'max_delta_mb': float(np.max(memory_deltas)),
            }

            if tokens_per_sec:
                report['throughput'] = {
                    'mean_tokens_per_sec': float(np.mean(tokens_per_sec)),
                    'std_tokens_per_sec': float(np.std(tokens_per_sec)),
                }

            # Check for issues
            issues = []
            if report['latency']['std'] / report['latency']['mean'] > 0.2:
                issues.append("High latency variance (>20%)")
            if report['memory']['mean_delta_mb'] > 100:
                issues.append(f"Memory creep detected ({report['memory']['mean_delta_mb']:.0f} MB/iter)")
            if report['success_rate'] < 100:
                issues.append(f"Failures detected ({len(failed)} / {len(self.results)})")

            report['issues'] = issues
            report['status'] = 'PASS' if not issues else 'WARN'
        else:
            report['status'] = 'FAIL'
            report['issues'] = ['All iterations failed']

        if failed:
            report['errors'] = [
                {'iteration': r['iteration'], 'error': r.get('error', 'Unknown')}
                for r in failed[:10]  # First 10 errors
            ]

        return report


def print_report(report: Dict):
    """Print formatted test report"""
    print("\n" + "=" * 80)
    print("PHASE 0 TEST REPORT")
    print("=" * 80)
    print(f"Status: {report['status']}")
    print(f"Success Rate: {report['success_rate']:.1f}% ({report['successful']}/{report['total_iterations']})")
    print(f"Duration: {report['duration_seconds']:.1f}s")

    if 'latency' in report:
        print(f"\nLatency:")
        print(f"  Mean: {report['latency']['mean']:.2f}s ± {report['latency']['std']:.2f}s")
        print(f"  Range: [{report['latency']['min']:.2f}, {report['latency']['max']:.2f}]")
        print(f"  P95: {report['latency']['p95']:.2f}s | P99: {report['latency']['p99']:.2f}s")

    if 'memory' in report:
        print(f"\nMemory:")
        print(f"  Mean Δ: {report['memory']['mean_delta_mb']:+.0f} MB ± {report['memory']['std_delta_mb']:.0f} MB")
        print(f"  Max Δ: {report['memory']['max_delta_mb']:+.0f} MB")

    if 'throughput' in report:
        print(f"\nThroughput:")
        print(f"  Mean: {report['throughput']['mean_tokens_per_sec']:.1f} tokens/s")

    if report.get('issues'):
        print(f"\nIssues:")
        for issue in report['issues']:
            print(f"  ⚠ {issue}")

    if report.get('errors'):
        print(f"\nFirst {len(report['errors'])} Errors:")
        for err in report['errors']:
            print(f"  Iter {err['iteration']}: {err['error'][:100]}")

    print("=" * 80)

    # Next steps
    if report['status'] == 'PASS':
        print("\n✓ Phase 0 PASSED - Ready for Phase 1 (context ramp)")
    elif report['status'] == 'WARN':
        print("\n⚠ Phase 0 PASSED WITH WARNINGS - Review issues before Phase 1")
    else:
        print("\n✗ Phase 0 FAILED - Investigate errors before proceeding")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='DeepSeek V4 Phase 0 Stress Test')
    parser.add_argument('--iterations', type=int, default=100,
                        help='Number of test iterations (default: 100)')
    parser.add_argument('--url', type=str, default='http://127.0.0.1:8888/v1',
                        help='vLLM server URL (default: http://127.0.0.1:8888/v1)')
    parser.add_argument('--output', type=str, default=None,
                        help='Output JSON file for results (default: logs/phase0_report_<timestamp>.json)')

    args = parser.parse_args()

    # Run test
    tester = Phase0Tester(base_url=args.url)
    report = tester.run_test(num_iterations=args.iterations)

    # Print report
    print_report(report)

    # Save to file
    if args.output:
        output_path = Path(args.output)
    else:
        log_dir = PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = log_dir / f"phase0_report_{timestamp}.json"

    output_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to: {output_path}")

    # Exit code
    sys.exit(0 if report['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
