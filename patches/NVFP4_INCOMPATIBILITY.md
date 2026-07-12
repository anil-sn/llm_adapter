# NVFP4 Model Incompatibility Issue

## Problem

The `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` model cannot be loaded with vLLM 0.20.2 when using tensor parallelism = 4.

## Root Cause (Complete 5 Whys Analysis)

**Why #1:** vLLM crashes with `RuntimeError: size_n = 672, actual_size_n = 704`

**Why #2:** The Marlin FP4 kernel requires weight dimensions divisible by 64, but the model has intermediate_size=2688, which when split across 4 GPUs gives 672 (not divisible by 64)

**Why #3:** We attempted to pad tensors from 672→704, but the `gptq_marlin_repack` C++ kernel validates that the input tensor size matches the declared `size_n` parameter BEFORE repacking

**Why #4:** The padding must happen at the C++ kernel level, not in Python preprocessing, because the kernel performs dimension validation on the raw input tensor

**Why #5:** **ROOT CAUSE:** vLLM's NVFP4 Marlin kernel implementation doesn't support automatic dimension padding for non-64-aligned architectures (unlike the FP8 variant which has padding logic)

## Attempted Fixes

###Fix Attempt #1: Add Python-level padding in `marlin_utils_fp4.py`
- **Result:** Failed - kernel validates input tensor size before accepting padding parameter
- **Error:** `RuntimeError: size_n = 672, actual_size_n = 704`

### Fix Attempt #2: Update `layer.moe_config.intermediate_size_per_partition`  
- **Result:** Failed - runtime uses actual tensor dimensions, not config values
- **Error:** Same dimension mismatch

### Fix Attempt #3: Enable V1 API
- **Result:** Failed - same kernel incompatibility in V1
- **Error:** Same

## Why FP8 Works But FP4 Doesn't

The FP8 Marlin implementation (`marlin_utils_fp8.py`) has:
```python
# size_n may not divisible by block_size[0]
scales = scales[:, :part_size_n]  # Truncation/padding logic
```

The FP4 implementation (`marlin_utils_fp4.py`) lacks this, and the underlying C++ kernel is stricter.

## Recommended Solutions

### Option 1: Use FP8 Model Variant (RECOMMENDED)
```bash
# Use config-nemotron.yaml instead
export LLM_CONFIG=config/config-nemotron.yaml
```

**Pros:**
- Works out of the box
- Well-tested and stable
- Similar performance

**Cons:**
- Uses more VRAM (~30GB more total across 4 GPUs)
- Slightly larger model size

### Option 2: Use Different Tensor Parallelism
```bash
# TP=2 gives 1344 per GPU (divisible by 64)
# TP=1 gives 2688 (divisible by 64) 
```

**Pros:**
- Can use NVFP4 model

**Cons:**
- Requires 2×RTX 6000 Ada or 1×H100/A100 with enough VRAM
- Reduced throughput with lower parallelism

### Option 3: Wait for vLLM Fix
Track upstream: https://github.com/vllm-project/vllm/issues

**Pros:**
- Future-proof

**Cons:**
- Blocks current deployment
- No ETA on fix

## Configuration Changes Made

### Working: FP8 Model
File: `config/config-nemotron.yaml`
- Model: `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8`
- KV Cache: FP8 compatible
- VRAM: ~85GB total (4 GPUs)

### Not Working: NVFP4 Model  
Files: `config/config-nemotron-super.yaml`, `config/config-nemotron-super-no-mtp.yaml`
- Model: `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`
- Issue: Dimension incompatibility (672 not divisible by 64)
- Status: **BLOCKED on vLLM kernel limitation**

## Technical Details

- Model intermediate_size: 2688
- Tensor parallel size: 4
- Per-GPU dimension: 2688 ÷ 4 = 672
- Required: Multiple of 64
- Gap: 672 % 64 = 32 (padding needed: 32 → 704)

## Files Modified (Experimental - Not Working)

- `.venv/.../vllm/.../marlin_utils_fp4.py` (attempted padding)
- `patches/marlin_utils_fp4.py.backup` (original backup)

**Note:** These modifications did not resolve the issue and can be reverted.

## Conclusion

**Use `config/config-nemotron.yaml` (FP8 variant) for production deployment.**

The NVFP4 model is not compatible with current vLLM + this specific tensor parallelism configuration due to kernel-level dimension constraints.
