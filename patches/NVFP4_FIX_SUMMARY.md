# NVFP4 Marlin FP4 Padding Fix - Applied Successfully

## Issue
`RuntimeError: size_n = 672 is not divisible by tile_n_size = 64`

## Root Cause
Model's intermediate_size (2688) ÷ tensor_parallel_size (4) = 672, which isn't divisible by Marlin kernel's required tile size of 64.

## Solution Applied
Patched vLLM's `marlin_utils_fp4.py` to add dimension padding (672 → 704) before Marlin repacking.

## How to Re-apply After vLLM Upgrade
```bash
./scripts/apply_vllm_patches.sh
```

The script is idempotent - safe to run multiple times.

## Verification
Model successfully loaded with:
- VRAM: ~19.7GB per GPU (78.8GB total)
- Context: 256K tokens  
- KV Cache: FP8
- Inference: Working ✓

## Files Modified
- `.venv/lib/python3.12/site-packages/vllm/model_executor/layers/quantization/utils/marlin_utils_fp4.py`

## Backups
- `patches/marlin_utils_fp4.py.backup.*` (timestamped)

## Memory Leak Investigation Needed
User reported memory leaks during long runs - needs investigation.
