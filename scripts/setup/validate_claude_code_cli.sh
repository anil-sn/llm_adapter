#!/usr/bin/env bash
# Validate Claude Code CLI Integration with Nemo-Gateway
# Run this after setup_claude_code_cli.sh

set -e

GATEWAY_URL="http://10.172.249.149:8888"
MODEL="nemotron-3-super"

echo "========================================================================="
echo "  Claude Code CLI Validation Tests"
echo "========================================================================="
echo ""

PASSED=0
FAILED=0

# Helper function
test_claude_command() {
    local test_name="$1"
    local prompt="$2"
    local expected_pattern="$3"

    echo -n "Testing: $test_name... "

    # Run claude with timeout
    RESPONSE=$(timeout 30 claude --model "$MODEL" "$prompt" 2>&1 || echo "TIMEOUT")

    if echo "$RESPONSE" | grep -qi "$expected_pattern" && ! echo "$RESPONSE" | grep -q "TIMEOUT"; then
        echo "✓ PASS"
        ((PASSED++))
        return 0
    else
        echo "✗ FAIL"
        echo "  Expected pattern: $expected_pattern"
        echo "  Got: ${RESPONSE:0:100}..."
        ((FAILED++))
        return 1
    fi
}

# Test 1: Basic response
echo "--- Basic Functionality ---"
test_claude_command \
    "Basic arithmetic" \
    "What is 5+3? Just give the number." \
    "8"

# Test 2: Model awareness
test_claude_command \
    "Model identity" \
    "What model are you? Reply with just the model name." \
    "nemotron"

# Test 3: File operations (if in a git repo)
if [ -d ".git" ]; then
    test_claude_command \
        "File awareness" \
        "List the files in the current directory. Just list names." \
        "config.yaml"
fi

# Test 4: Multi-turn capability
echo ""
echo "--- Multi-turn Conversation ---"
echo "Testing conversational context..."

# Create test conversation file
CONV_FILE=$(mktemp)
cat > "$CONV_FILE" << 'EOF'
My name is Alice.
EOF

RESPONSE1=$(timeout 30 claude --model "$MODEL" "$(cat $CONV_FILE)" 2>&1)
if echo "$RESPONSE1" | grep -qi "alice"; then
    echo "✓ Context preserved"
    ((PASSED++))
else
    echo "✗ Context not preserved"
    ((FAILED++))
fi

rm -f "$CONV_FILE"

# Test 5: Streaming mode
echo ""
echo "--- Streaming Mode ---"
echo -n "Testing streaming output... "

# Run in background and check for incremental output
STREAM_TEST=$(timeout 10 claude --model "$MODEL" "Count from 1 to 5" 2>&1 || echo "TIMEOUT")

if [ "$STREAM_TEST" != "TIMEOUT" ] && [ -n "$STREAM_TEST" ]; then
    echo "✓ Streaming works"
    ((PASSED++))
else
    echo "✗ Streaming failed"
    ((FAILED++))
fi

# Summary
echo ""
echo "========================================================================="
echo "  Test Results"
echo "========================================================================="
echo "  Total Tests: $((PASSED + FAILED))"
echo "  ✓ Passed: $PASSED"
echo "  ✗ Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "  🎉 All tests passed! Claude Code is working with your Nemotron gateway."
    echo ""
    echo "  Try these next:"
    echo "    cd ~/coding/nemo_orchestrator"
    echo "    claude 'Review config.yaml and explain the memory settings'"
    echo "    claude 'What are the main components in this codebase?'"
else
    echo "  ⚠️  Some tests failed. Check the output above."
    echo ""
    echo "  Troubleshooting:"
    echo "    1. Verify gateway is running: curl ${GATEWAY_URL}/health"
    echo "    2. Check Claude Code config: cat ~/.config/claude/settings.json"
    echo "    3. Check logs: tail ~/Coding/nemo_orchestrator/logs/nemo_gateway.log"
fi

echo "========================================================================="
exit $FAILED
