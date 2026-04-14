# Nemo Orchestrator Architecture

## Overview

Nemo Orchestrator is a high-performance inference cluster designed for Nemotron-3 Super 120B model, featuring multi-protocol support and production-ready Claude Code integration.

## Components

###  1. Gateway (`src/nemo_orchestrator/gateway/`)

The main traffic-shaping router that:
- Routes requests to appropriate adapters based on model ID
- Handles protocol conversion
- Manages response normalization
- Provides health checking and monitoring

### 2. Adapters (`src/nemo_orchestrator/adapters/`)

Protocol-specific normalization layers:

#### **ClaudeAdapterV2** (Production)
- Based on battle-tested [claude-adapter-py](https://github.com/XuYan-Breeze/claude-adapter-py)
- Handles Anthropic Messages API ↔ OpenAI Chat Completions conversion
- Features:
  - Production-ready streaming with real-time block closing
  - Robust tool call handling
  - Proper error recovery
  - Claude Code CLI compatible

#### **NemotronAdapter**
- NVIDIA Nemotron-specific optimizations
- Handles reasoning tokens
- Extended thinking support

#### **OpenAIAdapter**
- Direct OpenAI Chat Completions API support
- Minimal overhead pass-through

### 3. Pulse Scheduler (`src/nemo_orchestrator/scheduler/`)

Temporal coalescing engine for request batching:
- Configurable batching window (5ms-30ms)
- Smart request grouping
- Throughput optimization

### 4. Claude Code Converters (`src/nemo_orchestrator/adapters/claude_code/`)

Production-ready converters extracted from claude-adapter-py:

- **`streaming.py`**: SSE event stream conversion with StreamState management
- **`response.py`**: Non-streaming response conversion
- **`tools.py`**: Tool definition conversion between protocols
- **`models/`**: Pydantic models for type safety

## Request Flow

```
Claude Code CLI
     │
     ▼
[Gateway] ← config.yaml (model routing rules)
     │
     ├─→ [ClaudeAdapterV2] ─→ OpenAI format
     ├─→ [NemotronAdapter] ─→ OpenAI format
     └─→ [OpenAIAdapter] ──→ OpenAI format
     │
     ▼
[Pulse Scheduler] (optional batching)
     │
     ▼
[vLLM Backend] (Nemotron-3 Super 120B)
     │
     ▼
[Response] ← Converted back to Anthropic format
     │
     ▼
Claude Code CLI
```

## Configuration

See `config/config.yaml` for:
- Model routing rules
- Adapter selection
- Context limits (TokenGuard)
- Batching parameters

## Testing

- **Unit Tests**: `tests/unit/` - Adapter logic, converters
- **Integration Tests**: `tests/integration/` - API compatibility
- **E2E Tests**: `tests/e2e/` - Full tool execution flow

## Key Features

### 1. TokenGuard
- Automatic context window clamping
- Prevents OOM errors
- Configurable per-model limits

### 2. Multi-Protocol Support
- Anthropic Messages API
- OpenAI Chat Completions
- NVIDIA Nemotron native

### 3. Production-Ready Streaming
- Real-time SSE event conversion
- Dynamic content block management
- Graceful error handling

### 4. Tool Calling
- Native tool call support
- Proper tool_use ↔ function call conversion
- Streaming tool argument assembly

## Performance

- **Max Context**: 32,768 tokens (configurable)
- **KV Cache**: FP8/FP4 Quantized
- **Batching Window**: 5ms-30ms (adaptive)
- **Protocol Overhead**: <1ms (adapter conversion)
