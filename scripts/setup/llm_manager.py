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
from typing import List, Dict

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

def get_model_suffix():
    """Get served model name from config as suffix if available."""
    try:
        # Load config without validation to prevent recursive dependencies
        config = load_config(project_root=PROJECT_ROOT, validate=False)
        return config["model"].get("served_model_name", "")
    except Exception:
        return ""

def get_pid_file(name):
    if name.startswith("vllm_replica"):
        if suffix := get_model_suffix():
            return BASE_DIR / f".{name}_{suffix}.pid"
    return BASE_DIR / f".{name}.pid"

def get_log_file(name):
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    if name.startswith("vllm_replica"):
        if suffix := get_model_suffix():
            return log_dir / f"{name}_{suffix}.log"
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

def graceful_kill_pids(pids, label):
    """Gracefully terminate a list of PIDs with SIGTERM, falling back to SIGKILL if necessary."""
    if not pids:
        return 0
    
    print(f"  Sending SIGTERM to {len(pids)} {label} process(es)...")
    killed_count = 0
    
    # 1. Send SIGTERM to all
    for pid in pids:
        try:
            # Try to kill process group if possible
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGTERM)
            except OSError:
                os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
            
    # 2. Wait up to 2 seconds for processes to exit gracefully
    for _ in range(20): # 2 seconds total, check every 100ms
        alive_pids = []
        for pid in pids:
            try:
                os.kill(pid, 0)
                alive_pids.append(pid)
            except OSError:
                pass
        if not alive_pids:
            break
        time.sleep(0.1)
        
    # 3. Force kill any remaining alive processes with SIGKILL
    alive_pids = []
    for pid in pids:
        try:
            os.kill(pid, 0)
            alive_pids.append(pid)
        except OSError:
            pass
            
    if alive_pids:
        print(f"  {len(alive_pids)} process(es) did not exit gracefully, sending SIGKILL...")
        for pid in alive_pids:
            try:
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGKILL)
                except OSError:
                    os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
            killed_count += 1
    
    return len(pids)

def cleanup_zombies():
    """Kill any zombie vLLM or gateway processes not tracked by PID files."""
    print("[Cleanup] Scanning for zombie processes...")
    vllm_pids = []
    gateway_pids = []

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
                    vllm_pids.append(pid)
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
                    gateway_pids.append(pid)
    except FileNotFoundError:
        pass

    killed = 0
    if vllm_pids:
        killed += graceful_kill_pids(vllm_pids, "orphaned vLLM")
    if gateway_pids:
        killed += graceful_kill_pids(gateway_pids, "orphaned gateway")

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
        print(f"[Cleanup] Cleaned up {killed} orphaned process(es).")

    # Wait briefly for ports to be released
    time.sleep(1)


