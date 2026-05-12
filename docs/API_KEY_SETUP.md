# API Key Authentication - Complete Setup Guide

## Overview

Your LLM Gateway now **requires valid API keys** for all GPU access. Only users with authorized API keys can make requests.

---

## How It Works

**All POST requests require a valid API key in the Authorization header:**

```bash
curl -H "Authorization: Bearer sk-your-key-here" \
     -X POST http://10.172.249.149:8888/v1/chat/completions ...
```

**Without a valid API key:**
```json
{
  "error": {
    "type": "authentication_required",
    "message": "Valid API key required to access GPU resources"
  }
}
```

---

## Assigned API Keys

Edit `/home/asrirang/Coding/llm_adapter/config/api_keys.yaml`:

```yaml
api_keys:
  "sk-asrirang-local-dev": "asrirang"        # Your local development
  "sk-hermes-production": "hermes"           # Hermes client
  "sk-claude-code-dev": "claude-code"        # Claude Code
  "sk-zpa-connector": "zpa-connector"        # ZPA connector (10.172.248.50)
  "sk-openwebui-test": "openwebui"           # Open WebUI

  # Add team members:
  # "sk-john-dev-2024": "john"
  # "sk-sarah-prod-2024": "sarah"
```

**Key format:**
- Must start with `sk-`
- Minimum 16 characters
- Each key maps to a username (shown in logs)

---

## Client Configuration

### 1. Claude Code (`~/.claude/settings.json`)

```json
{
  "llm": {
    "anthropic": {
      "baseURL": "http://localhost:8888",
      "apiKey": "sk-asrirang-local-dev"
    }
  }
}
```

**Or keep using port 8000 directly** (bypasses gateway, localhost exempt):
```json
{
  "llm": {
    "anthropic": {
      "baseURL": "http://localhost:8000",
      "apiKey": "dummy"
    }
  }
}
```

### 2. Python (Anthropic SDK)

```python
from anthropic import Anthropic

client = Anthropic(
    base_url="http://10.172.249.149:8888",
    api_key="sk-your-assigned-key"  # Use your actual key
)

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100
)
```

### 3. Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://10.172.249.149:8888/v1",
    api_key="sk-your-assigned-key"
)

response = client.chat.completions.create(
    model="qwen-3.6-27b",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### 4. cURL

```bash
curl -H "Authorization: Bearer sk-your-assigned-key" \
     -H "Content-Type: application/json" \
     -X POST http://10.172.249.149:8888/v1/chat/completions \
     -d '{
       "model": "qwen-3.6-27b",
       "messages": [{"role": "user", "content": "Hello!"}],
       "max_tokens": 100
     }'
```

### 5. Hermes Configuration

Locate Hermes config file and add:

```yaml
# Hermes config
api:
  base_url: "http://10.172.249.149:8888"
  api_key: "sk-hermes-production"
```

### 6. Open WebUI

In Open WebUI admin panel:
1. Go to Settings → Connections
2. Set Base URL: `http://10.172.249.149:8888`
3. Set API Key: `sk-openwebui-test`

---

## Localhost Bypass

**Localhost (127.0.0.1) is exempt** from API key requirement:

```yaml
# In config/api_keys.yaml
allow_localhost_bypass: true  # Set to false to enforce for localhost too
```

This means:
- ✅ Your Claude Code on `localhost:8000` → No key needed
- ✅ Local scripts on `localhost:8888` → No key needed  
- ❌ Remote clients → API key required

---

## Testing

### Test Localhost (Should Work Without Key)

```bash
curl -X POST http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-3.6-27b","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
```

### Test Remote Without Key (Should Fail)

```bash
curl -X POST http://10.172.249.149:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-3.6-27b","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
```

**Expected:**
```json
{
  "error": {
    "type": "authentication_required",
    "message": "Valid API key required to access GPU resources"
  }
}
```

### Test With Valid Key (Should Work)

```bash
curl -H "Authorization: Bearer sk-asrirang-local-dev" \
     -H "Content-Type": application/json" \
     -X POST http://10.172.249.149:8888/v1/chat/completions \
     -d '{"model":"qwen-3.6-27b","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
```

### Test With Invalid Key (Should Fail)

```bash
curl -H "Authorization: Bearer sk-fake-key" \
     -X POST http://10.172.249.149:8888/v1/chat/completions \
     -d '{"model":"qwen-3.6-27b","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
```

**Expected:**
```json
{
  "error": {
    "type": "invalid_api_key",
    "message": "The provided API key is not valid"
  }
}
```

---

## Monitoring

Logs now show the **username** associated with each API key:

```bash
tail -f logs/nemo_gateway.log | grep '\[.*\] Request:'
```

**Example:**
```
[2026-05-08 06:00:00] [llm-gateway] [INFO] [localhost] Request: qwen-3.6-27b - Stream: False
[2026-05-08 06:00:05] [llm-gateway] [INFO] [hermes] Request: qwen-3.6-27b - Stream: True
[2026-05-08 06:00:10] [llm-gateway] [INFO] [zpa-connector] Request: qwen-3.6-27b - Stream: False
```

---

## Adding New Users

1. **Generate a new API key:**
   ```bash
   echo "sk-$(openssl rand -hex 16)"
   # Output: sk-a1b2c3d4e5f6...
   ```

2. **Add to config/api_keys.yaml:**
   ```yaml
   api_keys:
     "sk-a1b2c3d4e5f6...": "new-user-name"
   ```

3. **Reload configuration** (no restart needed):
   ```python
   # In Python console
   from llm_adapter.middleware.api_key_auth import get_api_key_manager
   from pathlib import Path
   manager = get_api_key_manager(Path("/home/asrirang/Coding/llm_adapter"))
   manager.reload_config()
   ```

   Or just restart gateway to pick up changes.

4. **Give key to user:**
   ```
   Your API key: sk-a1b2c3d4e5f6...
   
   Add to your client:
   Authorization: Bearer sk-a1b2c3d4e5f6...
   ```

---

## Revoking Access

Simply remove the key from `config/api_keys.yaml` and restart (or reload).

---

## Configuration Options

Edit `config/api_keys.yaml`:

```yaml
# Enable/disable API key enforcement
enforce_api_keys: true  # Set to false to disable authentication

# Allow localhost bypass
allow_localhost_bypass: true  # Set to false to enforce for localhost too

# Key format requirements
require_prefix: "sk-"  # All keys must start with this
min_key_length: 16     # Minimum key length
```

---

## Activation

```bash
cd /home/asrirang/Coding/llm_adapter
source .venv/bin/activate
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py stop
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py start
```

---

## What Happens After Restart

| Client | Location | API Key Required? | Status |
|--------|----------|-------------------|--------|
| Your Claude Code | localhost:8000 | ❌ No (direct to vLLM) | ✅ Works |
| Your scripts | localhost:8888 | ❌ No (localhost bypass) | ✅ Works |
| ZPA Connector | 10.172.248.50 → 8888 | ✅ Yes | ❌ Blocked until key added |
| Hermes | Remote → 8888 | ✅ Yes | ❌ Blocked until key added |
| Open WebUI | Remote → 8888 | ✅ Yes | ❌ Blocked until key added |

---

## Summary

✅ **API key authentication enforced** for all external GPU access  
✅ **Localhost exempt** (your local development unaffected)  
✅ **Each user gets their own API key**  
✅ **Logs show usernames** instead of IP addresses  
✅ **Easy to add/revoke** users  
✅ **Standard Anthropic/OpenAI API format** (no custom code needed)  

Now you have **complete control** over who accesses your GPUs! 🔒
