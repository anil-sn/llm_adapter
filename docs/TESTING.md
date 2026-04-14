# Testing Guide

## Test Structure

```
tests/
├── unit/           # Unit tests for individual components
│   └── test_adapter_unit.py
├── integration/    # API integration tests
│   ├── test_adapter_api.sh
│   ├── test_adapter_v2.py
│   └── test_claude_code_cli.sh
└── e2e/            # End-to-end tests
    └── test_e2e_tool_execution.py
```

## Running Tests

### All Tests
```bash
# Run all test suites
python -m pytest tests/

# Or use the testing script
./scripts/testing/run_all_tests.sh
```

### Unit Tests
```bash
# Test adapter logic
python tests/unit/test_adapter_unit.py
```

### Integration Tests
```bash
# Test API compatibility
bash tests/integration/test_adapter_api.sh

# Test Claude Code CLI compatibility
bash tests/integration/test_claude_code_cli.sh

# Test V2 adapter
python tests/integration/test_adapter_v2.py
```

### E2E Tests
```bash
# Full tool execution flow
python tests/e2e/test_e2e_tool_execution.py
```

## Test Scenarios

### 1. Non-Streaming Responses
- Basic text generation
- Tool calling
- Multi-turn conversations
- Tool result handling

### 2. Streaming Responses
- Text delta events
- Tool use events
- Dynamic block switching (text → tool_use)
- Error handling during streams

### 3. Claude Code CLI Compatibility
- stop_reason field presence
- stop_sequence field
- Content block structure (text vs tool_use)
- Tool execution flow
- Multi-turn tool conversations

### 4. Protocol Conversion
- Anthropic → OpenAI request conversion
- OpenAI → Anthropic response conversion
- Tool definition conversion
- Message format conversion

## Expected Behavior

### Non-Streaming with Tools
```json
{
  "stop_reason": "tool_use",
  "content": [
    {"type": "tool_use", "id": "...", "name": "Bash", "input": {...}}
  ]
}
```
**Note**: NO text blocks when tools are present!

### Streaming with Tools
```
event: message_start
event: content_block_start (type: tool_use)
event: input_json_delta (tool arguments streaming)
event: content_block_stop
event: message_delta (stop_reason: tool_use)
event: message_stop
```
**Note**: 0 text_delta events when tools are called!

## Debugging Failed Tests

### Tool Calling Not Working
1. Check logs for "Tool call missing 'id'" errors
2. Verify vLLM has `enable_auto_tool_choice: true`
3. Check `tool_call_parser: qwen3_coder` is set
4. Ensure model supports tool calling

### HTTP 400 Errors
1. Check for `content: None` in messages
2. Verify tool_result blocks are handled correctly
3. Check request body with `--verbose` flag

### Streaming Issues
1. Check SSE event format
2. Verify all blocks are properly closed
3. Check for uncaught exceptions in stream
4. Monitor backend response chunks

## Performance Benchmarks

### Target Metrics
- **Non-streaming latency**: < 100ms (adapter overhead)
- **Streaming first token**: < 50ms
- **Tool call detection**: Immediate (0 text deltas)
- **Error recovery**: Graceful shutdown with proper events

### Running Benchmarks
```bash
python scripts/testing/benchmark.py
```
