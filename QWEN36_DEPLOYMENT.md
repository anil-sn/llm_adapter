# Qwen 3.6 35B Deployment Summary

**Date:** 2026-05-06  
**Status:** ✓ Operational

---

## Model Information

- **Model ID:** `cyankiwi/Qwen3.6-35B-A3B-AWQ-4bit`
- **Served Name:** `qwen-3.6-35b`
- **Quantization:** Compressed-Tensors 4-bit
- **Model Size:** ~23GB (downloaded)
- **Context Length:** 128K tokens (131,072)
- **Hardware:** 4× RTX 6000 Ada (Tensor Parallel)

---

## Resource Usage

### GPU Memory (per GPU)
- **Used:** 39.4 GB / 49.1 GB
- **Free:** 9.7 GB per GPU (~20% headroom)
- **Temperature:** 59-61°C (normal)

### Total System
- **Total VRAM:** 196 GB
- **Used VRAM:** ~158 GB
- **Free VRAM:** ~38 GB

---

## Endpoints

### Gateway (Port 8888)
- Base URL: `http://localhost:8888`
- Models: `GET /v1/models`
- Chat: `POST /v1/chat/completions`
- Completions: `POST /v1/completions`

### vLLM Direct (Port 8000)
- Base URL: `http://localhost:8000`
- Same API structure as above

---

## Quick Start

### Start the LLM
```bash
LLM_CONFIG=config/config-qwen36-35b.yaml python3 scripts/setup/llm_manager.py start
```

### Stop the LLM
```bash
LLM_CONFIG=config/config-qwen36-35b.yaml python3 scripts/setup/llm_manager.py stop
```

### Check Status
```bash
LLM_CONFIG=config/config-qwen36-35b.yaml python3 scripts/setup/llm_manager.py status
```

### Run Tests
```bash
python3 scripts/test_qwen36.py
```

---

## Example Usage

### Python
```python
import requests

response = requests.post(
    "http://localhost:8888/v1/chat/completions",
    json={
        "model": "qwen-3.6-35b",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
)

print(response.json()['choices'][0]['message']['content'])
```

### cURL
```bash
curl http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-3.6-35b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 500,
    "temperature": 0.7
  }'
```

---

## Performance Characteristics

### Inference Speed
- **Prefill:** Mixed prefill-decode with CUDA graphs
- **Decode:** Full CUDA graph optimization
- **Batch Size:** Up to 4 concurrent requests
- **Max Batched Tokens:** 32,768

### Memory Efficiency
- **Prefix Caching:** Enabled (reuses KV cache)
- **Chunked Prefill:** Enabled (handles long contexts)
- **KV Cache:** Auto-optimized

---

## Model Capabilities

✓ Chat completion  
✓ Text generation  
✓ Reasoning/thinking mode (built-in)  
✓ Tool calling (Qwen3 parser)  
✓ Long context (128K tokens)  
✓ Streaming responses  
✓ Multi-turn conversations  

---

## Configuration File

**Location:** `config/config-qwen36-35b.yaml`

Key settings:
- Tensor parallel: 4 GPUs
- GPU memory utilization: 85%
- Max model length: 131,072 tokens
- Max sequences: 4
- Attention backend: TRITON_ATTN

---

## Logs

- **vLLM:** `logs/vllm_replica_0.log`
- **Gateway:** `logs/nemo_gateway.log`

Monitor in real-time:
```bash
tail -f logs/vllm_replica_0.log
```

---

## Troubleshooting

### LLM won't start
1. Check if another instance is running: `ps aux | grep vllm`
2. Kill zombie processes: `pkill -f vllm`
3. Clear VRAM: wait 10-15 seconds after stop
4. Check logs: `tail -100 logs/vllm_replica_0.log`

### Out of Memory
1. Reduce `gpu_memory_utilization` to 0.80
2. Reduce `max_num_seqs` to 2 or 1
3. Reduce `max_model_len` if using shorter contexts

### Slow inference
1. Check GPU utilization: `nvidia-smi`
2. Verify CUDA graphs captured (in logs)
3. Enable prefix caching (already enabled)

---

## Deployment Notes

### Why This Model?
- **Ada compatible:** Works on RTX 6000 Ada (no FP8 tensor cores required)
- **Efficient:** 4-bit quantization reduces memory by ~75%
- **Native 128K:** No aggressive RoPE scaling needed
- **Production ready:** Compressed-tensors is well-supported in vLLM

### Alternative Models Considered
1. `Qwen/Qwen3.6-35B-A3B` - Full BF16 (68GB) - Too large
2. Various AWQ models - Found to use compressed-tensors instead
3. GPTQ models - Require specific config files

### Download Location
```
~/.cache/huggingface/hub/models--cyankiwi--Qwen3.6-35B-A3B-AWQ-4bit/
```

---

## Next Steps

1. ✓ Model downloaded and verified
2. ✓ LLM started successfully
3. ✓ Tests passed (models, chat, streaming)
4. ⏭ Integrate with your application
5. ⏭ Monitor performance in production
6. ⏭ Tune batch size and memory settings as needed

---

**Deployment successful! 🎉**
