# File Cleanup Proposal

**Goal:** Remove redundant files, consolidate documentation, keep only what's essential

---

## 📋 KEEP (Essential Files)

### Core Application
- ✅ `src/llm_adapter/` - Main application code
- ✅ `pyproject.toml` - Project dependencies
- ✅ `test_all.py` - Comprehensive test suite (enhanced)
- ✅ `README.md` - Main documentation

### Active Configs (Currently Used)
- ✅ `config/config.yaml` - Base config
- ✅ `config/config-adapter.yaml` - Adapter config
- ✅ `config/config-qwen36-27b.yaml` - Qwen 27B 1M context ⭐
- ✅ `config/config-qwen36-35b.yaml` - Qwen 35B 1M context ⭐ CURRENT

### Essential Scripts
- ✅ `scripts/setup/llm_manager.py` - LLM management (main script)
- ✅ `scripts/test_1m_context.py` - 1M context testing
- ✅ `scripts/test_qwen36.py` - Qwen testing
- ✅ `scripts/download_qwen36_27b.sh` - Model download
- ✅ `scripts/download_qwen36_awq.sh` - Model download

### Documentation (Keep)
- ✅ `QWEN36_1M_CONTEXT.md` - Qwen deployment guide (LATEST)
- ✅ `TEST_SUITE_ENHANCEMENTS.md` - Test suite docs
- ✅ `docs/ARCHITECTURE.md` - System architecture
- ✅ `docs/TESTING.md` - Testing guide

---

## 🗑️ REMOVE (Redundant/Outdated)

### Outdated Documentation
- ❌ `CLEANUP_SUMMARY.md` - Old cleanup notes (superseded)
- ❌ `QWEN36_DEPLOYMENT.md` - Superseded by QWEN36_1M_CONTEXT.md
- ❌ `docs/PHASE0_TEST_PLAN.md` - Phase 0 complete
- ❌ `docs/README_TESTING.md` - Redundant with TESTING.md
- ❌ `docs/README_V3_EXTREME.md` - Old version docs
- ❌ `docs/REORGANIZATION.md` - Reorganization complete
- ❌ `docs/CLAUDE_CODE_COMPATIBILITY_FIXES.md` - Fixes applied
- ❌ `docs/CLAUDE_CODE_SETUP.md` - Not using Claude Code CLI
- ❌ `docs/CLAUDE.md` - Not applicable
- ❌ `docs/API_COMPLIANCE_REVIEW.md` - Review complete

### Unused Configs
- ❌ `config/config-qwen.yaml` - Using qwen36-27b/35b instead
- ❌ `config/config-qwen-1m.yaml` - Using qwen36 configs instead
- ❌ `config/config-nemotron.yaml` - Not using Nemotron
- ❌ `config/config-emergency-4k.yaml` - Not needed

### Unused Scripts
- ❌ `scripts/test_deepseek_phase0.py` - Phase 0 complete
- ❌ `scripts/run_phase0_test.sh` - Phase 0 complete
- ❌ `scripts/check_system_compatibility.sh` - System validated
- ❌ `scripts/cleanup.sh` - Old cleanup script
- ❌ `scripts/cleanup_project.py` - Old cleanup script
- ❌ `scripts/switch_model.sh` - Use llm_manager.py instead
- ❌ `scripts/find_python.sh` - Python installed
- ❌ `scripts/install_python312.sh` - Python installed
- ❌ `scripts/install_python312_pyenv.sh` - Python installed
- ❌ `scripts/setup_venv.sh` - Venv created
- ❌ `scripts/run_tests.sh` - Use test_all.py instead

### Setup Scripts (One-time use, complete)
- ❌ `scripts/setup/install_nvidia_driver.sh` - Driver installed
- ❌ `scripts/setup/install_nvidia_from_source.sh` - Driver installed
- ❌ `scripts/setup/upgrade_nvidia_driver.sh` - Driver installed
- ❌ `scripts/setup/test_cuda_install.sh` - CUDA validated
- ❌ `scripts/setup/test_nvidia_prerequisites.sh` - Prerequisites validated
- ❌ `scripts/setup/setup_claude_code_cli.sh` - Not using
- ❌ `scripts/setup/validate_claude_code_cli.sh` - Not using
- ❌ `scripts/setup/fix_paths_after_reorganization.sh` - Reorganization complete
- ❌ `scripts/setup/download_reasoning_parser.sh` - Not needed
- ❌ `scripts/setup/run_claude_adapter.py` - Use llm_manager.py

### Testing Scripts (Redundant)
- ❌ `scripts/testing/check_tool_calling.sh` - Use test_all.py
- ❌ `scripts/testing/verify_startup.sh` - Use test_all.py
- ❌ `scripts/testing/debug_memory.sh` - Memory stable
- ❌ `scripts/testing/test_context_kv_cache.py` - Use test_1m_context.py
- ❌ `scripts/testing/benchmark.py` - Not needed for production

