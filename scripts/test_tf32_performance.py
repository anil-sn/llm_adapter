import torch
import time
import sys

def benchmark_matmul(size=4096, steps=100, precision="highest"):
    # Clear cache and reset precision
    torch.cuda.empty_cache()
    torch.set_float32_matmul_precision(precision)
    
    # Check what got set
    actual_prec = torch.get_float32_matmul_precision()
    
    # Warmup
    a = torch.randn(size, size, device="cuda", dtype=torch.float32)
    b = torch.randn(size, size, device="cuda", dtype=torch.float32)
    for _ in range(10):
        _ = torch.matmul(a, b)
    torch.cuda.synchronize()
    
    # Benchmark
    start_time = time.perf_counter()
    for _ in range(steps):
        _ = torch.matmul(a, b)
    torch.cuda.synchronize()
    end_time = time.perf_counter()
    
    elapsed = end_time - start_time
    avg_time = elapsed / steps
    
    # Operations calculation: 2 * N^3 per matmul
    ops = 2.0 * (size ** 3)
    tflops = (ops / avg_time) / 1e12
    
    return actual_prec, avg_time, tflops

def run_diagnostics():
    print("=" * 60)
    print("PyTorch CUDA / TF32 Diagnostic & Benchmark Utility")
    print("=" * 60)
    
    # System Info
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"PyTorch Version: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("ERROR: CUDA is not available. This script must be run on a GPU-enabled machine.")
        sys.exit(1)
        
    device_id = torch.cuda.current_device()
    gpu_name = torch.cuda.get_device_name(device_id)
    capability = torch.cuda.get_device_capability(device_id)
    print(f"GPU: {gpu_name} (Compute Capability: {capability[0]}.{capability[1]})")
    
    # Check default startup settings (configured by sitecustomize.py)
    print("\n--- Startup Precision Settings (from sitecustomize.py) ---")
    print(f"Default Matmul Precision: {torch.get_float32_matmul_precision()}")
    print(f"allow_tf32 (CUDA Matmul): {torch.backends.cuda.matmul.allow_tf32}")
    print(f"allow_tf32 (CuDNN): {torch.backends.cudnn.allow_tf32}")
    
    # Run benchmarks
    print("\n--- Running Matrix Multiplication Benchmarks (Size: 4096 x 4096) ---")
    
    # 1. FP32 (highest)
    print("Benchmarking precision='highest' (Standard FP32)...")
    p1, t1, tflops1 = benchmark_matmul(precision="highest")
    print(f" -> Setting: {p1} | Avg Time: {t1*1000:.3f} ms | Performance: {tflops1:.3f} TFLOPS")
    
    # 2. TF32 (high)
    print("Benchmarking precision='high' (TensorFloat-32 / TF32)...")
    p2, t2, tflops2 = benchmark_matmul(precision="high")
    print(f" -> Setting: {p2} | Avg Time: {t2*1000:.3f} ms | Performance: {tflops2:.3f} TFLOPS")
    
    # 3. TF32/Half (medium)
    print("Benchmarking precision='medium' (BF16 / FP16 range)...")
    p3, t3, tflops3 = benchmark_matmul(precision="medium")
    print(f" -> Setting: {p3} | Avg Time: {t3*1000:.3f} ms | Performance: {tflops3:.3f} TFLOPS")
    
    print("\n--- Results Analysis ---")
    speedup = t1 / t2
    tflops_diff = tflops2 - tflops1
    print(f"TF32 Speedup Ratio: {speedup:.2f}x")
    print(f"TF32 Performance Boost: +{tflops_diff:.2f} TFLOPS")
    
    if speedup > 1.2:
        print("\n[SUCCESS] TF32 Matrix Multiplications are functioning and yielding significant speedups!")
    else:
        print("\n[INFO] TF32 did not yield a massive speedup. This is expected if the matrix size is small, or the device is already fully loaded.")

if __name__ == "__main__":
    run_diagnostics()
