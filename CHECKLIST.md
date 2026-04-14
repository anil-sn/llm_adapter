# Post-Reorganization Checklist

## ✅ Verification Steps

### 1. Project Structure
- [ ] Root directory is clean (only pyproject.toml, uv.lock, README.md)
- [ ] All source code in `src/nemo_orchestrator/`
- [ ] All tests in `tests/{unit,integration,e2e}/`
- [ ] All scripts in `scripts/{setup,testing,deployment}/`
- [ ] All configs in `config/`
- [ ] All docs in `docs/`

### 2. Integration with claude-adapter-py
- [ ] Production converters copied to `src/nemo_orchestrator/adapters/claude_code/`
- [ ] Models directory present: `src/nemo_orchestrator/adapters/claude_code/models/`
- [ ] ClaudeAdapterV2 created using production converters
- [ ] Imports fixed (no broken relative imports)

### 3. Test the V2 Adapter

```bash
# Terminal 1: Start vLLM backend
cd /mnt/data/coding/nemo_orchestrator
./llm_manager.py start

# Terminal 2 (local): Test V2 adapter
cd ~/coding/nemo_orchestrator
python tests/integration/test_adapter_v2.py
```

**Expected Output:**
```
✓ Converted request to OpenAI format
✓ Converted response to Anthropic format
✓ Streaming completed
✓ Tool use found: True
✓ Text deltas: 0
✓ Perfect! Tool calls with 0 text deltas (as expected)
✓ ALL TESTS PASSED
```

### 4. Test E2E Tool Execution

```bash
python tests/e2e/test_e2e_tool_execution.py
```

**Expected:**
```
✓ ALL TESTS PASSED
✓ Tool execution flow works end-to-end
✓ Claude Code CLI should work correctly
```

### 5. Update Gateway to Use V2

**Edit:** `src/nemo_orchestrator/gateway/server.py`

Replace:
```python
from adapters.claude_adapter import ClaudeAdapter
```

With:
```python
from nemo_orchestrator.adapters import ClaudeAdapterV2
```

And update instantiation:
```python
adapter = ClaudeAdapterV2(backend_url="http://127.0.0.1:8000")
```

### 6. Deploy and Test

```bash
# Rsync to remote server
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='archive' \
  ~/coding/nemo_orchestrator/ \
  asrirang@10.172.249.149:/mnt/data/coding/nemo_orchestrator/

# SSH and restart
ssh asrirang@10.172.249.149
cd /mnt/data/coding/nemo_orchestrator
./llm_manager.py restart
```

### 7. Test Claude Code CLI

```bash
# On local machine
claude "list files in current directory"
```

**Expected:**
- Tool executes (Bash command runs)
- Actual file listing returned
- No "thinking text" displayed
- Clean tool execution

### 8. Streaming Verification

```bash
# Test streaming with curl
curl -X POST http://10.172.249.149:8888/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-haiku-4-5-20251001",
    "messages": [{"role": "user", "content": "List files"}],
    "tools": [{
      "name": "Bash",
      "description": "Execute bash",
      "input_schema": {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"]
      }
    }],
    "stream": true,
    "max_tokens": 200
  }'
```

**Expected:**
- `event: message_start`
- `event: content_block_start` (type: tool_use)
- `event: input_json_delta` (tool arguments)
- `event: content_block_stop`
- `event: message_delta` (stop_reason: tool_use)
- `event: message_stop`
- **NO `text_delta` events!**

---

## 🐛 Troubleshooting

### Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'nemo_orchestrator'
```

**Fix:**
```bash
# Install package in editable mode
pip install -e .
# Or
uv pip install -e .
```

### Relative Import Errors

**Error:**
```
ImportError: attempted relative import beyond top-level package
```

**Fix:** Check all imports in `src/nemo_orchestrator/adapters/claude_code/*.py` use:
```python
from .models.anthropic import ...  # NOT from ..models
from .utils import logger          # NOT from ..utils
```

### Tools Not Working

**Error:** Model returns text instead of tool_use

**Check:**
1. vLLM config has `enable_auto_tool_choice: true`
2. vLLM config has `tool_call_parser: qwen3_coder`
3. Model supports tool calling
4. Adapter is correctly converting tool schemas

### Streaming Issues

**Error:** Text deltas sent when tools present

**Check:**
1. Using ClaudeAdapterV2 (not old ClaudeAdapter)
2. StreamState is properly accumulating tool calls
3. Text buffering is working correctly
4. Check logs for "Tool call missing 'id'" errors

---

## 📋 Rollback Plan

If something breaks:

```bash
# Restore from archive
cp -r archive/deprecated/* .

# Or from git
git checkout HEAD -- .
```

---

## ✨ Success Criteria

- [x] Project restructured professionally
- [ ] V2 adapter tests pass
- [ ] E2E tests pass
- [ ] Gateway updated to use V2
- [ ] Deployed to remote server
- [ ] Claude Code CLI works with tools
- [ ] Streaming has 0 text deltas with tools
- [ ] No import errors
- [ ] All documentation updated
