# Production-Grade vLLM Kernel Bootstrap Validation

This document outlines the blueprint for a robust, production-grade model routing and capability verification layer, replacing fragile static capability checks with a dynamic **Constrained-Engine Dry-Run**.

## The Problem with Low-Level Probing
Attempting to check low-level symbols directly in Triton (e.g., searching for `'float8_e8m0fnu'`) is fragile and prone to false signals. A model's execution success is an **emergent property** of multiple overlapping layers:
1. **Triton Python Bindings** (operational types)
2. **vLLM's Internal Kernel Registry** (GEMM planners)
3. **Compiled JIT Extensions** (flashinfer, quack-kernels, tilelang)
4. **CUDA Driver & PTX Toolkits** (compilation capabilities)

If any of these links is broken, a static check will lie.

## The Solution: Constrained-Engine Dry-Run
Instead of checking static registries, the gateway runs a lightweight, subprocess-level dry-run of the actual vLLM engine initialization. This forces vLLM to instantiate its entire kernel planner and compilation graph under extremely tight constraint parameters, capturing any failure immediately before allocating host or GPU memory.

### Constrained Dry-Run Command
The capability probe launches vLLM with constraints designed to initialize kernels instantly without reserving VRAM:

```bash
python3 -m vllm.entrypoints.openai.api_server \
  --model <model_id> \
  --gpu-memory-utilization 0.01 \
  --max-model-len 1 \
  --max-num-seqs 1 \
  --disable-custom-all-reduce \
  --tensor-parallel-size <tp_size>
```

### Validator Architecture Flow
```
               [ Start Model Service ]
                         │
                         ▼
        [ Run Constrained Dry-Run Probe ] ──(Fails)──► [ Fallback to BF16/FP16 ]
                         │                                         │
                    (Succeeds)                                     ▼
                         │                            [ Log Warning: Triton/FP8 ]
                         ▼                                         │
        [ Launch Production vLLM Server ]                         ▼
            (Full VRAM, Full Context)                 [ Start Server in FP16 ]
```

### Key Advantages
* **Deterministic:** Replicates the exact failure surface (kernel planning compilation).
* **Version-Resilient:** Immune to internal symbol naming changes in future Triton/vLLM updates.
* **No VRAM Contention:** Using `gpu_memory_utilization=0.01` ensures the check is fast and doesn't conflict with other active models.
