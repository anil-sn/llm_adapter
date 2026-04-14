#!/usr/bin/env bash
# Memory profiling script for debugging MoE OOM issues
# Usage: ./debug_memory.sh

echo "=== Nemo-Orchestrator Memory Profiler ==="
echo ""

echo "1. Current GPU Memory State:"
nvidia-smi --query-gpu=index,name,memory.used,memory.total,memory.free,utilization.gpu --format=csv

echo ""
echo "2. vLLM Process Memory:"
ps aux | grep "vllm.entrypoints" | grep -v grep

echo ""
echo "3. Detailed Memory Breakdown (GPU 0-3):"
for gpu in {0..3}; do
    echo "--- GPU $gpu ---"
    nvidia-smi -i $gpu --query-compute-apps=pid,used_memory --format=csv,noheader
done

echo ""
echo "4. CUDA Memory Fragmentation Check:"
python3 << 'EOF'
import torch
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f"GPU {i}:")
        print(f"  Allocated: {torch.cuda.memory_allocated(i) / 1e9:.2f} GB")
        print(f"  Reserved:  {torch.cuda.memory_reserved(i) / 1e9:.2f} GB")
        print(f"  Max Alloc: {torch.cuda.max_memory_allocated(i) / 1e9:.2f} GB")
        fragmentation = (torch.cuda.memory_reserved(i) - torch.cuda.memory_allocated(i)) / 1e9
        print(f"  Fragmentation: {fragmentation:.2f} GB")
        print()
else:
    print("CUDA not available")
EOF

echo ""
echo "5. vLLM Log Tail (last 50 lines):"
if [ -d "logs" ]; then
    tail -50 logs/vllm_replica_0.log | grep -i "memory\|oom\|alloc"
fi
