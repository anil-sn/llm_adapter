#!/bin/bash
# Environment setup for using Claude Code with Gemma 4 via tested endpoint
# Usage: source env_gemma4.sh && claude --model gemma4

# API endpoint (tested working)
export ANTHROPIC_BASE_URL=https://gemma4.dev.ocp-ai.calix.local/
export ANTHROPIC_API_KEY=""

# HTTPS (self-signed certs)
export NODE_TLS_REJECT_UNAUTHORIZED=0

# Claude Code settings
export CLAUDE_CODE_ATTRIBUTION_HEADER=0
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=80
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
export CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1

# Model routing (all point to the same Gemma 4 endpoint)
export ANTHROPIC_MODEL=gemma-4-26b-a4b-it
export ANTHROPIC_DEFAULT_OPUS_MODEL=gemma-4-26b-a4b-it
export ANTHROPIC_DEFAULT_SONNET_MODEL=gemma-4-26b-a4b-it
export ANTHROPIC_DEFAULT_HAIKU_MODEL=gemma-4-26b-a4b-it
export ANTHROPIC_SMALL_FAST_MODEL=gemma-4-26b-a4b-it
export CLAUDE_AGENT_SUBAGENT_MODEL=gemma-4-26b-a4b-it

echo "✅ Gemma 4 environment loaded"
echo "   Base URL: $ANTHROPIC_BASE_URL"
echo "   Model: $ANTHROPIC_MODEL"
echo ""
echo "   Run: claude --model gemma-4-26b-a4b-it"
