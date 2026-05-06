# LLM Adapter — Professional-Grade Project Structure

## Overview

High-performance LLM inference orchestrator with multi-protocol support (Anthropic,
OpenAI, Nemotron, Qwen), intelligent batching, layered configuration, and Claude Code
integration. Built on vLLM serving with 4x RTX 6000 Ada GPUs (196GB VRAM each).

---

## Current State

The project already has a solid foundation:
- Multi-protocol adapters (Claude, Nemotron, Qwen, OpenAI)
- Pulse Scheduler for request batching
- TokenGuard for context window management
- Layered YAML configuration system
- Model aliases for flexible routing
- Claude Code compatibility with tool calling

This document proposes a reorganization to elevate it to professional-grade standards.

---

## Proposed Directory Layout

```
llm_adapter/
│
├── pyproject.toml              # Project metadata, deps, build config (hatchling)
├── poetry.lock                 # Locked dependencies
├── Makefile                    # Common commands (test, lint, build, deploy)
├── docker-compose.yml          # Local dev environment (vLLM + gateway + monitoring)
├── Dockerfile                  # Production container (multi-stage GPU build)
├── .env.example                # Template for environment variables
├── .gitignore
├── .pre-commit-config.yaml     # Linting/formatting hooks (ruff, mypy)
├── README.md                   # Project overview, quick start
│
├── docs/                       # Documentation
│   ├── architecture/           # Architecture diagrams and decisions
│   │   ├── overview.md         # High-level system overview
│   │   ├── adapter-design.md   # Protocol adapter architecture
│   │   ├── scheduler.md        # Pulse Scheduler design
│   │   └── adr/                # Architecture Decision Records
│   │       └── 001-<decision>.md
│   ├── api/                    # API documentation
│   │   ├── anthropic-api.md    # Anthropic Messages API spec
│   │   ├── openai-api.md       # OpenAI Chat Completions spec
│   │   └── openapi.yaml        # Combined OpenAPI spec
│   ├── guides/                 # User/developer guides
│   │   ├── quickstart.md
│   │   ├── deployment.md
│   │   ├── model-switching.md
│   │   ├── driver-upgrade.md
│   │   └── troubleshooting.md
│   └── diagrams/               # Visual diagrams (ASCII/SVG)
│       └── system-architecture.md
│
├── src/                        # Source code
│   └── llm_adapter/
│       ├── __init__.py
│       ├── main.py             # Entry point (FastAPI/ASGI app)
│       │
│       ├── adapters/           # Protocol adapters
│       │   ├── __init__.py
│       │   ├── base.py         # Base adapter interface
│       │   ├── factory.py      # Adapter factory pattern
│       │   ├── claude/         # Anthropic Claude adapter
│       │   │   ├── __init__.py
│       │   │   ├── adapter.py  # Main Claude adapter
│       │   │   ├── streaming.py # SSE streaming implementation
│       │   │   ├── tools.py    # Tool calling support
│       │   │   └── models/     # Request/response models
│       │   │       ├── anthropic.py
│       │   │       └── openai.py
│       │   ├── openai/         # OpenAI adapter
│       │   │   ├── __init__.py
│       │   │   └── adapter.py
│       │   ├── nemotron/       # NVIDIA Nemotron adapter
│       │   │   ├── __init__.py
│       │   │   └── adapter.py
│       │   └── qwen/           # Qwen adapter (thinking/reasoning mode)
│       │       ├── __init__.py
│       │       └── adapter.py
│       │
│       ├── gateway/            # Traffic router & API server
│       │   ├── __init__.py
│       │   ├── server.py       # FastAPI server setup
│       │   ├── router.py       # Request routing logic
│       │   ├── middleware.py   # Auth, rate limiting, CORS
│       │   └── health.py       # Health check endpoints
│       │
│       ├── scheduler/          # Request batching & scheduling
│       │   ├── __init__.py
│       │   ├── pulse.py        # Pulse Scheduler (5ms-30ms windows)
│       │   ├── queue.py        # Request queue management
│       │   └── priority.py     # Priority-based scheduling
│       │
│       ├── context/            # Context window management
│       │   ├── __init__.py
│       │   ├── token_guard.py  # TokenGuard (OOM prevention)
│       │   ├── truncation.py   # Context truncation strategies
│       │   └── window.py       # Dynamic window sizing
│       │
│       ├── config/             # Configuration management
│       │   ├── __init__.py
│       │   ├── loader.py       # Layered YAML config loader
│       │   ├── schema.py       # Pydantic config schema
│       │   └── aliases.py      # Model aliases system
│       │
│       ├── vllm/               # vLLM integration layer
│       │   ├── __init__.py
│       │   ├── client.py       # vLLM HTTP client
│       │   ├── cluster.py      # Multi-GPU cluster management
│       │   └── lifecycle.py    # Model loading/unloading
│       │
│       └── utils/              # Shared utilities
│           ├── __init__.py
│           ├── logging.py      # Structured logging
│           ├── metrics.py      # Performance metrics
│           ├── reasoning.py    # Reasoning/thinking parser
│           └── validation.py   # Input validation
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures
│   ├── unit/                   # Unit tests
│   │   ├── adapters/
│   │   │   ├── test_claude.py
│   │   │   ├── test_openai.py
│   │   │   ├── test_nemotron.py
│   │   │   └── test_qwen.py
│   │   ├── test_scheduler.py
│   │   ├── test_context.py
│   │   ├── test_config.py
│   │   └── test_aliases.py
│   ├── integration/            # Integration tests
│   │   ├── test_api.py         # API endpoint tests
│   │   ├── test_streaming.py   # SSE streaming tests
│   │   ├── test_tool_calling.py # Claude Code tool calling
│   │   └── test_routing.py     # Request routing tests
│   └── e2e/                    # End-to-end tests
│       ├── test_claude_flow.py # Full Claude API flow
│       └── test_model_switch.py # Model switching flow
│
├── examples/                   # Usage examples
│   ├── basic_chat.py           # Simple chat completion
│   ├── tool_calling.py         # Claude Code tool calling
│   ├── streaming.py            # SSE streaming example
│   └── model_comparison.py     # Compare models side by side
│
├── scripts/                    # Operational scripts
│   ├── deploy.sh               # Deployment script
│   ├── switch_model.sh         # Model switching
│   ├── benchmark.py            # Performance benchmarks
│   ├── monitoring/             # Monitoring scripts
│   │   ├── gpu_stats.sh
│   │   └── request_stats.py
│   └── maintenance/            # Maintenance scripts
│       ├── cleanup.sh
│       └── driver_upgrade.sh
│
├── config/                     # Configuration files
│   ├── default.yaml            # Base configuration
│   ├── development.yaml        # Dev overrides
│   ├── production.yaml         # Production overrides
│   ├── models/                 # Model-specific configs
│   │   ├── nemotron.yaml
│   │   ├── qwen.yaml
│   │   └── qwen36-27b.yaml
│   └── adapters/               # Adapter-specific configs
│       ├── claude.yaml
│       └── openai.yaml
│
└── .github/                    # CI/CD
    └── workflows/
        ├── ci.yml              # Tests, linting, type checking
        ├── release.yml         # Release automation
        └── deploy.yml          # Deployment pipeline
```

