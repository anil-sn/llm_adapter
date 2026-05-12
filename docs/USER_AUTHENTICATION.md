# User Authentication - GPU Access Control

## Overview

The LLM Gateway now **requires** users to identify themselves before accessing GPU resources. This ensures you always know who is using your GPUs.

## How It Works

**All POST requests** (inference requests) **REQUIRE** the `X-User-Name` header.

**Without the header:**
```bash
curl -X POST http://your-server:8888/v1/chat/completions ...
```
**Response:**
```json
{
  "error": "authentication_required",
  "message": "GPU access requires user identification. Please provide X-User-Name header."
}
```

**With the header (✅ Works):**
```bash
curl -H "X-User-Name: john" -X POST http://your-server:8888/v1/chat/completions ...
```

---

## Client Setup

### Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "llm": {
    "anthropic": {
      "baseURL": "http://10.172.249.149:8888",
      "apiKey": "dummy",
      "headers": {
        "X-User-Name": "your-name-here"
      }
    }
  }
}
```

**Replace `your-name-here` with your actual name!**

### Python (Anthropic SDK)

```python
from anthropic import Anthropic

client = Anthropic(
    base_url="http://10.172.249.149:8888",
    api_key="dummy",
    default_headers={"X-User-Name": "john"}
)

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100
)
```

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://10.172.249.149:8888/v1",
    api_key="dummy",
    default_headers={"X-User-Name": "john"}
)

response = client.chat.completions.create(
    model="qwen-3.6-27b",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### cURL

```bash
curl -H "X-User-Name: john" \
     -H "Content-Type: application/json" \
     -X POST http://10.172.249.149:8888/v1/chat/completions \
     -d '{
       "model": "qwen-3.6-27b",
       "messages": [{"role": "user", "content": "Hello!"}],
       "max_tokens": 100
     }'
```

### JavaScript/TypeScript

```javascript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
  baseURL: 'http://10.172.249.149:8888',
  apiKey: 'dummy',
  defaultHeaders: {
    'X-User-Name': 'john'
  }
});

const response = await client.messages.create({
  model: 'claude-haiku-4-5-20251001',
  messages: [{ role: 'user', content: 'Hello!' }],
  max_tokens: 100
});
```

### Requests Library (Python)

```python
import requests

headers = {"X-User-Name": "john"}

response = requests.post(
    "http://10.172.249.149:8888/v1/chat/completions",
    headers=headers,
    json={
        "model": "qwen-3.6-27b",
        "messages": [{"role": "user", "content": "Hello!"}],
        "max_tokens": 100
    }
)
```

---

## Rules

### Username Requirements

- **Minimum length:** 2 characters
- **Maximum length:** 50 characters
- **Blocked names:** unknown, anonymous, test, guest, admin, root

### Alternative Headers

The system accepts these header names (in order of priority):

1. `X-User-Name` (recommended)
2. `X-User-ID`
3. `User-Name`
4. `User-ID`

---

## Configuration

Edit `/home/asrirang/Coding/llm_adapter/config/auth.yaml`:

```yaml
# Enable/disable authentication
enabled: true

# Require X-User-Name header
require_user_header: true

# Blocked usernames
blocked_usernames:
  - "unknown"
  - "anonymous"
  - "test"

# Whitelist specific IPs (optional)
whitelisted_ips: []
  # - "127.0.0.1"  # Localhost bypass
```

---

## Monitoring

After restart, check logs to see who's accessing your GPUs:

```bash
# Live monitoring
tail -f logs/nemo_gateway.log | grep '\[.*\] Request:'

# User summary
./scripts/list_all_users.sh

# Live dashboard
./scripts/monitor_users_live.sh
```

**Example logs:**
```
[2026-05-08 05:20:00] [llm-gateway] [INFO] [john] Request: qwen-3.6-27b - Stream: False
[2026-05-08 05:20:01] [llm-gateway] [INFO] [sarah] Request: qwen-3.6-27b - Stream: True
[2026-05-08 05:20:02] [llm-gateway] [INFO] [mike] Request: qwen-3.6-27b - Stream: False
```

---

## Restart Required

To activate authentication:

```bash
cd /home/asrirang/Coding/llm_adapter
source .venv/bin/activate
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py stop
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py start
```

---

## Testing

**Test without header (should fail):**
```bash
curl -X POST http://10.172.249.149:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen-3.6-27b", "messages": [{"role": "user", "content": "hi"}]}'
```

**Expected response:**
```json
{
  "error": "authentication_required",
  "message": "GPU access requires user identification. Please provide X-User-Name header."
}
```

**Test with header (should work):**
```bash
curl -H "X-User-Name: test-user" \
     -H "Content-Type: application/json" \
     -X POST http://10.172.249.149:8888/v1/chat/completions \
     -d '{"model": "qwen-3.6-27b", "messages": [{"role": "user", "content": "hi"}], "max_tokens": 50}'
```

**Expected response:**
```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "choices": [...]
}
```

---

## Troubleshooting

### "authentication_required" error

**Solution:** Add `X-User-Name` header to your requests.

### Client can't connect

**Check:** Is the header configured correctly in your client settings?

### Name rejected

**Check:** Is your username in the blocked list? Change it to your real name.

---

## Summary

✅ **All GPU access now requires user identification**  
✅ **Simple header-based authentication** (no passwords)  
✅ **Easy to set up** in any client  
✅ **Full visibility** into who's using your GPUs  
✅ **Configurable** rules and whitelist  

Now you'll always know exactly who is using your GPU resources! 🔒
