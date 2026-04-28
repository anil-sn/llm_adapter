#!/bin/bash

###############################################################################
# Complete Virtual Environment Setup for LLM Adapter v2.1.0
# Creates venv with Python 3.12, installs all dependencies with PyTorch cu129
# Matches driver 575.64.03 (CUDA 12.9 support)
###############################################################################

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

echo "=================================================="
echo "LLM Adapter v2.1.0 - Virtual Environment Setup"
echo "=================================================="
echo ""
echo "Project: $PROJECT_DIR"
echo ""

# Check for Python 3.12 (try multiple locations)
if [ -x "/usr/local/bin/python3.12" ]; then
    PYTHON_BIN="/usr/local/bin/python3.12"
    PYTHON_VERSION=$($PYTHON_BIN --version 2>&1 | awk '{print $2}')
    echo "✓ Using Python 3.12 from /usr/local: $PYTHON_VERSION"
elif command -v python3.12 &> /dev/null; then
    PYTHON_BIN="python3.12"
    PYTHON_VERSION=$(python3.12 --version 2>&1 | awk '{print $2}')
    echo "✓ Using Python 3.12 from PATH: $PYTHON_VERSION"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 12 ]; then
        PYTHON_BIN="python3"
        echo "✓ Using system Python: $PYTHON_VERSION"
    else
        echo "❌ ERROR: Python 3.12+ required, found $PYTHON_VERSION"
        echo ""
        echo "Python 3.12 may be installed but not in PATH."
        echo "Check: ls -la /usr/local/bin/python3.12"
        exit 1
    fi
else
    echo "❌ ERROR: Python 3 not found"
    exit 1
fi
echo ""

# Step 1: Remove old venv if it exists
if [ -d "$VENV_DIR" ]; then
    echo "📦 Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
    echo "✓ Old venv removed"
    echo ""
fi

# Step 2: Check if uv is installed
if command -v uv &> /dev/null; then
    echo "📦 Creating virtual environment with uv..."
    cd "$PROJECT_DIR"
    uv venv --python $PYTHON_BIN
    echo "✓ Virtual environment created with uv"
else
    echo "📦 Creating virtual environment with $PYTHON_BIN -m venv..."
    $PYTHON_BIN -m venv "$VENV_DIR"
    echo "✓ Virtual environment created with venv"
fi
echo ""

# Step 3: Activate venv
source "$VENV_DIR/bin/activate"
echo "✓ Virtual environment activated"
echo ""

# Verify Python in venv
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PYTHON_VERSION=$($VENV_PYTHON --version 2>&1 | awk '{print $2}')

echo "Virtual environment Python: $VENV_PYTHON_VERSION"
echo "Python path: $VENV_PYTHON"
echo ""

# Step 4: Ensure pip is installed
if [ ! -f "$VENV_DIR/bin/pip" ]; then
    echo "📦 Installing pip in virtual environment..."
    $VENV_PYTHON -m ensurepip --upgrade
    echo ""
fi

# Step 4b: Upgrade pip
echo "📦 Upgrading pip, setuptools, wheel..."
$VENV_PYTHON -m pip install --upgrade pip setuptools wheel
echo ""

# Step 5: Install PyTorch cu129 FIRST (before other dependencies)
echo "=================================================="
echo "Installing PyTorch 2.11.0+cu129 (CUDA 12.9)"
echo "=================================================="
echo ""

$VENV_PYTHON -m pip install --no-cache-dir \
    torch==2.11.0+cu129 \
    torchvision==0.26.0+cu129 \
    torchaudio==2.11.0+cu129 \
    --index-url https://download.pytorch.org/whl/cu129

echo ""
echo "✓ PyTorch cu129 installed"
echo ""

# Step 6: Verify PyTorch CUDA
echo "Verifying PyTorch CUDA..."
TORCH_VERSION=$($VENV_PYTHON -c "import torch; print(torch.__version__)" 2>&1)
TORCH_CUDA=$($VENV_PYTHON -c "import torch; print(torch.version.cuda)" 2>&1)
CUDA_AVAILABLE=$($VENV_PYTHON -c "import torch; print(torch.cuda.is_available())" 2>&1)
GPU_COUNT=$($VENV_PYTHON -c "import torch; print(torch.cuda.device_count())" 2>&1)

echo "  PyTorch: $TORCH_VERSION"
echo "  CUDA:    $TORCH_CUDA"
echo "  Available: $CUDA_AVAILABLE"
echo "  GPUs:    $GPU_COUNT"
echo ""

if [ "$TORCH_CUDA" != "12.9" ]; then
    echo "❌ ERROR: PyTorch CUDA is $TORCH_CUDA (expected 12.9)"
    exit 1
fi

if [ "$CUDA_AVAILABLE" != "True" ]; then
    echo "⚠ WARNING: CUDA not available (may need system reboot)"
    echo "  This is OK if driver was just installed"
