#!/bin/bash
###############################################################################
# Fix Paths After Reorganization
# Run this on the server after copying the reorganized project
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Project Root: $PROJECT_ROOT"

# Verify critical paths exist
echo ""
echo "Checking critical paths..."

ERRORS=0

if [ ! -f "$PROJECT_ROOT/config/config.yaml" ]; then
    echo "❌ ERROR: config/config.yaml not found"
    ((ERRORS++))
else
    echo "✅ config/config.yaml found"
fi

if [ ! -f "$PROJECT_ROOT/src/nemo_orchestrator/gateway/server.py" ]; then
    echo "❌ ERROR: src/nemo_orchestrator/gateway/server.py not found"
    ((ERRORS++))
else
    echo "✅ Gateway server.py found"
fi

if [ ! -f "$PROJECT_ROOT/scripts/setup/llm_manager.py" ]; then
    echo "❌ ERROR: scripts/setup/llm_manager.py not found"
    ((ERRORS++))
else
    echo "✅ llm_manager.py found"
fi

echo ""

if [ $ERRORS -gt 0 ]; then
    echo "❌ $ERRORS critical files missing. Cannot proceed."
    echo ""
    echo "Make sure you've copied the entire reorganized project:"
    echo "  rsync -avz ~/coding/nemo_orchestrator/ server:/path/to/nemo_orchestrator/"
    exit 1
fi

echo "✅ All critical paths verified!"
echo ""
echo "You can now run:"
echo "  python3 scripts/setup/llm_manager.py restart"
echo ""
