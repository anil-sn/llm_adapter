# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-04-28

### Added
- **CUDA 12.x Compatibility**: Full support for CUDA 12.4+ toolkit and CUDA 12.9 driver
- **Automated Setup Script**: `scripts/setup_venv.sh` for one-command environment setup
- **CUDA Toolkit Auto-Detection**: `llm_manager.py` now auto-detects CUDA installation paths
- **Comprehensive Setup Guide**: New `SETUP_GUIDE.md` with detailed installation instructions
- **CUDA Compatibility Documentation**: `VLLM_CUDA_COMPATIBILITY.md` documenting CUDA issues and solutions
- **System Compatibility Checker**: Enhanced `scripts/check_system_compatibility.sh`

### Changed
- **vLLM Version**: Downgraded from 0.20.0 to 0.19.0 for CUDA 12.x pre-built wheel compatibility
- **PyTorch Version**: Updated to 2.10.0+cu129 (from 2.11.0+cu129)
- **Transformers Version**: Updated to 4.57.6 (compatible with vLLM 0.19)
- **KV Cache Configuration**: Changed `kv_cache_dtype` from `fp8_e5m2`/`fp8` to `auto` for vLLM 0.19 compatibility
- **Attention Backend**: Updated to use `FLASH_ATTN` (FlashAttention 2) instead of FLASHINFER
- **Environment Setup**: Migrated from vLLM 0.20 TurboQuant to vLLM 0.19 standard KV cache

### Fixed
- **CUDA Library Mismatch**: Fixed `libcudart.so.13` import error by using vLLM 0.19 with CUDA 12 wheels
- **Missing nvcc Compiler**: Added CUDA toolkit dependency documentation and auto-detection
- **KV Cache Type Error**: Fixed `kv_cache_dtype` incompatibility with FLASH_ATTN backend
- **LD_LIBRARY_PATH Configuration**: Added PyTorch CUDA libraries to library path in `llm_manager.py`
- **FlashInfer JIT Compilation**: Resolved by installing CUDA toolkit 12.4 and configuring PATH

### Removed
- vLLM 0.20+ specific features (TurboQuant 2-bit KV cache, FlashAttention 4)
- FLASHINFER attention backend requirement (replaced with FLASH_ATTN)

### Technical Details

#### Dependency Changes
```diff
- vllm>=0.20.0
+ vllm==0.19.0

- transformers>=5.0.0
+ transformers>=4.56.0,<5.0.0

- torch==2.11.0+cu129
+ torch==2.10.0+cu129
```

#### Configuration Changes
```diff
# config/config.yaml
inference:
-  kv_cache_dtype: "fp8_e5m2"
+  kv_cache_dtype: "auto"

hardware:
-  attention_backend: "FLASHINFER"
+  attention_backend: "FLASH_ATTN"

# config/config-qwen.yaml
inference:
-  kv_cache_dtype: "fp8"
+  kv_cache_dtype: "auto"
```

#### Environment Requirements
```diff
+ CUDA Toolkit 12.4+ (for nvcc compiler)
  NVIDIA Driver 575.64.03+ (CUDA 12.9 support)
  Python 3.12.3+
```

### Migration Guide

#### For Existing Installations

1. **Update Virtual Environment**:
   ```bash
   # Remove old venv
   rm -rf .venv

   # Run new setup script
   bash scripts/setup_venv.sh
   ```

2. **Install CUDA Toolkit** (if not already installed):
   ```bash
   sudo apt install cuda-nvcc-12-4 cuda-cudart-dev-12-4
   ```

3. **Update Configuration Files**:
   - Pull latest `config/config.yaml` and `config/config-qwen.yaml`
   - Or manually change `kv_cache_dtype: "fp8"` → `kv_cache_dtype: "auto"`

4. **Restart Server**:
   ```bash
   LLM_CONFIG=config-qwen.yaml python scripts/setup/llm_manager.py start
   ```

### Known Issues

- vLLM 0.19 does not support TurboQuant 2-bit KV cache (vLLM 0.20+ feature)
- FP8 KV cache works but not with FLASH_ATTN backend (use `kv_cache_dtype: "auto"`)
- Building vLLM from source requires CUDA toolkit installation

### Performance Impact

- **Context Length**: Still supports 640K tokens with YaRN 2.5x scaling
- **KV Cache**: Standard precision (auto) instead of FP8 - ~10% higher VRAM usage
- **Throughput**: Similar to vLLM 0.20 with FlashAttention 2
- **VRAM Usage**: ~43-44GB per GPU for 640K context (vs ~39-40GB with FP8)

### Compatibility Matrix

| Component | Version | CUDA Support | Status |
|-----------|---------|--------------|--------|
| vLLM | 0.19.0 | CUDA 12.x | ✅ Stable |
| PyTorch | 2.10.0+cu129 | CUDA 12.9 | ✅ Tested |
| CUDA Driver | 575.64.03+ | 12.9 | ✅ Verified |
| CUDA Toolkit | 12.4+ | 12.4 | ✅ Required |
| FlashAttention | FA2 (built-in) | 12.x | ✅ Working |

---

## [2.0.0] - Previous Release

### Initial Features
- Multi-model support (Nemotron, Qwen)
- Adapter pattern with protocol translation
- Layered configuration system
- Gateway routing
- Extended context support (up to 512K)
- GPTQ quantization support

---

## Version Numbering

- **Major** (X.0.0): Breaking changes, major architecture updates
- **Minor** (x.X.0): New features, dependency updates, backward-compatible
- **Patch** (x.x.X): Bug fixes, documentation updates

---

**Repository**: https://github.com/your-username/llm_adapter
**Documentation**: See README.md, SETUP_GUIDE.md, VLLM_CUDA_COMPATIBILITY.md
