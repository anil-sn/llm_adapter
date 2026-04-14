#!/usr/bin/env bash
# Verify that vLLM started successfully and isn't hitting memory limits
# Usage: ./verify_startup.sh

set -e

GATEWAY_PORT=8888
MAX_WAIT=300  # 5 minutes
CHECK_INTERVAL=5

echo "=== Nemo-Orchestrator Startup Verification ==="
echo ""

# Check if processes are running
echo "1. Checking process status..."
if ! pgrep -f "vllm.entrypoints.openai.api_server" > /dev/null; then
    echo "❌ ERROR: vLLM process not found!"
    exit 1
fi
echo "✓ vLLM processes running"

if ! pgrep -f "nemo_gateway.py" > /dev/null; then
    echo "❌ ERROR: Gateway process not found!"
    exit 1
fi
echo "✓ Gateway process running"

# Check GPU memory
echo ""
echo "2. Checking GPU memory allocation..."
for gpu in {0..3}; do
    mem_used=$(nvidia-smi -i $gpu --query-gpu=memory.used --format=csv,noheader,nounits)
    mem_total=$(nvidia-smi -i $gpu --query-gpu=memory.total --format=csv,noheader,nounits)
    utilization=$((100 * mem_used / mem_total))

    if [ $utilization -gt 85 ]; then
        echo "⚠️  GPU $gpu: ${utilization}% (${mem_used}MB / ${mem_total}MB) - DANGER ZONE"
    elif [ $utilization -gt 70 ]; then
        echo "✓ GPU $gpu: ${utilization}% (${mem_used}MB / ${mem_total}MB) - OK"
    else
        echo "✓ GPU $gpu: ${utilization}% (${mem_used}MB / ${mem_total}MB) - Healthy"
    fi
done

# Wait for vLLM to be ready
echo ""
echo "3. Waiting for vLLM to initialize (max ${MAX_WAIT}s)..."
elapsed=0
while [ $elapsed -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ vLLM health check passed"
        break
    fi

    # Check for OOM in logs
    if [ -f "logs/vllm_replica_0.log" ]; then
        if tail -100 logs/vllm_replica_0.log | grep -i "out of memory" > /dev/null; then
            echo "❌ ERROR: OOM detected in vLLM logs!"
            echo ""
            echo "Last 20 lines of log:"
            tail -20 logs/vllm_replica_0.log
            exit 1
        fi
    fi

    sleep $CHECK_INTERVAL
    elapsed=$((elapsed + CHECK_INTERVAL))
    echo -n "."
done

if [ $elapsed -ge $MAX_WAIT ]; then
    echo ""
    echo "❌ ERROR: vLLM did not become ready in time"
    exit 1
fi

# Wait for Gateway
echo ""
echo "4. Checking Gateway..."
if ! curl -s http://localhost:${GATEWAY_PORT}/v1/models > /dev/null 2>&1; then
    echo "⚠️  Gateway not responding yet, waiting..."
    sleep 5
fi

if curl -s http://localhost:${GATEWAY_PORT}/v1/models > /dev/null 2>&1; then
    echo "✓ Gateway responding"
else
    echo "❌ ERROR: Gateway not responding"
    exit 1
fi

# Get model list
echo ""
echo "5. Available models:"
curl -s http://localhost:${GATEWAY_PORT}/v1/models | python3 -m json.tool | grep '"id"'

echo ""
echo "=== ✅ ALL CHECKS PASSED ==="
echo ""
echo "System is ready. Current memory state:"
nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv,noheader
