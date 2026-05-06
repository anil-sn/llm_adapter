#!/usr/bin/env python3
"""
LLM Orchestrator - Process Manager
Manages vLLM replicas and gateway with layered configuration support
Optimized for vLLM v0.19.0+ API

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import os
import sys
import signal
import subprocess
import time
import argparse
import json
from pathlib import Path

# Add src to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Import config loader
try:
    from llm_adapter.utils.config_loader import load_config, ConfigError
except ImportError as e:
    print(f"Error: Could not import config loader: {e}", file=sys.stderr)
    print(f"Ensure you're running from project root: {PROJECT_ROOT}", file=sys.stderr)
    sys.exit(1)

BASE_DIR = PROJECT_ROOT  # For backward compatibility


def get_config():
    """
    Load configuration using layered config system.

    Returns:
        dict: Merged configuration

    Raises:
        SystemExit: If config loading fails
    """
    try:
        config = load_config(project_root=PROJECT_ROOT, validate=True)
        return config
    except ConfigError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        print("\nHint: Set LLM_CONFIG environment variable to select model config:", file=sys.stderr)
        print("  export LLM_CONFIG=config/config-qwen.yaml", file=sys.stderr)
        print("  export LLM_CONFIG=config/config-nemotron.yaml", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error loading config: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

def get_pid_file(name):
    return BASE_DIR / f".{name}.pid"

def get_log_file(name):
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir / f"{name}.log"

def is_running(name):
    pid_file = get_pid_file(name)
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (OSError, ValueError):
            pid_file.unlink()
    return None

def cleanup_zombies():
    """Kill any zombie vLLM or gateway processes not tracked by PID files."""
    print("[Cleanup] Scanning for zombie processes...")
    killed = 0

    # Find all vLLM API server processes
    try:
        result = subprocess.run(
            ["pgrep", "-f", "vllm.entrypoints.openai.api_server"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            for pid_str in result.stdout.strip().split('\n'):
                if not pid_str.strip():
                    continue
                pid = int(pid_str.strip())
                # Check if this PID is tracked
                is_tracked = False
                for i in range(10):  # Check up to 10 replicas
                    tracked_pid = is_running(f"vllm_replica_{i}")
                    if tracked_pid == pid:
                        is_tracked = True
                        break
                if not is_tracked:
                    try:
                        os.kill(pid, signal.SIGKILL)
                        print(f"  Killed orphaned vLLM process (PID: {pid})")
                        killed += 1
                    except OSError:
                        pass
    except FileNotFoundError:
        pass  # pgrep not available

    # Find gateway processes
    try:
        result = subprocess.run(
            ["pgrep", "-f", "nemo_gateway.py"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            for pid_str in result.stdout.strip().split('\n'):
                if not pid_str.strip():
                    continue
                pid = int(pid_str.strip())
                tracked_pid = is_running("nemo_gateway")
                if pid != tracked_pid:
                    try:
                        os.kill(pid, signal.SIGKILL)
                        print(f"  Killed orphaned gateway process (PID: {pid})")
                        killed += 1
                    except OSError:
                        pass
    except FileNotFoundError:
        pass

    # Clean up stale PID files for processes that are no longer running
    for pid_file in BASE_DIR.glob(".*.pid"):
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # Check if process exists
        except (OSError, ValueError):
            # Process not running, remove PID file
            pid_file.unlink(missing_ok=True)

    if killed == 0:
        print("[Cleanup] No zombies found.")
    else:
        print(f"[Cleanup] Killed {killed} orphaned process(es).")

    # Wait briefly for ports to be released
    time.sleep(1)


def aggressive_cleanup():
    """Kill all vLLM/gateway processes and free VRAM before starting."""
    print("[Cleanup] Aggressively killing all related processes...")
    
    # Kill all patterns that could hold VRAM
    kill_patterns = [
        "vllm.entrypoints.openai.api_server",
        "VLLM::Worker",
        "VLLM::EngineCore",
        "nemo_gateway",
    ]
    
    killed_count = 0
    for pattern in kill_patterns:
        try:
            result = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                for pid_str in result.stdout.strip().split('\n'):
                    if pid_str.strip():
                        pid = int(pid_str.strip())
                        # Don't kill ourselves
                        if pid == os.getpid():
                            continue
                        try:
                            os.kill(pid, signal.SIGKILL)
                            killed_count += 1
                        except OSError:
                            pass
        except FileNotFoundError:
            pass
    
    # Also kill by process name for any stragglers
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python.*llm_adapter"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            for pid_str in result.stdout.strip().split('\n'):
                if pid_str.strip():
                    pid = int(pid_str.strip())
                    if pid != os.getpid():
                        try:
                            os.kill(pid, signal.SIGKILL)
                            killed_count += 1
                        except OSError:
                            pass
    except FileNotFoundError:
        pass
    
    # Clean up all PID files
    for f in BASE_DIR.glob(".*.pid"):
        f.unlink(missing_ok=True)
    
    # Wait for VRAM to be released
    print(f"[Cleanup] Killed {killed_count} processes. Waiting 10s for VRAM release...")
    time.sleep(10)
    print("[Cleanup] VRAM should be freed.")


def start():
    # Always clean up aggressively first
    aggressive_cleanup()

    config = get_config()
    num_replicas = config["replicas"]["count"]

    for i in range(num_replicas):
        name = f"vllm_replica_{i}"
        # If already running, stop it first for a fresh start
        if pid := is_running(name):
            print(f"Stopping existing Replica {i} (PID: {pid}) for fresh start...")
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass  # Already terminated
            except OSError:
                pass
            pid_file = get_pid_file(name)
            if pid_file.exists():
                pid_file.unlink()
            time.sleep(1)  # Let GPU memory release

        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = config["replicas"]["gpu_groups"][i]

        # PyTorch memory fragmentation fix (helps with MoE models)
        env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

        venv_bin = str(BASE_DIR / ".venv" / "bin")
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

        # Use PyTorch's bundled CUDA libraries to avoid CUDA version mismatch
        # vLLM wheel may be compiled for CUDA 13, but PyTorch has CUDA 12
        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = BASE_DIR / ".venv" / "lib" / python_version / "site-packages"
        torch_lib = str(site_packages / "torch" / "lib")
        nvidia_cuda_lib = str(site_packages / "nvidia" / "cuda_runtime" / "lib")
        existing_ld_path = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{torch_lib}:{nvidia_cuda_lib}:{existing_ld_path}" if existing_ld_path else f"{torch_lib}:{nvidia_cuda_lib}"

        # Add CUDA nvcc to PATH for FlashInfer JIT compilation
        # Try multiple CUDA locations
        cuda_locations = [
            env.get("CUDA_HOME", ""),
            "/usr/local/cuda-12.4",  # Explicit CUDA 12.4 installation
            "/usr/local/cuda",
        ]

        for cuda_home in cuda_locations:
            if cuda_home and (cuda_path := Path(cuda_home)).exists():
                nvcc_path = cuda_path / "bin" / "nvcc"
                if nvcc_path.exists():
                    env["CUDA_HOME"] = str(cuda_path)
                    env["PATH"] = f"{cuda_path}/bin:{env['PATH']}"
                    print(f"  CUDA Toolkit: {cuda_path} (nvcc found)")
                    break

        if env_vars := config["hardware"].get("env_vars"):
            for k, v in env_vars.items(): env[k] = str(v)

        port = config["replicas"]["base_port"] + i
        core_range = config["replicas"]["core_ranges"][i]
        venv_python = str(BASE_DIR / ".venv" / "bin" / "python")

        # BASE COMMAND (Official Nemotron-3 Super Config)
        cmd = [
            "taskset", "-c", core_range,
            venv_python, "-m", "vllm.entrypoints.openai.api_server",
            "--model", config["model"]["id"],
            "--host", "127.0.0.1",
            "--port", str(port),
            "--tensor-parallel-size", str(config["hardware"]["tensor_parallel_size"]),
            "--gpu-memory-utilization", str(config["hardware"]["gpu_memory_utilization"]),
            "--kv-cache-dtype", config["inference"]["kv_cache_dtype"],
            "--max-model-len", str(config["inference"]["max_model_len"]),
            "--trust-remote-code",
            "--tokenizer-mode", config["model"].get("tokenizer_mode", "auto"),
            "--dtype", config["hardware"]["dtype"],
        ]

        # Quantization for model weights (critical for MoE models)
        if quant_config := config.get("quantization"):
            if quant_method := quant_config.get("method"):
                cmd.extend(["--quantization", quant_method])
                print(f"  Weight Quantization: {quant_method.upper()} (reduces model memory ~50%)")

        # Hardware optimizations (matching official cookbook)
        if config["hardware"].get("attention_backend"):
            cmd.extend(["--attention-backend", config["hardware"]["attention_backend"]])

        # RoPE Scaling for extended context (YaRN) - via HF overrides
        if rope_config := config["inference"].get("rope_scaling"):
            # Pass rope_scaling to HuggingFace model config via --hf-overrides
            hf_overrides = {"rope_scaling": rope_config}
            hf_overrides_json = json.dumps(hf_overrides)
            cmd.extend(["--hf-overrides", hf_overrides_json])
            print(f"  RoPE Scaling: {rope_config.get('type')} {rope_config.get('factor')}x (via hf-overrides)")

        # FEATURE FLAGS
        cmd.append("--no-enable-log-requests")

        if config["inference"].get("enable_prefix_caching"):
            cmd.append("--enable-prefix-caching")

        # Handle chunked prefill based on config (vLLM 0.19.0 syntax)
        if config["inference"].get("enable_chunked_prefill", False):
            cmd.append("--enable-chunked-prefill")
        # Note: vLLM defaults to disabled, so we don't need --no-enable-chunked-prefill

        if config["inference"].get("max_num_seqs"):
            cmd.extend(["--max-num-seqs", str(config["inference"]["max_num_seqs"])])

        # Use explicit max_num_batched_tokens from config, or calculate default
        if batched_tokens := config["inference"].get("max_num_batched_tokens"):
            cmd.extend(["--max-num-batched-tokens", str(batched_tokens)])
        else:
            # Fallback: 2x of typical request size for memory efficiency
            max_batched = min(config["inference"]["max_model_len"], 16384)
            cmd.extend(["--max-num-batched-tokens", str(max_batched)])

        if config["inference"].get("enable_thinking"):
            reasoning_parser = config["inference"].get("reasoning_parser", "super_v3")
            reasoning_parser_plugin = config["inference"].get("reasoning_parser_plugin")

            if reasoning_parser_plugin:
                # Convert to absolute path if relative
                plugin_path = BASE_DIR / reasoning_parser_plugin if not reasoning_parser_plugin.startswith("/") else Path(reasoning_parser_plugin)
                cmd.extend(["--reasoning-parser-plugin", str(plugin_path)])

            cmd.extend(["--reasoning-parser", reasoning_parser])

        if config["hardware"].get("disable_custom_all_reduce"):
            cmd.append("--disable-custom-all-reduce")

        # Enforce eager mode for memory-intensive models (MoE)
        if config["inference"].get("enforce_eager"):
            cmd.append("--enforce-eager")

        if config["inference"].get("enable_auto_tool_choice"):
            cmd.append("--enable-auto-tool-choice")

        if parser := config["inference"].get("tool_call_parser"):
            cmd.extend(["--tool-call-parser", parser])

        # Model Aliases - only the clean served name
        # Gateway handles all other aliases (claude-*, gpt-*, etc.)
        primary_served = config["model"].get("served_model_name", "nemotron-3-super")
        served_names = [primary_served]

        for alias in served_names:
            cmd.extend(["--served-model-name", alias])

        print(f"Launching Replica {i} | GPUs {config['replicas']['gpu_groups'][i]} | Port {port}")
        with open(get_log_file(name), "w") as log: # Use "w" to clear log on start
            process = subprocess.Popen(cmd, env=env, stdout=log, stderr=log, start_new_session=True)
        get_pid_file(name).write_text(str(process.pid))

    # Restart gateway if it's already running
    gateway_was_running = is_running("nemo_gateway")
    if gateway_was_running:
        print(f"Stopping existing Gateway (PID: {gateway_was_running}) for fresh start...")
        try:
            os.kill(gateway_was_running, signal.SIGTERM)
            time.sleep(1)
            try:
                os.kill(gateway_was_running, signal.SIGKILL)
            except OSError:
                pass
        except OSError:
            pass
        pid_file = get_pid_file("nemo_gateway")
        if pid_file.exists():
            pid_file.unlink()
        time.sleep(1)

    print(f"Launching Nemo-Gateway on Port {config['cluster']['gateway_port']}...")
    gateway_path = BASE_DIR / "src" / "llm_adapter" / "gateway" / "server.py"
    if not gateway_path.exists():
        # Fallback to old location for backward compatibility
        gateway_path = BASE_DIR / "nemo_gateway.py"

    with open(get_log_file("nemo_gateway"), "w") as log:
        process = subprocess.Popen(
            [str(BASE_DIR / ".venv" / "bin" / "python"), str(gateway_path)],
            stdout=log, stderr=log, start_new_session=True
        )
    get_pid_file("nemo_gateway").write_text(str(process.pid))
    print(f"Gateway started (PID: {process.pid})")

    print("\n[Start] Cluster launch complete. All processes started fresh.")

def kill_process_group(pid, name):
    """Kill a process and all its children using process group."""
    print(f"Stopping {name} (PID: {pid})...")
    try:
        # Kill entire process group (parent + all children)
        pgid = os.getpgid(pid)
        os.killpg(pgid, signal.SIGTERM)
        time.sleep(2)
        # Force kill if still alive
        try:
            os.killpg(pgid, signal.SIGKILL)
        except OSError:
            pass
    except (OSError, ProcessLookupError):
        # Fallback: kill individual process
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def stop():
    """Stop all cluster processes, including any zombies."""
    aggressive_cleanup()
    print("[Stop] All processes killed. Cleanup complete.")

def status():
    config = get_config()
    print("--- Nemo-Orchestrator Cluster Status ---")
    for i in range(config["replicas"]["count"]):
        name = f"vllm_replica_{i}"
        state = "ACTIVE" if is_running(name) else "INACTIVE"
        print(f"Replica {i}: {state}")
    gw = "ACTIVE" if is_running("nemo_gateway") else "INACTIVE"
    print(f"Gateway: {gw} (Port: {config['cluster']['gateway_port']})")

def stop_gateway():
    """Stop only the gateway, keep vLLM replicas running."""
    print("[Stop Gateway] Stopping Nemo-Gateway...")
    pid = is_running("nemo_gateway")
    if pid:
        kill_process_group(pid, "nemo_gateway")
        get_pid_file("nemo_gateway").unlink(missing_ok=True)
        print(f"[Stop Gateway] Gateway stopped (PID: {pid})")
    else:
        print("[Stop Gateway] Gateway was not running")

def start_gateway():
    """Start only the gateway, assuming vLLM replicas are already running."""
    config = get_config()

    # Check if gateway is already running
    if is_running("nemo_gateway"):
        print("[Start Gateway] Gateway already running, stopping first...")
        stop_gateway()
        time.sleep(1)

    print(f"[Start Gateway] Launching Nemo-Gateway on Port {config['cluster']['gateway_port']}...")
    gateway_path = PROJECT_ROOT / "src" / "llm_adapter" / "gateway" / "server.py"
    if not gateway_path.exists():
        # Fallback to old location
        gateway_path = PROJECT_ROOT / "nemo_gateway.py"

    if not gateway_path.exists():
        print(f"[Start Gateway] ERROR: Gateway not found at {gateway_path}")
        sys.exit(1)

    with open(get_log_file("nemo_gateway"), "w") as log:
        process = subprocess.Popen(
            [str(PROJECT_ROOT / ".venv" / "bin" / "python"), str(gateway_path)],
            stdout=log, stderr=log, start_new_session=True
        )
    get_pid_file("nemo_gateway").write_text(str(process.pid))
    print(f"[Start Gateway] Gateway started (PID: {process.pid})")
    print(f"[Start Gateway] Logs: {get_log_file('nemo_gateway')}")

def restart_gateway():
    """Restart only the gateway without affecting vLLM replicas."""
    print("[Restart Gateway] Restarting Nemo-Gateway (keeping vLLM running)...")
    stop_gateway()
    time.sleep(1)
    start_gateway()
    print("[Restart Gateway] Gateway restarted successfully")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Nemo-Orchestrator Cluster Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start              Start entire cluster (vLLM + Gateway)
  stop               Stop entire cluster
  restart            Restart entire cluster
  status             Show cluster status
  restart-gateway    Restart ONLY the gateway (keeps vLLM running)
  stop-gateway       Stop ONLY the gateway
  start-gateway      Start ONLY the gateway

Examples:
  # Full cluster restart
  python llm_manager.py restart

  # Quick gateway restart (after code changes)
  python llm_manager.py restart-gateway
        """
    )
    parser.add_argument("command", choices=[
        "start", "stop", "restart", "status",
        "restart-gateway", "stop-gateway", "start-gateway"
    ])
    args = parser.parse_args()

    if args.command == "start":
        start()
    elif args.command == "stop":
        stop()
    elif args.command == "status":
        status()
    elif args.command == "restart":
        stop()
        time.sleep(2)
        start()
    elif args.command == "restart-gateway":
        restart_gateway()
    elif args.command == "stop-gateway":
        stop_gateway()
    elif args.command == "start-gateway":
        start_gateway()
