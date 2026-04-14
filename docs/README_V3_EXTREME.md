# 🔱 Nemo-Orchestrator v3.0 (Extreme)
### Coherent Inference Cluster for 4x RTX 6000 Ada (192GB VRAM)
**Status:** `10.5/10 Optimized` | **Architecture:** `Dual-Replica Speculative MoE` | **Context:** `180k–256k (TurboQuant)`

---

## 1. 🧩 System Architecture: Topology-Aware Design

Nemo-Orchestrator is a production-grade inference cluster designed to maximize the utility of workstation-class hardware. It specifically addresses the **"Interconnect Tax"** of PCIe-based multi-GPU systems where inter-device communication is constrained by a flat `SYS` (System-wide) topology.

### The Problem: The TP=4 Synchronous Bottleneck
In a standard `TP=4` configuration, every transformer layer requires global synchronization across the system bus. In a `SYS` topology, this "All-Reduce" operation incurs significant latency as it traverses multiple PCIe bridges and the CPU memory controller, leading to diminishing returns in per-token latency.

### The Solution: 2x TP=2 Functional Isolation
Nemo-Orchestrator pivots to a **Dual-Replica** strategy. By sharding the 120B model into two independent `TP=2` instances, the system achieves:
*   **Reduced Synchronization Domain:** Layer synchronization is localized to GPU pairs (0,1 and 2,3), cutting the broadcast participant count and overhead by 50%.
*   **Throughput Scaling:** Enables true parallel request handling. Instead of one heavy, latency-bound engine, the system operates as two high-speed engines.
*   **Aggregate Efficiency:** 2x TP=2 replicas on `SYS` hardware typically deliver **40-60% higher aggregate throughput** than a single TP=4 instance under load.

```text
                     [ CLIENT / API ]
                            |
                 ___________________________
                |       NEMO-GATEWAY        | (Port 8888)
                |  (Prefix-Hash Router)     |
                |___________________________|
                 /                         \
        [ REPLICA 0 ]                 [ REPLICA 1 ]
        (Port 8000)                   (Port 8001)
    ___________________           ___________________
   |  SMT Cores 0-27   |         |  SMT Cores 28-55  |
   |  (Threads 56-83)  |         |  (Threads 84-111) |
   |___________________|         |___________________|
    /                 \           /                 \
 [GPU 0]           [GPU 1]     [GPU 2]           [GPU 3]
 (48GB)            (48GB)      (48GB)            (48GB)
   \_________________/           \_________________/
      TP=2 Domain 0                 TP=2 Domain 1
   (Comm: Local PCIe)            (Comm: Local PCIe)
```

---

## 🚀 2. The 10.5/10 Optimization Stack

### 2.1 4-bit KV Cache Quantization (TurboQuant-style)
Nemo-Orchestrator employs advanced 4-bit KV quantization to compress the attention mechanism's memory footprint.
*   **Capacity Expansion:** Enables a functional **180k–256k token window** (workload-dependent) within a ~32–40GB effective VRAM budget per replica.
*   **Precision:** Token structure is preserved (no pruning), but numerical precision is reduced. This maintains compatibility with prefix caching while doubling memory density.
*   **Note:** KV quantization introduces minor numerical drift, which may modestly affect speculative acceptance rates in high-entropy tasks.

### 2.2 Speculative Decoding (Draft-Target Orchestration)
To amortize PCIe synchronization costs, each replica uses a hierarchical execution model:
*   **The Scout (Nemotron-8B):** A lightweight drafter that predicts token sequences at high speed.
*   **The Brain (Nemotron-120B):** The flagship target model that verifies guesses in parallel.
*   **Impact:** Delivers a **1.3x–1.8x throughput speedup** depending on prompt entropy and speculative acceptance rates.

### 2.3 Context Affinity (Nemo-Gateway)
The Gateway uses a **Prefix-Aware Sticky Routing** algorithm. It hashes the initial context root to ensure requests sharing the same history land on the same VRAM cache.
*   **Near-Zero Prefill:** For repeated or prefix-aligned requests (e.g., codebase RAG), prefill costs are effectively eliminated after the first pass.

---

## 📈 3. Performance Envelope & Limits

| Metric | Target Performance | Constraints |
| :--- | :--- | :--- |
| **Aggregate TPS** | 150 - 220 Tokens/Sec | Varies by prompt complexity and acceptance. |
| **Max Context** | 180k - 256k Tokens | High context reduces max batch size. |
| **Latency (p50)** | < 45ms per token | Optimized for reasoning, not micro-QPS. |
| **VRAM Safety** | 0.88 Utilization | High fragmentation risk > 0.90. |

### 🛑 Explicit Failure Modes
*   **KV Fragmentation:** At extreme context (>200k tokens), allocator overhead may trigger OOM or severe batching degradation.
*   **Speculative Drift:** High-entropy outputs may see lower speculative acceptance, reducing speedup to the lower bound (~1.3x).
*   **Cache Miss Amplification:** Frequent prefix changes (e.g., rapid context-switching) will cause redundant prefills, neutralizing the Gateway's efficiency.
*   **Throughput Collapse:** Extreme concurrency with long contexts (>4 per replica) will trigger spillover logic but may still lead to severe latency spikes.

### ⚖️ Technical Considerations
*   **Determinism:** Due to 4-bit KV quantization and speculative decoding, outputs may vary slightly between runs, especially at extreme context lengths.
*   **Scaling Note:** Performance scales sub-linearly with context length due to attention complexity and KV cache bandwidth constraints.
*   **Implementation Note:** Actual stability depends on backend support for **FlashInfer** kernels and 4-bit quantization maturity in the vLLM/SGLang runtime.

---

## 🛠 4. Operation & Management

### 4.1 Setup & Downloader
```bash
uv sync # Isolated Python 3.12 environment
# Ultra-fast parallel download (70GB+)
./hf_downloader.py --model nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-FP8
./hf_downloader.py --model nvidia/NVIDIA-Nemotron-3-Super-8B-FP8
```

### 4.2 Lifecycle Management
*   **`start`**: Spins up the 3-process cluster (Gateway + 2 Replicas) as background daemons.
*   **`status`**: Reports SMT-aware core pinning, GPU utilization, and cluster health.
*   **`stop`**: Gracefully terminates processes to prevent "Zombie" VRAM allocations.
*   **`benchmark`**: Validates aggregate TPS and latency under configurable load.

---

## ⚙️ 5. Configuration Strategy (`config.yaml`)

| Section | Parameter | Default | Rationale |
| :--- | :--- | :--- | :--- |
| **Replica** | `tensor_parallel_size` | `2` | Minimizes cross-root PCIe broadcast overhead. |
| **Replica** | `core_ranges` | `SMT-Aware` | Hard-pins processes to physical cores + siblings. |
| **Inference**| `kv_cache_dtype` | `fp4` | Algorithmic compression for 256k context. |
| **Hardware** | `NCCL_ALGO` | `Tree` | Optimized for high-latency system-level paths. |
| **Observability**| `metrics` | `true` | Prometheus-compatible endpoint at port 9090. |

---
**Nemo-Orchestrator** | *Built for the absolute limits of workstation-class AI.*
