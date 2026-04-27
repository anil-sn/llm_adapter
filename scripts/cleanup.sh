#!/bin/bash
#
# Cleanup Script for LLM Orchestrator
#
# Removes temporary files, caches, and build artifacts
#
# Usage:
#   ./scripts/cleanup.sh        # Clean caches and temp files
#   ./scripts/cleanup.sh all    # Clean everything including logs
#
# Author: Anil Srirangapatna Nagesh
# Version: 2.0

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================================================"
echo "  LLM Orchestrator - Cleanup"
echo -e "========================================================================${NC}"
echo ""

CLEAN_ALL="$1"

# Count files before cleanup
echo "Scanning for temporary files..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" | wc -l | tr -d ' ')
PYC_COUNT=$(find . -type f -name "*.pyc" | wc -l | tr -d ' ')
BAK_COUNT=$(find . -type f -name "*.bak" -o -name "*~" | wc -l | tr -d ' ')

echo ""
echo "Found:"
echo "  - __pycache__ directories: $PYCACHE_COUNT"
echo "  - .pyc files: $PYC_COUNT"
echo "  - Backup files (.bak, ~): $BAK_COUNT"
echo ""

# Clean Python cache
if [ "$PYCACHE_COUNT" -gt 0 ] || [ "$PYC_COUNT" -gt 0 ]; then
    echo -e "${BLUE}Cleaning Python caches...${NC}"
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo -e "${GREEN}✓ Python caches cleaned${NC}"
fi

# Clean backup files
if [ "$BAK_COUNT" -gt 0 ]; then
    echo -e "${BLUE}Cleaning backup files...${NC}"
    find . -type f \( -name "*.bak" -o -name "*~" \) -delete 2>/dev/null || true
    echo -e "${GREEN}✓ Backup files cleaned${NC}"
fi

# Clean pytest cache
if [ -d ".pytest_cache" ]; then
    echo -e "${BLUE}Cleaning pytest cache...${NC}"
    rm -rf .pytest_cache
    echo -e "${GREEN}✓ Pytest cache cleaned${NC}"
fi

# Clean coverage reports
if [ -d "htmlcov" ] || [ -f ".coverage" ]; then
    echo -e "${BLUE}Cleaning coverage reports...${NC}"
    rm -rf htmlcov .coverage
    echo -e "${GREEN}✓ Coverage reports cleaned${NC}"
fi

# Clean merged config output (if exists)
if [ -f "merged_config.json" ]; then
    echo -e "${BLUE}Cleaning merged config output...${NC}"
    rm -f merged_config.json
    echo -e "${GREEN}✓ Merged config cleaned${NC}"
fi

# Clean all (including logs) if requested
if [ "$CLEAN_ALL" = "all" ]; then
    echo ""
    echo -e "${YELLOW}Deep clean mode: Removing logs and PID files...${NC}"

    # Clean logs
    if [ -d "logs" ]; then
        rm -rf logs/*.log
        echo -e "${GREEN}✓ Logs cleaned${NC}"
    fi

    # Clean PID files
    if ls .*.pid 1> /dev/null 2>&1; then
        rm -f .*.pid
        echo -e "${GREEN}✓ PID files cleaned${NC}"
    fi

    echo -e "${YELLOW}Note: This removed active logs and PIDs. You may need to restart services.${NC}"
fi

echo ""
echo -e "${BLUE}========================================================================${NC}"
echo -e "${GREEN}✓ Cleanup complete!${NC}"
echo -e "${BLUE}========================================================================${NC}"
echo ""

if [ "$CLEAN_ALL" != "all" ]; then
    echo "Tip: Run './scripts/cleanup.sh all' to also clean logs and PID files"
    echo ""
fi
