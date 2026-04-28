#!/bin/bash
# NVIDIA Driver Upgrade Script
# ⚠️  NVIDIA DRIVERS **CANNOT** BE INSTALLED IN VENV ⚠️
# Drivers are kernel modules - require root/sudo access
#
# This script generates an upgrade request for your system administrator
#
# Author: Anil Srirangapatna Nagesh
# Version: 2.0

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================"
echo "NVIDIA Driver Upgrade Utility"
echo "======================================${NC}"
echo ""
echo -e "${CYAN}IMPORTANT: NVIDIA drivers are KERNEL MODULES${NC}"
echo -e "${CYAN}They CANNOT be installed in Python venv${NC}"
echo -e "${CYAN}Root/sudo access is REQUIRED${NC}"
echo ""

# Check current driver version
echo -e "${YELLOW}[1/5] Checking current NVIDIA driver...${NC}"
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}ERROR: nvidia-smi not found. Install NVIDIA driver first.${NC}"
    exit 1
fi

CURRENT_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n1)
CUDA_VERSION=$(nvidia-smi | grep "CUDA Version:" | awk '{print $9}')

echo "  Current Driver: $CURRENT_VERSION"
echo "  Current CUDA: $CUDA_VERSION"
echo ""

# Check if upgrade is needed
MAJOR_VERSION=$(echo $CURRENT_VERSION | cut -d. -f1)
if [ "$MAJOR_VERSION" -ge 550 ]; then
    echo -e "${GREEN}✓ Driver version $CURRENT_VERSION is already compatible with CUDA 12.4+${NC}"
    echo -e "${GREEN}  No upgrade needed!${NC}"
    exit 0
fi

echo -e "${YELLOW}⚠ Driver upgrade required:${NC}"
echo "  Current: $CURRENT_VERSION (CUDA $CUDA_VERSION)"
echo "  Required: 550+ (CUDA 12.4+)"
echo ""

# Detect distribution
echo -e "${YELLOW}[2/5] Detecting Linux distribution...${NC}"
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    VERSION=$VERSION_ID
    echo "  Detected: $NAME $VERSION"
else
    echo -e "${RED}ERROR: Cannot detect Linux distribution${NC}"
    exit 1
fi

# Provide upgrade instructions
echo ""
echo -e "${YELLOW}[3/5] Upgrade Instructions:${NC}"
echo ""

case $DISTRO in
    ubuntu|debian)
        echo -e "${BLUE}For Ubuntu/Debian:${NC}"
        echo ""
        echo "  # Add NVIDIA repository"
        echo "  wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb"
        echo "  sudo dpkg -i cuda-keyring_1.1-1_all.deb"
        echo "  sudo apt-get update"
        echo ""
        echo "  # Install driver 550+"
        echo "  sudo apt-get install -y nvidia-driver-550"
        echo "  sudo reboot"
        ;;
    rhel|centos|rocky|almalinux)
        echo -e "${BLUE}For RHEL/CentOS/Rocky/AlmaLinux:${NC}"
        echo ""
        echo "  # Add NVIDIA repository"
        echo "  sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo"
        echo "  sudo dnf clean all"
        echo ""
        echo "  # Install driver 550+"
        echo "  sudo dnf install -y nvidia-driver-550"
        echo "  sudo reboot"
        ;;
    *)
        echo -e "${YELLOW}Unknown distribution. Manual installation required.${NC}"
        echo ""
        echo "Visit: https://www.nvidia.com/Download/index.aspx"
        echo "Select: Driver Type: Production Branch"
        echo "        Version: 550+ or later"
        ;;
esac

echo ""
echo -e "${YELLOW}[4/5] Alternative: Run this script with --auto flag (REQUIRES SUDO):${NC}"
echo "  sudo $0 --auto"
echo ""

echo -e "${YELLOW}[5/5] After upgrading:${NC}"
echo "  1. Reboot your system"
echo "  2. Verify with: nvidia-smi"
echo "  3. Run: uv sync"
echo "  4. Start vLLM: python scripts/setup/llm_manager.py start"
echo ""

# Generate admin request ticket
echo -e "${BLUE}=========================================${NC}"
echo -e "${YELLOW}NO SUDO ACCESS? Generate Admin Request:${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
read -p "Generate upgrade request for admin? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    REQUEST_FILE="nvidia_driver_upgrade_request_$(date +%Y%m%d_%H%M%S).txt"

    cat > "$REQUEST_FILE" << EOF
================================================================================
NVIDIA DRIVER UPGRADE REQUEST
================================================================================

