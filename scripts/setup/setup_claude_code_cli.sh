#!/usr/bin/env bash
# Complete Claude Code CLI Setup for Nemo-Gateway
# Run this script to configure Claude Code to use your local Nemotron model

set -e

GATEWAY_URL="http://10.172.249.149:8888"
MODEL="nemotron-3-super"
CLAUDE_CONFIG_DIR="$HOME/.config/claude"

echo "========================================================================="
echo "  Claude Code CLI Setup for Nemo-Gateway"
echo "========================================================================="
echo ""

# Step 1: Test gateway connectivity
echo "1. Testing gateway connectivity..."
if curl -s "${GATEWAY_URL}/health" > /dev/null 2>&1; then
    echo "   ✓ Gateway is reachable at ${GATEWAY_URL}"
else
    echo "   ✗ Cannot reach gateway at ${GATEWAY_URL}"
    echo "   Make sure the gateway is running: ssh asrirang@slcx-p7960.calix.local './llm_manager.py status'"
    exit 1
fi

# Step 2: Create config directory
echo ""
echo "2. Creating Claude Code config directory..."
mkdir -p "$CLAUDE_CONFIG_DIR"
echo "   ✓ Created $CLAUDE_CONFIG_DIR"

# Step 3: Create auth file (bypass login)
echo ""
echo "3. Creating authentication bypass..."
cat > "$CLAUDE_CONFIG_DIR/auth.json" << 'EOF'
{
  "apiKey": "nemo-gateway",
  "loggedIn": true
}
EOF
echo "   ✓ Created auth.json"

# Step 4: Create settings file
echo ""
echo "4. Creating settings.json..."
cat > "$CLAUDE_CONFIG_DIR/settings.json" << EOF
{
  "llm": {
    "anthropic": {
      "apiKey": "nemo-gateway",
      "baseURL": "${GATEWAY_URL}"
    }
  },
  "model": "${MODEL}"
}
EOF
echo "   ✓ Created settings.json"

# Step 5: Verify configuration
echo ""
echo "5. Verifying configuration..."
if [ -f "$CLAUDE_CONFIG_DIR/settings.json" ] && [ -f "$CLAUDE_CONFIG_DIR/auth.json" ]; then
    echo "   ✓ All configuration files created"
else
    echo "   ✗ Configuration files missing"
    exit 1
fi

# Step 6: Test API call
echo ""
echo "6. Testing API endpoint..."
RESPONSE=$(curl -s -X POST "${GATEWAY_URL}/v1/messages" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -H "x-api-key: nemo-gateway" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"Say 'Ready'\"}],
    \"max_tokens\": 10
  }" 2>/dev/null)

if echo "$RESPONSE" | jq -e '.content[0].text' > /dev/null 2>&1; then
    REPLY=$(echo "$RESPONSE" | jq -r '.content[0].text')
    echo "   ✓ API working! Response: $REPLY"
else
    echo "   ✗ API call failed"
    echo "   Response: $RESPONSE"
    exit 1
fi

echo ""
echo "========================================================================="
echo "  ✅ Setup Complete!"
echo "========================================================================="
echo ""
echo "Configuration saved to: $CLAUDE_CONFIG_DIR/"
echo ""
echo "You can now use Claude Code CLI with your local Nemotron model:"
echo ""
echo "  # Start interactive session"
echo "  claude"
echo ""
echo "  # Single query"
echo "  claude 'What is 2+2?'"
echo ""
echo "  # With file context"
echo "  cd ~/coding/nemo_orchestrator"
echo "  claude 'Explain the config.yaml file'"
echo ""
echo "  # Override model (if needed)"
echo "  claude --model nemotron-3-super"
echo ""
echo "Your settings:"
echo "  Gateway: ${GATEWAY_URL}"
echo "  Model:   ${MODEL}"
echo "  Auth:    Bypassed (local gateway)"
echo ""
echo "========================================================================="
