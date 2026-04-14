# Testing Guide for Nemo-Orchestrator Claude Adapter

This directory contains comprehensive test suites to validate the Claude adapter works correctly with Claude Code CLI.

## Test Files

### 1. `test_adapter_unit.py` - Unit Tests
Tests adapter logic in isolation without making network calls.

**Run:**
```bash
python3 test_adapter_unit.py
```

**Tests:**
- ✓ Basic request building
- ✓ Tool schema conversion (Anthropic → OpenAI)
- ✓ Tool result handling (no None content bug)
- ✓ Response normalization (text only)
- ✓ Response normalization (with tools - no text blocks)
- ✓ Thinking/reasoning text filtering
- ✓ Empty content handling

### 2. `test_adapter_api.sh` - API Integration Tests
Tests actual HTTP requests to the running gateway.

**Run:**
```bash
./test_adapter_api.sh
```

**Requirements:** Gateway must be running on http://10.172.249.149:8888

**Tests:**
- ✓ Basic text responses
- ✓ Tool calls (non-streaming)
- ✓ Multi-turn conversations with tool results
- ✓ Streaming responses with tools
- ✓ Thinking text filtering
- ✓ Empty content handling

### 3. `test_claude_code_cli.sh` - Claude Code CLI Compatibility
Tests that mimic Claude Code's exact behavior.

**Run:**
```bash
./test_claude_code_cli.sh
```

**Requirements:** Gateway must be running

**Tests:**
- ✓ Streaming tool call requests (with anthropic-client header)
- ✓ Tool result submission (the 400 error bug)
- ✓ No text blocks when tools present
- ✓ Streaming suppresses text when tools present
- ✓ All required Anthropic API fields present

## Running All Tests

```bash
# Run all tests in sequence
cd ~/coding/nemo_orchestrator

echo "=== Unit Tests ==="
python3 test_adapter_unit.py

echo -e "\n=== API Tests ==="
./test_adapter_api.sh

echo -e "\n=== Claude Code CLI Tests ==="
./test_claude_code_cli.sh
```

## Continuous Testing

Add to your deployment workflow:

```bash
# After making changes to adapters/claude_adapter.py
python3 test_adapter_unit.py || exit 1

# After restarting gateway
./test_adapter_api.sh || exit 1
./test_claude_code_cli.sh || exit 1

# If all tests pass, it's safe to use with Claude Code CLI
```

## Common Issues Caught by Tests

| Issue | Test That Catches It |
|-------|---------------------|
| Missing `stop_reason` field | API Test 2, CLI Test 1 |
| Text blocks with tool_use | API Test 2, CLI Test 3 |
| `content: null` bug | API Test 3, CLI Test 2 |
| Thinking text not filtered | API Test 5 |
| Streaming sends text with tools | CLI Test 4 |
| Missing required fields | CLI Test 5 |

## Expected Test Results

All tests should pass:
- **Unit Tests:** 29 passed, 0 failed
- **API Tests:** ~20 passed, 0 failed
- **CLI Tests:** ~10 passed, 0 failed

If any tests fail, DO NOT deploy to production!
