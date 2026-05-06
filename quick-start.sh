#!/bin/bash
# LLM Adapter - Quick Start Script
# Automated setup for new installations

set -e

echo "======================================================================"
echo "LLM Adapter - Quick Start"
echo "======================================================================"
echo ""

# Check Python version
echo "Checking Python version..."
if ! command -v python3.12 &> /dev/null; then
    echo "❌ Python 3.12+ not found. Please install Python 3.12 or newer."
    exit 1
fi

PYTHON_VERSION=$(python3.12 --version | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3.12 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
echo "This may take a few minutes..."
pip install -e ".[tools]" -q
echo "✓ Dependencies installed"
echo ""

# Create .env file
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "✓ .env file created (edit as needed)"
else
    echo "✓ .env file already exists"
fi
echo ""

# Check GPU
echo "Checking GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    GPU_COUNT=$(nvidia-smi --list-gpus | wc -l)
    echo "✓ Found $GPU_COUNT NVIDIA GPU(s)"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | nl
else
    echo "⚠ nvidia-smi not found. GPU check skipped."
fi
echo ""

# Verify installation
echo "Verifying installation..."
if python -c "import llm_adapter" 2>/dev/null; then
    echo "✓ llm_adapter package imported successfully"
else
    echo "❌ Failed to import llm_adapter"
    exit 1
fi
echo ""

# Check tool dependencies
if python -c "from ddgs import DDGS" 2>/dev/null; then
    echo "✓ Web search tool (ddgs) installed"
else
    echo "⚠ Web search tool not installed (optional)"
    echo "  Install with: pip install ddgs"
fi
echo ""

echo "======================================================================"
echo "✅ Installation Complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Download a model (choose one):"
echo "   bash scripts/download_qwen36_27b.sh    # Recommended: 27B model"
echo ""
echo "2. Start the LLM:"
echo "   make start"
echo "   # or"
echo "   LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py start"
echo ""
echo "3. Test the installation:"
echo "   make test"
echo "   # or"
echo "   python tests/test_tool_calling_comprehensive.py"
echo ""
echo "4. Try the examples:"
echo "   python examples/tool_calling_example.py"
echo ""
echo "For more information, see INSTALL.md"
echo ""
echo "Enjoy! 🚀"
