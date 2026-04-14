# Claude Code CLI Setup for Nemo-Gateway

Use your local Nemotron-3 120B model as the backend for Claude Code CLI.

## Quick Start

```bash
cd ~/coding/nemo_orchestrator

# 1. Run setup (creates config files)
./setup_claude_code_cli.sh

# 2. Test Claude Code
claude "Hello, are you working?"

# 3. Run validation suite (optional)
./validate_claude_code_cli.sh
```

## What Gets Configured

The setup script creates:

1. **`~/.config/claude/settings.json`**
   ```json
   {
     "llm": {
       "anthropic": {
         "apiKey": "nemo-gateway",
         "baseURL": "http://10.172.249.149:8888"
       }
     },
     "model": "nemotron-3-super"
   }
   ```

2. **`~/.config/claude/auth.json`**
   - Bypasses login requirement for local gateway

## Usage Examples

### Basic Commands

```bash
# Interactive session
claude

# Single query
claude "What is 2+2?"

# With file context
cd ~/coding/nemo_orchestrator
claude "Explain the config.yaml file"

# Code review
claude "Review the nemo_gateway.py file for potential issues"
```

### Advanced Usage

```bash
# Use different model (if multiple available)
claude --model nemotron-3-super "Your question"

# With environment variables (alternative to settings.json)
ANTHROPIC_API_KEY="nemo-gateway" \
ANTHROPIC_BASE_URL="http://10.172.249.149:8888" \
claude "Your question"
```

## Validation Scripts

### 1. `setup_claude_code_cli.sh`
- Creates configuration files
- Tests gateway connectivity
- Verifies API responses

### 2. `validate_claude_code_cli.sh`
- Runs 5+ integration tests
- Validates streaming mode
- Tests multi-turn conversations
- Checks file awareness

### 3. `test_claude_code_env.sh`
- Quick connectivity check
- Model availability verification
- Basic API call test

## Troubleshooting

### Issue: "Not logged in"

**Solution:**
```bash
# Re-run setup script
./setup_claude_code_cli.sh

# Or manually create auth file
mkdir -p ~/.config/claude
echo '{"apiKey": "nemo-gateway", "loggedIn": true}' > ~/.config/claude/auth.json
```

### Issue: Connection timeout

**Solution:**
```bash
# Check if gateway is running
curl http://10.172.249.149:8888/health

# On remote server
ssh asrirang@slcx-p7960.calix.local
cd ~/Coding/nemo_orchestrator
./llm_manager.py status
./verify_startup.sh
```

### Issue: Wrong model responding

**Solution:**
```bash
# Check available models
curl -s http://10.172.249.149:8888/v1/models | jq -r '.data[].id'

# Should show: nemotron-3-super

# Force model in command
claude --model nemotron-3-super "Your question"
```

### Issue: Slow responses

**Solution:**
```bash
# Check GPU utilization on remote server
ssh asrirang@slcx-p7960.calix.local
nvidia-smi

# Expected: ~65% VRAM usage on all 4 GPUs
# If 99%: Memory pressure, reduce max_num_seqs in config.yaml
```

## Performance Tips

1. **Keep prompts focused**: Nemotron-3 works best with clear, specific prompts
2. **Use streaming mode**: Responses start appearing immediately
3. **Leverage file context**: Claude Code automatically includes relevant files
4. **Monitor gateway logs**: `tail -f ~/Coding/nemo_orchestrator/logs/nemo_gateway.log`

## Technical Details

- **Gateway**: http://10.172.249.149:8888
- **Model**: nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8
- **Served Name**: nemotron-3-super
- **Protocol**: Anthropic Messages API (compatible)
- **Context Window**: 8,192 tokens (configurable in config.yaml)
- **Tensor Parallelism**: 4 GPUs (TP=4)
- **GPU Memory**: 65% utilization (32GB per GPU)

## Next Steps

After setup, try these workflows:

```bash
# Code review
cd ~/coding/nemo_orchestrator
claude "Review this codebase for optimization opportunities"

# Debug assistance
claude "Analyze the logs and suggest improvements"

# Documentation
claude "Create a README for this project"

# Architecture questions
claude "Explain how the adapter pattern works in this gateway"
```

## See Also

- Main test suite: `./test_endpoints.py`
- Comprehensive API tests: `./test_claude_code_cli_comprehensive.sh`
- Startup verification: `./verify_startup.sh`
- System configuration: `config.yaml`
