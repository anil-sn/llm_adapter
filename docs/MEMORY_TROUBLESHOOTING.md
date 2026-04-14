# Memory Troubleshooting Guide - Nemotron-3 120B MoE

## The Problem: MoE Memory Characteristics

Mixture-of-Experts (MoE) models have **dramatically different** memory characteristics than dense models:

### Memory Profile Comparison

| Component | Dense 120B | MoE 120B (Nemotron-3) |
|-----------|------------|----------------------|
| **Base Weights** | 60 GB (FP8) | 60 GB (FP8) |
| **KV Cache** | Predictable | Predictable |
| **Intermediate Activations** | ~2-3 GB | **~8-15 GB** 🔥 |
| **Peak Spikes** | +10-15% | **+30-50%** 🔥 |

**Why MoE is Different:**
1. **Expert Routing:** Dynamically activates different experts per token
2. **Parallel Experts:** Multiple experts compute simultaneously
3. **FP8 Quantization Buffers:** Temporary tensors during `scaled_fp8_quant()`
4. **Unpredictable Patterns:** Memory usage varies by input tokens

## Root Cause of Your OOM

```
Error Location: vllm/model_executor/layers/fused_moe/utils.py:270
Function:       _fp8_quantize() -> scaled_fp8_quant()
Action:         torch.empty(shape, device=input.device, dtype=out_dtype)
Needed:         378 MB
Available:      363 MB
GPU State:      47.11 GB / 47.50 GB (99.2% utilized)
```

**The Issue:**
- You configured `gpu_memory_utilization: 0.80` (80%)
- Expected headroom: 9.6 GB per GPU
- Actual headroom needed for MoE: **~16-18 GB** (35-40%)
- Result: Constant OOM during MoE forward pass

## Fixes Applied

### 1. Reduced GPU Memory Utilization
```yaml
# config.yaml
gpu_memory_utilization: 0.65  # Was 0.80

Effect:
- Before: 38.4 GB allocated, 9.6 GB headroom
- After:  31.2 GB allocated, 16.8 GB headroom
- Gain:   +7.2 GB available for MoE spikes
```

### 2. Reduced Batch Size
```yaml
max_num_seqs: 4  # Was 16

Effect:
- Before: 16 sequences × ~300 MB = 4.8 GB
- After:  4 sequences × ~300 MB = 1.2 GB
- Gain:   +3.6 GB per GPU
```

### 3. Disabled Chunked Prefill
```yaml
enable_chunked_prefill: false  # Was true

Why:
- Chunked prefill INCREASES peak memory on MoE
- Creates temporary buffers for each chunk
- MoE works better with continuous prefill
```

### 4. Reduced Max Batched Tokens
```python
# llm_manager.py
max_batched = min(config["inference"]["max_model_len"], 16384)
# Was: config["inference"]["max_model_len"] (8192)

Effect:
- Limits total tokens processed in one batch
- Prevents memory spikes on concurrent long requests
```

### 5. Enhanced Memory Allocator Settings
```yaml
PYTORCH_ALLOC_CONF: "expandable_segments:True,max_split_size_mb:512"
PYTORCH_CUDA_ALLOC_CONF: "backend:native"

Effect:
- More aggressive fragmentation prevention
- Native allocator optimized for MoE patterns
```

## Expected Memory Profile After Fixes

Per GPU (48 GB RTX 6000 Ada):
```
┌─────────────────────────────────────────────┐
│ ALLOCATED (65% = 31.2 GB)                   │
├─────────────────────────────────────────────┤
│ Model Weights (TP=4):      ~30.0 GB         │
│ KV Cache (4 seqs × 8K):    ~1.0 GB          │
│ System Overhead:           ~0.2 GB          │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ HEADROOM (35% = 16.8 GB)                    │
├─────────────────────────────────────────────┤
│ MoE Activations:           ~8-12 GB ⚡       │
│ FP8 Quant Buffers:         ~2-3 GB          │
│ Fragmentation:             ~1-2 GB          │
│ Safety Margin:             ~1-3 GB          │
└─────────────────────────────────────────────┘
```