---

## Key Professional-Grade Practices

### 1. Adapter Architecture

Each protocol adapter follows a consistent pattern:

```
adapters/<protocol>/
├── __init__.py         # Public API exports
├── adapter.py          # Main adapter implementation
├── streaming.py        # Protocol-specific streaming
├── tools.py            # Tool calling (if applicable)
└── models/             # Request/response models
    └── <protocol>.py
```

Benefits:
- Clear separation of concerns per protocol
- Easy to add new adapters
- Self-contained adapter modules
- Consistent interface via base adapter

### 2. Configuration Management

Layered YAML configuration with inheritance:

```
config/
├── default.yaml          # Base defaults (all settings)
├── development.yaml      # Dev overrides (debug, local GPUs)
├── production.yaml       # Prod overrides (optimized settings)
├── models/               # Per-model tuning
│   └── nemotron.yaml
└── adapters/             # Per-adapter settings
    └── claude.yaml
```

Loading order: default -> environment -> model -> adapter -> CLI flags

### 3. Testing Strategy

| Layer         | Scope                        | Mock LLM? |
|---------------|------------------------------|-----------|
| Unit          | Individual modules           | Yes       |
| Integration   | API + adapter + scheduler    | Yes       |
| E2E           | Full request flow            | No*       |

\* E2E tests use actual vLLM but with small models for speed.

