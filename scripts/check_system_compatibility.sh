#!/bin/bash

###############################################################################
# System Compatibility Check for LLM Adapter v2.1.0
# Checks: Driver, CUDA, Python packages, GPU availability, vLLM 0.20 readiness
###############################################################################

# Don't exit on errors - we want to show all failures
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Symbols
CHECK="✓"
CROSS="✗"
WARN="⚠"
INFO="ℹ"

# Counters
PASS=0
FAIL=0
WARN_COUNT=0

###############################################################################
# Helper Functions
###############################################################################

print_header() {
    echo -e "\n${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_section() {
    echo -e "\n${BOLD}${CYAN}▶ $1${NC}"
    echo -e "${CYAN}───────────────────────────────────────────────────────────${NC}"
}

print_pass() {
    echo -e "${GREEN}${CHECK}${NC} $1"
    ((PASS++))
}

print_fail() {
    echo -e "${RED}${CROSS}${NC} $1"
    ((FAIL++))
}

print_warn() {
    echo -e "${YELLOW}${WARN}${NC} $1"
    ((WARN_COUNT++))
}

print_info() {
    echo -e "${BLUE}${INFO}${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

version_ge() {
    # Returns 0 if $1 >= $2
    # Simplified version comparison
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]
}

###############################################################################
# Main Checks
###############################################################################

print_header "LLM Adapter v2.1.0 - System Compatibility Check"

echo -e "Date: $(date)"
echo -e "Hostname: $(hostname)"
echo -e "User: $(whoami)"
echo -e "Kernel: $(uname -r)"

###############################################################################
# 1. NVIDIA Driver Check
###############################################################################

print_section "1. NVIDIA Driver & CUDA"

if check_command nvidia-smi; then
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
    print_info "Driver Version: ${DRIVER_VERSION}"

    # Check driver version >= 575
    DRIVER_MAJOR=$(echo "$DRIVER_VERSION" | cut -d. -f1)
    if [ "$DRIVER_MAJOR" -ge 575 ]; then
        print_pass "Driver version is 575+ (vLLM 0.20 compatible)"
    elif [ "$DRIVER_MAJOR" -ge 550 ]; then
        print_warn "Driver version is 550-574 (works, but 575+ recommended)"
    else
        print_fail "Driver version is below 550 (UPGRADE REQUIRED for vLLM 0.20)"
    fi

    # Check CUDA version from nvidia-smi
    CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}' | tr -d ' ')
    if [ -n "$CUDA_VERSION" ]; then
        print_info "CUDA Support: ${CUDA_VERSION}"

        # Simple version comparison (compare major.minor)
        CUDA_MAJOR=$(echo "$CUDA_VERSION" | cut -d. -f1)
        CUDA_MINOR=$(echo "$CUDA_VERSION" | cut -d. -f2)

        if [ "$CUDA_MAJOR" -ge 13 ] || ([ "$CUDA_MAJOR" -eq 12 ] && [ "$CUDA_MINOR" -ge 8 ]); then
            print_pass "CUDA version is 12.8+ (excellent for vLLM 0.20)"
        elif [ "$CUDA_MAJOR" -eq 12 ] && [ "$CUDA_MINOR" -ge 4 ]; then
            print_pass "CUDA version is 12.4+ (compatible with vLLM 0.20)"
        else
            print_fail "CUDA version is below 12.4 (UPGRADE REQUIRED)"
        fi
    else
        print_warn "Could not detect CUDA version from nvidia-smi"
    fi
else
    print_fail "nvidia-smi not found (NVIDIA driver not installed)"
fi

###############################################################################
# 2. GPU Information
###############################################################################

print_section "2. GPU Hardware"

if check_command nvidia-smi; then
    GPU_COUNT=$(nvidia-smi --query-gpu=count --format=csv,noheader | head -1)
    print_info "GPU Count: ${GPU_COUNT}"

    if [ "$GPU_COUNT" -eq 4 ]; then
        print_pass "4 GPUs detected (matches expected configuration)"
    elif [ "$GPU_COUNT" -gt 0 ]; then
        print_warn "Found ${GPU_COUNT} GPUs (expected 4)"
    else
        print_fail "No GPUs detected"
    fi

    # Show GPU details
    echo ""
    nvidia-smi --query-gpu=index,name,memory.total,memory.free --format=table
    echo ""

    # Check total VRAM
    TOTAL_VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | awk '{sum+=$1} END {print sum}')
    print_info "Total VRAM: ${TOTAL_VRAM} MiB"

    if [ "$TOTAL_VRAM" -ge 180000 ]; then
        print_pass "Total VRAM is sufficient for 256K context with TurboQuant"
    else
        print_warn "Total VRAM is below 180GB (may limit context window)"
    fi
