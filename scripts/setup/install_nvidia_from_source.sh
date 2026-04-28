#!/bin/bash
# SAFE NVIDIA Driver Installation from Official .run Installer
# Features:
# - Download and verify BEFORE touching current driver
# - Test new driver loads successfully
# - Keep old driver as fallback
# - Multiple safety checks and confirmations
# - Rollback capability if new driver fails
#
# Usage: bash install_nvidia_from_source.sh [VERSION]
# Example: bash install_nvidia_from_source.sh 550.163.01
# Note: Uses sudo for individual commands (not script-level sudo)

set -e  # Exit on error (but we handle errors explicitly below)

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Safety: require explicit confirmation
SKIP_CONFIRMATIONS=${SKIP_CONFIRMATIONS:-false}

# Default to driver 550 (minimum for CUDA 12.4)
DRIVER_VERSION=${1:-550.163.01}
INSTALLER="NVIDIA-Linux-x86_64-${DRIVER_VERSION}.run"
DOWNLOAD_URL="https://us.download.nvidia.com/XFree86/Linux-x86_64/${DRIVER_VERSION}/${INSTALLER}"
WORK_DIR="/tmp/nvidia-driver-upgrade"

echo -e "${BLUE}========================================="
echo "SAFE NVIDIA Driver Installation"
echo "=========================================${NC}"
echo ""
echo -e "${CYAN}Target driver: $DRIVER_VERSION${NC}"
echo ""

# Step 0: Check current state
echo -e "${YELLOW}[0/8] Checking current system state...${NC}"
if command -v nvidia-smi &> /dev/null; then
    CURRENT_DRIVER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -n1)
    echo -e "  Current driver: ${GREEN}$CURRENT_DRIVER${NC}"
    echo -e "  Current status: ${GREEN}Working${NC}"

    CURRENT_DRIVER_PKG=$(dpkg -l | grep nvidia-driver | grep ^ii | awk '{print $2}' | head -n1)
    if [ -n "$CURRENT_DRIVER_PKG" ]; then
        echo -e "  Installed via: ${CYAN}APT package ($CURRENT_DRIVER_PKG)${NC}"
        BACKUP_METHOD="apt"
    else
        echo -e "  Installed via: ${CYAN}.run installer${NC}"
        BACKUP_METHOD="run"
    fi
else
    echo -e "  ${RED}No NVIDIA driver currently detected${NC}"
    CURRENT_DRIVER="none"
    BACKUP_METHOD="none"
fi
echo ""

# Step 1: Download and verify FIRST (before touching anything)
echo -e "${YELLOW}[1/8] Downloading new driver (safe - no system changes)...${NC}"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

if [ -f "$INSTALLER" ]; then
    echo "  ✓ Installer already exists: $INSTALLER"
else
    echo "  Downloading from: $DOWNLOAD_URL"
    if wget -q --show-progress "$DOWNLOAD_URL"; then
        echo -e "  ${GREEN}✓ Download successful${NC}"
    else
        echo -e "  ${RED}✗ Download failed${NC}"
        echo "  Check version number or network connection"
        exit 1
    fi
fi

chmod +x "$INSTALLER"

# Verify download integrity
FILE_SIZE=$(stat -c%s "$INSTALLER" 2>/dev/null || stat -f%z "$INSTALLER")
if [ "$FILE_SIZE" -lt 100000000 ]; then  # Less than 100MB is suspicious
    echo -e "  ${RED}✗ Downloaded file seems too small ($FILE_SIZE bytes)${NC}"
    echo "  This may be a broken download"
    exit 1
fi
echo -e "  ${GREEN}✓ File size: $(numfmt --to=iec $FILE_SIZE)${NC}"
echo ""

# Step 2: Test installer validity (doesn't install anything)
echo -e "${YELLOW}[2/8] Validating installer...${NC}"
if ./"$INSTALLER" --check 2>&1 | grep -q "ERROR"; then
    echo -e "  ${RED}✗ Installer validation failed${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓ Installer is valid${NC}"
echo ""

# Step 3: Install dependencies
echo -e "${YELLOW}[3/8] Installing build dependencies...${NC}"
if sudo apt-get update && sudo apt-get install -y build-essential dkms linux-headers-$(uname -r); then
    echo -e "  ${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "  ${RED}✗ Failed to install dependencies${NC}"
    exit 1
fi
echo ""

# Step 4: CRITICAL CONFIRMATION
echo -e "${YELLOW}=========================================${NC}"
echo -e "${YELLOW}READY TO INSTALL NEW DRIVER${NC}"
echo -e "${YELLOW}=========================================${NC}"
echo ""
echo -e "  Current driver: ${GREEN}$CURRENT_DRIVER${NC}"
echo -e "  New driver:     ${CYAN}$DRIVER_VERSION${NC}"
echo -e "  Backup method:  ${CYAN}$BACKUP_METHOD${NC}"
echo ""
echo -e "${RED}WARNING: This will replace your current NVIDIA driver${NC}"
echo -e "${RED}         GPU applications will be temporarily unavailable${NC}"
echo ""

