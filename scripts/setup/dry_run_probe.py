#!/usr/bin/env python3
"""
LLM Orchestrator - Standalone Dry Run Probe
Executes the constrained dry-run capability probe for validation on SM89/SM90
without stopping the active production model or permanently launching processes.
"""

import os
import sys
import json
from pathlib import Path

# Add src and scripts/setup to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "setup"))

try:
    import llm_manager
except ImportError as e:
    print(f"Error: Could not import llm_manager: {e}")
    sys.exit(1)

def run_probe():
    # 1. Load config
    config = llm_manager.get_config()
    
    # 2. Extract configuration values
    model_id = config["model"]["id"]
    served_name = config["model"].get("served_model_name", "vllm")
    
    print(f"[Dry Run Probe] Model ID: {model_id}")
    print(f"[Dry Run Probe] Served Model Name: {served_name}")
    
    # 3. Setup environment mimicking llm_manager.py
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = config["replicas"]["gpu_groups"][0]
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    
    if "PYTHONWARNINGS" not in env:
        env["PYTHONWARNINGS"] = "ignore:resource_tracker:UserWarning"
    else:
        env["PYTHONWARNINGS"] = f"ignore:resource_tracker:UserWarning,{env['PYTHONWARNINGS']}"
        
    venv_bin = str(PROJECT_ROOT / ".venv" / "bin")
    env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
    
    # Library paths
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = PROJECT_ROOT / ".venv" / "lib" / python_version / "site-packages"
    torch_lib = str(site_packages / "torch" / "lib")
    nvidia_cuda_lib = str(site_packages / "nvidia" / "cuda_runtime" / "lib")
    nvidia_nccl_lib = str(site_packages / "nvidia" / "nccl" / "lib")
    existing_ld_path = env.get("LD_LIBRARY_PATH", "")
    lib_paths = [torch_lib, nvidia_cuda_lib, nvidia_nccl_lib]
    if existing_ld_path:
        lib_paths.append(existing_ld_path)
    env["LD_LIBRARY_PATH"] = ":".join(lib_paths)
    
    # CUDA bin search
    cuda_locations = [
        env.get("CUDA_HOME", ""),
        "/usr/local/cuda",
        "/usr/local/cuda-13.2",
        "/usr/local/cuda-12.4",
    ]
    for cuda_home in cuda_locations:
        if cuda_home and (cuda_path := Path(cuda_home)).exists():
            nvcc_path = cuda_path / "bin" / "nvcc"
            if nvcc_path.exists():
                env["CUDA_HOME"] = str(cuda_path)
                env["PATH"] = f"{cuda_path}/bin:{env['PATH']}"
                break
                
    if env_vars := config["hardware"].get("env_vars"):
        for k, v in env_vars.items(): env[k] = str(v)
        
    if vllm_env := config.get("vllm", {}).get("env"):
        for k, v in vllm_env.items(): env[k] = str(v)
        
    # 4. Construct launching command mimicking llm_manager.py
    port = config["replicas"]["base_port"]
    core_range = config["replicas"]["core_ranges"][0]
    venv_python = str(PROJECT_ROOT / ".venv" / "bin" / "python")
    
    cmd = [
        "taskset", "-c", core_range,
        venv_python, "-u", "-m", "vllm.entrypoints.openai.api_server",
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

    if skip_layers := config["inference"].get("kv_cache_dtype_skip_layers"):
        cmd.extend(["--kv-cache-dtype-skip-layers", skip_layers])
    
    if quant_config := config.get("quantization"):
        if quant_method := quant_config.get("method"):
            cmd.extend(["--quantization", quant_method])
            
    if config["hardware"].get("attention_backend"):
        cmd.extend(["--attention-backend", config["hardware"]["attention_backend"]])
        
    if config["hardware"].get("linear_backend"):
        cmd.extend(["--linear-backend", config["hardware"]["linear_backend"]])
        
    hf_overrides = {}
    if config_hf_overrides := config["inference"].get("hf_overrides"):
        hf_overrides.update(config_hf_overrides)
        
    if rope_config := config["inference"].get("rope_scaling"):
        hf_overrides["rope_scaling"] = rope_config
        
    if hf_overrides:
        cmd.extend(["--hf-overrides", json.dumps(hf_overrides)])
        
    cmd.append("--no-enable-log-requests")
    
    if config["inference"].get("enable_prefix_caching"):
        cmd.append("--enable-prefix-caching")
        
    if config["inference"].get("enable_chunked_prefill", False):
        cmd.append("--enable-chunked-prefill")
        
    if config["inference"].get("max_num_seqs"):
        cmd.extend(["--max-num-seqs", str(config["inference"]["max_num_seqs"])])
        
    if batched_tokens := config["inference"].get("max_num_batched_tokens"):
        cmd.extend(["--max-num-batched-tokens", str(batched_tokens)])
        
    if config["inference"].get("enable_thinking"):
        reasoning_parser = config["inference"].get("reasoning_parser", "super_v3")
        cmd.extend(["--reasoning-parser", reasoning_parser])
        if reasoning_parser_plugin := config["inference"].get("reasoning_parser_plugin"):
            cmd.extend(["--reasoning-parser-plugin", str(PROJECT_ROOT / reasoning_parser_plugin)])
            
    if config["hardware"].get("disable_custom_all_reduce"):
        cmd.append("--disable-custom-all-reduce")
        
    if max_workers := config["hardware"].get("max_parallel_loading_workers"):
        cmd.extend(["--max-parallel-loading-workers", str(max_workers)])
        
    if config["inference"].get("enforce_eager"):
        cmd.append("--enforce-eager")
        
    if config["inference"].get("enable_auto_tool_choice"):
        cmd.append("--enable-auto-tool-choice")
        
    if config["inference"].get("enable_expert_parallel"):
        cmd.append("--enable-expert-parallel")
        
    if moe_backend := config["inference"].get("moe_backend"):
        cmd.extend(["--moe-backend", moe_backend])
        
    if limit_mm := config["inference"].get("limit_mm_per_prompt"):
        cmd.extend(["--limit-mm-per-prompt", json.dumps(limit_mm)])
        
    if parser := config["inference"].get("tool_call_parser"):
        cmd.extend(["--tool-call-parser", parser])
        
    if chat_template := config["model"].get("chat_template"):
        cmd.extend(["--chat-template", chat_template])
        
    spec_config = config.get("speculative_decoding") or config.get("inference", {}).get("speculative_decoding")
    if spec_config:
        spec_dict = {
            "method": spec_config["method"],
            "num_speculative_tokens": spec_config.get("num_speculative_tokens", 5),
        }
        draft_model = spec_config.get("model") or spec_config.get("draft_model")
        if draft_model:
            spec_dict["model"] = draft_model
            spec_dict["draft_tensor_parallel_size"] = spec_config.get("draft_tensor_parallel_size", config["hardware"]["tensor_parallel_size"])
        cmd.extend(["--speculative-config", json.dumps(spec_dict)])
        
    cmd.extend(["--served-model-name", served_name])
    
    # 5. Run the dry run capability probe!
    success = llm_manager.run_constrained_dry_run(cmd, env)
    
    if success:
        print("[Dry Run Probe] Done. Bootstrap dry-run succeeded!")
        sys.exit(0)
    else:
        print("[Dry Run Probe] Done. Bootstrap dry-run FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    run_probe()
