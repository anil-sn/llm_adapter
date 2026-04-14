# Claude Code Guide - Nemo-Orchestrator

## Project Overview
Nemo-Orchestrator is a high-performance inference cluster for large language models (specifically Nemotron-3 120B), optimized for multi-GPU workstations. It uses a custom gateway with an adapter-based architecture to support both OpenAI and Anthropic protocols, featuring a "Pulse Scheduler" for high-throughput batching and "TokenGuard" for context safety.

## Key Directories
- `nemo_orchestrator/`: Core application directory.
- `nemo_orchestrator/adapters/`: Provider-specific normalization (Claude, Nemotron, OpenAI).
- `nemo_orchestrator/config.yaml`: Central system configuration.
- `nemo_orchestrator/nemo_gateway.py`: The main traffic-shaping router.
- `nemo_orchestrator/scheduler.py`: The temporal coalescing engine (Pulse Scheduler).

## Common Commands

### System Lifecycle
- `./llm_manager.py start`: Launch the vLLM replicas and the Gateway.
- `./llm_manager.py stop`: Gracefully terminate the cluster.
- `./llm_manager.py status`: Check the health and process status.
- `./llm_manager.py restart`: Full system reset.

### Testing & Validation
- `./test_endpoints.py`: Run the V7.0 Multi-Protocol validation suite (9 tests).
- `curl -s http://localhost:8888/v1/models`: Check active model IDs.

### Development Environment
- `uv sync`: Synchronize dependencies using `uv`.
- `uv run <script>`: Run a script within the project's environment.

## Coding Standards
- **Protocol Neutrality**: New model logic should be added as an adapter in `adapters/` and registered in `config.yaml` under `model_rules`.
- **Async First**: All gateway and scheduler logic must be asynchronous (`async/await`) to maintain high concurrency.
- **Safety**: Ensure all requests pass through `adapter.build_request()` to trigger the `TokenGuard` clamping.
- **Logging**: Use the standard Python `logging` module with the format defined in `nemo_gateway.py`.

## Model Aliases
The system maps multiple identities to the underlying Nemotron-3 120B model:
- `claude-haiku-4-5-20251001` (Triggers ClaudeAdapter)
- `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8` (Triggers NemotronAdapter)

## Context Configuration
- Maximum Context: 32,768 tokens (Clamped by TokenGuard).
- KV Cache: FP8/FP4 Quantized.
- Batching: Pulse-Scheduled (Window: 5ms-30ms).
