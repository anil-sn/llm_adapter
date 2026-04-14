# Nemo Orchestrator

**High-Performance LLM Inference Cluster for Nemotron-3 Super 120B**

A production-ready inference orchestrator featuring multi-protocol support, intelligent batching, and seamless Claude Code integration.

---

## 🚀 Features

- **Multi-Protocol Support**: Anthropic Messages API, OpenAI Chat Completions, NVIDIA Nemotron
- **Production-Ready Streaming**: Battle-tested converters from [claude-adapter-py](https://github.com/XuYan-Breeze/claude-adapter-py)
- **Pulse Scheduler**: Smart request batching with configurable windows (5ms-30ms)
- **TokenGuard**: Automatic context window management to prevent OOM errors
- **Claude Code Compatible**: Full tool calling support with proper SSE streaming
- **FP8/FP4 KV Cache**: Optimized for Nemotron-3 Super 120B (32K context)

---

## 📁 Project Structure

```
nemo_orchestrator/
├── src/nemo_orchestrator/      # Main source code
│   ├── adapters/                # Protocol adapters
│   │   ├── claude_adapter_v2.py      # Production Claude adapter
│   │   ├── nemotron_adapter.py       # Nemotron optimizations
│   │   ├── openai_adapter.py         # OpenAI pass-through
│   │   └── claude_code/              # Production converters
│   ├── gateway/                 # Traffic router
│   ├── scheduler/               # Request batching
│   └── utils/                   # Utilities
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # API tests
│   └── e2e/                     # End-to-end tests
├── scripts/                     # Management scripts
│   ├── setup/                   # Setup & deployment
│   ├── testing/                 # Test scripts
│   └── deployment/              # Deployment tools
├── config/                      # Configuration files
├── docs/                        # Documentation
└── archive/                     # Deprecated code
```

---

## 🛠️ Installation

### Prerequisites
- Python 3.10+
- NVIDIA GPU with 80GB+ VRAM (for Nemotron-3 Super 120B)
- CUDA 12.1+
- `uv` package manager (or pip)

### Setup

```bash
# Install dependencies
uv sync

# Or with pip
pip install -e .
```

---

## 🚦 Quick Start

### 1. Start the Cluster

```bash
# Start vLLM + Gateway
python scripts/setup/llm_manager.py start

# Check status
python scripts/setup/llm_manager.py status
```

### 2. Configure Claude Code CLI

```bash
# Run setup script
bash scripts/setup/setup_claude_code_cli.sh

# Test
claude "list files in current directory"
```

### 3. Run Tests

```bash
# Unit tests
python tests/unit/test_adapter_unit.py

# E2E tool execution
python tests/e2e/test_e2e_tool_execution.py
```

---

## 🔧 Configuration

See `config/config.yaml` for:
- Model routing rules
- Adapter selection
- Context limits (TokenGuard)
- Batching parameters

---

## 📊 Performance

| Metric | Value |
|--------|-------|
| Max Context | 32,768 tokens |
| KV Cache | FP8/FP4 Quantized |
| Batching Window | 5-30ms (adaptive) |
| Protocol Overhead | <1ms |

---

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and components
- [Testing Guide](docs/TESTING.md) - Running and writing tests
- [Claude Code Setup](docs/CLAUDE_CODE_SETUP.md) - Integration guide
- [V3 Extreme Details](docs/README_V3_EXTREME.md) - Advanced optimizations

---

## 🤝 Credits

- **Production Converters**: Based on [claude-adapter-py](https://github.com/XuYan-Breeze/claude-adapter-py)
- **Backend**: Powered by [vLLM](https://github.com/vllm-project/vllm)
- **Model**: NVIDIA Nemotron-3 Super 120B

---

## 📝 License

MIT License
