#!/bin/bash
# Test Prerequisites for NVIDIA Driver Installation
# Tests all requirements WITHOUT making any changes to the system

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}========================================="
echo "NVIDIA Driver Prerequisites Test"
echo "=========================================${NC}"
echo ""

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Helper functions
pass() {
    echo -e "  ${GREEN}✓ PASS${NC}: $1"
    ((PASS_COUNT++))
}

fail() {
    echo -e "  ${RED}✗ FAIL${NC}: $1"
    ((FAIL_COUNT++))
}

warn() {
    echo -e "  ${YELLOW}⚠ WARN${NC}: $1"
    ((WARN_COUNT++))
}

info() {
    echo -e "  ${CYAN}ℹ INFO${NC}: $1"
}

echo -e "${YELLOW}[1/10] Testing sudo access...${NC}"
if sudo -n true 2>/dev/null; then
    pass "Passwordless sudo available"
elif sudo true 2>/dev/null; then
    pass "Sudo access confirmed (requires password)"
else
    fail "No sudo access"
fi
echo ""

echo -e "${YELLOW}[2/10] Testing apt-get commands...${NC}"
if sudo apt-get --version &>/dev/null; then
    pass "apt-get accessible"
    if sudo apt-get update -qq 2>/dev/null; then
        pass "apt-get update works"
    else
        fail "apt-get update failed"
    fi
else
    fail "apt-get not available"
fi
echo ""

echo -e "${YELLOW}[3/10] Checking current NVIDIA driver...${NC}"
if command -v nvidia-smi &>/dev/null; then
    CURRENT_DRIVER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -n1)
    if [ -n "$CURRENT_DRIVER" ]; then
        pass "Current driver: $CURRENT_DRIVER"
        info "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)"
    else
        warn "nvidia-smi found but can't query driver version"
    fi
else
    warn "nvidia-smi not found (no current driver)"
fi
echo ""

echo -e "${YELLOW}[4/10] Checking disk space...${NC}"
DISK_SPACE=$(df /tmp | awk 'NR==2 {print $4}')
DISK_SPACE_GB=$((DISK_SPACE / 1024 / 1024))
if [ "$DISK_SPACE_GB" -gt 5 ]; then
    pass "Sufficient disk space: ${DISK_SPACE_GB}GB available in /tmp"
else
    fail "Insufficient disk space: only ${DISK_SPACE_GB}GB in /tmp (need 5GB+)"
fi
echo ""

echo -e "${YELLOW}[5/10] Testing write access to /tmp...${NC}"
TEST_FILE="/tmp/nvidia-test-$$"
if touch "$TEST_FILE" 2>/dev/null; then
    pass "Can write to /tmp"
    rm -f "$TEST_FILE"
else
    fail "Cannot write to /tmp"
fi
echo ""

echo -e "${YELLOW}[6/10] Checking kernel headers...${NC}"
KERNEL_VERSION=$(uname -r)
info "Kernel version: $KERNEL_VERSION"
if dpkg -l | grep -q "linux-headers-$KERNEL_VERSION"; then
    pass "Kernel headers installed for $KERNEL_VERSION"
elif [ -d "/lib/modules/$KERNEL_VERSION/build" ]; then
    pass "Kernel build directory exists"
else
    warn "Kernel headers not found (will install during driver setup)"
fi
echo ""

echo -e "${YELLOW}[7/10] Checking build tools...${NC}"
if command -v gcc &>/dev/null; then
    GCC_VERSION=$(gcc --version | head -n1)
    pass "GCC installed: $GCC_VERSION"
else
    warn "GCC not installed (will install during driver setup)"
fi

if command -v make &>/dev/null; then
    pass "make installed"
else
    warn "make not installed (will install during driver setup)"
fi
echo ""

echo -e "${YELLOW}[8/10] Testing network connectivity...${NC}"
# Test with a real driver URL (small HEAD request)
if wget -q --spider --timeout=5 https://us.download.nvidia.com/XFree86/Linux-x86_64/550.163.01/NVIDIA-Linux-x86_64-550.163.01.run 2>/dev/null; then
    pass "Can reach NVIDIA download servers"
elif ping -c 1 -W 2 us.download.nvidia.com &>/dev/null; then
    pass "Can reach NVIDIA servers (ping works)"
else
    fail "Cannot reach NVIDIA download servers"
fi
echo ""

echo -e "${YELLOW}[9/10] Testing kernel module operations...${NC}"
if sudo modprobe --version &>/dev/null; then
    pass "modprobe available"
else
    fail "modprobe not available"
fi

if lsmod | grep -q nvidia; then
    pass "NVIDIA modules currently loaded"
    info "Loaded modules: $(lsmod | grep nvidia | awk '{print $1}' | tr '\n' ' ')"
else
    warn "No NVIDIA modules currently loaded"
fi
echo ""

echo -e "${YELLOW}[10/10] Checking for conflicting processes...${NC}"
GPU_PROCS=$(lsof /dev/nvidia* 2>/dev/null | tail -n +2 | wc -l)
if [ "$GPU_PROCS" -eq 0 ]; then
    pass "No processes using GPU"
else
    warn "$GPU_PROCS processes using GPU (will need to stop them)"
    info "Run: python scripts/setup/llm_manager.py stop"
fi
echo ""

# Summary
echo -e "${BLUE}========================================="
echo "Test Summary"
echo "=========================================${NC}"
echo -e "  ${GREEN}Passed: $PASS_COUNT${NC}"
echo -e "  ${YELLOW}Warnings: $WARN_COUNT${NC}"
echo -e "  ${RED}Failed: $FAIL_COUNT${NC}"
echo ""

if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ All critical tests passed!${NC}"
    echo ""
    echo -e "${CYAN}Ready to install NVIDIA driver.${NC}"
    echo "Run: bash scripts/setup/install_nvidia_from_source.sh 575.64.03"
    exit 0
else
    echo -e "${RED}✗ Some critical tests failed${NC}"
    echo ""
    echo -e "${YELLOW}Fix the failures above before proceeding${NC}"
    exit 1
fi
