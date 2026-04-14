#!/usr/bin/env bash
# Check if tool calling flags are enabled in running vLLM process

set -e

echo "========================================================================="
echo "  Tool Calling Configuration Check"
echo "========================================================================="
echo ""

# Check if vLLM is running
if ! pgrep -f "vllm.entrypoints" > /dev/null; then
    echo "✗ vLLM is not running"
    exit 1
fi

echo "1. Checking config.yaml settings..."
echo ""

if grep -q "enable_auto_tool_choice: true" config.yaml; then
    echo "   ✓ enable_auto_tool_choice: true (config.yaml)"
else
    echo "   ✗ enable_auto_tool_choice: false or missing (config.yaml)"
fi

if grep -q 'tool_call_parser: "qwen3_coder"' config.yaml; then
    echo "   ✓ tool_call_parser: qwen3_coder (config.yaml)"
else
    echo "   ✗ tool_call_parser not set to qwen3_coder (config.yaml)"
fi

echo ""
echo "2. Checking actual vLLM process flags..."
echo ""

# Get the full command line
VLLM_CMD=$(ps aux | grep "[v]llm.entrypoints.openai.api_server" | head -1)

if echo "$VLLM_CMD" | grep -q -- "--enable-auto-tool-choice"; then
    echo "   ✓ --enable-auto-tool-choice found in process"
else
    echo "   ✗ --enable-auto-tool-choice NOT found in process"
    echo "   This flag is REQUIRED for tool calling!"
fi

if echo "$VLLM_CMD" | grep -q -- "--tool-call-parser"; then
    PARSER=$(echo "$VLLM_CMD" | grep -oP '(?<=--tool-call-parser )\w+' || echo "$VLLM_CMD" | sed -n 's/.*--tool-call-parser \([^ ]*\).*/\1/p')
    echo "   ✓ --tool-call-parser $PARSER found in process"
else
    echo "   ✗ --tool-call-parser NOT found in process"
    echo "   This flag is REQUIRED for tool calling!"
fi

echo ""
echo "3. Full vLLM command (tool-related flags):"
echo ""
echo "$VLLM_CMD" | tr ' ' '\n' | grep -E "tool|enable-auto" | sed 's/^/   /'

echo ""
echo "========================================================================="
echo "  Summary"
echo "========================================================================="
echo ""

if echo "$VLLM_CMD" | grep -q -- "--enable-auto-tool-choice" && \
   echo "$VLLM_CMD" | grep -q -- "--tool-call-parser"; then
    echo "✓ Tool calling is ENABLED"
    echo ""
    echo "Expected output format: <toolcall> {...json...} </toolcall>"
else
    echo "✗ Tool calling is NOT properly enabled"
    echo ""
    echo "To fix:"
    echo "  1. Verify config.yaml has:"
    echo "     enable_auto_tool_choice: true"
    echo "     tool_call_parser: \"qwen3_coder\""
    echo ""
    echo "  2. Restart the gateway:"
    echo "     ./llm_manager.py restart"
fi

echo "========================================================================="
