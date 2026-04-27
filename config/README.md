# Configuration Architecture

## Overview

The LLM Orchestrator uses a **layered configuration system** with inheritance:

```
config.yaml          (Base - shared settings)
  ↓
config-adapter.yaml  (Adapter routing + settings)
  ↓
config-qwen.yaml     (Model-specific overrides)
  OR
config-nemotron.yaml (Model-specific overrides)
```

**Loading order:** Base → Adapters → Model-specific (deep merge)

---

## File Structure

```
config/
├── config.yaml              # Base configuration (hardware, cluster, common)
├── config-adapter.yaml      # Adapter routing rules and settings
├── config-qwen.yaml         # Qwen-specific overrides
├── config-nemotron.yaml     # Nemotron-specific overrides
├── MODEL_COMPARISON.md      # Model comparison guide
├── HARDWARE_TUNING.md       # Hardware-specific tuning
└── README.md                # This file
```

---

## Configuration Files

### 1. `config.yaml` (Base)

**Purpose:** Shared settings for all models

**Contains:**
- Cluster settings (gateway, routing, spillover)
- Replica configuration (GPU groups, ports)
- Hardware settings (tensor parallelism, environment vars)
- Common inference settings (KV cache, batching defaults)
- Observability (logging, metrics)

**Do NOT edit unless:** Changing hardware setup or global defaults

---

### 2. `config-adapter.yaml` (Adapters)

**Purpose:** Adapter routing and adapter-specific settings

**Contains:**
- `model_rules`: Pattern-based routing (e.g., "qwen" → QwenAdapter)
- Adapter settings (sampling profiles, defaults)

**Edit when:** Adding new adapters or changing routing rules

---

### 3. `config-qwen.yaml` (Qwen Model)

**Purpose:** Qwen-specific overrides

**Contains:**
- Model ID and name
- Memory utilization override (0.80)
- Context length (262K → 384K → 512K progressive)
- YaRN RoPE scaling configuration
- Batch size overrides
- Reasoning parser (qwen3)
- Output settings

**Edit when:** Tuning Qwen performance or scaling context

---

### 4. `config-nemotron.yaml` (Nemotron Model)

**Purpose:** Nemotron-specific overrides

**Contains:**
- Model ID and name
- Memory utilization override (0.85)
- Context length (192K)
- Reasoning parser (super_v3) + plugin
- Batch size settings

**Edit when:** Tuning Nemotron performance

---

## Usage

### Switch Between Models

**Method 1: Environment Variable**
```bash
# Use Qwen
export LLM_CONFIG=config/config-qwen.yaml
python scripts/setup/llm_manager.py start

# Use Nemotron
export LLM_CONFIG=config/config-nemotron.yaml
python scripts/setup/llm_manager.py start
```

**Method 2: Inline**
```bash
LLM_CONFIG=config/config-qwen.yaml python scripts/setup/llm_manager.py start
```

**Method 3: Switcher Script (after implementation)**
```bash
./scripts/switch_model.sh qwen
./scripts/switch_model.sh nemotron
```

---

## How Config Merging Works

**Example:** Loading Qwen config

1. **Load `config.yaml`:**
   ```yaml
   hardware:
     tensor_parallel_size: 4
     gpu_memory_utilization: 0.80  # Base default
   inference:
     max_num_seqs: 2
   ```

2. **Merge `config-adapter.yaml`:**
   ```yaml
   model_rules:
     - pattern: "qwen"
       adapter: "qwen"
   qwen_adapter:
     sampling_profiles:
       thinking_general: {...}
   ```

3. **Merge `config-qwen.yaml`:**
   ```yaml
   model:
     id: "Qwen/Qwen3.5-122B-A10B"
   hardware:
     gpu_memory_utilization: 0.80  # Override base
   inference:
     max_model_len: 262144          # Add Qwen-specific
   ```

4. **Final merged config:**
   ```yaml
   hardware:
     tensor_parallel_size: 4        # From base
     gpu_memory_utilization: 0.80   # Overridden by Qwen
   inference:
     max_num_seqs: 2                # From base
     max_model_len: 262144          # From Qwen
   model:
     id: "Qwen/Qwen3.5-122B-A10B"   # From Qwen
   model_rules:                     # From adapter config
     - pattern: "qwen"
       adapter: "qwen"
   ```