Coverage targets:
- Unit tests: 90%+ coverage
- Integration tests: All API endpoints
- E2E tests: Critical paths (chat, streaming, tool calling)

### 4. CI/CD Pipeline

```
Push/PR -> Lint (ruff) -> Type Check (mypy) -> Unit Tests -> Integration Tests
                                                                    |
                                                                    v
                                                           Tag Release -> E2E Tests -> Publish
```

- ruff for linting and formatting
- mypy for type checking
- pytest with coverage reporting
- bandit for security scanning
- Automated semantic versioning on tags

### 5. Observability

- Structured JSON logging with request IDs
- Metrics: latency, throughput, GPU utilization, token counts
- Tracing: request flow through adapter -> scheduler -> vLLM
- Health checks: GPU status, model loaded, queue depth
- Error tracking: failed requests, OOM events, timeouts

### 6. Performance Targets

| Metric                  | Target        |
|-------------------------|---------------|
| Request routing         | <5ms p99      |
| Adapter transformation  | <10ms p99     |
| Pulse batch window      | 5-30ms config |
| Token generation        | Model-dependent|
| Context window          | 32K-256K (YaRN)|
| GPU memory efficiency   | >85% utilization|
| Concurrent requests     | 100+ queued   |

### 7. Deployment

- Multi-stage Docker build (GPU-optimized)
- NVIDIA Container Toolkit integration
- Health probes (liveness/readiness)
- Resource limits (GPU, memory, CPU)
- Horizontal scaling via multiple gateway instances
- Model hot-swapping without downtime

---

## Architecture Flow

```
Client Request (Anthropic/OpenAI/etc.)
  │
  ▼
┌──────────────┐
│   Gateway     │  FastAPI server, routing, middleware
│   (API)       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Adapter      │  Protocol transformation
│  (Factory)    │  Claude <-> OpenAI <-> Nemotron <-> Qwen
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  TokenGuard   │  Context window management, OOM prevention
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Pulse        │  Request batching, priority scheduling
│  Scheduler    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  vLLM Cluster │  Multi-GPU inference (4x RTX 6000 Ada)
│  (Inference)  │  FP8/FP4 KV Cache, YaRN context expansion
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Adapter      │  Response transformation back to client protocol
│  (Reverse)    │  SSE streaming, tool calling format
└──────┬───────┘
       │
       ▼
Client Response (streaming or batch)
```

---

## Migration Plan

### Phase 1: Structure (Low Risk)
1. Create new directory structure
2. Move existing files to new locations
3. Update imports
4. Verify all tests pass

### Phase 2: Adapter Refinement
1. Split claude_code/ into adapters/claude/ submodules
2. Extract streaming logic into dedicated modules
3. Add adapter-specific model classes

### Phase 3: Gateway Enhancement
1. Add middleware (auth, rate limiting, CORS)
2. Add health check endpoints
3. Add structured logging with request tracing

### Phase 4: Testing Expansion
1. Add unit tests for all modules
2. Add integration tests for API endpoints
3. Add E2E tests for critical flows
4. Set up CI pipeline

### Phase 5: Documentation
1. API documentation with OpenAPI spec
2. Architecture diagrams
3. Deployment guides
4. Troubleshooting guides

---

## Getting Started

```bash
# Clone and setup
git clone <repo>
cd llm_adapter
make setup

# Run tests
make test          # Unit tests
make test-int     # Integration tests
make test-e2e     # End-to-end tests

# Run locally
make dev          # Start gateway + vLLM locally

# Build and deploy
make build        # Build Docker image
make deploy       # Deploy to cluster

# Switch models
./scripts/switch_model.sh nemotron-3-super
./scripts/switch_model.sh qwen36-27b
```