### Old Code
- ❌ `archive/deprecated/` - Already in archive, can delete entirely

### Community Files (Not Needed)
- ❌ `CODE_OF_CONDUCT.md` - Not a public project
- ❌ `CONTRIBUTING.md` - Not a public project

### Other
- ❌ `VLLM_CUDA_COMPATIBILITY.md` - Issues resolved, info in docs
- ❌ `tests/test_config_system.py` - Superseded by test_all.py
- ❌ `tests/test_qwen_adapter.py` - Superseded by test_all.py
- ❌ `adapters/` directory - Empty or unused
- ❌ `~` file in root - Looks like backup file

---

## 📦 MAYBE KEEP (Decision Needed)

### Documentation (Might Be Useful)
- 🤔 `docs/MEMORY_TROUBLESHOOTING.md` - Useful if issues recur
- 🤔 `config/README.md` - Config documentation

### Scripts (Might Be Useful)
- 🤔 `scripts/deployment/clean.sh` - Cleanup utility
- 🤔 `scripts/deployment/restart_gateway.sh` - Restart utility
- 🤔 `scripts/setup/hf_downloader.py` - Generic downloader

---

## 📊 Summary

| Category | Count | Action |
|----------|-------|--------|
| **Keep** | ~20 files | Essential for operation |
| **Remove** | ~45 files | Delete (outdated/redundant) |
| **Maybe** | ~5 files | Discuss |
| **Total** | ~70 files | Current count |
| **After Cleanup** | ~25 files | Target |

---

## 🎯 Cleanup Benefits

1. **Clarity** - Easy to find what you need
2. **Maintenance** - Less confusion about what's current
3. **Performance** - Smaller repo size
4. **Organization** - Clear structure

---

## ✅ Recommended Actions

### Immediate (Safe to Delete)
```bash
# Remove old documentation
rm CLEANUP_SUMMARY.md QWEN36_DEPLOYMENT.md VLLM_CUDA_COMPATIBILITY.md
rm CODE_OF_CONDUCT.md CONTRIBUTING.md

# Remove unused configs
rm config/config-qwen.yaml config/config-qwen-1m.yaml
rm config/config-nemotron.yaml config/config-emergency-4k.yaml

# Remove deprecated code
rm -rf archive/

# Remove setup scripts (one-time use, complete)
rm -rf scripts/setup/install_nvidia*.sh
rm -rf scripts/setup/*claude*.sh
rm scripts/setup/fix_paths_after_reorganization.sh
rm scripts/setup/download_reasoning_parser.sh
rm scripts/setup/run_claude_adapter.py
rm scripts/setup/test_*.sh

# Remove redundant test scripts
rm -rf scripts/testing/
rm scripts/test_deepseek_phase0.py
rm scripts/run_phase0_test.sh

# Remove old scripts
rm scripts/cleanup.sh scripts/cleanup_project.py
rm scripts/switch_model.sh
rm scripts/find_python.sh scripts/install_python*.sh
rm scripts/setup_venv.sh scripts/run_tests.sh
rm scripts/check_system_compatibility.sh

# Remove redundant docs
rm -rf docs/PHASE0_TEST_PLAN.md docs/README_TESTING.md
rm -rf docs/README_V3_EXTREME.md docs/REORGANIZATION.md
rm -rf docs/CLAUDE*.md docs/API_COMPLIANCE_REVIEW.md

# Remove superseded tests
rm tests/test_config_system.py tests/test_qwen_adapter.py

# Remove backup file
rm ~
```

### After Cleanup Structure
```
llm_adapter/
├── config/
│   ├── config.yaml
│   ├── config-adapter.yaml
│   ├── config-qwen36-27b.yaml
│   └── config-qwen36-35b.yaml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── TESTING.md
│   └── MEMORY_TROUBLESHOOTING.md (optional)
├── logs/
├── scripts/
│   ├── setup/
│   │   ├── llm_manager.py
│   │   └── hf_downloader.py (optional)
│   ├── deployment/ (optional)
│   ├── download_qwen36_27b.sh
│   ├── download_qwen36_awq.sh
│   ├── test_1m_context.py
│   └── test_qwen36.py
├── src/
│   └── llm_adapter/
├── QWEN36_1M_CONTEXT.md
├── TEST_SUITE_ENHANCEMENTS.md
├── README.md
├── pyproject.toml
└── test_all.py
```

**Clean, focused, production-ready structure! ✨**

---

## 🔍 Next Steps

1. Review this proposal
2. Confirm deletions
3. Execute cleanup commands
4. Update README.md with new structure
5. Git commit with message: "Clean up: Remove 45 outdated/redundant files"
