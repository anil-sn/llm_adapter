# vLLM CUDA Compatibility Issue & Solution

## Problem Summary

**Error:**
```
ImportError: libcudart.so.13: cannot open shared object file: No such file or directory
```

**Root Cause:**
- vLLM 0.20+ pre-built wheels from PyPI are compiled against **CUDA 13**
- Your system has **CUDA 12.9** (Driver 575.64.03)
- CUDA runtime libraries have **ABI symbol version mismatches** between major versions
- Simple symlinks (`libcudart.so.13 -> libcudart.so.12`) fail due to missing symbol versions

## Deep Analysis

### Library Dependencies

vLLM's `_C.abi3.so` binary requires:
```bash
$ ldd vllm/_C.abi3.so
    libcudart.so.13 => not found          # CUDA 13 runtime (incompatible)
    libtorch.so => not found              # From PyTorch
    libtorch_cuda.so => not found         # From PyTorch
    libc10_cuda.so => not found           # From PyTorch
```

### Why Symlinks Don't Work

```bash
$ ln -s libcudart.so.12 libcudart.so.13
$ ldd vllm/_C.abi3.so
    libcudart.so.13: version `libcudart.so.13' not found
```

The binary looks for **specific symbol versions** (e.g., `libcudart.so.13@@LIBCUDART_13.0`) that don't exist in CUDA 12.

## Solutions

### ✅ Solution 1: Build vLLM from Source (Recommended)

**Pros:**
- Guaranteed CUDA 12.9 compatibility
- Uses your system's CUDA version
- No ABI mismatch issues

**Cons:**
- Takes 10-15 minutes to compile
- Requires build tools (cmake, ninja)

**Implementation:**
```bash
# Already integrated into scripts/setup_venv.sh
export CUDA_HOME=/usr/local/cuda
export TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"
export MAX_JOBS=$(nproc)
export VLLM_TARGET_DEVICE=cuda

pip install --no-build-isolation -v "vllm==0.20.0"
```

### ⚠️ Solution 2: Downgrade to vLLM 0.19 (Fallback)

vLLM 0.19 has CUDA 12.x pre-built wheels:
```bash
pip install "vllm==0.19.0" --torch-backend=cu124
```

**Trade-offs:**
- Loses vLLM 0.20 features (TurboQuant 2-bit, FlashAttention 4)
- Easier/faster installation
- Good for quick testing

### ❌ Solution 3: Install CUDA 13 Runtime (Not Recommended)

Installing CUDA 13 libraries alongside CUDA 12:
```bash
# Don't do this - creates system conflicts
apt install cuda-cudart-13-0
```

**Why avoid:**
- Driver conflicts
- System instability
- Doesn't solve PyTorch library version issues

## Verification

After building from source, verify:
```bash
# 1. Check vLLM can import
python -c "import vllm; print(vllm.__version__)"

# 2. Check all libraries resolve
export LD_LIBRARY_PATH="$VENV/lib/python3.12/site-packages/torch/lib:$LD_LIBRARY_PATH"
ldd $VENV/lib/python3.12/site-packages/vllm/_C.abi3.so | grep "not found"
# Should return nothing

# 3. Test vLLM server
python -m vllm.entrypoints.openai.api_server --model facebook/opt-125m
```

## Reference

- Your System: CUDA 12.9 (Driver 575.64.03)
- PyTorch: 2.11.0+cu129
- vLLM: 0.20.0 (source build)
- GPUs: 4x NVIDIA RTX 6000 Ada (Compute 8.9)

## Related Files

- `scripts/setup_venv.sh` - Automated setup with source build
- `scripts/setup/llm_manager.py` - Sets `LD_LIBRARY_PATH` for PyTorch libs
- This document - VLLM_CUDA_COMPATIBILITY.md
