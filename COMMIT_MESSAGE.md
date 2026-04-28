# Commit Message

## Title
```
Fix: Downgrade to vLLM 0.19.0 for CUDA 12.x compatibility
```

## Description
```
This commit resolves CUDA library incompatibility issues by downgrading from
vLLM 0.20 to vLLM 0.19.0, which has pre-built wheels for CUDA 12.x.

Major Changes:
- Downgrade vLLM 0.20.0 → 0.19.0 (CUDA 12.x wheels available)
- Downgrade PyTorch 2.11.0 → 2.10.0 (compatible with vLLM 0.19)
- Update transformers 5.x → 4.57.6 (required by vLLM 0.19)
- Change kv_cache_dtype: fp8_e5m2/fp8 → auto (vLLM 0.19 compatible)
- Add CUDA toolkit auto-detection in llm_manager.py
- Document CUDA toolkit 12.4+ requirement for nvcc

Fixes:
- Fix libcudart.so.13 import error (CUDA 13 vs 12 mismatch)
- Fix kv_cache_dtype incompatibility with FLASH_ATTN backend
- Add PyTorch CUDA libraries to LD_LIBRARY_PATH
- Auto-detect CUDA installation paths

Documentation:
- Add SETUP_GUIDE.md with comprehensive installation steps
- Add VLLM_CUDA_COMPATIBILITY.md documenting CUDA issues
- Add CHANGELOG.md tracking version changes
- Update README.md with correct system requirements
- Update pyproject.toml dependencies

Configuration Updates:
- config/config.yaml: kv_cache_dtype auto, attention_backend FLASH_ATTN
- config/config-qwen.yaml: kv_cache_dtype auto
- scripts/setup_venv.sh: vLLM 0.19.0 installation
- scripts/setup/llm_manager.py: CUDA path detection, LD_LIBRARY_PATH

System Tested:
- Ubuntu 24.04
- NVIDIA Driver 575.64.03 (CUDA 12.9)
- CUDA Toolkit 12.4
- 4x RTX 6000 Ada (196GB VRAM)
- Qwen 3.5-122B model running successfully with 640K context

Breaking Changes:
- Removed vLLM 0.20 features (TurboQuant 2-bit KV cache)
- Requires CUDA toolkit installation (nvcc compiler)
- Configuration files require kv_cache_dtype: "auto" instead of "fp8"

Migration:
See CHANGELOG.md and SETUP_GUIDE.md for migration instructions.
```

## Files Changed

### Configuration
- `pyproject.toml` - Update dependencies (vLLM, transformers)
- `config/config.yaml` - Update kv_cache_dtype, attention_backend
- `config/config-qwen.yaml` - Update kv_cache_dtype

### Scripts
- `scripts/setup_venv.sh` - vLLM 0.19.0 installation
- `scripts/setup/llm_manager.py` - CUDA auto-detection, LD_LIBRARY_PATH

### Documentation
- `README.md` - Update system requirements, installation steps
- `SETUP_GUIDE.md` - NEW: Comprehensive setup guide
- `CHANGELOG.md` - NEW: Version history and changes
- `VLLM_CUDA_COMPATIBILITY.md` - NEW: CUDA compatibility documentation
- `COMMIT_MESSAGE.md` - NEW: This file

### Test Results
```
✅ Server starts successfully
✅ Model loads (Qwen 3.5-122B)
✅ 640K context working
✅ FlashAttention 2 enabled
✅ All 4 GPUs utilized
✅ API endpoints responding
```

---

## Git Commands

```bash
# Stage all changes
git add .

# Commit
git commit -m "Fix: Downgrade to vLLM 0.19.0 for CUDA 12.x compatibility

Major Changes:
- Downgrade vLLM 0.20.0 → 0.19.0 (CUDA 12.x pre-built wheels)
- Update PyTorch to 2.10.0+cu129
- Change kv_cache_dtype to 'auto' for vLLM 0.19 compatibility
- Add CUDA toolkit auto-detection
- Document CUDA 12.4+ requirement

Fixes:
- libcudart.so.13 import error
- KV cache dtype incompatibility with FLASH_ATTN
- CUDA library path configuration

Documentation:
- Add SETUP_GUIDE.md, CHANGELOG.md, VLLM_CUDA_COMPATIBILITY.md
- Update README.md and pyproject.toml

Tested: Ubuntu 24.04, Driver 575.64.03, CUDA 12.4, vLLM 0.19.0
Server running successfully with Qwen 3.5-122B (640K context)

See CHANGELOG.md for detailed changes and migration guide.
"

# Push
git push origin main
```
