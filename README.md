# Nemo Orchestrator

**High-Performance LLM Inference Cluster for Nemotron-3 Super 120B**

A production-ready inference orchestrator featuring multi-protocol support, intelligent batching, layered configuration system, and seamless Claude Code integration.

**Author**: Anil Srirangapatna Nagesh
**Version**: 2.0.0
**License**: MIT

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-beta-yellow.svg)

---

## 🚀 Features

### Core Capabilities
- **Multi-Protocol Support**: Anthropic Messages API, OpenAI Chat Completions, NVIDIA Nemotron, Qwen
- **Production-Ready Streaming**: Battle-tested converters from [claude-adapter-py](https://github.com/XuYan-Breeze/claude-adapter-py)
- **Pulse Scheduler**: Smart request batching with configurable windows (5ms-30ms)
- **TokenGuard**: Automatic context window management to prevent OOM errors
- **Claude Code Compatible**: Full tool calling support with proper SSE streaming
- **FP8/FP4 KV Cache**: Optimized for Nemotron-3 Super 120B (32K context, capable of 256K)

### Advanced Features
- **QwenAdapter**: Native support for Qwen models with thinking/reasoning mode
- **Model Aliases System**: Flexible model routing (e.g., `claude-haiku-4-5-20251001` → `nemotron-3-super`)
- **Layered Configuration**: 3-tier YAML inheritance (base → adapter → model-specific)
- **Environment-Based Switching**: Change models via `LLM_CONFIG` environment variable
- **Comprehensive Cleanup**: Automated project maintenance (`scripts/cleanup_project.py`)
- **NVIDIA Driver Management**: Installation, upgrade, and verification scripts
- **API Compliance Validation**: Automated protocol compliance testing

---

## 💻 System Requirements

| Component | Requirement | Notes |
|-----------|-------------|-------|
| **Python** | 3.12+ | Required for type hints and modern syntax |
| **GPU** | 4x RTX 6000 Ada (196GB VRAM) | Or equivalent high-memory GPUs |
| **NVIDIA Driver** | 535.230.02+ (current)<br>550+ (recommended) | Driver 550+ unlocks ~40-50% performance gain |
| **CUDA** | 12.1+ (12.2+ installed) | CUDA 12.4+ required for vLLM 0.20+ |
| **Disk Space** | ~250GB | Model weights (~120GB) + cache + logs |
| **CPU** | Multi-core with PCIe topology | Non-NVLink GPU configuration |
| **RAM** | 32GB+ system memory | For model loading and overhead |

### Driver Version Impact

⚠️ **Performance Note**: Current driver 535.230.02 works but runs ~40-50% slower than driver 550+. The driver upgrade is pending and will enable:
- vLLM 0.20+ with Triton attention backend
- Context expansion to 256K tokens (via YaRN)
- Chunked prefill for long contexts
- Auto tool choice for enhanced API compatibility

See `ADMIN_DRIVER_UPGRADE_REQUEST.md` for upgrade details.

---

## 📁 Project Structure

```
nemo_orchestrator/
├── src/nemo_orchestrator/      # Main source code
│   ├── adapters/                # Protocol adapters (4 adapters)
│   │   ├── claude_adapter_v2.py      # Production Claude adapter
│   │   ├── nemotron_adapter.py       # Nemotron optimizations
│   │   ├── qwen_adapter.py           # Qwen with thinking mode
│   │   ├── openai_adapter.py         # OpenAI pass-through
│   │   ├── factory.py                # Adapter factory pattern
│   │   └── claude_code/              # Production converters
│   ├── gateway/                 # Traffic router
│   ├── scheduler/               # Request batching (Pulse Scheduler)
│   └── utils/                   # Utilities (TokenGuard, etc.)
├── tests/                       # Test suite
│   ├── test_config_system.py    # Configuration system tests
│   └── test_qwen_adapter.py     # Qwen adapter tests
├── scripts/                     # Management scripts
│   ├── setup/                   # Setup & deployment
│   │   ├── llm_manager.py            # Process orchestration
│   │   ├── install_nvidia_driver.sh  # Driver installation
│   │   ├── upgrade_nvidia_driver.sh  # Driver upgrade
│   │   └── test_*.sh                 # Verification scripts
│   ├── testing/                 # Test scripts
│   └── cleanup_project.py       # Automated maintenance
├── config/                      # Configuration files (3-tier system)
│   ├── config.yaml              # Base cluster config
│   ├── config-adapter.yaml      # Adapter routing rules
│   ├── config-nemotron.yaml     # Model-specific overrides
│   └── config-qwen.yaml         # Qwen-specific settings
├── docs/                        # Documentation (10+ files)
└── archive/                     # Deprecated code
```

---

## 🛠️ Installation

### Prerequisites Check

Before installation, verify your system meets the requirements:

```bash
# Check Python version
python --version  # Should be 3.12+

# Check NVIDIA driver
nvidia-smi  # Should show driver 535.230.02+ (550+ recommended)

# Check CUDA version
nvcc --version  # Should be 12.1+

# Run comprehensive prerequisite test
bash scripts/setup/test_nvidia_prerequisites.sh
```

### Python Environment Setup

```bash
# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -e .

# Verify installation
python -c "import nemo_orchestrator; print('✓ Installation successful')"
```

### Model Download

```bash
# Download Nemotron-3 Super 120B model weights (~120GB)
# This requires Hugging Face authentication
python scripts/setup/hf_downloader.py
```

### NVIDIA Driver Verification

```bash
# Test CUDA installation
bash scripts/setup/test_cuda_install.sh

# If driver upgrade is needed (for 550+)
# See ADMIN_DRIVER_UPGRADE_REQUEST.md for instructions
```

---

## 🚦 Quick Start

### 1. Verify Prerequisites

```bash
# Run verification script
bash scripts/setup/test_nvidia_prerequisites.sh
# Should show: ✓ All checks passed
```

### 2. Start the Cluster

```bash
# Start vLLM + Gateway (default: Nemotron model)
python scripts/setup/llm_manager.py start

# Check status
python scripts/setup/llm_manager.py status

# Switch to Qwen model (optional)
LLM_CONFIG=config-qwen.yaml python scripts/setup/llm_manager.py start
```

### 3. Configure Claude Code CLI

```bash
# Run setup script
bash scripts/setup/setup_claude_code_cli.sh

# Validate installation
bash scripts/setup/validate_claude_code_cli.sh

# Test
claude "list files in current directory"
```

### 4. Run Tests

```bash
# Configuration system tests
python tests/test_config_system.py

# Qwen adapter tests
python tests/test_qwen_adapter.py

# Context/KV cache validation
python scripts/testing/test_context_kv_cache.py

# Tool calling verification
bash scripts/testing/check_tool_calling.sh

# Run all tests
bash scripts/run_tests.sh
```

### 4. Project Maintenance

```bash
# Run cleanup script (dry run - shows what would be deleted)
python scripts/cleanup_project.py --dry-run

# Actual cleanup (removes cache files, logs, PID files, etc.)
python scripts/cleanup_project.py

# Clean specific project
python scripts/cleanup_project.py --project /path/to/project
```

---

## 🧹 Project Maintenance

### Cleanup Script

The project includes a comprehensive cleanup script (`scripts/cleanup_project.py`) that:

- Removes `__pycache__` directories
- Deletes PID and lock files (`.pid`, `.lock`, `.sock`)
- Clears log files from `logs/` directory
- Removes build artifacts (`.pyc`, `.pyo`, `.egg-info`, etc.)
- Cleans temporary files (`.tmp`, `.temp`, `.bak`, etc.)
- Removes stale markdown files (keeps essential ones)
- Updates `.gitignore` with comprehensive patterns

**Usage:**
```bash
# Preview what would be cleaned
python scripts/cleanup_project.py --dry-run

# Perform actual cleanup
python scripts/cleanup_project.py
```

**Space Saved:** Typically 100+ MB of cache files, logs, and artifacts.

---

## 🔧 Configuration

### Layered Configuration System

Nemo Orchestrator uses a **3-tier YAML inheritance system** for flexible configuration:

#### 1. Base Configuration (`config/config.yaml`)
**Purpose**: Hardware and cluster settings shared across all models

```yaml
cluster:
  gateway_port: 8888
  routing_strategy: "prefix_hash"

hardware:
  tensor_parallel_size: 4      # MUST match GPU count
  device: "cuda"
  dtype: "auto"
  attention_backend: "TRITON_ATTN"
  disable_custom_all_reduce: true  # PCIe topology

replicas:
  count: 1
  base_port: 8000
  gpu_groups: ["0,1,2,3"]      # 4x RTX 6000 Ada
```

#### 2. Adapter Configuration (`config/config-adapter.yaml`)
**Purpose**: Model routing rules and adapter selection

```yaml
model_rules:
  - pattern: "^claude-.*"
    adapter: "claude_v2"
    vllm_model: "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8"

  - pattern: "^qwen.*"
    adapter: "qwen"
    vllm_model: "Qwen/Qwen2.5-72B-Instruct-AWQ"
```

#### 3. Model-Specific Configuration (`config-nemotron.yaml`, `config-qwen.yaml`)
**Purpose**: Model-specific overrides (context limits, KV cache, thinking mode)

```yaml
# config-nemotron.yaml
inference:
  max_model_len: 32768         # Context window
  kv_cache_dtype: "fp8"        # FP8 quantization
  enable_thinking: false       # No reasoning tokens

# config-qwen.yaml
inference:
  max_model_len: 131072        # Larger context
  kv_cache_dtype: "auto"
  enable_thinking: true        # Enable thinking mode
```

### Switching Models

```bash
# Default (Nemotron)
python scripts/setup/llm_manager.py start

# Use Qwen
LLM_CONFIG=config-qwen.yaml python scripts/setup/llm_manager.py start
```

### TokenGuard Context Management

TokenGuard automatically clamps requests to prevent OOM errors:

- **Reads** `max_model_len` from config
- **Enforces** context limits before sending to vLLM
- **Prevents** GPU memory exhaustion
- **Logs** when clamping occurs

### Model Alias Resolution

The system resolves model IDs using regex patterns:

1. **Request arrives** with model ID (e.g., `claude-haiku-4-5-20251001`)
2. **Pattern matching** against `model_rules` in config
3. **Adapter selection** based on matched pattern
4. **Model alias resolution** to actual vLLM model path

---

## 🏗️ Architecture

### Request Flow Pipeline

```
┌─────────────────┐
│ Claude Code CLI │
│  OR  OpenAI API │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Gateway (nemo_gateway.py)          │
│  • Protocol detection               │
│  • Model ID parsing                 │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Adapter Factory                    │
│  • Regex pattern matching           │
│  • Adapter selection                │
└────────┬────────────────────────────┘
         │
    ┌────┴────┬──────────┬────────┐
    ▼         ▼          ▼        ▼
┌─────────┐ ┌────────┐ ┌──────┐ ┌──────┐
│ Claude  │ │Nemotron│ │ Qwen │ │OpenAI│
│Adapter  │ │Adapter │ │Adapter│ │Adapter│
└────┬────┘ └───┬────┘ └──┬───┘ └──┬───┘
     │          │          │        │
     └──────────┴──────────┴────────┘
                 │
                 ▼
         ┌───────────────┐
         │  TokenGuard   │
         │  • Clamp ctx  │
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │Pulse Scheduler│
         │ • 5-30ms batch│
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │  vLLM Backend │
         │ • GPU Inference│
         └───────┬───────┘
                 │
                 ▼
         ┌───────────────┐
         │Response Stream│
         │ • SSE/JSON    │
         └───────────────┘
```

### Component Details

**Gateway**: Traffic-shaping router
- Handles both Anthropic and OpenAI protocols
- Routes based on model ID patterns
- Manages adapter lifecycle

**Adapters**: Protocol normalization layers
- `ClaudeAdapterV2`: Anthropic ↔ OpenAI conversion (production-ready)
- `NemotronAdapter`: NVIDIA-specific optimizations
- `QwenAdapter`: Qwen models with thinking mode support
- `OpenAIAdapter`: Direct pass-through for OpenAI clients

**TokenGuard**: Context window safety
- Reads `max_model_len` from config
- Automatically truncates oversized requests
- Prevents GPU OOM errors

**Pulse Scheduler**: Temporal coalescing
- Groups requests within 5-30ms windows
- Maximizes GPU utilization
- Reduces per-request latency

**vLLM Backend**: GPU inference engine
- Handles actual model execution
- Manages KV cache
- Supports FP8/FP4 quantization

---

## 🚀 Deployment

### Process Orchestration

Nemo Orchestrator uses **process-based deployment** via `llm_manager.py` (no Docker or systemd required):

```bash
# Start cluster
python scripts/setup/llm_manager.py start
# ├── Launches vLLM process (binds to GPUs 0-3)
# ├── Launches Gateway process (port 8888)
# ├── Writes PID files to /tmp/
# └── Returns immediately

# Check status
python scripts/setup/llm_manager.py status
# Shows: PID, ports, GPU assignments, uptime

# Restart gateway only (hot-reload)
python scripts/setup/llm_manager.py restart-gateway

# Stop everything
python scripts/setup/llm_manager.py stop
# ├── Graceful SIGTERM to all processes
# ├── Wait for shutdown (max 10s)
# └── Remove PID files
```

### Process Management Features

- **PID Tracking**: Stores PIDs in `/tmp/vllm_*.pid` and `/tmp/gateway.pid`
- **CPU Affinity**: Binds processes to specific CPU cores (from `core_ranges` config)
- **GPU Assignment**: Distributes workload across GPU groups
- **Graceful Shutdown**: SIGTERM → wait → SIGKILL fallback
- **Hot Reload**: Restart gateway without touching vLLM backend

### Deployment Architecture

```
┌──────────────────────────────────────┐
│         llm_manager.py               │
│  ┌────────────┐    ┌──────────────┐  │
│  │ vLLM Proc  │    │ Gateway Proc │  │
│  │ PID: 12345 │    │ PID: 12346   │  │
│  │ Port: 8000 │    │ Port: 8888   │  │
│  │ GPUs: 0-3  │    │ CPUs: 0-55   │  │
│  └────────────┘    └──────────────┘  │
└──────────────────────────────────────┘
```

---

## 🛠️ Scripts & Tools

### Deployment Scripts

| Script | Purpose |
|--------|---------|
| `llm_manager.py` | Start/stop/status/restart cluster |
| `setup_claude_code_cli.sh` | Configure Claude Code integration |
| `validate_claude_code_cli.sh` | Verify Claude Code setup |

### NVIDIA Management Scripts

| Script | Purpose |
|--------|---------|
| `install_nvidia_driver.sh` | Install NVIDIA driver from .run file |
| `install_nvidia_from_source.sh` | Build driver from source |
| `upgrade_nvidia_driver.sh` | Upgrade to driver 550+ |
| `test_nvidia_prerequisites.sh` | Comprehensive system check |
| `test_cuda_install.sh` | Verify CUDA installation |

### Testing Scripts

| Script | Purpose | Location |
|--------|---------|----------|
| `test_config_system.py` | Configuration system validation | `tests/` |
| `test_qwen_adapter.py` | Qwen adapter unit tests | `tests/` |
| `test_context_kv_cache.py` | Context limits and KV cache validation | `scripts/testing/` |
| `benchmark.py` | Performance benchmarking | `scripts/testing/` |
| `check_tool_calling.sh` | Verify tool calling functionality | `scripts/testing/` |
| `run_tests.sh` | Run all tests | `scripts/` |

### Maintenance Scripts

| Script | Purpose |
|--------|---------|
| `cleanup_project.py` | Remove cache, logs, build artifacts |

**Usage:**
```bash
# Cleanup with dry-run
python scripts/cleanup_project.py --dry-run

# Actual cleanup (saves ~100MB)
python scripts/cleanup_project.py
```

---

## 📊 Performance

### Current Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Context Window** | 32,768 tokens (stable) | Capable of 256K with driver 550+ |
| **KV Cache** | FP8/FP4 Quantized | Reduces memory by ~75% |
| **Batching Window** | 5-30ms (adaptive) | Pulse Scheduler optimization |
| **Protocol Overhead** | <1ms | Gateway + adapter processing |
| **GPU Utilization** | ~85-90% | With proper batching |
| **Throughput** | ~40-50 tokens/sec/user | Depends on batch size |

### Hardware Configuration

| Component | Specification |
|-----------|--------------|
| **GPUs** | 4x NVIDIA RTX 6000 Ada (49GB each) |
| **Total VRAM** | 196GB |
| **Topology** | PCIe (non-NVLink) |
| **Tensor Parallelism** | 4-way split |
| **Driver** | 535.230.02 (CUDA 12.2) |

### Context Window Evolution

The project has explored various context configurations:

- **v1.0**: 32K tokens (baseline)
- **v2.0**: Expanded to 48K
- **v2.5**: Reached 64K
- **v3.0**: Tested 256K (YaRN scaling)
- **v2.0.0** (current): **Stable at 32K** (optimal for current driver)

**Rationale for 32K**: Maximum reliability with driver 535. After driver upgrade to 550+, we can safely expand to 256K with YaRN.

---

## ⚠️ Known Issues & Limitations

### 1. Driver Upgrade Pending

**Current State**: Driver 535.230.02 (CUDA 12.2)
**Recommended**: Driver 550+ (CUDA 12.4+)

**Impact:**
- ❌ ~40-50% slower inference compared to driver 550+
- ❌ Cannot use vLLM 0.20+ (latest optimizations)
- ❌ Cannot use PyTorch 2.11+ features
- ❌ Missing Triton attention backend (30-40% faster)
- ❌ Context limited to 32K instead of 256K
- ❌ No chunked prefill for long contexts
- ❌ No auto tool choice feature

**Timeline**: Driver upgrade requested (see `ADMIN_DRIVER_UPGRADE_REQUEST.md`)

### 2. Context Window Limitation

**Current**: 32,768 tokens (stable and reliable)
**Capable**: 256K tokens with YaRN scaling (requires driver 550+)

**Why Limited**: Driver 535 doesn't support the CUDA features needed for YaRN RoPE scaling and extended context windows.

### 3. Hardware-Specific Optimizations

**Optimized for**: 4x RTX 6000 Ada, PCIe topology (non-NVLink)

The configuration is tuned for this specific hardware:
- `disable_custom_all_reduce: true` (PCIe topology)
- `tensor_parallel_size: 4` (matches GPU count)
- Custom NCCL settings for PCIe communication

**If using different hardware**: Adjust `config/config.yaml` accordingly.

### 4. Model Weight Storage

**Requirement**: ~250GB disk space
- Nemotron-3 Super 120B: ~120GB (FP8 quantized)
- Qwen2.5-72B: ~50GB (AWQ quantized)
- Cache and logs: ~80GB

**Storage**: Models cached in `~/.cache/huggingface/hub/`

---

## 📚 Documentation

### Core Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, components, and request flow |
| [TESTING.md](docs/TESTING.md) | Running and writing tests |
| [CLAUDE_CODE_SETUP.md](docs/CLAUDE_CODE_SETUP.md) | Claude Code integration guide |
| [README_V3_EXTREME.md](docs/README_V3_EXTREME.md) | Advanced optimizations and tuning |

### Specialized Documentation

| Document | Description |
|----------|-------------|
| [API_COMPLIANCE_REVIEW.md](docs/API_COMPLIANCE_REVIEW.md) | Protocol compliance validation report |
| [MEMORY_TROUBLESHOOTING.md](docs/MEMORY_TROUBLESHOOTING.md) | GPU memory management and OOM fixes |
| [CLAUDE_CODE_COMPATIBILITY_FIXES.md](docs/CLAUDE_CODE_COMPATIBILITY_FIXES.md) | Integration fixes and workarounds |
| [README_TESTING.md](docs/README_TESTING.md) | Comprehensive test suite documentation |
| [REORGANIZATION.md](docs/REORGANIZATION.md) | Project structure evolution |
| [CLAUDE.md](docs/CLAUDE.md) | Claude Code agent guide for this project |

### Admin Documentation

| Document | Description |
|----------|-------------|
| [ADMIN_DRIVER_UPGRADE_REQUEST.md](ADMIN_DRIVER_UPGRADE_REQUEST.md) | NVIDIA driver upgrade instructions |
| [DRIVER_UPGRADE_TICKET.txt](DRIVER_UPGRADE_TICKET.txt) | Driver upgrade tracking |

---

## 🎉 Recent Improvements

### April 2026 - Professional Cleanup & Documentation Overhaul

**Commit**: `cbf8058` - Professional cleanup and documentation overhaul

**Achievements:**
- ✅ **106MB saved** via comprehensive cleanup
- ✅ **+5,762 insertions** of documentation and improvements
- ✅ Comprehensive `.gitignore` with 100+ patterns
- ✅ Professional `.editorconfig` for consistent formatting
- ✅ Automated cleanup script (`cleanup_project.py`)

### April 2026 - Context Window Stabilization

**Evolution**: 32K → 48K → 64K → 256K → **32K (stable)**

**Rationale:**
- Context expansion requires driver 550+ for YaRN scaling
- 32K provides maximum reliability with current driver 535
- Will expand to 256K after driver upgrade

**Commits:**
- `3cd337e` - Maximize context: 48K → 64K + chunked prefill
- `0489e15` - Context expansion: 65K → 256K (native model default)
- `06c95bc` - Fix: Disable vLLM v1 async-scheduling (KV cache bug)
- `9258029` - Fix Context Length

### April 2026 - NVIDIA Driver Management

**New Scripts:**
- `install_nvidia_driver.sh` - Automated driver installation
- `install_nvidia_from_source.sh` - Build from source
- `upgrade_nvidia_driver.sh` - Upgrade to 550+
- `test_nvidia_prerequisites.sh` - Comprehensive verification
- `test_cuda_install.sh` - CUDA validation

**Documentation:**
- Complete driver upgrade request with admin instructions
- Performance impact analysis (~40-50% slower without 550+)
- Rollback procedures

### April 2026 - API Compliance Review

**New Documentation:**
- Comprehensive protocol compliance validation
- Anthropic Messages API SSE streaming verification
- OpenAI Chat Completions API compatibility check
- Tool calling protocol verification

**Result**: ✅ High compliance for both protocols

---

## 🤝 Contributing

Contributions are welcome! Please see our contributing guidelines:

### Code Standards

- **Python**: Follow PEP 8, use type hints (Python 3.12+)
- **Async**: All gateway/scheduler code must be async
- **Testing**: Add tests for new features
- **Documentation**: Update relevant docs

### Development Workflow

```bash
# 1. Fork and clone
git clone https://github.com/your-username/nemo_orchestrator.git

# 2. Create branch
git checkout -b feature/your-feature

# 3. Make changes and test
bash scripts/run_tests.sh

# 4. Run cleanup
python scripts/cleanup_project.py

# 5. Commit and push
git commit -m "feat: Add your feature"
git push origin feature/your-feature

# 6. Create pull request
```

### Adding New Adapters

1. Create adapter in `src/nemo_orchestrator/adapters/`
2. Inherit from `BaseAdapter`
3. Implement required methods
4. Add routing rule to `config/config-adapter.yaml`
5. Add tests in `tests/unit/`
6. Update documentation

### Reporting Issues

- Use GitHub Issues
- Include system info (`nvidia-smi`, Python version)
- Provide reproduction steps
- Attach relevant logs from `logs/`

---

## 🤝 Credits

- **Production Converters**: Based on [claude-adapter-py](https://github.com/XuYan-Breeze/claude-adapter-py)
- **Backend**: Powered by [vLLM](https://github.com/vllm-project/vllm)
- **Model**: NVIDIA Nemotron-3 Super 120B

---

## 📝 License

MIT License
