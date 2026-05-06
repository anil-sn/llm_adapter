# DeepSeek V4 Phase 0 Test Plan

## Objective

Validate basic stability of DeepSeek V4 Flash (284B MoE, 13B activated) on 4× RTX 6000 Ada with vLLM 0.20.1 under **minimal load** before scaling to production workloads.

This is a **controlled experiment**, not a "try and hope" run.

---

## Configuration

### Hardware
- **GPUs**: 4× NVIDIA RTX 6000 Ada (48GB each = 196GB total)
- **Driver**: 595.58.03
- **CUDA**: 13.2
- **Tensor Parallel**: 4
- **Pipeline Parallel**: 1

### vLLM Parameters (Conservative)
```yaml
# Memory
gpu_memory_utilization: 0.80    # Conservative (allows fragmentation headroom)
max_model_len: 262144           # 256K context (Phase 0 baseline)

# Batching (STRICT limits to prevent scheduler edge cases)
max_num_seqs: 4                 # Max 4 concurrent sequences
max_num_batched_tokens: 8192    # Conservative token batching

# Execution
enforce_eager: true             # Bypass graph capture/inductor
seed: 0                         # Deterministic

# V1 Engine (HARD DISABLE)
VLLM_USE_V1: 0
VLLM_DISABLE_V1_MULTIPROCESSING: 1

# Torch Compile (DISABLE - known fragility with FP8 + MoE)
TORCH_COMPILE_DISABLE: 1
TORCHINDUCTOR_DISABLE: 1
PYTORCH_JIT: 0

# MoE
enable_expert_parallel: true
block_size: 256

# Quantization
quantization: fp8
kv_cache_dtype: fp8

# Attention
attention_backend: FLASH_ATTN

# Caching (DISABLED for Phase 0 simplicity)
enable_prefix_caching: false
enable_chunked_prefill: false
```

---

## Test Protocol

### Phase 0: Baseline Stability (100 iterations)
- **Batch size**: 1 only (sequential)
- **Prompt length**: 512–1K tokens (4 variants, rotating)
- **Output length**: ≤128 tokens
- **Deterministic**: seed=0, temperature=0.0
- **Monitoring**:
  - GPU memory per iteration
  - Latency per iteration
  - CUDA errors
  - OOM errors
  - Routing failures

### Success Criteria
- ✅ Zero CUDA errors
- ✅ Zero OOM errors
- ✅ Zero routing failures
- ✅ Stable memory usage (no creep >50 MB/iter)
- ✅ Latency variance < 20%

### Failure Modes to Watch
| Symptom | Root Cause |
|---------|------------|
| Intermittent CUDA errors | Kernel instability |
| Memory creep | KV fragmentation |
| Latency spikes | Scheduler fallback path |
| Routing errors | MoE instability |

---

## Next Steps

### If Phase 0 Passes ✓
**Phase 1: Context Ramp** (incremental scaling)
- Test at: 32K → 64K → 128K → 192K → 256K
- At each step:
  - Run multiple iterations
  - Monitor KV cache allocation
  - Check latency scaling (should be ~linear)
  - Watch for fragmentation

**Phase 2: MoE Stress**
- Mixed prompt domains (code, math, NL)
- Mixed lengths in same batch (8K, 32K, 64K, 128K)
- Forces uneven expert utilization
- Tests routing pressure

**Phase 3: Hybrid Attention Validation**
- Long, uniform sequences (≥128K)
- Batch size = 1–2
- Test CSA/HCA transitions
- Check for attention degradation at long range

**Phase 4: Combined System Test**
- Batching + MoE diversity + long context
- Gradually increase:
  - `max_num_seqs` (4 → 8 → 16)
  - `gpu_memory_utilization` (0.80 → 0.85 → 0.90)
  - Context (256K → 512K → 768K → 1M)

### If Phase 0 Fails ✗
**Investigate**:
1. Check vLLM logs: `tail -f logs/vllm_replica_0.log`
2. Look for specific error patterns:
   - V1 engine residue (search for "V1", "async")
   - MoE routing issues (search for "expert", "moe")
   - Attention errors (search for "attention", "kv")
   - FP8 kernel issues (search for "fp8", "quantization")