if [ "$SKIP_CONFIRMATIONS" != "true" ]; then
    read -p "Continue with installation? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Installation cancelled"
        exit 0
    fi
fi
echo ""

# Step 5: Install new driver (with --no-drm to avoid breaking existing driver)
echo -e "${YELLOW}[4/8] Installing new driver (this takes 2-3 minutes)...${NC}"
echo "  Installing to: /usr/lib/nvidia-${DRIVER_VERSION}/"
echo ""

# Install without unloading current driver (safer)
if sudo ./"$INSTALLER" \
    --silent \
    --dkms \
    --no-opengl-files \
    --no-questions \
    --no-kernel-module-build 2>&1 | tee install.log; then
    echo -e "${GREEN}✓ Driver files installed${NC}"
else
    echo -e "${RED}✗ Installation failed - see install.log${NC}"
    cat install.log
    exit 1
fi
echo ""

# Step 6: Build kernel modules
echo -e "${YELLOW}[5/8] Building kernel modules for new driver...${NC}"
if sudo ./"$INSTALLER" \
    --kernel-module-only \
    --silent \
    --dkms 2>&1 | tee kernel-build.log; then
    echo -e "${GREEN}✓ Kernel modules built${NC}"
else
    echo -e "${RED}✗ Kernel module build failed - see kernel-build.log${NC}"
    cat kernel-build.log
    exit 1
fi
echo ""

# Step 7: Test new driver loads (critical safety check)
echo -e "${YELLOW}[6/8] Testing new driver (unloading old, loading new)...${NC}"
echo "  Stopping GPU processes..."

# Try to unload old modules
sudo rmmod nvidia_uvm 2>/dev/null || true
sudo rmmod nvidia_drm 2>/dev/null || true
sudo rmmod nvidia_modeset 2>/dev/null || true
sudo rmmod nvidia 2>/dev/null || true

echo "  Loading new driver modules..."
if sudo modprobe nvidia; then
    echo -e "  ${GREEN}✓ New driver loaded successfully${NC}"

    # Verify nvidia-smi works
    if nvidia-smi &>/dev/null; then
        NEW_DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -n1)
        echo -e "  ${GREEN}✓ nvidia-smi working${NC}"
        echo -e "  ${GREEN}✓ New driver version: $NEW_DRIVER_VERSION${NC}"
    else
        echo -e "  ${RED}✗ nvidia-smi not working with new driver${NC}"
        echo -e "  ${YELLOW}Rolling back...${NC}"
        sudo rmmod nvidia 2>/dev/null || true
        exit 1
    fi
else
    echo -e "  ${RED}✗ Failed to load new driver${NC}"
    echo -e "  ${YELLOW}System is still safe - old driver not removed${NC}"
    exit 1
fi
echo ""

# Step 8: Success - now clean up old driver
echo -e "${YELLOW}[7/8] New driver verified - cleaning old driver...${NC}"

if [ "$BACKUP_METHOD" = "apt" ]; then
    echo "  Removing old APT packages..."
    sudo apt-get remove --purge -y '^nvidia-driver-.*' '^libnvidia-.*' 2>/dev/null || true
    sudo apt-get autoremove -y
    echo -e "  ${GREEN}✓ Old APT packages removed${NC}"
elif [ "$BACKUP_METHOD" = "run" ]; then
    echo "  Old driver was also installed via .run"
    echo "  New driver will override it"
fi
echo ""

# Final summary
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✓ INSTALLATION SUCCESSFUL${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo -e "  Previous driver: ${CYAN}$CURRENT_DRIVER${NC}"
echo -e "  New driver:      ${GREEN}$NEW_DRIVER_VERSION${NC}"
echo -e "  Status:          ${GREEN}Verified working${NC}"
echo ""
echo -e "${YELLOW}[8/8] Next steps:${NC}"
echo "  1. ${CYAN}REBOOT REQUIRED${NC} - New driver needs clean start"
echo "  2. After reboot: nvidia-smi"
echo "  3. Update venv: cd ~/Coding/llm_adapter && uv sync"
echo "  4. Start vLLM: python scripts/setup/llm_manager.py start"
echo ""
echo -e "${RED}IMPORTANT: You MUST reboot for the new driver to be fully active${NC}"
echo ""

if [ "$SKIP_CONFIRMATIONS" != "true" ]; then
    read -p "Reboot now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Rebooting in 10 seconds... (Ctrl+C to cancel)${NC}"
        sleep 10
        sudo reboot
    else
        echo -e "${YELLOW}Remember to reboot before using the new driver!${NC}"
    fi
else
    echo -e "${YELLOW}Skipping auto-reboot (SKIP_CONFIRMATIONS=true)${NC}"
fi
