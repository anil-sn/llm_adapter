# Testing Scripts

## Available Tests

### 1. Context Length Testing
**Script:** `test_context_kv_cache.py`
**Purpose:** Verify maximum context length and KV cache allocation

**Quick usage:**
```bash
# Test with defaults
python3 test_context_kv_cache.py

# Aggressive testing (up to 98% of max)
python3 test_context_kv_cache.py --aggressive

# Custom sizes
python3 test_context_kv_cache.py --sizes 100000 250000 500000
```

**Documentation:** See [CONTEXT_TESTING.md](./CONTEXT_TESTING.md) for comprehensive guide

---

## Test Scenarios

### Scenario 1: Verify 512K Qwen Context
After upgrading to 512K context with YaRN:
```bash
cd ~/Coding/nemo_orchestrator
python3 scripts/testing/test_context_kv_cache.py --aggressive --model qwen-3.5-122b
```

**Expected:**
- Max context: `524,288 tokens`
- Tests pass up to `~500K tokens`
- KV cache: `~8-10GB per GPU`

### Scenario 2: Smoke Test After Config Change
Quick validation after modifying config:
```bash
python3 scripts/testing/test_context_kv_cache.py \
  --sizes 10000 100000 250000 \
  --stop-on-failure
```

### Scenario 3: Stress Test with Long Output
Test decode performance:
```bash
python3 scripts/testing/test_context_kv_cache.py \
  --aggressive \
  --max-output 1000 \
  --timeout 900
```

---

## Monitoring During Tests

### GPU Memory
```bash
# Terminal 1: Run test
python3 scripts/testing/test_context_kv_cache.py --aggressive

# Terminal 2: Monitor GPUs
watch -n 1 nvidia-smi

# Terminal 3: Watch logs
tail -f ~/Coding/nemo_orchestrator/logs/vllm_replica_0.log | grep -i "oom\|memory\|cache"
```

---

## Adding New Tests

### Template for new test scripts:
```python
#!/usr/bin/env python3
"""
Test description here
"""

import httpx
import sys
from pathlib import Path

API_BASE = "http://10.172.249.149:8888"

def main():
    # Your test logic here
    pass

if __name__ == "__main__":
    main()
```

---

## CI/CD Integration

### Pre-deployment Gate
```bash
#!/bin/bash
# Run before deploying config changes

echo "Running pre-deployment tests..."

# Test 1: Context length
if ! python3 scripts/testing/test_context_kv_cache.py --aggressive; then
    echo "❌ Context test failed"
    exit 1
fi

echo "✅ All tests passed - safe to deploy"
```

### Nightly Regression
```bash
# Crontab entry: 0 2 * * *
cd ~/Coding/nemo_orchestrator
python3 scripts/testing/test_context_kv_cache.py --aggressive \
  2>&1 | tee logs/nightly_context_test_$(date +%Y%m%d).log
```

---

## Test Results Archive

Store test results for trend analysis:
```bash
# Create results directory
mkdir -p ~/Coding/nemo_orchestrator/test_results

# Run and save
python3 scripts/testing/test_context_kv_cache.py --aggressive \
  2>&1 | tee test_results/context_$(date +%Y%m%d_%H%M%S).log
```

---

## Troubleshooting Test Failures

### Common Issues

**1. Connection refused**
- Check if vLLM is running: `ps aux | grep vllm`
- Verify port: `curl http://localhost:8888/health`
- Check gateway: `ps aux | grep nemo_gateway`

**2. Timeout errors**
- Increase timeout: `--timeout 1200`
- Check GPU memory: `nvidia-smi`
- Review vLLM logs for OOM

**3. Tests fail at high context**
- Reduce max_model_len in config
- Decrease gpu_memory_utilization
- Lower max_num_seqs (2 → 1)

---

## Future Test Additions

- [ ] Tool calling test suite
- [ ] Thinking mode validation
- [ ] Multi-turn conversation tests
- [ ] Streaming performance benchmarks
- [ ] Concurrent request stress test
- [ ] Memory leak detection (long-running)
