# Qwen 3.6 Models - 1M Context Configuration

**1M Token Context via YaRN 8× RoPE Scaling**

---

## Model Comparison

### Qwen 3.6 27B (Recommended for Throughput)

**Model:** `cyankiwi/Qwen3.6-27B-AWQ-4bit`  
**Config:** `config/config-qwen36-27b.yaml`

**Specifications:**
- Parameters: 27 billion
- Quantization: 4-bit (AWQ/Compressed-Tensors)
- Model weights: ~15-18GB
- Max context: 1M tokens (YaRN 8×)
- Concurrent requests: 2 (can try 3 with headroom)
- GPU memory: ~35-40GB per GPU

**Best for:**
- ✅ Higher throughput (2+ concurrent requests)
- ✅ Production deployments needing parallelism
- ✅ Cost-effective inference
- ✅ Faster response times

**Download:**
```bash
bash scripts/download_qwen36_27b.sh
```

**Start:**
```bash
LLM_CONFIG=config/config-qwen36-27b.yaml python3 scripts/setup/llm_manager.py start
```

---

### Qwen 3.6 35B (Recommended for Quality)

**Model:** `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`  
**Config:** `config/config-qwen36-35b.yaml`

**Specifications:**
- Parameters: 35 billion
- Quantization: 4-bit (Compressed-Tensors)
- Model weights: ~20-23GB
- Max context: 1M tokens (YaRN 8×)
- Concurrent requests: 1 (tight memory)
- GPU memory: ~43-45GB per GPU

**Best for:**
- ✅ Maximum quality
- ✅ Complex reasoning tasks
- ✅ Research and evaluation
- ✅ Single-user workloads

**Download:**
```bash
bash scripts/download_qwen36_awq.sh
```

**Start:**
```bash
LLM_CONFIG=config/config-qwen36-35b.yaml python3 scripts/setup/llm_manager.py start
```

---

## 1M Context Configuration

Both models use identical RoPE scaling configuration:

```yaml
inference:
  max_model_len: 1048576           # 1M tokens
  
  rope_scaling:
    type: "yarn"
    factor: 8.0                    # 8× from 128K native
    original_max_position_embeddings: 131072
  
  kv_cache_dtype: "fp8"            # Critical for 1M context
  gpu_memory_utilization: 0.90
```

---

## Memory Usage Comparison

| Metric | 27B Model | 35B Model |
|--------|-----------|-----------|
| **Model Weights** | ~18GB | ~23GB |
| **KV Cache (1M, 1 seq, FP8)** | ~100GB | ~100GB |
| **Total (1 seq)** | ~138GB | ~143GB |
| **GPU Memory per GPU** | ~35GB | ~36GB |
| **Free Memory** | ~14GB (29%) | ~13GB (27%) |
| **Max Concurrent Seqs** | 2-3 | 1 |

*With 2 concurrent sequences (27B only):*
- Total: ~180GB
- Per GPU: ~45GB
- Free: ~4GB (8%)

---

## Quality Considerations

### RoPE Scaling Impact

YaRN 8× scaling enables 1M context but may impact quality:

- **128K (native):** 100% quality ✅
- **256K (2×):** ~98% quality ✅
- **512K (4×):** ~90-95% quality ⚠️
- **768K (6×):** ~80-90% quality ⚠️
- **1M (8×):** ~75-85% quality ⚠️⚠️

**Recommendations:**
1. Test with your actual workloads
2. For production, consider 512K-768K for better quality
3. Use 1M only when necessary
4. Monitor long-range attention accuracy

---

## Progressive Scaling Plan

Start conservatively and scale up:

### Phase 1: 256K Context
```yaml
max_model_len: 262144
rope_scaling:
  factor: 2.0
```
- Low risk, high quality
- Test basic functionality

### Phase 2: 512K Context
```yaml
max_model_len: 524288
rope_scaling:
  factor: 4.0
```
- Good quality/capacity balance
- Recommended for production

