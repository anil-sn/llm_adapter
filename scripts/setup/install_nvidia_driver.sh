#!/bin/bash
# Install latest NVIDIA driver for CUDA 12.4+ support
# Run with: sudo bash scripts/setup/install_nvidia_driver.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: This script must be run with sudo${NC}"
    echo "Usage: sudo bash $0"
    exit 1
fi

echo -e "${BLUE}========================================="
echo "NVIDIA Driver Installation"
echo "==========================================${NC}"
echo ""

# Search for available nvidia drivers
echo -e "${YELLOW}[1/4] Searching for available NVIDIA drivers...${NC}"
echo ""

apt-cache search "^nvidia-driver-[0-9]" | grep -E "nvidia-driver-[0-9]+" | sort -V | tail -10

echo ""
echo -e "${YELLOW}[2/4] Recommended packages:${NC}"

# Check what's available
if apt-cache show nvidia-driver-550 &>/dev/null; then
    DRIVER_PKG="nvidia-driver-550"
    echo "  ✓ nvidia-driver-550 (CUDA 12.4)"
elif apt-cache show nvidia-driver-555 &>/dev/null; then
    DRIVER_PKG="nvidia-driver-555"
    echo "  ✓ nvidia-driver-555 (CUDA 12.5)"
elif apt-cache show nvidia-driver-560 &>/dev/null; then
    DRIVER_PKG="nvidia-driver-560"
    echo "  ✓ nvidia-driver-560 (CUDA 12.6)"
elif apt-cache show cuda-drivers &>/dev/null; then
    DRIVER_PKG="cuda-drivers"
    echo "  ✓ cuda-drivers (meta-package, latest stable)"
else
    echo -e "${RED}  ERROR: No suitable driver package found${NC}"
    echo ""
    echo "Available packages:"
    apt-cache search nvidia-driver | grep "^nvidia-driver-[0-9]"
    exit 1
fi

echo ""
echo -e "${YELLOW}Selected package: $DRIVER_PKG${NC}"
echo ""
read -p "Install $DRIVER_PKG? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo -e "${YELLOW}[3/4] Installing $DRIVER_PKG...${NC}"

# Remove old drivers first
echo "  Removing old drivers..."
apt-get remove --purge -y 'nvidia-*' || true
apt-get autoremove -y

# Install new driver
echo "  Installing $DRIVER_PKG..."
apt-get install -y "$DRIVER_PKG"

echo ""
echo -e "${GREEN}✓ Driver installation complete!${NC}"
echo ""

echo -e "${YELLOW}[4/4] Next steps:${NC}"
echo "  1. REBOOT your system: sudo reboot"
echo "  2. After reboot, verify: nvidia-smi"
echo "  3. Expected driver: 550+ with CUDA 12.4+"
echo "  4. Then run: cd ~/Coding/llm_adapter && uv sync"
echo "  5. Start vLLM: python scripts/setup/llm_manager.py start"
echo ""

read -p "Reboot now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Rebooting in 5 seconds...${NC}"
    sleep 5
    reboot
else
    echo -e "${YELLOW}Remember to reboot before using the new driver!${NC}"
fi