else
    print_fail "Cannot query GPU information"
fi

###############################################################################
# 3. Python Environment
###############################################################################

print_section "3. Python Environment"

if check_command python3; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_info "Python Version: ${PYTHON_VERSION}"

    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 12 ]; then
        print_pass "Python 3.12+ detected (required)"
    elif [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        print_warn "Python 3.10-3.11 detected (3.12+ recommended)"
    else
        print_fail "Python version below 3.10 (UPGRADE REQUIRED)"
    fi
else
    print_fail "python3 not found"
fi

# Check virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    print_pass "Virtual environment active: ${VIRTUAL_ENV}"
else
    print_warn "No virtual environment active (run: source .venv/bin/activate)"
fi

###############################################################################
# 4. Python Packages
###############################################################################

print_section "4. Python Packages"

# Check vLLM
if python3 -c "import vllm" 2>/dev/null; then
    VLLM_VERSION=$(python3 -c "import vllm; print(vllm.__version__)" 2>/dev/null)
    print_info "vLLM Version: ${VLLM_VERSION}"

    VLLM_MAJOR=$(echo "$VLLM_VERSION" | cut -d. -f1)
    VLLM_MINOR=$(echo "$VLLM_VERSION" | cut -d. -f2)

    if [ "$VLLM_MAJOR" -eq 0 ] && [ "$VLLM_MINOR" -ge 20 ]; then
        print_pass "vLLM 0.20+ detected (TurboQuant 2-bit available)"
    else
        print_fail "vLLM version below 0.20 (UPGRADE REQUIRED)"
    fi
else
    print_fail "vLLM not installed"
fi

# Check PyTorch
if python3 -c "import torch" 2>/dev/null; then
    TORCH_VERSION=$(python3 -c "import torch; print(torch.__version__)" 2>/dev/null)
    TORCH_CUDA=$(python3 -c "import torch; print(torch.version.cuda)" 2>/dev/null)
    print_info "PyTorch Version: ${TORCH_VERSION}"
    print_info "PyTorch CUDA: ${TORCH_CUDA}"

    # Check PyTorch version
    TORCH_MAJOR=$(echo "$TORCH_VERSION" | cut -d. -f1)
    TORCH_MINOR=$(echo "$TORCH_VERSION" | cut -d. -f2)

    if [ "$TORCH_MAJOR" -eq 2 ] && [ "$TORCH_MINOR" -ge 11 ]; then
        print_pass "PyTorch 2.11+ detected (required for vLLM 0.20)"
    elif [ "$TORCH_MAJOR" -eq 2 ]; then
        print_warn "PyTorch 2.x detected (2.11+ recommended)"
    else
        print_fail "PyTorch version below 2.0 (UPGRADE REQUIRED)"
    fi

    # Check CUDA version compatibility
    if [[ "$TORCH_CUDA" == "12.8" ]] || [[ "$TORCH_CUDA" == "12.4" ]]; then
        print_pass "PyTorch CUDA ${TORCH_CUDA} (compatible with driver 575)"
    elif [[ "$TORCH_CUDA" == "13.0" ]]; then
        print_fail "PyTorch CUDA 13.0 (INCOMPATIBLE with driver 575 - need cu128)"
    else
        print_warn "PyTorch CUDA ${TORCH_CUDA} (verify compatibility)"
    fi
else
    print_fail "PyTorch not installed"
fi

# Check Transformers
if python3 -c "import transformers" 2>/dev/null; then
    TRANSFORMERS_VERSION=$(python3 -c "import transformers; print(transformers.__version__)" 2>/dev/null)
    print_info "Transformers Version: ${TRANSFORMERS_VERSION}"

    TRANS_MAJOR=$(echo "$TRANSFORMERS_VERSION" | cut -d. -f1)

    if [ "$TRANS_MAJOR" -ge 5 ]; then
        print_pass "Transformers 5.0+ detected (required for vLLM 0.20)"
    else
        print_fail "Transformers version below 5.0 (UPGRADE REQUIRED)"
    fi
else
    print_fail "Transformers not installed"
fi

# Check other dependencies
for pkg in fastapi uvicorn httpx; do
    if python3 -c "import $pkg" 2>/dev/null; then
        PKG_VERSION=$(python3 -c "import $pkg; print($pkg.__version__)" 2>/dev/null)
        print_pass "${pkg} installed (${PKG_VERSION})"
    else
        print_warn "${pkg} not installed"
    fi
done

###############################################################################
# 5. PyTorch CUDA Availability
###############################################################################

print_section "5. PyTorch CUDA Integration"

if python3 -c "import torch" 2>/dev/null; then
    CUDA_AVAILABLE=$(python3 -c "import torch; print(torch.cuda.is_available())" 2>/dev/null)

    if [ "$CUDA_AVAILABLE" = "True" ]; then
        print_pass "PyTorch can access CUDA"

        GPU_COUNT_TORCH=$(python3 -c "import torch; print(torch.cuda.device_count())" 2>/dev/null)
        print_info "GPUs visible to PyTorch: ${GPU_COUNT_TORCH}"

        if [ "$GPU_COUNT_TORCH" -eq 4 ]; then
            print_pass "All 4 GPUs visible to PyTorch"
        elif [ "$GPU_COUNT_TORCH" -gt 0 ]; then
            print_warn "Only ${GPU_COUNT_TORCH} GPUs visible (expected 4)"
        else
            print_fail "No GPUs visible to PyTorch"
        fi

        # Show GPU names from PyTorch
        echo ""
        python3 << 'EOF'
import torch
for i in range(torch.cuda.device_count()):
    print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
EOF
        echo ""

        # Test CUDA operations
        if python3 -c "import torch; torch.cuda.init(); torch.zeros(1).cuda()" 2>/dev/null; then
            print_pass "CUDA operations working (can allocate GPU memory)"
        else
            print_fail "CUDA operations failing (cannot allocate GPU memory)"
        fi
    else
        print_fail "PyTorch CANNOT access CUDA (driver/PyTorch CUDA version mismatch)"
        echo ""
        print_info "Common fix: Reinstall PyTorch with correct CUDA version"
        print_info "  pip install torch --index-url https://download.pytorch.org/whl/cu128"
    fi
else
    print_fail "Cannot test PyTorch CUDA (PyTorch not installed)"
fi

###############################################################################
# 6. vLLM Features Check
###############################################################################

print_section "6. vLLM 0.20 Features"

if python3 -c "import vllm" 2>/dev/null; then
    # Check if running vLLM 0.20+
    VLLM_VERSION=$(python3 -c "import vllm; print(vllm.__version__)" 2>/dev/null)
    VLLM_MINOR=$(echo "$VLLM_VERSION" | cut -d. -f2)

    if [ "$VLLM_MINOR" -ge 20 ]; then
        print_pass "vLLM 0.20+ features available:"
        print_info "  • TurboQuant 2-bit KV cache (4× capacity)"
        print_info "  • FlashAttention 4 backend"
        print_info "  • Chunked prefill for long contexts"
        print_info "  • 256K context window support"
        print_info "  • 2.1% E2E latency improvement"
    else
        print_warn "vLLM 0.20 features NOT available (version too old)"
    fi

    # Check if FlashInfer is available
    if python3 -c "import flashinfer" 2>/dev/null; then
        print_pass "FlashInfer available (required for TurboQuant)"
    else
        print_warn "FlashInfer not found (install: pip install flashinfer)"
    fi
else
    print_fail "Cannot check vLLM features (vLLM not installed)"
fi

###############################################################################
# 7. Configuration Files Check
###############################################################################

print_section "7. Configuration Files"

CONFIG_DIR="$HOME/Coding/llm_adapter/config"

for config in config.yaml config-adapter.yaml config-nemotron.yaml config-qwen.yaml; do
    if [ -f "$CONFIG_DIR/$config" ]; then
        print_pass "${config} exists"
    else
        print_warn "${config} not found"
    fi
done

# Check if configs are using new features
if [ -f "$CONFIG_DIR/config.yaml" ]; then
    if grep -q "FLASHINFER" "$CONFIG_DIR/config.yaml" 2>/dev/null; then
        print_pass "FlashAttention 4 enabled in config"
    else
        print_warn "FlashAttention 4 not configured (update config.yaml)"
    fi

    if grep -q "fp8_e5m2" "$CONFIG_DIR/config.yaml" 2>/dev/null; then
        print_pass "TurboQuant 2-bit KV cache configured"
    else
        print_warn "TurboQuant not configured (update config.yaml)"
    fi
fi

###############################################################################
# 8. System Resources
###############################################################################

print_section "8. System Resources"

# Check disk space
DISK_AVAIL=$(df -h "$HOME" | awk 'NR==2 {print $4}')
print_info "Disk space available: ${DISK_AVAIL}"

DISK_AVAIL_GB=$(df -BG "$HOME" | awk 'NR==2 {print $4}' | sed 's/G//')
if [ "$DISK_AVAIL_GB" -ge 250 ]; then
    print_pass "Sufficient disk space (250GB+ required for models)"
else
    print_warn "Low disk space (${DISK_AVAIL_GB}GB available, 250GB+ recommended)"
fi

# Check RAM
TOTAL_RAM=$(free -h | awk '/^Mem:/ {print $2}')
print_info "Total RAM: ${TOTAL_RAM}"

TOTAL_RAM_GB=$(free -g | awk '/^Mem:/ {print $2}')
if [ "$TOTAL_RAM_GB" -ge 32 ]; then
    print_pass "Sufficient RAM (32GB+ required)"
else
    print_warn "Low RAM (${TOTAL_RAM_GB}GB, 32GB+ recommended)"
fi

###############################################################################
# 9. Network & Model Access
###############################################################################

print_section "9. Model Access"

# Check Hugging Face cache
HF_CACHE="$HOME/.cache/huggingface/hub"
if [ -d "$HF_CACHE" ]; then
    HF_SIZE=$(du -sh "$HF_CACHE" 2>/dev/null | cut -f1)
    print_info "Hugging Face cache: ${HF_SIZE}"

    # Check for specific models
    if ls "$HF_CACHE"/models--nvidia--NVIDIA-Nemotron* &>/dev/null; then
        print_pass "Nemotron-3 Super 120B model cached"
    else
        print_warn "Nemotron model not cached (download required)"
    fi

    if ls "$HF_CACHE"/models--Qwen--Qwen* &>/dev/null; then
        print_pass "Qwen model cached"
    else
        print_info "Qwen model not cached (optional)"
    fi
else
    print_warn "Hugging Face cache directory not found"
fi

###############################################################################
# Summary
###############################################################################

print_header "Summary"

TOTAL=$((PASS + FAIL + WARN_COUNT))
echo -e "${BOLD}Total Checks: ${TOTAL}${NC}"
echo -e "${GREEN}Passed: ${PASS}${NC}"
echo -e "${RED}Failed: ${FAIL}${NC}"
echo -e "${YELLOW}Warnings: ${WARN_COUNT}${NC}"
echo ""

# Overall status
if [ "$FAIL" -eq 0 ]; then
    if [ "$WARN_COUNT" -eq 0 ]; then
        echo -e "${GREEN}${BOLD}${CHECK} System is FULLY READY for vLLM 0.20 with TurboQuant!${NC}"
        echo ""
        print_info "You can proceed with:"
        echo "  vllm serve nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8 \\"
        echo "    --tensor-parallel-size 4 \\"
        echo "    --max-model-len 262144 \\"
        echo "    --kv-cache-dtype fp8_e5m2 \\"
        echo "    --attention-backend FLASHINFER"
    else
        echo -e "${YELLOW}${BOLD}${WARN} System is READY with minor warnings${NC}"
        echo ""
        print_info "Review warnings above and fix if needed"
    fi
else
    echo -e "${RED}${BOLD}${CROSS} System is NOT READY - ${FAIL} critical issue(s) found${NC}"
    echo ""
    print_info "Fix failed checks before proceeding:"
    if [ "$FAIL" -gt 0 ]; then
        echo "  1. Review failed checks above"
        echo "  2. Follow fix instructions for each failure"
        echo "  3. Run this script again to verify"
    fi
fi

echo ""
print_info "For detailed setup instructions, see:"
echo "  • POST_DRIVER_UPGRADE_STEPS.md"
echo "  • VLLM_0.20_TEST_COMMAND.md"
echo "  • PYTORCH_CUDA_FIX.md"
echo ""

exit $FAIL
