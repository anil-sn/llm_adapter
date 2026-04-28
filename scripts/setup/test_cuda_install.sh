#!/bin/bash
# Test if CUDA can be installed/used without sudo
#
# IMPORTANT DISTINCTION:
# - CUDA **DRIVER** (nvidia-smi): Kernel-level, requires sudo, cannot be in venv
# - CUDA **TOOLKIT** (nvcc, libraries): Userspace, CAN be installed in venv
# - PyTorch with CUDA: CAN be installed in venv with bundled CUDA libs

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================="
echo "CUDA Installation Test (No Sudo Required)"
echo "==========================================${NC}"
echo ""

# Check current system driver
echo -e "${YELLOW}[1/4] System NVIDIA Driver (cannot change without sudo):${NC}"
if command -v nvidia-smi &> /dev/null; then
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n1)
    DRIVER_CUDA=$(nvidia-smi | grep "CUDA Version:" | awk '{print $9}')
    echo "  Driver Version: $DRIVER_VERSION"
    echo "  Max CUDA Support: $DRIVER_CUDA"
else
    echo -e "${RED}  ERROR: nvidia-smi not found${NC}"
    exit 1
fi
echo ""

# Test 1: Can we install CUDA toolkit in venv?
echo -e "${YELLOW}[2/4] Testing CUDA Toolkit installation (in venv):${NC}"
echo "  Command: uv pip install nvidia-cuda-toolkit-cu12"
echo ""
read -p "  Run this test? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    uv pip install nvidia-cuda-toolkit-cu12 2>&1 | tail -5
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ CUDA Toolkit can be installed in venv${NC}"
    else
        echo -e "${RED}  ✗ Failed to install CUDA Toolkit${NC}"
    fi
fi
echo ""

# Test 2: Can we use PyTorch with newer CUDA than system driver?
echo -e "${YELLOW}[3/4] Testing PyTorch with CUDA 12.4 (newer than driver):${NC}"
echo "  This tests if PyTorch's bundled CUDA libs work despite older driver"
echo "  Command: uv pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu124"
echo ""
read -p "  Run this test? (WARNING: will modify venv) (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    uv pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu124

    # Try to import and use CUDA
    python3 << 'PYTHON'
import torch
print(f"  PyTorch version: {torch.__version__}")
print(f"  CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"  CUDA version (PyTorch): {torch.version.cuda}")
    print(f"  GPU count: {torch.cuda.device_count()}")
    try:
        # Try to allocate tensor on GPU
        x = torch.zeros(1).cuda()
        print("  ✓ GPU tensor allocation: SUCCESS")
    except Exception as e:
        print(f"  ✗ GPU tensor allocation: FAILED - {e}")
else:
    print("  ✗ CUDA not available in PyTorch")
PYTHON
fi
echo ""

# Test 3: Check compatibility
echo -e "${YELLOW}[4/4] Driver vs Runtime Compatibility Check:${NC}"
python3 << 'PYTHON'
import subprocess
import re

# Get driver version
try:
    result = subprocess.run(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                          capture_output=True, text=True)
    driver_version = result.stdout.strip().split('\n')[0]
    driver_major = int(driver_version.split('.')[0])

    print(f"  Driver Version: {driver_version}")

    # CUDA compatibility matrix
    # https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html
    compat = {
        525: "CUDA 12.0",
        530: "CUDA 12.1",
        535: "CUDA 12.2",
        545: "CUDA 12.3",
        550: "CUDA 12.4",
        555: "CUDA 12.5",
    }

    max_cuda = None
    for min_driver, cuda_ver in sorted(compat.items()):
        if driver_major >= min_driver:
            max_cuda = cuda_ver

    print(f"  Maximum CUDA: {max_cuda}")
    print()

    if driver_major < 550:
        print("  ❌ Driver too old for PyTorch 2.11 (CUDA 12.4)")
        print("  ℹ️  PyTorch 2.11 REQUIRES driver 550+")
        print()
        print("  OPTIONS:")
        print("    A) Request sudo access to upgrade driver")
        print("    B) Use older PyTorch/vLLM (performance penalty)")
        print("    C) Ask admin to upgrade driver to 550+")
    else:
        print("  ✓ Driver compatible with latest PyTorch/vLLM")

except Exception as e:
    print(f"  Error: {e}")
PYTHON

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}SUMMARY:${NC}"
echo "  1. System driver: CANNOT be changed without sudo"
echo "  2. CUDA toolkit: CAN be installed in venv"
echo "  3. PyTorch with CUDA: CAN be installed in venv"
echo "  4. Compatibility: PyTorch runtime must match driver capabilities"
echo ""
echo -e "${YELLOW}VERDICT:${NC}"
echo "  Without sudo, you are LIMITED to CUDA versions your driver supports."
echo "  Driver 525-549 → Max CUDA 12.2 → Max PyTorch 2.2.x → Max vLLM 0.6.x"
echo "  Driver 550+    → CUDA 12.4+   → PyTorch 2.11+   → vLLM 0.19+"
echo ""