**Pivot Options**:
- **Option B**: Try vLLM nightly/dev build
  ```bash
  pip install vllm --pre --upgrade
  ```
- **Option C**: Patch vLLM engine selection
  - Hard-disable V1 paths in code
  - Force legacy V0/V2 engine
- **Option D**: Simplify architecture
  - Reduce expert parallelism
  - Disable hybrid attention (if configurable)
  - Test with BF16 KV cache instead of FP8

---

## Running the Test

### Quick Start
```bash
cd /home/asrirang/Coding/llm_adapter
./scripts/run_phase0_test.sh
```

This will:
1. Stop any existing vLLM processes
2. Launch vLLM with Phase 0 config
3. Wait for server readiness
4. Run 100-iteration stress test
5. Generate detailed report

### Manual Steps
```bash
# 1. Set config
export LLM_CONFIG=config/config-deepseek-phase0.yaml

# 2. Launch vLLM
python scripts/setup/llm_manager.py start

# 3. Run test (in new terminal)
python scripts/test_deepseek_phase0.py --iterations 100

# 4. Stop vLLM
python scripts/setup/llm_manager.py stop
```

### Monitoring During Test
```bash
# Watch vLLM logs
tail -f logs/vllm_replica_0.log

# Monitor GPU memory
watch -n 1 nvidia-smi

# Check test progress
# (test script prints live updates)
```

---

## Files Created

```
config/
  config-deepseek-phase0.yaml     # Conservative test configuration

scripts/
  test_deepseek_phase0.py         # 100-iteration stress test
  run_phase0_test.sh              # Launcher script

docs/
  PHASE0_TEST_PLAN.md             # This document

logs/
  vllm_replica_0.log              # vLLM server logs
  phase0_report_*.json            # Test results (auto-generated)
```

---

## Expected Behavior

### Normal Operation
```
✓ Iter   1:   3.45s | Tokens:  612 → 128 | Mem Δ:   +42 MB
✓ Iter   2:   3.52s | Tokens:  698 → 128 | Mem Δ:    +8 MB
✓ Iter   3:   3.48s | Tokens:  754 → 128 | Mem Δ:   +12 MB
...
--- Stats (last 25) ---
  Latency: 3.50s ± 0.15s [3.32, 3.78]
  Memory Δ: +10 MB ± 15 MB
```

### Warning Signs
```
⚠ Iter  45:   4.12s | Tokens:  612 → 128 | Mem Δ:  +185 MB  <-- Memory spike
⚠ Memory creep detected: +95 MB over 50 iterations            <-- Fragmentation
```

### Critical Failure
```
✗ Iter  23: CUDAError: CUDA driver version is insufficient
!!! CRITICAL: CUDA error detected at iteration 23
```

---

## Report Interpretation

The test generates a JSON report with detailed metrics:

```json
{
  "status": "PASS" | "WARN" | "FAIL",
  "success_rate": 100.0,
  "latency": {
    "mean": 3.50,
    "std": 0.15,
    "p95": 3.75,
    "p99": 3.85
  },
  "memory": {
    "mean_delta_mb": 10.5,
    "max_delta_mb": 85.0
  },
  "issues": [
    "High latency variance (>20%)",
    "Memory creep detected (95 MB/iter)"
  ]
}
```

---

## Risk Assessment

### Low Risk (Expected to Pass)
vLLM 0.20.1 has specific DeepSeek V4 fixes:
- torch inductor error (#41135)
- topk cooperative deadlock (#41189)
- megamoe TP guard (#41522)

### Medium Risk (Monitor Closely)
- **MoE routing** under multi-sequence batching
- **Hybrid attention** (CSA+HCA) transitions
- **FP8 KV cache** memory layout

### High Risk (May Require Investigation)
- **V1 engine residue** (even with flags, heuristics may activate V1 paths)
- **Memory fragmentation** at long context
- **Expert imbalance** causing OOM on specific GPUs

---

## Contact & Support

Created by: Claude Code (Anthropic)
Test designed: 2026-05-05
vLLM version: 0.20.1

For issues:
1. Check logs first
2. Review error patterns
3. Consult vLLM GitHub issues for similar reports
4. Consider engine patching if systematic V1 interference