def aggressive_cleanup():
    """Kill only vLLM/replica processes for the current model being started, allowing multiple models to co-exist."""
    try:
        config = get_config()
        model_id = config["model"]["id"]
        served_name = config["model"].get("served_model_name", "vllm")
        gpu_groups = config["replicas"]["gpu_groups"]
    except Exception:
        model_id = ""
        served_name = "vllm"
        gpu_groups = []

    print(f"[Cleanup] Cleaning up processes for model: {served_name} ({model_id or 'all'})...")
    
    replica_pids = []
    lingering_pids = []
    
    # Target only the vLLM process that matches our current model_id
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
                if pid == os.getpid():
                    continue
                try:
                    cmdline_path = Path(f"/proc/{pid}/cmdline")
                    if cmdline_path.exists():
                        cmdline = cmdline_path.read_text().replace('\x00', ' ')
                        # If the command contains our model_id, kill it!
                        if not model_id or model_id in cmdline:
                            replica_pids.append(pid)
                except OSError:
                    pass
    except Exception:
        pass

    # Target any lingering VLLM::EngineCore or VLLM::Worker_TP processes that are running on our targeted GPU group
    if gpu_groups:
        target_gpus = [g.strip() for group in gpu_groups for g in group.split(",")]
        try:
            result = subprocess.run(
                ["pgrep", "-f", "VLLM"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                for pid_str in result.stdout.strip().split('\n'):
                    if not pid_str.strip():
                        continue
                    pid = int(pid_str.strip())
                    if pid == os.getpid():
                        continue
                    try:
                        environ_path = Path(f"/proc/{pid}/environ")
                        if environ_path.exists():
                            environ_data = environ_path.read_text(errors='ignore')
                            # Check if CUDA_VISIBLE_DEVICES in environ matches any of our target GPUs
                            for gpu in target_gpus:
                                if f"CUDA_VISIBLE_DEVICES={gpu}" in environ_data:
                                    lingering_pids.append(pid)
                                    break
                    except OSError:
                        pass
        except Exception:
            pass
        
    killed_count = 0
    if replica_pids:
        killed_count += graceful_kill_pids(replica_pids, "replica")
    if lingering_pids:
        killed_count += graceful_kill_pids(lingering_pids, "lingering VLLM worker")

    # Clean up the replica-specific PID file if it exists
    name = f"vllm_replica_0"
    pid_file = get_pid_file(name)
    if pid_file.exists():
        pid_file.unlink(missing_ok=True)
    
    # Wait for VRAM to release if something was killed
    if killed_count > 0:
        print(f"[Cleanup] Waiting 3s for VRAM release...")
        time.sleep(3)
    else:
        print("[Cleanup] No active processes found for this model.")

    # Clean up any lingering shared memory / POSIX semaphores owned by the current user to prevent leaks
    try:
        shm_dir = Path("/dev/shm")
        if shm_dir.exists():
            my_uid = os.getuid()
            purged_shm = 0
            for pattern in ["psm_*", "sem.mp-*"]:
                for item in shm_dir.glob(pattern):
                    try:
                        if item.stat().st_uid == my_uid:
                            item.unlink(missing_ok=True)
                            purged_shm += 1
                    except OSError:
                        pass
            if purged_shm > 0:
                print(f"[Cleanup] Purged {purged_shm} lingering shared memory/semaphore segments from /dev/shm.")
    except Exception as e:
        pass


def apply_vllm_patches():
    """Apply required vLLM patches (e.g., NVFP4 Marlin padding fix)"""
    patch_script = PROJECT_ROOT / "scripts" / "apply_vllm_patches.sh"
    if patch_script.exists():
        print("[Patches] Checking vLLM patches...")
        try:
            subprocess.run([str(patch_script)], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"[Warning] Patch application had issues: {e.stderr}", file=sys.stderr)
    else:
        print("[Patches] No patch script found, skipping")

def run_constrained_dry_run(cmd: List[str], env: Dict[str, str]) -> bool:
    """
    Perform a constrained dry-run engine bootstrap validation (Path C).
    Launches vLLM in a subprocess with minimal constraints (VRAM = 0.01, Max len = 1)
    to check if the compiled Triton, PyTorch, and vLLM JIT kernels successfully resolve
    without throwing runtime errors or KeyErrors.
    """
    print("\n[Capability Probe] Initiating constrained vLLM bootstrap dry-run...")
    print("  Ensuring compiled kernel registries and GEMM planners resolve on host...")

    dry_run_cmd = list(cmd)
    
    # Override cmd parameters for tight constraints
    def override_arg(cmd_list, arg_name, new_val):
        try:
            idx = cmd_list.index(arg_name)
            cmd_list[idx + 1] = str(new_val)
        except ValueError:
            cmd_list.extend([arg_name, str(new_val)])

    override_arg(dry_run_cmd, "--gpu-memory-utilization", "0.01")
    override_arg(dry_run_cmd, "--max-model-len", "1")
    override_arg(dry_run_cmd, "--max-num-seqs", "1")
    override_arg(dry_run_cmd, "--port", "8099")  # Temp non-conflicting port

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    dry_run_log_path = log_dir / "vllm_dry_run_probe.log"
    
    with open(dry_run_log_path, "w") as log_file:
        # Launch dry-run in its own process group so we can SIGKILL it cleanly
        process = subprocess.Popen(
            dry_run_cmd, env=env, stdout=log_file, stderr=log_file, start_new_session=True
        )
        
        # Wait and parse the log file in real time for success or failure signatures
        check_interval = 0.5
        max_checks = int(90 / check_interval)  # Max 90 seconds for compilation/loading on large MoE/dense models
        succeeded = False
        
        for check in range(max_checks):
            time.sleep(check_interval)
            
            # Check if process terminated on its own
            ret_code = process.poll()
            if ret_code is not None:
                if ret_code != 0:
                    succeeded = False
                    break
            
            # Read and parse current log output
            try:
                log_text = dry_run_log_path.read_text()
                
                # Check for known failure signatures
                if any(err in log_text for err in ["KeyError", "RuntimeError", "Traceback", "Exception", "Error", "float8_e8m0fnu"]):
                    succeeded = False
                    break
                    
                # Check for success signatures
                if any(ok in log_text for ok in ["Started server process", "Uvicorn running on", "EngineCoreClient initialized", "connected to EngineCore"]):
                    succeeded = True
                    break
            except Exception:
                pass
        
        # Cleanly kill the dry-run process group
        try:
            pgid = os.getpgid(process.pid)
            os.killpg(pgid, signal.SIGKILL)
        except OSError:
            try:
                process.kill()
            except OSError:
                pass
                
    if succeeded:
        print("[Capability Probe] ✓ Bootstrap dry-run succeeded! All kernels and planners verified.")
        return True
    else:
        print("[Capability Probe] ✗ Bootstrap dry-run FAILED.")
        # Print the last few lines of the dry-run log to show the exact traceback
        try:
            log_lines = dry_run_log_path.read_text().splitlines()
            last_lines = log_lines[-30:] if len(log_lines) > 30 else log_lines
            print("\n" + "=" * 80)
            print("CAPABILITY PROBE BOOTSTRAP TRACEBACK:")
            print("=" * 80)
            for line in last_lines:
                print(f"  {line}")
            print("=" * 80 + "\n")
        except Exception:
            pass
        return False


def start():
    # Always clean up aggressively first
    aggressive_cleanup()

    # Apply vLLM patches if needed (idempotent)
    apply_vllm_patches()

    config = get_config()

    # Validate that model config is present
    if "model" not in config or "id" not in config.get("model", {}):
        print("Error: No model configured. Model-specific config is required to start vLLM.", file=sys.stderr)
        print("\nPlease set LLM_CONFIG to a valid model config file:", file=sys.stderr)
        print("  export LLM_CONFIG=config/config-nemotron-super.yaml", file=sys.stderr)
        print("  export LLM_CONFIG=config/config-qwen.yaml", file=sys.stderr)
        sys.exit(1)

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

        # Silence benign resource_tracker warnings at shutdown
        if "PYTHONWARNINGS" not in env:
            env["PYTHONWARNINGS"] = "ignore:resource_tracker:UserWarning"
        else:
            env["PYTHONWARNINGS"] = f"ignore:resource_tracker:UserWarning,{env['PYTHONWARNINGS']}"

        # PyTorch memory fragmentation fix (helps with MoE models)
        env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

        # Set HuggingFace cache location if not already set
        if "HF_HOME" not in env:
            env["HF_HOME"] = str(Path.home() / ".cache" / "huggingface")

        venv_bin = str(BASE_DIR / ".venv" / "bin")
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

        # Use PyTorch's bundled CUDA libraries to avoid CUDA version mismatch
        # Add NCCL library path for multi-GPU support (required for PyTorch 2.11.0)
        python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site_packages = BASE_DIR / ".venv" / "lib" / python_version / "site-packages"
        torch_lib = str(site_packages / "torch" / "lib")
        nvidia_cuda_lib = str(site_packages / "nvidia" / "cuda_runtime" / "lib")
        nvidia_nccl_lib = str(site_packages / "nvidia" / "nccl" / "lib")
        existing_ld_path = env.get("LD_LIBRARY_PATH", "")
        lib_paths = [torch_lib, nvidia_cuda_lib, nvidia_nccl_lib]
        if existing_ld_path:
            lib_paths.append(existing_ld_path)
        env["LD_LIBRARY_PATH"] = ":".join(lib_paths)

        # Add CUDA nvcc to PATH for FlashInfer JIT compilation
        # Try multiple CUDA locations (prefer system default)
        cuda_locations = [
            env.get("CUDA_HOME", ""),
            "/usr/local/cuda",       # System default (currently CUDA 13.2)
            "/usr/local/cuda-13.2",  # Explicit CUDA 13.2 for vLLM 0.23.0+
            "/usr/local/cuda-12.4",  # Fallback to CUDA 12.4 if needed
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

        # Apply vLLM-specific environment variables
        if vllm_env := config.get("vllm", {}).get("env"):
            for k, v in vllm_env.items(): env[k] = str(v)

        port = config["replicas"]["base_port"] + i
        core_range = config["replicas"]["core_ranges"][i]
        venv_python = str(BASE_DIR / ".venv" / "bin" / "python")

        # BASE COMMAND (Official Nemotron-3 Super Config)
        cmd = [
            "taskset", "-c", core_range,
            venv_python, "-u", "-m", "vllm.entrypoints.openai.api_server",  # -u for unbuffered output
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

        # Linear backend for NVFP4 models (workaround for Marlin alignment bugs)
        if config["hardware"].get("linear_backend"):
            cmd.extend(["--linear-backend", config["hardware"]["linear_backend"]])

        # HuggingFace model config overrides (RoPE, MTP, etc.)
        hf_overrides = {}

        # Add explicit hf_overrides from config (e.g., num_nextn_predict_layers for MTP)
        if config_hf_overrides := config["inference"].get("hf_overrides"):
            hf_overrides.update(config_hf_overrides)

        # RoPE Scaling for extended context (YaRN)
        if rope_config := config["inference"].get("rope_scaling"):
            hf_overrides["rope_scaling"] = rope_config
            print(f"  RoPE Scaling: {rope_config.get('type')} {rope_config.get('factor')}x (via hf-overrides)")

        # Pass merged hf_overrides to vLLM if any exist
        if hf_overrides:
            hf_overrides_json = json.dumps(hf_overrides)
            cmd.extend(["--hf-overrides", hf_overrides_json])
            if "num_nextn_predict_layers" in hf_overrides:
                mtp_status = "enabled" if hf_overrides["num_nextn_predict_layers"] > 0 else "disabled"
                print(f"  MTP (Multi-Token Prediction): {mtp_status} (layers={hf_overrides['num_nextn_predict_layers']})")

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

        # Serial model weight loading to prevent OOM memory spikes on shared hosts
        if max_workers := config["hardware"].get("max_parallel_loading_workers"):
            cmd.extend(["--max-parallel-loading-workers", str(max_workers)])

        # Enforce eager mode for memory-intensive models (MoE)
        if config["inference"].get("enforce_eager"):
            cmd.append("--enforce-eager")

        if config["inference"].get("enable_auto_tool_choice"):
            cmd.append("--enable-auto-tool-choice")

        # Expert parallel for MoE models (Nemotron Super)
        if config["inference"].get("enable_expert_parallel"):
            cmd.append("--enable-expert-parallel")

        # MoE Backend configuration
        if moe_backend := config["inference"].get("moe_backend"):
            cmd.extend(["--moe-backend", moe_backend])

        # Multimodal limits (disable vision/image for text-only models)
        if limit_mm := config["inference"].get("limit_mm_per_prompt"):
            limit_mm_json = json.dumps(limit_mm)
            cmd.extend(["--limit-mm-per-prompt", limit_mm_json])

        if parser := config["inference"].get("tool_call_parser"):
            cmd.extend(["--tool-call-parser", parser])

        # Chat template override (important for tool calling)
        if chat_template := config["model"].get("chat_template"):
            cmd.extend(["--chat-template", chat_template])

        # Speculative decoding configuration (N-gram, EAGLE, Medusa, draft_model, etc.)
        # Check both top-level (legacy) and inference.speculative_decoding (new location)
        spec_config = config.get("speculative_decoding") or config.get("inference", {}).get("speculative_decoding")
        if spec_config:
            method = spec_config["method"]
            num_tokens = spec_config.get("num_speculative_tokens", 5)
            print(f"  Speculative Decoding: {method.upper()} with {num_tokens} tokens")

            # Build speculative config JSON
            spec_dict = {
                "method": method,
                "num_speculative_tokens": num_tokens,
            }

            # Add draft/EAGLE model if specified (supports both "model" and "draft_model" keys)
            draft_model = spec_config.get("model") or spec_config.get("draft_model")
            if draft_model:
                spec_dict["model"] = draft_model
                draft_tp_size = spec_config.get("draft_tensor_parallel_size", config["hardware"]["tensor_parallel_size"])
                spec_dict["draft_tensor_parallel_size"] = draft_tp_size
                print(f"    Draft/EAGLE model: {draft_model}")
                print(f"    Draft TP size: {draft_tp_size}")

            spec_json = json.dumps(spec_dict)
            cmd.extend(["--speculative-config", spec_json])

        # Model Aliases - only the clean served name
        # Gateway handles all other aliases (claude-*, gpt-*, etc.)
        primary_served = config["model"].get("served_model_name", "nemotron-3-super")
        served_names = [primary_served]

        for alias in served_names:
            cmd.extend(["--served-model-name", alias])

        # For the first replica, run the capability dry-run check to verify kernel resolution
        if i == 0:
            if not run_constrained_dry_run(cmd, env):
                print("\n[Capability Warning] Dynamic capability probe failed!")
                print("  The current configuration is incompatible with this CUDA/Triton stack.")
                print("  Proceeding to launch the production server anyway as requested...\n")
                # Purely observational - do not fall back, proceed to launch the model anyway

        print(f"Launching Replica {i} | GPUs {config['replicas']['gpu_groups'][i]} | Port {port}")
        # Open log file and keep it open for the subprocess (don't use context manager)
        log = open(get_log_file(name), "w")  # Clear log on start
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

    # Open log file and keep it open for the subprocess
    log = open(get_log_file("nemo_gateway"), "w")
    process = subprocess.Popen(
        [str(BASE_DIR / ".venv" / "bin" / "python"), "-u", str(gateway_path)],  # -u for unbuffered
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

    env = os.environ.copy()
    if "PYTHONWARNINGS" not in env:
        env["PYTHONWARNINGS"] = "ignore:resource_tracker:UserWarning"
    else:
        env["PYTHONWARNINGS"] = f"ignore:resource_tracker:UserWarning,{env['PYTHONWARNINGS']}"

    with open(get_log_file("nemo_gateway"), "w") as log:
        process = subprocess.Popen(
            [str(PROJECT_ROOT / ".venv" / "bin" / "python"), str(gateway_path)],
            env=env, stdout=log, stderr=log, start_new_session=True
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

def download():
    """Download model using hf_downloader.py."""
    config = get_config()

    # Validate that model config is present
    if "model" not in config or "id" not in config.get("model", {}):
        print("Error: No model configured. Model-specific config is required for download.", file=sys.stderr)
        print("\nPlease set LLM_CONFIG to a valid model config file:", file=sys.stderr)
        print("  export LLM_CONFIG=config/config-nemotron-super.yaml", file=sys.stderr)
        print("  export LLM_CONFIG=config/config-qwen.yaml", file=sys.stderr)
        print("\nNote: Remove the duplicate 'config/' if present in your path.", file=sys.stderr)
        sys.exit(1)

    model_id = config["model"]["id"]

    print(f"[Download] Starting model download: {model_id}")
    print(f"[Download] Using: scripts/setup/hf_downloader.py")
    print()

    # Call hf_downloader.py with current environment (preserves LLM_CONFIG)
    downloader_script = PROJECT_ROOT / "scripts" / "setup" / "hf_downloader.py"

    try:
        result = subprocess.run(
            [sys.executable, str(downloader_script)],
            cwd=PROJECT_ROOT,
            env=os.environ.copy(),  # Inherit LLM_CONFIG and other env vars
            check=True
        )
        print(f"\n[Download] Base model download completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"\n[Download] Base model download failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\n[Download] Error downloading base model: {e}")
        sys.exit(1)

    # Download draft model if speculative decoding is enabled
    # Check both top-level (legacy) and inference.speculative_decoding (new location)
    spec_config = config.get("speculative_decoding") or config.get("inference", {}).get("speculative_decoding")
    if spec_config:
        draft_model_id = spec_config.get("draft_model")
        if draft_model_id:
            print(f"\n[Download] EAGLE draft model detected: {draft_model_id}")
            print(f"[Download] Starting draft model download...")
            print()

            try:
                # Download draft model using hf (new HF CLI)
                result = subprocess.run(
                    ["hf", "download", draft_model_id],
                    cwd=PROJECT_ROOT,
                    check=True
                )
                print(f"\n[Download] Draft model download completed successfully")
            except subprocess.CalledProcessError as e:
                print(f"\n[Download] Draft model download failed with exit code {e.returncode}")
                print(f"[Download] You can manually download with:")
                print(f"  hf download {draft_model_id}")
                sys.exit(e.returncode)
            except FileNotFoundError:
                print(f"\n[Download] ERROR: 'hf' command not found")
                print(f"[Download] Install with: pip install huggingface_hub[cli]")
                print(f"[Download] Or manually download: hf download {draft_model_id}")
                sys.exit(1)
            except Exception as e:
                print(f"\n[Download] Error downloading draft model: {e}")
                sys.exit(1)

    print(f"\n[Download] All models downloaded successfully")
    return 0


def benchmark(mode="throughput", **kwargs):
    """Run vLLM benchmark using benchmark_vllm.py."""
    config = get_config()

    # Validate that model config is present
    if "model" not in config or "served_model_name" not in config.get("model", {}):
        print("Error: No model configured. Model-specific config is required for benchmarking.", file=sys.stderr)
        print("\nPlease set LLM_CONFIG to a valid model config file:", file=sys.stderr)
        print("  export LLM_CONFIG=config/config-nemotron-super.yaml", file=sys.stderr)
        print("  export LLM_CONFIG=config/config-qwen.yaml", file=sys.stderr)
        sys.exit(1)

    model_name = config["model"]["served_model_name"]

    print(f"[Benchmark] Running vLLM benchmark")
    print(f"[Benchmark] Model: {model_name}")
    print(f"[Benchmark] Mode: {mode}")
    print()

    # Build benchmark command
    benchmark_script = PROJECT_ROOT / "scripts" / "benchmark_vllm.py"
    cmd = [sys.executable, str(benchmark_script), "--mode", mode, "--model", model_name]

    # Add optional arguments
    if "url" in kwargs and kwargs["url"]:
        cmd.extend(["--url", kwargs["url"]])
    if "input_lengths" in kwargs and kwargs["input_lengths"]:
        cmd.extend(["--input-lengths"] + [str(x) for x in kwargs["input_lengths"]])
    if "output_lengths" in kwargs and kwargs["output_lengths"]:
        cmd.extend(["--output-lengths"] + [str(x) for x in kwargs["output_lengths"]])
    if "concurrent" in kwargs and kwargs["concurrent"]:
        cmd.extend(["--concurrent"] + [str(x) for x in kwargs["concurrent"]])

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            env=os.environ.copy(),
            check=True
        )
        print(f"\n[Benchmark] Benchmark completed successfully")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"\n[Benchmark] Benchmark failed with exit code {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\n[Benchmark] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Nemo-Orchestrator Cluster Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  download           Download model from HuggingFace
  start              Start entire cluster (vLLM + Gateway)
  stop               Stop entire cluster
  restart            Restart entire cluster
  status             Show cluster status
  restart-gateway    Restart ONLY the gateway (keeps vLLM running)
  stop-gateway       Stop ONLY the gateway
  start-gateway      Start ONLY the gateway
  benchmark          Run vLLM performance benchmark

Examples:
  # Download model
  LLM_CONFIG=config/config-mistral-medium-3.5.yaml python llm_manager.py download

  # Full cluster restart
  python llm_manager.py restart

  # Quick gateway restart (after code changes)
  python llm_manager.py restart-gateway

  # Run benchmark
  python llm_manager.py benchmark --mode throughput
  python llm_manager.py benchmark --mode concurrent
  python llm_manager.py benchmark --mode all
        """
    )
    parser.add_argument("command", choices=[
        "download", "start", "stop", "restart", "status",
        "restart-gateway", "stop-gateway", "start-gateway", "benchmark"
    ])
    parser.add_argument("--mode", default="throughput",
                       choices=["throughput", "concurrent", "streaming", "all"],
                       help="Benchmark mode (for benchmark command)")
    parser.add_argument("--url", default="http://127.0.0.1:8000",
                       help="vLLM API URL (for benchmark command)")
    args = parser.parse_args()

    if args.command == "download":
        download()
    elif args.command == "start":
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
    elif args.command == "benchmark":
        benchmark(mode=args.mode, url=args.url)
