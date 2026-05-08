# LLM Gateway - System Status
**Last Updated:** 2026-05-08 05:56:00

## ✅ System Operational

All services running with mandatory API key authentication.

### Services Status
- **Gateway:** Running (PID: 2851316) on port 8888
- **vLLM Replica 0:** Running (PID: 2851315) on port 8000
- **Model:** Qwen-2-VL-3.6-27B-Instruct (Loaded)
- **Authentication:** API Key Enforcement ACTIVE

---

## API Keys (Active)

| API Key | Username | User | Status |
|---------|----------|------|--------|
| `EDGE-AI-ADMIN` | `admin` | Admin account | ✅ Active |
| `EDGE-AI-CLAUDE-ANIL` | `anil` | Anil (Claude Code) | ✅ Active |
| `EDGE-AI-HERMES-ANIL` | `anil-hermes` | Anil (Hermes) | ✅ Active |
| `EDGE-AI-CLAUDE-ANUJ` | `anuj` | Anuj | ✅ Active |
| `EDGE-AI-CLAUDE-THEO` | `theo` | Theo | ✅ Active |
| `EDGE-AI-CLAUDE-MOULI` | `mouli` | Mouli | ✅ Active |
| `EDGE-AI-CLAUDE-SHASH` | `shash` | Shash | ✅ Active |
| `localhost` | `localhost` | Local bypass | ✅ Active (127.0.0.1 only) |

**Total Active Keys:** 8

---

## Verified Functionality

### ✅ Authentication Testing
```bash
# Invalid key - REJECTED ✓
curl -H "Authorization: Bearer invalid-key" \
     -X POST http://10.172.249.149:8888/v1/chat/completions \
     -d '{"model":"qwen-3.6-27b","messages":[...]}'
# Result: 403 Forbidden - "Invalid API key"

# Valid key - ACCEPTED ✓
curl -H "Authorization: Bearer EDGE-AI-ADMIN" \
     -X POST http://10.172.249.149:8888/v1/chat/completions \
     -d '{"model":"qwen-3.6-27b","messages":[...],"max_tokens":10}'
# Result: 200 OK - Response with 273 tokens
```

### ✅ Complete Audit Trail
Every request logged with:
1. **Authentication:** `✓ Auth: admin (key: EDGE-AI-ADMIN) from 10.172.249.149`
2. **Request:** `[admin] Request: qwen-3.6-27b - Stream: False - Key: EDGE-AI-ADMIN`
3. **Response:** `[admin] Response: 273 tokens - Input: 17, Output: 256 - Key: EDGE-AI-ADMIN`

### ✅ Monitoring Scripts
All monitoring scripts working correctly:
- `./scripts/list_all_users.sh` - Historical usage with API keys
- `./scripts/monitor_users.sh` - Current stats with API keys
- `./scripts/monitor_users_live.sh` - Live dashboard with API keys

---

## API Usage Examples

### Claude Code (Recommended Setup)
Edit `~/.claude/settings.json`:
```json
{
  "llm": {
    "anthropic": {
      "apiKey": "EDGE-AI-CLAUDE-ANIL",
      "baseURL": "http://10.172.249.149:8888"
    }
  }
}
```

### Python (Anthropic SDK)
```python
from anthropic import Anthropic

client = Anthropic(
    api_key="EDGE-AI-CLAUDE-ANIL",
    base_url="http://10.172.249.149:8888"
)

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Python (OpenAI SDK)
```python
from openai import OpenAI

client = OpenAI(
    api_key="EDGE-AI-HERMES-ANIL",
    base_url="http://10.172.249.149:8888/v1"
)

response = client.chat.completions.create(
    model="qwen-3.6-27b",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### cURL (Direct HTTP)
```bash
curl -H "Authorization: Bearer EDGE-AI-ADMIN" \
     -H "Content-Type: application/json" \
     -X POST http://10.172.249.149:8888/v1/chat/completions \
     -d '{"model":"qwen-3.6-27b","messages":[{"role":"user","content":"test"}],"max_tokens":100}'
```

---

## Log Files

**Gateway Log:**
```bash
tail -f /home/asrirang/Coding/llm_adapter/logs/nemo_gateway.log
```

**vLLM GPU Log:**
```bash
tail -f /home/asrirang/Coding/llm_adapter/logs/vllm_replica_0.log
```

**Live Request Monitor:**
```bash
tail -f logs/nemo_gateway.log | grep -E "Auth:|Request:|Response:"
```

---

## Sample Log Output

```
[2026-05-08 05:55:53] [api-key-auth] [INFO] ✓ Auth: admin (key: EDGE-AI-ADMIN) from 10.172.249.149
[2026-05-08 05:55:53] [llm-gateway] [INFO] [admin] Request: qwen-3.6-27b - Stream: False - Key: EDGE-AI-ADMIN
[2026-05-08 05:55:56] [llm-gateway] [INFO] [admin] Response: 273 tokens - Input: 17, Output: 256 - Key: EDGE-AI-ADMIN
```

---

## Security Features

✅ **API Key Authentication** - All POST requests require valid API key
✅ **Localhost Bypass** - 127.0.0.1 requests bypass authentication (local development)
✅ **Masked Logging** - API keys masked in logs (first 15 chars + `...`)
✅ **Multiple Auth Methods** - Supports `Authorization: Bearer`, `X-API-Key`, `ANTHROPIC_API_KEY` headers
✅ **IP Tracking** - Every request logged with client IP address
✅ **Complete Audit Trail** - Authentication, request, and response logging for every access

---

## Next Steps

### For Team Members (Anuj, Theo, Mouli, Shash):

1. **Get your API key** from the table above
2. **Configure your client:**
   - **Claude Code:** Add to `~/.claude/settings.json`
   - **Python:** Use in Anthropic/OpenAI SDK
   - **Other:** Send as `Authorization: Bearer EDGE-AI-xxx` header
3. **Test your setup:**
   ```bash
   curl -H "Authorization: Bearer YOUR-KEY-HERE" \
        -X POST http://10.172.249.149:8888/v1/chat/completions \
        -d '{"model":"qwen-3.6-27b","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
   ```
4. **Verify in logs** - Your username should appear in logs

### For Admin:

Monitor usage:
```bash
# Quick stats
./scripts/list_all_users.sh

# Live monitoring
./scripts/monitor_users_live.sh

# Check specific user
tail -f logs/nemo_gateway.log | grep "\[anuj\]"
```

---

## Troubleshooting

### "Invalid API key" error
- Verify you're using the correct key from the table above
- Check header format: `Authorization: Bearer EDGE-AI-xxx`
- Ensure key starts with `EDGE-AI-` prefix

### "Authentication required" error
- You're missing the API key header entirely
- Add `Authorization: Bearer YOUR-KEY` to your request

### Localhost bypass not working
- Only works from 127.0.0.1 or ::1
- Remote requests always require API key

### Request not showing in logs
- Check you're sending to the correct endpoint: `http://10.172.249.149:8888`
- Verify gateway is running: `ps aux | grep llm_manager`

---

## System Commands

**Start services:**
```bash
cd /home/asrirang/Coding/llm_adapter
source .venv/bin/activate
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py start
```

**Stop services:**
```bash
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py stop
```

**Check status:**
```bash
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py status
```

---

🎉 **System fully operational with mandatory API key authentication and complete audit logging!**