fi

echo "✓ PyTorch cu129 verified"
echo ""

# Step 7: Install vLLM with CUDA 12.9 support
echo "=================================================="
echo "Installing vLLM 0.20+ with CUDA 12.9 backend"
echo "=================================================="
echo ""

# CRITICAL: vLLM 0.20 pre-built wheels are CUDA 13 only (ABI incompatible with CUDA 12)
# We MUST build from source for CUDA 12.9

echo "Pre-built vLLM wheels are CUDA 13 (incompatible with your CUDA 12.9)"
echo "Building vLLM from source for CUDA 12.9..."
echo "⏱️  This takes ~10-15 minutes, but ensures compatibility"
echo ""

# Set CUDA build environment
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
export TORCH_CUDA_ARCH_LIST="8.0;8.6;8.9;9.0"  # RTX 6000 Ada = 8.9
export MAX_JOBS=$(nproc)
export VLLM_TARGET_DEVICE=cuda

# Install build dependencies
echo "Installing build dependencies..."
$VENV_PYTHON -m pip install --upgrade pip setuptools wheel ninja packaging cmake

# Build vLLM from source (no isolation ensures it uses venv's PyTorch CUDA 12)
echo ""
echo "Building vLLM from source (patience required)..."
$VENV_PYTHON -m pip install --no-build-isolation -v "vllm==0.20.0"

echo ""
echo "✓ vLLM 0.20 built successfully for CUDA 12.9"
echo ""

# Step 8: Install other dependencies with pip
echo "=================================================="
echo "Installing other dependencies"
echo "=================================================="
echo ""

$VENV_PYTHON -m pip install \
    "transformers>=5.0.0" \
    "fastapi>=0.135.3" \
    "uvicorn>=0.44.0" \
    "httpx>=0.28.1" \
    "huggingface-hub>=0.36.2" \
    "hf-transfer>=0.1.9" \
    "pyyaml>=6.0.3"

echo ""
echo "✓ All dependencies installed"
echo ""

# Step 9: Install llm-adapter package (nemo_orchestrator module)
echo "=================================================="
echo "Installing llm-adapter package"
echo "=================================================="
echo ""

cd "$PROJECT_DIR"
$VENV_PYTHON -m pip install -e .

echo ""
echo "✓ llm-adapter package installed"
echo ""

# Step 10: Verify critical packages
echo "=================================================="
echo "Verifying Critical Packages"
echo "=================================================="
echo ""

# vLLM
if $VENV_PYTHON -c "import vllm" 2>/dev/null; then
    VLLM_VERSION=$($VENV_PYTHON -c "import vllm; print(vllm.__version__)" 2>&1)
    echo "✓ vLLM: $VLLM_VERSION"
else
    echo "❌ vLLM not installed"
fi

# Transformers
if $VENV_PYTHON -c "import transformers" 2>/dev/null; then
    TRANSFORMERS_VERSION=$($VENV_PYTHON -c "import transformers; print(transformers.__version__)" 2>&1)
    echo "✓ Transformers: $TRANSFORMERS_VERSION"
else
    echo "❌ Transformers not installed"
fi

# FastAPI
if $VENV_PYTHON -c "import fastapi" 2>/dev/null; then
    FASTAPI_VERSION=$($VENV_PYTHON -c "import fastapi; print(fastapi.__version__)" 2>&1)
    echo "✓ FastAPI: $FASTAPI_VERSION"
else
    echo "❌ FastAPI not installed"
fi

# nemo_orchestrator (local package)
if $VENV_PYTHON -c "from nemo_orchestrator.adapters.factory import get_adapter" 2>/dev/null; then
    echo "✓ nemo_orchestrator: Package installed and importable"
else
    echo "❌ nemo_orchestrator: Package not installed"
fi

echo ""

# Step 11: Final verification
echo "=================================================="
echo "Final System Check"
echo "=================================================="
echo ""

# Check NVIDIA driver
if command -v nvidia-smi &> /dev/null; then
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
    echo "✓ NVIDIA Driver: $DRIVER_VERSION"
else
    echo "⚠ NVIDIA driver not found"
fi

# GPU count
if command -v nvidia-smi &> /dev/null; then
    GPU_COUNT_SYSTEM=$(nvidia-smi --query-gpu=count --format=csv,noheader | head -1)
    echo "✓ GPUs detected: $GPU_COUNT_SYSTEM"
fi

echo ""
echo "=================================================="
echo "✅ Virtual Environment Setup Complete!"
echo "=================================================="
echo ""
echo "Activation command:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "Or from project root:"
echo "  source .venv/bin/activate"
echo ""
echo "Next steps:"
echo "  1. Activate venv: source .venv/bin/activate"
echo "  2. Verify setup: bash scripts/check_system_compatibility.sh"
echo "  3. Test vLLM: See VLLM_0.20_TEST_COMMAND.md"
echo ""
