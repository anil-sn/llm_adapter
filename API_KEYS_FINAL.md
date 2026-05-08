# Edge AI GPU - API Keys (Final)

## Active API Keys

| API Key | Username (in logs) | User | Status |
|---------|-------------------|------|--------|
| `EDGE-AI-ADMIN` | `admin` | Admin account | ✅ Active |
| `EDGE-AI-CLAUDE-ANIL` | `anil` | Anil (Claude Code) | ✅ Active |
| `EDGE-AI-HERMES-ANIL` | `anil-hermes` | Anil (Hermes) | ✅ Active |
| `EDGE-AI-CLAUDE-ANUJ` | `anuj` | Anuj | ✅ Active |
| `EDGE-AI-CLAUDE-THEO` | `theo` | Theo | ✅ Active |
| `EDGE-AI-CLAUDE-MOULI` | `mouli` | Mouli | ✅ Active |
| `EDGE-AI-CLAUDE-SHASH` | `shash` | Shash | ✅ Active |

---

## Enhanced Logging

**All logs now show:**
1. **Username** - Mapped from API key
2. **API Key** - Masked (first 15 characters + `...`)
3. **Request details** - Model, streaming, tokens
4. **IP address** - Client location

**Example log output:**
```
[2026-05-08 06:45:00] [llm-gateway] [INFO] ✓ Auth: anil (key: EDGE-AI-CLAUDE...) from 10.172.248.50
[2026-05-08 06:45:00] [llm-gateway] [INFO] [anil] Request: qwen-3.6-27b - Stream: False - Key: EDGE-AI-CLAUDE...
[2026-05-08 06:45:02] [llm-gateway] [INFO] [anil] Response: 1500 tokens - Input: 800, Output: 700 - Key: EDGE-AI-CLAUDE...
```

---

## Monitoring Commands

### Live Monitor (Updated with API Keys)
```bash
./scripts/monitor_users_live.sh
```

**Shows:**
- Active users
- Recent 15 requests with API keys
- API key usage summary
- Live stream of new requests

### User Summary (Updated with API Keys)
```bash
./scripts/list_all_users.sh
```

**Shows:**
- All users and request counts
- Requests by model
- User → Model breakdown
- Token usage by user
- **API key usage summary** (NEW)
- Recent 20 requests with API keys

### Simple Live Tail
```bash
tail -f logs/nemo_gateway.log | grep '\[.*\] Request:.*Key:'
```

---

## Log Files

**Gateway logs:** `/home/asrirang/Coding/llm_adapter/logs/nemo_gateway.log`
- Contains all request/response logs
- Shows API keys (masked)
- Shows usernames
- Shows token usage

**vLLM logs:** `/home/asrirang/Coding/llm_adapter/logs/vllm_replica_0.log`
- GPU inference logs
- Model loading
- Hardware status

---

## Audit Trail

Every request is logged with:

1. **Authentication event:**
   ```
   ✓ Auth: anil (key: EDGE-AI-CLAUDE...) from 10.172.248.50
   ```

2. **Request event:**
   ```
   [anil] Request: qwen-3.6-27b - Stream: False - Key: EDGE-AI-CLAUDE...
   ```

3. **Response event:**
   ```
   [anil] Response: 1500 tokens - Input: 800, Output: 700 - Key: EDGE-AI-CLAUDE...
   ```

This provides complete audit trail:
- ✅ Who accessed (username + API key)
- ✅ When accessed (timestamp)
- ✅ From where (IP address)
- ✅ What they did (model, tokens)
- ✅ How much they used (token counts)

---

## Security Notes

**API Key Masking:**
- Keys are masked in logs: `EDGE-AI-CLAUDE...` (first 15 chars + `...`)
- Full keys never appear in logs
- Enough to identify the key, not enough to steal it

**Authentication Logs:**
- Successful auth: `✓ Auth: username (key: EDGE-AI-xxx...) from IP`
- Failed auth: `Access denied: Invalid API key 'EDGE-AI-xxx...' from IP`

**Localhost Bypass:**
- Localhost requests show: `Key: localhost-bypass`
- No actual API key needed for 127.0.0.1

---

## Next Steps After Restart

1. ✅ Restart gateway (you'll do this)
2. ✅ Test with admin key
3. ✅ Distribute keys to team
4. ✅ Monitor logs to see who's using GPUs
5. ✅ Check API key usage summary

---

## Ready to Restart?

```bash
cd /home/asrirang/Coding/llm_adapter
source .venv/bin/activate
LLM_CONFIG=config/config-qwen36-27b.yaml python scripts/setup/llm_manager.py start
```

After restart, test:
```bash
# Should fail (no key)
curl -X POST http://10.172.249.149:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-3.6-27b","messages":[{"role":"user","content":"test"}],"max_tokens":10}'

# Should work (with admin key)
curl -H "Authorization: Bearer EDGE-AI-ADMIN" \
     -H "Content-Type: application/json" \
     -X POST http://10.172.249.149:8888/v1/chat/completions \
     -d '{"model":"qwen-3.6-27b","messages":[{"role":"user","content":"test"}],"max_tokens":10}'
```

Then check logs:
```bash
tail -20 logs/nemo_gateway.log | grep -E "Auth:|Request:|Response:"
```

You should see:
```
✓ Auth: admin (key: EDGE-AI-ADMIN...) from 10.172.249.149
[admin] Request: qwen-3.6-27b - Stream: False - Key: EDGE-AI-ADMIN
[admin] Response: XX tokens - Input: XX, Output: XX - Key: EDGE-AI-ADMIN
```

🎉 Complete API key authentication with full audit logging!
