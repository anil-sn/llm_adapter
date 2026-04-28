# Complete Setup Guide - LLM Adapter v2.1.0

## Overview

This guide covers the complete installation and configuration of the LLM Adapter system with vLLM 0.19.0, optimized for CUDA 12.x compatibility.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Quick Start](#quick-start)
3. [Detailed Installation](#detailed-installation)
4. [Troubleshooting](#troubleshooting)
5. [Configuration](#configuration)
6. [Testing](#testing)

---

## System Requirements

### Hardware

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| **GPU** | 4x RTX 6000 Ada (48GB each) | Same | 196GB total VRAM |
| **CPU** | 16 cores | 32+ cores | PCIe topology (non-NVLink) |
| **RAM** | 32GB | 64GB+ | For model loading |
| **Storage** | 250GB SSD | 500GB NVMe | Model weights + cache |

### Software

| Component | Version | Notes |
|-----------|---------|-------|
| **OS** | Ubuntu 22.04+ | Tested on 24.04 |
| **Python** | 3.12.3+ | Required for type hints |
| **NVIDIA Driver** | 575.64.03+ | CUDA 12.9 support |
| **CUDA Toolkit** | 12.4+ | For nvcc (FlashAttention JIT) |
| **vLLM** | 0.19.0 | CUDA 12.x pre-built wheels |
| **PyTorch** | 2.10.0+cu129 | Installed automatically |

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-username/llm_adapter.git
cd llm_adapter
```

### 2. Check System Compatibility

```bash
bash scripts/check_system_compatibility.sh
```

**Expected Output:**
- ✅ NVIDIA Driver 575.64.03+
- ✅ 4 GPUs detected
- ✅ Python 3.12+
- ⚠️ nvcc not found (OK - will install)

### 3. Run Automated Setup

```bash
bash scripts/setup_venv.sh
```

**This script handles:**
- Virtual environment creation
- PyTorch 2.10.0+cu129 installation
- vLLM 0.19.0 installation
- All dependencies
- Verification tests

**Duration:** ~5-10 minutes (downloads ~3GB)

### 4. Install CUDA Toolkit (if needed)

```bash
# Check if nvcc is available
nvcc --version

# If not found, install CUDA toolkit
sudo apt update
sudo apt install cuda-nvcc-12-4 cuda-cudart-dev-12-4

# Verify
nvcc --version  # Should show 12.4.x
```

### 5. Activate Environment

```bash
source .venv/bin/activate
```

### 6. Start Server

```bash
# Start Qwen model (recommended)
LLM_CONFIG=config-qwen.yaml python scripts/setup/llm_manager.py start

# Check status
tail -f logs/vllm_replica_0.log
```

**Success indicators:**
```
Loading safetensors checkpoint shards: 100% Completed
Capturing CUDA graphs: 100%
INFO:     Application startup complete.
```

### 7. Test Server

```bash
# Test health endpoint
curl http://127.0.0.1:8000/health

# Test models endpoint
curl http://127.0.0.1:8000/v1/models
```

---

## Detailed Installation

### Step 1: Prerequisites

#### Install Python 3.12

```bash
# Check current version
python3 --version

# If not 3.12+, install
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
```

#### Verify NVIDIA Driver

```bash
nvidia-smi

# Should show:
# - Driver Version: 575.64.03 or higher
# - CUDA Version: 12.9
# - 4 GPUs listed
```

If driver is outdated, see [NVIDIA Driver Upgrade](#nvidia-driver-upgrade).

### Step 2: Environment Setup

#### Option A: Automated Setup (Recommended)

```bash
cd /path/to/llm_adapter
bash scripts/setup_venv.sh
```

The script will:
1. ✅ Detect Python 3.12
2. ✅ Create virtual environment at `.venv`
3. ✅ Upgrade pip, setuptools, wheel
4. ✅ Install PyTorch 2.10.0+cu129
5. ✅ Install vLLM 0.19.0
6. ✅ Install all dependencies
7. ✅ Install llm-adapter package
8. ✅ Verify installation

#### Option B: Manual Setup

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install PyTorch with CUDA 12.9
pip install torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 \
    --index-url https://download.pytorch.org/whl/cu129

# Verify PyTorch CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPUs: {torch.cuda.device_count()}')"

# Install vLLM 0.19.0
pip install vllm==0.19.0

# Install other dependencies
pip install transformers>=4.56.0,<5.0.0 \
    fastapi>=0.135.3 \
    uvicorn>=0.44.0 \
    httpx>=0.28.1 \
    huggingface-hub>=0.36.2 \
    pyyaml>=6.0.3

# Install llm-adapter package
pip install -e .
```

### Step 3: CUDA Toolkit Installation

vLLM 0.19 uses FlashAttention which requires `nvcc` for JIT compilation.

```bash
# Check if nvcc exists
which nvcc
nvcc --version

# If not found, install CUDA toolkit 12.4
sudo apt update
sudo apt install cuda-nvcc-12-4 cuda-cudart-dev-12-4

# This installs:
# - /usr/local/cuda-12.4/bin/nvcc (compiler)
# - CUDA headers and libraries
# Size: ~250MB

# Verify installation
nvcc --version
ls -la /usr/local/cuda-12.4/bin/nvcc

# Add to PATH (optional, llm_manager.py auto-detects)
export PATH=/usr/local/cuda-12.4/bin:$PATH
```

### Step 4: Verification

```bash
# Run comprehensive system check
bash scripts/check_system_compatibility.sh

# Should show:
# ✅ NVIDIA Driver 575.64.03+
# ✅ 4 GPUs detected
# ✅ Python 3.12+
# ✅ vLLM 0.19.0
# ✅ PyTorch 2.10.0+cu129
# ✅ nvcc found
```

### Step 5: Model Configuration

#### Qwen Model (Recommended)

```bash
# Check if model is cached
ls -lh ~/.cache/huggingface/hub/ | grep Qwen3.5-122B

# If not cached, it will download on first start (~120GB)
# Ensure you have HF_TOKEN set if model requires authentication
export HF_TOKEN=your_token_here
```

#### Configuration Files

```bash
# View available configurations
ls config/

# Base config (shared settings)
config/config.yaml

# Adapter routing rules
config/config-adapter.yaml

# Model-specific configs
config/config-qwen.yaml      # Qwen 122B (recommended)
config/config-nemotron.yaml  # Nemotron 120B
```

---

## Troubleshooting

### Issue 1: CUDA Library Mismatch

**Error:**
```
ImportError: libcudart.so.13: cannot open shared object file
```

**Cause:** vLLM wheel compiled for CUDA 13, but system has CUDA 12

**Solution:**
- ✅ vLLM 0.19.0 has CUDA 12 wheels (already handled by setup script)
- If you manually installed vLLM 0.20+, downgrade: `pip install vllm==0.19.0`

### Issue 2: Missing nvcc Compiler

**Error:**
```
RuntimeError: Could not find nvcc
```

**Cause:** FlashAttention requires nvcc for JIT compilation

**Solution:**
```bash
sudo apt install cuda-nvcc-12-4 cuda-cudart-dev-12-4
```

### Issue 3: KV Cache Type Not Supported

**Error:**
```
ValueError: Selected backend FLASH_ATTN is not valid
Reason: ['kv_cache_dtype not supported']
```

**Cause:** Using `kv_cache_dtype: fp8` or `fp8_e5m2` (vLLM 0.20 features)

**Solution:**
```yaml
# In config-qwen.yaml, change to:
inference:
  kv_cache_dtype: "auto"  # Compatible with vLLM 0.19
```

### Issue 4: GPU Out of Memory

**Error:**
```
torch.cuda.OutOfMemoryError: CUDA out of memory
```

**Solutions:**
1. Reduce `gpu_memory_utilization`:
   ```yaml
   hardware:
     gpu_memory_utilization: 0.75  # Try lower values
   ```

2. Reduce context length:
   ```yaml
   inference:
     max_model_len: 524288  # Try 512K instead of 640K
   ```

3. Reduce batch size:
   ```yaml
   inference:
     max_num_seqs: 1  # Reduce from 2
   ```

### Issue 5: Server Crashes on Startup

**Check logs:**
```bash
# View full startup log
cat logs/vllm_replica_0.log

# Check for specific errors
grep -i "error\|failed\|exception" logs/vllm_replica_0.log
```

**Common fixes:**
1. Ensure no other vLLM processes running:
   ```bash
   pkill -f vllm
   ```

2. Clear VRAM:
   ```bash
   sudo fuser -v /dev/nvidia* | awk '{print $2}' | xargs -r kill -9
   ```

3. Restart with clean state:
   ```bash
   python scripts/setup/llm_manager.py stop
   sleep 5
   python scripts/setup/llm_manager.py start
   ```

---

## Configuration

### Key Configuration Files

#### 1. Base Configuration (`config/config.yaml`)

```yaml
hardware:
  tensor_parallel_size: 4           # Match number of GPUs
  device: "cuda"
  dtype: "auto"
  attention_backend: "FLASH_ATTN"  # Best performance
  gpu_memory_utilization: 0.80      # Adjust if OOM

inference:
  kv_cache_dtype: "auto"             # vLLM 0.19 compatible
  enable_prefix_caching: true
  enable_chunked_prefill: true
```

#### 2. Model-Specific (`config/config-qwen.yaml`)

```yaml
model:
  id: "Qwen/Qwen3.5-122B-A10B-GPTQ-Int4"
  served_model_name: "qwen-3.5-122b"

quantization:
  method: "gptq"                     # Int4 quantization

inference:
  max_model_len: 655360              # 640K tokens
  kv_cache_dtype: "auto"             # Must be "auto" for vLLM 0.19

  rope_scaling:                      # YaRN 2.5x scaling
    type: "yarn"
    factor: 2.5
    original_max_position_embeddings: 262144
```

### Environment Variables

```bash
# Model selection
export LLM_CONFIG=config-qwen.yaml

# Hugging Face token (if needed)
export HF_TOKEN=your_token_here

# CUDA configuration
export CUDA_HOME=/usr/local/cuda-12.4
export PATH=$CUDA_HOME/bin:$PATH
```

---

## Testing

### 1. System Compatibility Test

```bash
bash scripts/check_system_compatibility.sh
```

### 2. Server Health Check

```bash
# Start server
LLM_CONFIG=config-qwen.yaml python scripts/setup/llm_manager.py start

# Wait for startup (watch logs)
tail -f logs/vllm_replica_0.log

# Test health endpoint
curl http://127.0.0.1:8000/health

# List models
curl http://127.0.0.1:8000/v1/models | jq
```

### 3. Inference Test

```bash
# Simple completion test
curl -X POST http://127.0.0.1:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-3.5-122b",
    "prompt": "Hello, how are you?",
    "max_tokens": 50
  }' | jq
```

### 4. Performance Test

```bash
# Monitor GPU usage
watch -n 1 nvidia-smi

# Check logs for throughput
tail -f logs/vllm_replica_0.log | grep -i "throughput\|tokens"
```

---

## Additional Resources

- **CUDA Compatibility**: See `VLLM_CUDA_COMPATIBILITY.md`
- **API Documentation**: See `docs/API_REFERENCE.md`
- **Configuration Guide**: See `docs/CONFIGURATION.md`
- **Troubleshooting**: See `docs/TROUBLESHOOTING.md`

---

## Support

For issues or questions:
1. Check logs: `logs/vllm_replica_0.log`
2. Run diagnostics: `bash scripts/check_system_compatibility.sh`
3. Review compatibility doc: `VLLM_CUDA_COMPATIBILITY.md`
4. Open an issue on GitHub

---

**Last Updated**: 2026-04-28
**Version**: 2.1.0
**Tested Configuration**: Ubuntu 24.04, Driver 575.64.03, CUDA 12.4, vLLM 0.19.0
