#!/bin/bash
# restart_gateway.sh - Clean restart of Nemo-Gateway
set -e

cd "$(dirname "$0")"

echo "🔪 Killing existing gateway..."
pkill -9 -f nemo_gateway 2>/dev/null || true
pkill -9 -f "python.*nemo_gateway" 2>/dev/null || true
sleep 2

echo "🧹 Clearing Python caches..."
find . -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
rm -f .nemo_gateway.pid

echo "🔍 Verifying adapter imports..."
python3 -c "
from adapters.nemotron_adapter import NemotronAdapter
print('✅ NemotronAdapter loaded successfully')
"

echo "🚀 Starting gateway..."
nohup .venv/bin/python nemo_gateway.py > logs/nemo_gateway.log 2>&1 &
GATEWAY_PID=$!
echo "Gateway PID: $GATEWAY_PID"

echo "⏳ Waiting 5 seconds for startup..."
sleep 5

echo "✅ Testing endpoints..."
echo ""

# Test 1: OpenAI chat
echo "=== TEST 1: OpenAI Chat ==="
RESP=$(curl -s http://localhost:8888/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "nemotron-3-super", "messages": [{"role": "user", "content": "2+2?"}], "max_tokens": 10}')
echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if 'choices' in d:
    print('✅ PASS:', d['choices'][0]['message'].get('content', '')[:50])
else:
    print('❌ FAIL:', d)
"

echo ""

# Test 2: Anthropic messages
echo "=== TEST 2: Anthropic Messages ==="
RESP=$(curl -s http://localhost:8888/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model": "nemotron-3-super", "messages": [{"role": "user", "content": "2+2?"}], "max_tokens": 10}')
echo "$RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
blocks = d.get('content', [])
text = ''.join(b.get('text', '') for b in blocks if b.get('type') == 'text')
if text:
    print('✅ PASS:', text[:50])
else:
    print('❌ FAIL: Empty content')
    print('Response:', json.dumps(d, indent=2)[:200])
"

echo ""

# Test 3: Get Models
echo "=== TEST 3: Get Models ==="
curl -s http://localhost:8888/v1/models | python3 -c "
import sys, json
d = json.load(sys.stdin)
models = [m['id'] for m in d.get('data', [])]
print('✅ Models:', models)
"

echo ""
echo "✨ Restart complete!"
