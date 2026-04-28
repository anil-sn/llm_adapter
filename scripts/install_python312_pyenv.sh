#!/bin/bash

###############################################################################
# Install Python 3.12 via pyenv (No Sudo Required)
# This installs Python 3.12 in user's home directory
###############################################################################

set -e

echo "=================================================="
echo "Python 3.12 Installation via pyenv (No Sudo)"
echo "=================================================="
echo ""

# Check if pyenv is already installed
if command -v pyenv &> /dev/null; then
    echo "✓ pyenv is already installed"
    PYENV_ROOT=$(pyenv root)
    echo "  Location: $PYENV_ROOT"
else
    echo "📦 Installing pyenv..."

    # Install pyenv using official installer
    curl -fsSL https://pyenv.run | bash

    # Set up environment variables
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"

    # Add to shell config
    SHELL_RC="$HOME/.bashrc"

    if ! grep -q "PYENV_ROOT" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo '# pyenv configuration' >> "$SHELL_RC"
        echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$SHELL_RC"
        echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> "$SHELL_RC"
        echo 'eval "$(pyenv init -)"' >> "$SHELL_RC"
        echo "✓ Added pyenv to $SHELL_RC"
    fi

    # Initialize pyenv in current shell
    eval "$(pyenv init -)"

    echo "✓ pyenv installed"
fi

echo ""

# Check build dependencies (warn if missing)
echo "Checking build dependencies..."
MISSING_DEPS=()

for dep in gcc make libssl-dev libbz2-dev libreadline-dev libsqlite3-dev; do
    if ! dpkg -l | grep -q "^ii.*$dep" 2>/dev/null; then
        MISSING_DEPS+=("$dep")
    fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo "⚠ WARNING: Some build dependencies may be missing:"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "  - $dep"
    done
    echo ""
    echo "If Python compilation fails, ask admin to run:"
    echo "  sudo apt-get install -y build-essential libssl-dev libbz2-dev libreadline-dev libsqlite3-dev zlib1g-dev"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""

# Install Python 3.12
echo "=================================================="
echo "Installing Python 3.12.8 (this may take 10-15 min)"
echo "=================================================="
echo ""

# Set PYENV_ROOT if not already set
export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

# Check if Python 3.12.8 is already installed
if pyenv versions | grep -q "3.12.8"; then
    echo "✓ Python 3.12.8 is already installed"
else
    echo "📦 Downloading and compiling Python 3.12.8..."
    echo "  (This downloads source and compiles, please be patient)"
    echo ""

    pyenv install 3.12.8

    echo "✓ Python 3.12.8 installed"
fi

echo ""

# Set Python 3.12.8 as local version for this project
echo "📦 Setting Python 3.12.8 for llm_adapter project..."
cd ~/Coding/llm_adapter
pyenv local 3.12.8

echo "✓ Python 3.12.8 set for this directory"
echo ""

# Verify installation
echo "=================================================="
echo "Verification"
echo "=================================================="
echo ""

PYTHON_VERSION=$(python --version 2>&1)
PYTHON_PATH=$(which python)

echo "✓ Python Version: $PYTHON_VERSION"
echo "✓ Python Path: $PYTHON_PATH"
echo ""

# Verify it's actually 3.12
if [[ "$PYTHON_VERSION" != *"3.12"* ]]; then
    echo "❌ ERROR: Python version is not 3.12"
    echo "  Try: exec $SHELL  (to reload shell)"
    exit 1
fi

# Check pip
if python -m pip --version &>/dev/null; then
    PIP_VERSION=$(python -m pip --version)
    echo "✓ pip: $PIP_VERSION"
else
    echo "⚠ pip not found, installing..."
    python -m ensurepip --upgrade
fi

echo ""
echo "=================================================="
echo "✅ Python 3.12.8 Installation Complete!"
echo "=================================================="
echo ""
echo "Python 3.12 is now active in:"
echo "  $HOME/Coding/llm_adapter"
echo ""
echo "To activate in new terminal sessions:"
echo "  cd ~/Coding/llm_adapter"
echo "  (Python 3.12 will activate automatically)"
echo ""
echo "Next steps:"
echo "  1. Run: bash scripts/setup_venv.sh"
echo "  2. This will create venv with Python 3.12"
echo ""
