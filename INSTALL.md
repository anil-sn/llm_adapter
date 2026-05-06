# Installation Guide

Complete installation instructions for the LLM Adapter.

---

## Quick Start (Production)

```bash
# Clone the repository
git clone https://github.com/your-username/llm_adapter.git
cd llm_adapter

# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Or with tool calling support
pip install -e ".[tools]"

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Download model (choose one)
bash scripts/download_qwen36_27b.sh  # Recommended: 27B model

# Start LLM
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py start

# Test installation
python -c "import llm_adapter; print('✓ Installation successful')"
curl http://localhost:8888/v1/models
```

---

## System Requirements

| Component | Requirement |
|-----------|-------------|
| **Python** | 3.12+ |
| **GPU** | 4x RTX 6000 Ada (196GB VRAM) or equivalent |
| **NVIDIA Driver** | 575.64.03+ (CUDA 12.9 support) |
| **CUDA Toolkit** | 12.4+ (for nvcc) |
| **Disk Space** | ~250GB (models + cache) |
| **RAM** | 32GB+ system memory |
| **OS** | Linux (tested on Ubuntu 22.04+) |

---

## Installation Methods

### Method 1: UV (Recommended - Fastest)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/your-username/llm_adapter.git
cd llm_adapter

# Sync dependencies
uv sync

# Or with optional dependencies
uv sync --extra tools --extra dev
```

### Method 2: Pip (Standard)

```bash
# Clone
git clone https://github.com/your-username/llm_adapter.git
cd llm_adapter

# Create venv
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install
pip install -e .           # Core only
pip install -e ".[tools]"  # With tool calling
pip install -e ".[dev]"    # With dev tools
```

### Method 3: Poetry

```bash
# Install poetry
curl -sSL https://install.python-poetry.org | python3 -

# Clone and setup
git clone https://github.com/your-username/llm_adapter.git
cd llm_adapter

# Install dependencies
poetry install
poetry install --extras "tools dev"  # With optionals
```

---

## Verifying Installation

### 1. Check Python Import
```bash
python -c "import llm_adapter; print('✓ OK')"
```

### 2. Check GPU Access
```bash
nvidia-smi
```

Expected output:
- 4x RTX 6000 Ada GPUs visible
- Driver version 575.64.03 or newer
- CUDA 12.9 or compatible

### 3. Check Dependencies
```bash
pip list | grep -E "vllm|fastapi|transformers"
```

Expected:
- vllm==0.19.0
- fastapi>=0.135.3
- transformers>=4.56.0

### 4. Run Tests
```bash
# Basic tests
pytest tests/ -v

# Comprehensive tool calling tests
python tests/test_tool_calling_comprehensive.py
```

---

## Model Download

### Qwen 3.6 27B (Recommended for throughput)
```bash
bash scripts/download_qwen36_27b.sh
```
- Size: ~18GB
- Context: 1M tokens with YaRN
- Concurrent requests: 2-3

### Qwen 3.6 35B (Recommended for quality)
```bash
# Model auto-downloads on first start
LLM_CONFIG=config/config-qwen36-35b.yaml python scripts/setup/llm_manager.py start
```
- Size: ~23GB
- Context: 1M tokens with YaRN
- Concurrent requests: 1

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
nano .env  # or your favorite editor
```

Key variables:
- `LLM_CONFIG`: Which model config to use
- `CUDA_VISIBLE_DEVICES`: Which GPUs to use
- `VLLM_GPU_MEMORY_UTILIZATION`: GPU memory usage (0.80-0.90)
- `VLLM_MAX_NUM_SEQS`: Concurrent requests (1-4)

### Model Configs

Located in `config/`:
- `config-qwen36-27b.yaml` - Production recommended
- `config-qwen36-35b.yaml` - Quality optimized
- `config-nemotron.yaml` - Nemotron-3 Super 120B
- `config-qwen.yaml` - Qwen 122B base

---

## Starting the LLM

### Using LLM Manager (Recommended)
```bash
# Start
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py start

# Status
python scripts/setup/llm_manager.py status

# Stop
python scripts/setup/llm_manager.py stop
```

### Manual Start
```bash
# Activate venv
source .venv/bin/activate

# Start vLLM
vllm serve cyankiwi/Qwen3.6-27B-AWQ-INT4 \
  --port 8000 \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 1048576

# In another terminal, start gateway
python -m llm_adapter.gateway.server
```

---

## Testing

### Quick Test
```bash
curl http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-3.6-27b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

### Tool Calling Test
```bash
python examples/tool_calling_example.py
```

### Full Test Suite
```bash
pytest tests/ -v --cov=src/llm_adapter
```

---

## Troubleshooting

### ImportError: No module named 'llm_adapter'
**Solution:** Install in editable mode
```bash
pip install -e .
```

### CUDA Out of Memory
**Solution:** Reduce GPU memory utilization
```bash
# Edit .env
VLLM_GPU_MEMORY_UTILIZATION=0.75  # Lower from 0.85
VLLM_MAX_NUM_SEQS=1                # Reduce concurrent requests
```

### vLLM Won't Start
**Solution:** Check GPU availability
```bash
nvidia-smi  # Verify GPUs visible
pkill -f vllm  # Kill zombie processes
```

### Web Search Not Working
**Solution:** Install ddgs
```bash
pip install ddgs
```

---

## Next Steps

1. **Read the docs**: Check `docs/guides/setup.md`
2. **Run examples**: Try `examples/tool_calling_example.py`
3. **Configure your model**: Edit config files in `config/`
4. **Integrate with your app**: See `examples/README.md`

---

## Support

- **Documentation**: `docs/`
- **Examples**: `examples/`
- **Issues**: GitHub Issues
- **Architecture**: `docs/ARCHITECTURE.md`

---

**Installation complete! Ready to serve LLM requests. 🚀**