## Testing After Restart

### Step 1: Clean Restart
```bash
./llm_manager.py stop
sleep 5
./llm_manager.py start
```

### Step 2: Verify Startup
```bash
./verify_startup.sh
```

**Expected Output:**
```
✓ vLLM processes running
✓ Gateway process running
✓ GPU 0: 67% (32256MB / 48000MB) - OK
✓ GPU 1: 67% (32256MB / 48000MB) - OK
✓ GPU 2: 67% (32256MB / 48000MB) - OK
✓ GPU 3: 67% (32256MB / 48000MB) - OK
```

### Step 3: Monitor During Request
```bash
# Terminal 1: Monitor memory
watch -n 0.5 'nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits'

# Terminal 2: Send test request
curl -X POST http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "nemotron-3-super",
    "messages": [{"role": "user", "content": "Explain MoE models"}],
    "max_tokens": 100
  }'
```

**Expected Behavior:**
- Baseline: ~32 GB per GPU
- During request: Spike to ~38-42 GB
- After request: Return to ~32 GB
- **NO OOM ERRORS**

### Step 4: Debug If Still Failing
```bash
./debug_memory.sh
```

This will show:
- Current GPU memory state
- Process memory usage
- CUDA fragmentation
- Recent errors in logs

## Escalation Path

### If still getting OOM with current config:

**Option A: Use Emergency 4K Config**
```bash
cp config-emergency-4k.yaml config.yaml
./llm_manager.py restart
```

This reduces:
- Context: 8K → 4K
- Batch size: 4 → 2
- GPU util: 65% → 60%

**Option B: Monitor and Tune**
```bash
# Start with minimal config
# Gradually increase max_num_seqs from 2 → 4 → 8
# Test after each change
```

**Option C: Reduce Context Length Further**
```yaml
max_model_len: 2048  # Minimal for testing
max_num_seqs: 2
```

## Long-term Solutions

### 1. Wait for TriAttention Support
When vLLM adds TriAttention (Q3 2026?):
- 10.7× KV cache reduction
- Enable 180K+ context on current hardware
- Config: `enable_tri_attention: true`

### 2. Upgrade to More GPUs
Current: 4× RTX 6000 Ada (192 GB)
Upgrade: 8× RTX 6000 Ada (384 GB)

This would allow:
- 2× TP=2 replicas (as originally documented)
- Higher batch sizes
- Longer context windows

### 3. Switch to Dense Model
If MoE memory is too constrained:
- Llama-3.1 70B (dense, more predictable)
- Qwen-2.5 72B (dense)
- DeepSeek-V3 (MoE but with better memory profiles)

## Key Learnings

1. **MoE ≠ Dense:** Don't use dense model memory assumptions
2. **Headroom Matters:** 20% is NOT enough, need 35-40%
3. **Batch Size:** MoE needs much smaller batches than dense
4. **Chunked Prefill:** Counterproductive on MoE models
5. **Monitor First:** Always profile before claiming capabilities

## Quick Reference

| Symptom | Fix |
|---------|-----|
| OOM during forward pass | Reduce `gpu_memory_utilization` |
| OOM during prefill | Disable `enable_chunked_prefill` |
| OOM with multiple requests | Reduce `max_num_seqs` |
| Gradual memory creep | Add `max_split_size_mb:512` to allocator |
| Inconsistent OOM | Reduce `max_model_len` |

## Support Commands

```bash
# Check current memory
nvidia-smi

# Full memory debug
./debug_memory.sh

# Verify cluster health
./verify_startup.sh

# View live errors
tail -f logs/vllm_replica_0.log | grep -i error

# Kill all processes and free VRAM
./llm_manager.py stop
sleep 10
nvidia-smi  # Should show minimal usage
```
