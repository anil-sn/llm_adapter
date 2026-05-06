# LLM Adapter Examples

This directory contains example scripts demonstrating how to use the LLM adapter
with various features.

## Available Examples

### 1. Tool Calling Example (`tool_calling_example.py`)

Demonstrates how to use function calling / tool use with the LLM:
- **Web Search**: Search the web for current information
- **Calculator**: Perform mathematical calculations
- **DateTime**: Get current date/time information
- **Multi-turn conversations** with tool results

**Prerequisites:**
```bash
# Install web search dependency
pip install ddgs

# Ensure LLM is running
LLM_CONFIG=config/config-qwen36-35b.yaml python scripts/setup/llm_manager.py start
```

**Usage:**
```bash
python examples/tool_calling_example.py
```

**How it works:**
1. Send request with tool definitions
2. Model decides if tools are needed
3. Execute tool calls (web search, calculator, etc.)
4. Send results back to model
5. Get final answer incorporating tool results

---

### 2. Live Web Search Test (`test_web_search_live.py`)

End-to-end test demonstrating the complete web search tool calling workflow:
- LLM receives a question requiring web search
- Model autonomously calls the `web_search` tool
- Tool executes real DuckDuckGo search
- Results are fed back to the model
- Model synthesizes final answer from search results

**Prerequisites:**
```bash
# Install tool dependencies
pip install -e ".[tools]"

# Ensure LLM is running
make start
```

**Usage:**
```bash
python examples/test_web_search_live.py
```

**Expected Output:**
```
✅ SUCCESS: LLM called the web_search tool!
✅ Web search successful! Found 5 results
✅ COMPLETE SUCCESS: Full tool calling workflow works!
```

---

## Adding New Examples

To add a new example:

1. Create a new Python file in this directory
2. Add a docstring explaining what it demonstrates
3. Include inline comments for clarity
4. Update this README with usage instructions

---

## Common Patterns

### Basic Chat Completion
```python
import requests

response = requests.post(
    "http://localhost:8888/v1/chat/completions",
    json={
        "model": "qwen-3.6-35b",
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 500,
    }
)

print(response.json()["choices"][0]["message"]["content"])
```

### Streaming Response
```python
response = requests.post(
    "http://localhost:8888/v1/chat/completions",
    json={
        "model": "qwen-3.6-35b",
        "messages": [{"role": "user", "content": "Tell me a story"}],
        "stream": True,
    },
    stream=True,
)

for line in response.iter_lines():
    if line:
        print(line.decode("utf-8"))
```

### Tool Calling
See `tool_calling_example.py` for a complete example.

---

## Notes

- All examples assume the LLM is running on `localhost:8888`
- Change the `model` parameter to use different models
- Check `config/` directory for available model configurations
- See main README.md for more information about the adapter
