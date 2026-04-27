#!/bin/bash
#
# Model Switcher for LLM Orchestrator
#
# Switches between Qwen and Nemotron models by:
# 1. Stopping current model (if running)
# 2. Setting LLM_CONFIG environment variable
# 3. Starting new model
#
# Usage:
#   ./scripts/switch_model.sh qwen
#   ./scripts/switch_model.sh nemotron
#
# Author: Anil Srirangapatna Nagesh
# Version: 2.0

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root (script is in scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Model configurations
QWEN_CONFIG="config/config-qwen.yaml"
NEMOTRON_CONFIG="config/config-nemotron.yaml"

# Change to project root
cd "$PROJECT_ROOT"

# Helper functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo "========================================================================"
    echo "  LLM Orchestrator - Model Switcher"
    echo "========================================================================"
    echo ""
}

# Validate arguments
if [ $# -eq 0 ]; then
    print_header
    print_error "No model specified"
    echo ""
    echo "Usage: $0 {qwen|nemotron}"
    echo ""
    echo "Available models:"
    echo "  qwen     - Qwen3.5-122B-A10B-GPTQ-Int4 (262K context, RECOMMENDED)"
    echo "  nemotron - Nemotron-3-Super-120B (192K context, stable)"
    echo ""
    exit 1
fi

MODEL="$1"

# Determine config file
case "$MODEL" in
    qwen)
        CONFIG_FILE="$QWEN_CONFIG"
        MODEL_NAME="Qwen3.5-122B-A10B-GPTQ-Int4"
        MODEL_FEATURES="262K native context, GPTQ Int4 quantized, fits 4x48GB GPUs"
        ;;
    nemotron)
        CONFIG_FILE="$NEMOTRON_CONFIG"
        MODEL_NAME="Nemotron-3-Super-120B"
        MODEL_FEATURES="192K context, production-stable"
        ;;
    *)
        print_error "Unknown model: $MODEL"
        echo ""
        echo "Available models:"
        echo "  qwen     - Qwen3.5-122B GPTQ Int4 (RECOMMENDED)"
        echo "  nemotron - Nemotron-3-Super-120B (192K context)"
        exit 1
        ;;
esac

# Validate config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    print_error "Config file not found: $CONFIG_FILE"
    exit 1
fi

# Print header
print_header

echo "Target Model:   $MODEL_NAME"
echo "Config File:    $CONFIG_FILE"
echo "Features:       $MODEL_FEATURES"
echo ""

# Step 1: Stop current model
print_info "Stopping current model (if running)..."
if python3 scripts/setup/llm_manager.py stop 2>/dev/null; then
    print_success "Current model stopped"
else
    print_warning "No model was running (or stop failed)"
fi

echo ""

# Step 2: Export config environment variable
print_info "Setting LLM_CONFIG environment variable..."
export LLM_CONFIG="$CONFIG_FILE"
print_success "LLM_CONFIG=$CONFIG_FILE"

echo ""

# Step 3: Validate configuration
print_info "Validating configuration..."
if python3 -m src.nemo_orchestrator.utils.config_loader 2>&1 | grep -q "✓"; then
    print_success "Configuration validated"
else
    print_error "Configuration validation failed"
    echo ""
    echo "Run this to see details:"
    echo "  LLM_CONFIG=$CONFIG_FILE python3 -m src.nemo_orchestrator.utils.config_loader"
    exit 1
fi

echo ""

# Step 4: Start new model
print_info "Starting $MODEL_NAME..."
if LLM_CONFIG="$CONFIG_FILE" python3 scripts/setup/llm_manager.py start; then
    print_success "$MODEL_NAME started successfully!"
else
    print_error "Failed to start $MODEL_NAME"
    echo ""
    echo "Check logs for details:"
    echo "  tail -f logs/vllm_replica_0.log"
    echo "  tail -f logs/llm_gateway.log"
    exit 1
fi

echo ""

# Step 5: Wait for model to be ready
print_info "Waiting for model to be ready..."
sleep 10

# Step 6: Verify model is running
print_info "Verifying model is running..."
if curl -s http://localhost:8888/v1/models | jq -e '.data[0]' >/dev/null 2>&1; then
    MODEL_ID=$(curl -s http://localhost:8888/v1/models | jq -r '.data[0].id')
    print_success "Model is running: $MODEL_ID"
else
    print_warning "Could not verify model (API may still be starting)"
    print_info "Run this to check manually:"
    echo "  curl http://localhost:8888/v1/models | jq '.data[0]'"
fi

echo ""
echo "========================================================================"
print_success "Model switch completed: $MODEL_NAME"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "  1. Verify health: curl http://localhost:8888/v1/models | jq '.'"
echo "  2. Test completion: curl http://localhost:8888/v1/chat/completions \\"
echo "                       -H 'Content-Type: application/json' \\"
echo "                       -d '{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}]}'"
echo "  3. Monitor logs: tail -f logs/vllm_replica_0.log"
echo ""
echo "To switch back, run:"
if [ "$MODEL" = "qwen" ]; then
    echo "  ./scripts/switch_model.sh nemotron"
else
    echo "  ./scripts/switch_model.sh qwen"
fi
echo ""
