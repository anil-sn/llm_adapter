#!/bin/bash

###############################################################################
# Install Python 3.12 on Ubuntu via deadsnakes PPA
###############################################################################

set -e

echo "=================================================="
echo "Python 3.12 Installation"
echo "=================================================="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script needs sudo privileges."
    echo "It will prompt for your password."
    echo ""
fi

# Step 1: Add deadsnakes PPA
echo "📦 Adding deadsnakes PPA repository..."
sudo add-apt-repository ppa:deadsnakes/ppa -y
echo "✓ PPA added"
echo ""

# Step 2: Update package list
echo "📦 Updating package list..."
sudo apt-get update
echo "✓ Package list updated"
echo ""

# Step 3: Install Python 3.12 and essential packages
echo "📦 Installing Python 3.12 and dependencies..."
sudo apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3.12-distutils \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-pip

echo "✓ Python 3.12 installed"
echo ""

# Step 4: Verify installation
echo "=================================================="
echo "Verification"
echo "=================================================="
echo ""

PYTHON312_VERSION=$(python3.12 --version 2>&1)
PYTHON312_PATH=$(which python3.12)

echo "✓ Python 3.12 Version: $PYTHON312_VERSION"
echo "✓ Python 3.12 Path: $PYTHON312_PATH"
echo ""

# Step 5: Check pip for Python 3.12
if python3.12 -m pip --version &>/dev/null; then
    PIP_VERSION=$(python3.12 -m pip --version)
    echo "✓ pip for Python 3.12: $PIP_VERSION"
else
    echo "⚠ pip not available for Python 3.12, installing..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12
    echo "✓ pip installed"
fi

echo ""
echo "=================================================="
echo "✅ Python 3.12 Installation Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Run: bash scripts/setup_venv.sh"
echo "  2. This will create venv with Python 3.12"
echo ""
