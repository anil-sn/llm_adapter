import os
import sys
import time
import torch
import torch.distributed as dist

def run_all_reduce_benchmark(tensor_size_mb=100, steps=50):
    # Retrieve distributed env variables
    try:
        local_rank = int(os.environ["LOCAL_RANK"])
        world_size = int(os.environ["WORLD_SIZE"])
        rank = int(os.environ["RANK"])
    except KeyError:
        print("Error: This script must be launched using torchrun (e.g. torchrun --nproc_per_node=4 ...)")
        sys.exit(1)

    # Set active GPU device
    torch.cuda.set_device(local_rank)
    device = torch.device(f"cuda:{local_rank}")

    # Initialize PyTorch distributed process group
    dist.init_process_group("nccl", init_method="env://")

    # Allocate memory (float32 tensor of size N MB)
    # 1 float32 = 4 bytes, so size = MB * 1024 * 1024 / 4
    num_elements = int((tensor_size_mb * 1024 * 1024) / 4)
    
    # Large tensor for test
    tensor = torch.ones(num_elements, device=device, dtype=torch.float32) * (rank + 1.0)
    
    # Warmup
    for _ in range(5):
        dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    torch.cuda.synchronize()

    # Benchmark run
    start_time = time.perf_counter()
    for _ in range(steps):
        dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
    torch.cuda.synchronize()
    end_time = time.perf_counter()

    elapsed = end_time - start_time
    avg_time = elapsed / steps

    # Bandwidth calculation (Formula based on NCCL-tests)
    # For All-Reduce on P ranks, each rank transfers 2 * (P - 1) / P * size bytes
    bytes_transferred = 2 * (world_size - 1) / world_size * (tensor_size_mb * 1024 * 1024)
    gb_transferred = bytes_transferred / (1024 ** 3)
    bus_bandwidth_gbs = gb_transferred / avg_time

    if rank == 0:
        print("=" * 60)
        print("NCCL Multi-GPU Collective Bandwidth Benchmark")
        print("=" * 60)
        print(f"Num GPUs (Ranks): {world_size}")
        print(f"Tensor Size:      {tensor_size_mb} MB")
        print(f"Iterations:       {steps}")
        print(f"Average Time:     {avg_time * 1000:.3f} ms")
        print(f"Bus Bandwidth:    {bus_bandwidth_gbs:.3f} GB/s")
        print("=" * 60)

    dist.destroy_process_group()

if __name__ == "__main__":
    run_all_reduce_benchmark()