### Phase 3: 768K Context
```yaml
max_model_len: 786432
rope_scaling:
  factor: 6.0
```
- Large contexts with acceptable quality
- Monitor memory carefully

### Phase 4: 1M Context (Current Config)
```yaml
max_model_len: 1048576
rope_scaling:
  factor: 8.0
```
- Maximum capacity
- Test quality before production use

---

## Testing

### Test 1M Context (35B)
```bash
python3 scripts/test_1m_context.py
```

### Test 1M Context (27B)
```bash
# After switching to 27B model
python3 scripts/test_1m_context.py
```

### Monitor GPU Memory
```bash
watch -n 1 nvidia-smi
```

---

## Troubleshooting

### Out of Memory (OOM)

**For 35B:**
1. Reduce `max_num_seqs` to 1 (already set)
2. Reduce context to 768K or 512K
3. Lower `gpu_memory_utilization` to 0.85

**For 27B:**
1. Reduce `max_num_seqs` from 2 to 1
2. Reduce context to 768K or 512K
3. Disable one concurrent request

### Quality Issues

1. Reduce RoPE scaling factor (use 512K instead of 1M)
2. Test with diverse prompts
3. Compare outputs with native 128K context
4. Monitor attention pattern degradation

### Slow Inference

1. Check GPU utilization: `nvidia-smi`
2. Verify CUDA graphs captured (check logs)
3. Enable prefix caching (already enabled)
4. Reduce batch size if memory-bound

---

## Switching Between Models

### From 35B to 27B
```bash
# Stop 35B
LLM_CONFIG=config/config-qwen36-35b.yaml python3 scripts/setup/llm_manager.py stop

# Download 27B (if needed)
bash scripts/download_qwen36_27b.sh

# Start 27B
LLM_CONFIG=config/config-qwen36-27b.yaml python3 scripts/setup/llm_manager.py start
```

### From 27B to 35B
```bash
# Stop 27B
LLM_CONFIG=config/config-qwen36-27b.yaml python3 scripts/setup/llm_manager.py stop

# Start 35B (already downloaded)
LLM_CONFIG=config/config-qwen36-35b.yaml python3 scripts/setup/llm_manager.py start
```

---

## Production Recommendations

### For Quality-Critical Applications
- Use **35B model**
- Start with **512K context** (not 1M)
- Set `max_num_seqs: 1`
- Monitor quality metrics

### For High-Throughput Applications
- Use **27B model**
- Start with **512K context**
- Set `max_num_seqs: 2` (or 3 if stable)
- Load balance across instances

### For Research/Evaluation
- Use **35B model**
- Test with **full 1M context**
- Compare with baseline (128K native)
- Document quality degradation

---

## Files Reference

### Configuration
- `config/config-qwen36-27b.yaml` - 27B with 1M context
- `config/config-qwen36-35b.yaml` - 35B with 1M context

### Scripts
- `scripts/download_qwen36_27b.sh` - Download 27B model
- `scripts/download_qwen36_awq.sh` - Download 35B model
- `scripts/test_1m_context.py` - Test 1M context
- `scripts/test_qwen36.py` - General testing

### Documentation
- `QWEN36_DEPLOYMENT.md` - Initial 35B deployment (128K)
- `QWEN36_1M_CONTEXT.md` - This file

---

## Quick Reference

```bash
# Download models
bash scripts/download_qwen36_27b.sh  # 27B (~16GB)
bash scripts/download_qwen36_awq.sh  # 35B (~23GB)

# Start models (1M context)
LLM_CONFIG=config/config-qwen36-27b.yaml python3 scripts/setup/llm_manager.py start  # 27B
LLM_CONFIG=config/config-qwen36-35b.yaml python3 scripts/setup/llm_manager.py start  # 35B

# Test
python3 scripts/test_1m_context.py

# Stop
python3 scripts/setup/llm_manager.py stop

# Monitor
watch -n 1 nvidia-smi
tail -f logs/vllm_replica_0.log
```

---

**Status:** ✅ 35B with 1M context tested and working  
**Next:** Download and test 27B with 1M context
