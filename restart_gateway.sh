#!/bin/bash
# Helper script to restart the gateway with proper configuration

# Stop old gateway
if [ -f .nemo_gateway.pid ]; then
    OLD_PID=$(cat .nemo_gateway.pid)
    echo "Stopping old gateway (PID: $OLD_PID)..."
    kill -TERM $OLD_PID 2>/dev/null || echo "Process already stopped"
    sleep 2
fi

# Set environment for configuration if not already set
export LLM_CONFIG=${LLM_CONFIG:-"config/config-gemma4-31b.yaml"}

# Start new gateway
echo "Starting gateway with config: $LLM_CONFIG..."
nohup .venv/bin/python src/llm_adapter/gateway/server.py > logs/nemo_gateway.log 2>&1 &
NEW_PID=$!
echo $NEW_PID > .nemo_gateway.pid

echo "Gateway started with PID: $NEW_PID"
echo "Check logs: tail -f logs/nemo_gateway.log"

# Wait a bit and verify it started
sleep 3
if ps -p $NEW_PID > /dev/null; then
    echo "✓ Gateway is running"
    tail -10 logs/nemo_gateway.log | grep -E "(Configuration loaded|User detection|ACTIVE)"
else
    echo "✗ Gateway failed to start - check logs/nemo_gateway.log"
    tail -20 logs/nemo_gateway.log
fi
