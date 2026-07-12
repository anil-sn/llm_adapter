# vLLM NVFP4 Marlin Kernel Dimension Padding Fix

## Problem

When loading NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 with tensor parallelism, vLLM crashes with:

```
RuntimeError: size_n = 672 is not divisible by tile_n_size = 64
```

## Root Cause Analysis (5 Whys)

1. **Why did vLLM crash?** → Marlin kernel rejects dimension 672
2. **Why does it reject 672?** → Kernel requires dimensions divisible by 64
3. **Why is the dimension 672?** → Model's intermediate_size (2688) ÷ tensor_parallel (4) = 672
4. **Why no padding?** → marlin_utils_fp4.py lacks dimension padding logic present in marlin_utils_fp8.py
5. **Why is padding missing?** → FP4 support was added later without dimension compatibility checks

## Solution

Patched `/path/to/venv/lib/python3.12/site-packages/vllm/model_executor/layers/quantization/utils/marlin_utils_fp4.py` to:

1. Add `pad_to_tile()` function to round dimensions up to nearest multiple of 64
2. Pad weight tensors before repacking (w2: 672 → 704)
3. Apply same padding to scale tensors

## Changes Made

### File Modified
- `.venv/lib/python3.12/site-packages/vllm/model_executor/layers/quantization/utils/marlin_utils_fp4.py`

### Backup
- `patches/marlin_utils_fp4.py.backup` (original vLLM 0.20.2)

### Key Changes
1. Added TILE_SIZE constant (64)
2. Added pad_to_tile() helper function
3. Modified repack_weight() to pad weight tensors
4. Modified premute_scales() to use padded dimensions

## Verification

```bash
# Restart vLLM to test
python scripts/setup/llm_manager.py restart

# Watch logs for successful loading
tail -F logs/vllm_replica_0.log
```

Expected: Model loads without dimension errors.

## Dimensions

| Component | Original | Padded | Padding |
|-----------|----------|--------|---------|
| w13 (gate+up) | 1344 | 1344 | 0 (already divisible) |
| w2 (down) | 672 | 704 | 32 |

## Notes

- This fix mirrors the approach used in vLLM's FP8 Marlin utils
- Padding is zero-filled and shouldn't affect model accuracy
- Fix is specific to vLLM 0.20.2 - may be resolved in future versions
- Applied to both config-nemotron-super.yaml and config-nemotron-super-no-mtp.yaml

## Alternative Solutions Considered

1. ❌ Use FP8 model variant - Works but uses more VRAM
2. ❌ Reduce tensor parallelism - Would fit dimension but reduce performance
3. ✅ **Pad dimensions** - Zero overhead, maintains performance
4. ❌ Wait for upstream fix - Blocks current deployment

## Upstream Issue

Consider reporting to vLLM project: https://github.com/vllm-project/vllm/issues