Date: $(date)
Requested by: $(whoami)
Hostname: $(hostname)
Project: LLM Inference Cluster (vLLM)

================================================================================
CURRENT STATUS
================================================================================

Current Driver Version: $CURRENT_VERSION
Current CUDA Support: $CUDA_VERSION
Operating System: $NAME $VERSION

GPU Information:
$(nvidia-smi --query-gpu=name,memory.total --format=csv)

================================================================================
UPGRADE REQUIREMENT
================================================================================

Required Driver Version: 550+ (latest stable recommended)
Required CUDA Support: 12.4+

REASON:
- vLLM 0.19+ requires PyTorch 2.11+
- PyTorch 2.11+ requires CUDA 12.4+ runtime
- CUDA 12.4+ requires NVIDIA driver 550+

BUSINESS IMPACT:
- Cannot use latest vLLM with performance optimizations:
  * Triton attention backend (30%+ faster)
  * Extended context via RoPE scaling (YaRN)
  * FP8 KV cache quantization
  * Chunked prefill for long contexts
  * Auto tool choice for Claude API compatibility

- Performance degradation: ~40-50% slower inference with old vLLM versions
- Missing features required for production deployment

================================================================================
INSTALLATION STEPS (For System Administrator)
================================================================================

Distribution: $NAME $VERSION

EOF

    case $DISTRO in
        ubuntu|debian)
            cat >> "$REQUEST_FILE" << 'EOF'
# Ubuntu/Debian Installation

# 1. Add NVIDIA repository
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update

# 2. Install driver 550+ (or latest: 555, 560)
sudo apt-get install -y nvidia-driver-550

# 3. Reboot
sudo reboot

# 4. Verify installation
nvidia-smi
EOF
            ;;
        rhel|centos|rocky|almalinux)
            cat >> "$REQUEST_FILE" << 'EOF'
# RHEL/CentOS/Rocky/AlmaLinux Installation

# 1. Add NVIDIA repository
sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo
sudo dnf clean all

# 2. Install driver 550+ (or latest: 555, 560)
sudo dnf install -y nvidia-driver-550

# 3. Reboot
sudo reboot

# 4. Verify installation
nvidia-smi
EOF
            ;;
    esac

    cat >> "$REQUEST_FILE" << EOF

================================================================================
POST-INSTALLATION VERIFICATION
================================================================================

After driver upgrade and reboot, verify:

1. Driver version:
   nvidia-smi --query-gpu=driver_version --format=csv,noheader
   Expected: 550.x or higher

2. CUDA version:
   nvidia-smi | grep "CUDA Version"
   Expected: 12.4 or higher

3. GPU functionality:
   nvidia-smi
   Should show GPU list with no errors

================================================================================
DOWNTIME & ROLLBACK
================================================================================

Expected downtime: 15-30 minutes (install + reboot)
Rollback: Previous driver can be reinstalled if issues occur

================================================================================
REFERENCES
================================================================================

- NVIDIA Driver Downloads: https://www.nvidia.com/Download/index.aspx
- CUDA Compatibility: https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/
- vLLM Requirements: https://docs.vllm.ai/en/latest/getting_started/installation.html

================================================================================
CONTACT
================================================================================

For questions, contact: $(whoami)@$(hostname -d 2>/dev/null || echo "your-domain.com")

================================================================================
EOF

    echo -e "${GREEN}✓ Request generated: $REQUEST_FILE${NC}"
    echo ""
    echo "Send this file to your system administrator"
    echo "Location: $(pwd)/$REQUEST_FILE"
fi

echo ""

# Auto-install if flag provided (requires sudo)
if [ "$1" = "--auto" ]; then
    echo -e "${YELLOW}Starting automatic installation...${NC}"

    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}ERROR: --auto requires sudo privileges${NC}"
        echo -e "${RED}You do not have root access. Please use the admin request above.${NC}"
        exit 1
    fi

    case $DISTRO in
        ubuntu|debian)
            wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
            dpkg -i cuda-keyring_1.1-1_all.deb
            apt-get update
            apt-get install -y nvidia-driver-550
            echo -e "${GREEN}✓ Driver installed. Please reboot.${NC}"
            ;;
        rhel|centos|rocky|almalinux)
            dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo
            dnf clean all
            dnf install -y nvidia-driver-550
            echo -e "${GREEN}✓ Driver installed. Please reboot.${NC}"
            ;;
        *)
            echo -e "${RED}ERROR: Automatic installation not supported for $DISTRO${NC}"
            exit 1
            ;;
    esac
fi