---

## Configuration Principles

### 1. **DRY (Don't Repeat Yourself)**
- Common settings live in `config.yaml`
- Only override what's different per model

### 2. **No Hardcoding**
- All values come from config files
- Source code reads config, doesn't define defaults

### 3. **Progressive Overrides**
- Base provides safe defaults
- Model configs override for optimization

### 4. **Clear Ownership**
- Base config: Infra team
- Model configs: ML team
- Adapter config: Platform team

---

## Validation

### Test Config Loading
```bash
# Test config loader utility
cd /path/to/nemo_orchestrator
export LLM_CONFIG=config/config-qwen.yaml
python -m src.nemo_orchestrator.utils.config_loader

# Should output:
# - Loaded model config: config/config-qwen.yaml
# - Model ID: Qwen/Qwen3.5-122B-A10B
# - Context Length: 262144
# - Full merged config (JSON)
```

### Verify No Hardcoding
```bash
# Search for hardcoded values
grep -r "gpu_memory_utilization.*=" src/ scripts/ --include="*.py" | grep -v "config\["
grep -r "max_model_len.*=" src/ scripts/ --include="*.py" | grep -v "config\["

# Should return no results (or only config loading code)
```

---

## Progressive Scaling Example (Qwen)

### Phase 1: 262K Native (Safe Start)
```yaml
# config/config-qwen.yaml
inference:
  max_model_len: 262144
  # rope_scaling: DISABLED
```

### Phase 2: 384K with YaRN 1.5x
```yaml
# config/config-qwen.yaml
inference:
  max_model_len: 393216
  rope_scaling:
    type: "yarn"
    factor: 1.5
    original_max_position_embeddings: 262144
```

### Phase 3: 512K with YaRN 2.0x
```yaml
# config/config-qwen.yaml
inference:
  max_model_len: 524288
  rope_scaling:
    type: "yarn"
    factor: 2.0
    original_max_position_embeddings: 262144
```

**Restart after each phase:**
```bash
python scripts/setup/llm_manager.py restart
```

---

## Troubleshooting

### Config Not Loading
**Symptom:** "LLM_CONFIG not set" warning

**Solution:**
```bash
export LLM_CONFIG=config/config-qwen.yaml
```

### Wrong Model Loaded
**Symptom:** Nemotron loads instead of Qwen

**Check:**
```bash
echo $LLM_CONFIG  # Should show config/config-qwen.yaml
curl http://localhost:8888/v1/models | jq '.data[0].id'
```

### Merge Not Working
**Symptom:** Model-specific settings not applied

**Debug:**
```bash
# Test config loader
python -m src.nemo_orchestrator.utils.config_loader

# Check output for:
# - Which files loaded
# - Final merged values
```

---

## Best Practices

### 1. **Always Set LLM_CONFIG**
```bash
# Good
LLM_CONFIG=config/config-qwen.yaml python scripts/setup/llm_manager.py start

# Bad (uses base config only)
python scripts/setup/llm_manager.py start
```

### 2. **Document Overrides**
Add comments explaining why values differ:
```yaml
hardware:
  gpu_memory_utilization: 0.80  # Conservative for 512K context scaling
```

### 3. **Test After Changes**
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config/config-qwen.yaml'))"

# Test full load
LLM_CONFIG=config/config-qwen.yaml python -m src.nemo_orchestrator.utils.config_loader
```

### 4. **Version Control**
```bash
# Commit config changes together
git add config/
git commit -m "feat: add Qwen 512K context support"
```

---

## Migration from Old Config

### Old System (Single File)
```
config/config.yaml  # Everything in one file
```

### New System (Layered)
```
config/config.yaml          # Base
config/config-adapter.yaml  # Adapters
config/config-qwen.yaml     # Model-specific
```

### Migration Steps
1. Backup current config: `cp config.yaml config-backup.yaml`
2. Extract base settings → `config.yaml`
3. Extract model-specific → `config-qwen.yaml` or `config-nemotron.yaml`
4. Extract adapter rules → `config-adapter.yaml`
5. Test loading: `python -m src.nemo_orchestrator.utils.config_loader`
6. Verify behavior matches before migration

---

**Last Updated:** 2026-04-16
**Architecture Version:** 2.0 (Layered Configs)
