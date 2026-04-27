#!/bin/bash
#
# Test Runner for LLM Orchestrator
#
# Runs all tests with proper environment setup
#
# Usage:
#   ./scripts/run_tests.sh              # Run all tests
#   ./scripts/run_tests.sh config       # Run only config tests
#   ./scripts/run_tests.sh qwen         # Run only Qwen adapter tests
#   ./scripts/run_tests.sh verbose      # Run with verbose output
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
echo "  LLM Orchestrator - Test Suite"
echo -e "========================================================================${NC}"
echo ""

# Check if pytest is installed
if ! python3 -m pytest --version &>/dev/null; then
    echo -e "${YELLOW}Warning: pytest not found. Installing...${NC}"
    pip3 install pytest pytest-cov
fi

# Determine what to test
TEST_FILTER="$1"
PYTEST_ARGS="-v"

if [ "$TEST_FILTER" = "verbose" ] || [ "$TEST_FILTER" = "-v" ]; then
    PYTEST_ARGS="-vv -s"
    TEST_FILTER=""
fi

# Run tests
echo -e "${BLUE}Running tests...${NC}"
echo ""

case "$TEST_FILTER" in
    config)
        echo "Testing: Configuration System"
        python3 -m pytest tests/test_config_system.py $PYTEST_ARGS
        ;;
    qwen)
        echo "Testing: Qwen Adapter"
        python3 -m pytest tests/test_qwen_adapter.py $PYTEST_ARGS
        ;;
    coverage)
        echo "Testing: All tests with coverage"
        python3 -m pytest tests/ $PYTEST_ARGS --cov=src/nemo_orchestrator --cov-report=html
        echo ""
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;
    *)
        echo "Testing: All tests"
        python3 -m pytest tests/ $PYTEST_ARGS
        ;;
esac

TEST_EXIT_CODE=$?

echo ""
echo -e "${BLUE}========================================================================${NC}"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${YELLOW}✗ Some tests failed (exit code: $TEST_EXIT_CODE)${NC}"
fi

echo -e "${BLUE}========================================================================${NC}"
echo ""

exit $TEST_EXIT_CODE
