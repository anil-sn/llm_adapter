#!/bin/bash
# DeepSeek V4 Phase 0 Test Runner
# Launches vLLM with conservative config and runs stress test

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Activate venv
source .venv/bin/activate

echo "=============================================================================="
echo " DeepSeek V4 Phase 0 - Controlled Experiment"
echo "=============================================================================="
echo ""
echo "Configuration: config/config-deepseek-phase0.yaml"
echo "Test Protocol: 100 iterations, deterministic, batch_size=1"
echo "Monitoring: GPU memory, latency, CUDA errors"
echo ""

# Set config
export LLM_CONFIG="config/config-deepseek-phase0.yaml"

# Kill any existing processes
echo "[1/4] Cleaning up existing processes..."
python3 scripts/setup/llm_manager.py stop 2>/dev/null || true
sleep 5

# Launch vLLM with Phase 0 config
echo ""
echo "[2/4] Launching vLLM with Phase 0 config..."
echo "  - GPU memory util: 0.80 (conservative)"
echo "  - Max context: 256K"
echo "  - Max seqs: 4"
echo "  - Max batched tokens: 8192"
echo "  - Enforce eager: true"
echo "  - V1 engine: DISABLED"
echo ""

python3 scripts/setup/llm_manager.py start

# Wait for server to be fully ready
echo ""
echo "[3/4] Waiting for server to be ready..."
sleep 30

# Check if server is responding
echo "Checking server health..."
if ! curl -s http://127.0.0.1:8888/v1/models >/dev/null 2>&1; then
    echo "ERROR: Server not responding"
    echo "Check logs:"
    echo "  tail -f logs/vllm_replica_0.log"
    exit 1
fi

echo "✓ Server ready"

# Run stress test
echo ""
echo "[4/4] Running Phase 0 stress test..."
echo "----------------------------------------------------------------------"
echo ""

python3 scripts/test_deepseek_phase0.py --iterations 100

TEST_EXIT_CODE=$?

echo ""
echo "=============================================================================="
echo " Phase 0 Test Complete"
echo "=============================================================================="
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ PASSED - Ready to proceed to Phase 1 (context ramp)"
    echo ""
    echo "Next steps:"
    echo "  1. Review report in logs/phase0_report_*.json"
    echo "  2. If stable, run Phase 1: context ramp (32K → 64K → 128K → 192K → 256K)"
    echo "  3. Monitor for latency scaling and memory fragmentation"
else
    echo "✗ FAILED - Investigation required"
    echo ""
    echo "Debug steps:"
    echo "  1. Check vLLM logs: tail -f logs/vllm_replica_0.log"
    echo "  2. Review error patterns in logs/phase0_report_*.json"
    echo "  3. Look for CUDA errors, OOM, or routing failures"
    echo ""
    echo "Possible root causes:"
    echo "  - V1 engine still active (check vLLM logs for 'V1' or 'async')"
    echo "  - MoE routing instability (check for 'expert' or 'moe' errors)"
    echo "  - Hybrid attention incompatibility (check for 'attention' or 'kv' errors)"
    echo "  - FP8 kernel issues (check for 'fp8' or 'quantization' errors)"
fi

echo ""
echo "To stop vLLM:"
echo "  source .venv/bin/activate && python scripts/setup/llm_manager.py stop"
echo ""

exit $TEST_EXIT_CODE
