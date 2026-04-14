#!/usr/bin/env bash
# Download Nemotron-3 Super v3 reasoning parser plugin
# Required for --reasoning-parser super_v3

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_URL="https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16/resolve/main/super_v3_reasoning_parser.py"
PLUGIN_FILE="${SCRIPT_DIR}/super_v3_reasoning_parser.py"

echo "========================================================================="
echo "  Downloading Nemotron-3 Super v3 Reasoning Parser Plugin"
echo "========================================================================="
echo ""

if [ -f "$PLUGIN_FILE" ]; then
    echo "Plugin already exists: $PLUGIN_FILE"
    echo "Checking if update is needed..."
    mv "$PLUGIN_FILE" "${PLUGIN_FILE}.backup"
    echo "  Created backup: ${PLUGIN_FILE}.backup"
fi

echo "Downloading from:"
echo "  $PLUGIN_URL"
echo ""

if command -v wget &> /dev/null; then
    wget -q --show-progress "$PLUGIN_URL" -O "$PLUGIN_FILE"
elif command -v curl &> /dev/null; then
    curl -L --progress-bar "$PLUGIN_URL" -o "$PLUGIN_FILE"
else
    echo "ERROR: Neither wget nor curl found. Please install one of them."
    exit 1
fi

if [ -f "$PLUGIN_FILE" ]; then
    echo ""
    echo "✓ Download complete: $PLUGIN_FILE"
    echo ""

    # Verify it's a Python file
    if head -n 1 "$PLUGIN_FILE" | grep -q "python"; then
        echo "✓ File appears to be valid Python code"

        # Show first few lines
        echo ""
        echo "Preview (first 10 lines):"
        echo "----------------------------------------"
        head -n 10 "$PLUGIN_FILE"
        echo "----------------------------------------"
        echo ""
        echo "File size: $(du -h "$PLUGIN_FILE" | cut -f1)"
    else
        echo "⚠  Warning: File may not be valid Python code"
    fi

    # Remove backup if download successful
    if [ -f "${PLUGIN_FILE}.backup" ]; then
        rm "${PLUGIN_FILE}.backup"
        echo "  Removed backup file"
    fi
else
    echo "✗ Download failed"

    # Restore backup if exists
    if [ -f "${PLUGIN_FILE}.backup" ]; then
        mv "${PLUGIN_FILE}.backup" "$PLUGIN_FILE"
        echo "  Restored backup file"
    fi

    exit 1
fi

echo ""
echo "========================================================================="
echo "  Setup Complete"
echo "========================================================================="
echo ""
echo "The reasoning parser plugin is now available at:"
echo "  $PLUGIN_FILE"
echo ""
echo "You can now restart the gateway with:"
echo "  ./llm_manager.py restart"
echo ""
echo "========================================================================="
