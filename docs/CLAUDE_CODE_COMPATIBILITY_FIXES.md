# Claude Code CLI Compatibility Fixes

## Issues Identified

### 1. Silent Exception Handling (Line 232)
**Current:**
```python
except: pass  # Swallows ALL errors!
```

**Problem:** Claude Code CLI errors are hidden, making debugging impossible.

**Fix:**
```python
except json.JSONDecodeError as e:
    logger.warning(f"JSON decode error in stream chunk: {e}, line: {line}")
    continue
except KeyError as e:
    logger.warning(f"Missing key in chunk: {e}, chunk: {chunk}")
    continue
except Exception as e:
    logger.error(f"Unexpected error in stream: {e}")
    # Don't continue - re-raise to surface the issue
    raise
```

### 2. Overly Aggressive Content Filtering (Line 219)
**Current:**
```python
if content_sent == False and delta.get("content", "").startswith("Okay,"):
    continue
```

**Problem:** Claude Code CLI might expect this content for context.

**Fix:** Only filter when NOT in Claude Code mode:
```python
# Add flag detection
is_claude_code = request.get("headers", {}).get("anthropic-client", "").startswith("claude-code")

if not self.thinking_requested and not is_claude_code:
    if "reasoning" in delta or "thinking" in delta: continue
    if content_sent == False and delta.get("content", "").startswith("Okay,"): continue
```

### 3. Missing Error Responses
**Current:** Returns empty responses on errors

**Problem:** Claude Code CLI needs proper error messages

**Fix:** Add error event type:
```python
def sse_error(error_type, message):
    return f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': error_type, 'message': message}})}\n\n".encode()
```

### 4. Usage Token Estimation Inaccuracy
**Current:**
```python
self.estimated_input_tokens = int(len(json.dumps(body)) / 2.5)
```

**Problem:** Wildly inaccurate, causes Claude Code budget issues

**Fix:** Use tokenizer:
```python
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
self.estimated_input_tokens = len(enc.encode(json.dumps(body.get("messages", []))))
```

### 5. Response HTTP Status Not Checked
**Current:** No status code validation before parsing

**Problem:** 4xx/5xx errors aren't surfaced to Claude Code CLI

**Fix:**
```python
async with client.stream("POST", target_url, json=request, timeout=None) as response:
    if response.status_code != 200:
        error_msg = await response.aread()
        yield sse_error("api_error", f"vLLM returned {response.status_code}: {error_msg.decode()}")
        return

    async for line in response.aiter_lines():
        # ... existing code
```

### 6. Missing ping Events for Long Responses
**Problem:** Claude Code CLI might timeout on long-running requests

**Fix:** Add ping events every 15s:
```python
import asyncio

last_event_time = time.time()

async for line in response.aiter_lines():
    current_time = time.time()
    if current_time - last_event_time > 15.0:
        yield b"event: ping\ndata: {}\n\n"
        last_event_time = current_time

    # ... process line
```

## Implementation Priority

### P0 - Critical (Fix Today)
1. Fix silent exception handling (add logging)
2. Check HTTP status codes
3. Add proper error events

### P1 - High (Fix This Week)
4. Improve token estimation
5. Add ping events for timeouts
6. Test with actual Claude Code CLI

### P2 - Medium (Fix Next Week)
7. Add integration test that calls actual Claude Code CLI
8. Add compatibility mode detection
9. Create debug logging mode

## Testing Protocol

### Step 1: Update Adapter
```bash
cd /Users/asrirang/coding/nemo_orchestrator
# Apply fixes to adapters/claude_adapter.py
```

### Step 2: Restart Gateway
```bash
./llm_manager.py stop
sleep 5
./llm_manager.py start
./verify_startup.sh
```

### Step 3: Test with Claude Code CLI
```bash
# Configure Claude Code to use the gateway
cat >> ~/.claude/settings.json << 'EOF'
{
  "llm": {
    "anthropic": {
      "apiKey": "nemo-gateway",
      "baseURL": "http://10.172.249.149:8888"
    }
  }
}
EOF

# Test simple query
echo "Test prompt: What is 2+2?" | claude code --model nemotron-3-super
```

### Step 4: Check Logs for Errors
```bash
tail -50 logs/nemo_gateway.log
grep -i "error\|warning\|exception" logs/nemo_gateway.log | tail -20
```

## Common Claude Code CLI Error Patterns

### Error: "Invalid response format"
**Cause:** Missing required fields in streaming response

**Fix:** Ensure all Anthropic SSE events have required fields:
```python
# message_start MUST have these fields
{
  "type": "message_start",
  "message": {
    "id": "msg_...",
    "type": "message",
    "role": "assistant",
    "content": [],
    "model": "...",
    "usage": {"input_tokens": N, "output_tokens": 0}
  }
}
```

### Error: "Connection timeout"
**Cause:** No events sent for >30s

**Fix:** Add ping events (see fix #6 above)

### Error: "Unexpected end of stream"
**Cause:** Missing `message_stop` event

**Fix:** Ensure STATE 5 termination always runs:
```python
try:
    # ... streaming logic
finally:
    # Always send termination
    if not message_stopped:
        yield sse("message_stop", {"type": "message_stop"})
```

## Recommended Configuration for Claude Code

```json
{
  "llm": {
    "anthropic": {
      "apiKey": "nemo-gateway",
      "baseURL": "http://10.172.249.149:8888",
      "timeout": 600000,
      "maxRetries": 3
    }
  },
  "model": "nemotron-3-super",
  "temperature": 0.7,
  "maxTokens": 4096
}
```

## Graphify Configuration Update

For graphify AXOS extraction, update config:

```yaml
# config/production.yaml
llm:
  base_url: "http://10.172.249.149:8888/v1"  # Updated from localhost
  model: "nemotron-3-super"                    # Match actual model
  api_key: "nemo-gateway"
  timeout: 600
  max_retries: 3
  concurrency: 4  # Match nemo-gateway max_num_seqs
  temperature: 0.0
  entity_max_tokens: 2048
  relation_max_tokens: 2048
  response_format: "json_object"
```

## Next Steps

1. Apply P0 fixes to claude_adapter.py
2. Test with test_endpoints.py (should still pass 17/17)
3. Test with actual Claude Code CLI
4. Document specific error messages and fixes
5. Add integration test that spawns Claude Code CLI process
