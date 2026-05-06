# Final Cleanup Plan

**Date:** 2026-05-06  
**Status:** Ready to Execute

---

## ✅ What Will Be KEPT

### Configs (ALL 8 - Per User Request)
- ✅ `config/config.yaml` - Base config
- ✅ `config/config-adapter.yaml` - Adapter config
- ✅ `config/config-qwen36-27b.yaml` - Qwen 27B 1M context (ACTIVE)
- ✅ `config/config-qwen36-35b.yaml` - Qwen 35B 1M context (CURRENT)
- ✅ `config/config-qwen.yaml` - Qwen 122B (KEPT per request)
- ✅ `config/config-qwen-1m.yaml` - Qwen 122B 1M (KEPT per request)
- ✅ `config/config-nemotron.yaml` - Nemotron (KEPT per request)
- ✅ `config/config-emergency-4k.yaml` - Emergency (KEPT per request)
- ✅ `config/README.md` - Config documentation

### Core Application & Scripts
- ✅ `src/llm_adapter/` - Main application
- ✅ `pyproject.toml` - Dependencies
- ✅ `test_all.py` - Comprehensive test suite
- ✅ `scripts/setup/llm_manager.py` - LLM management
- ✅ `scripts/setup/hf_downloader.py` - Model downloader
- ✅ `scripts/test_1m_context.py` - 1M context tests
- ✅ `scripts/test_qwen36.py` - Qwen tests
- ✅ `scripts/download_qwen36_27b.sh` - Download script
- ✅ `scripts/download_qwen36_awq.sh` - Download script
- ✅ `scripts/deployment/` - Deployment utilities

### Documentation (Essential)
- ✅ `README.md` - Main documentation
- ✅ `QWEN36_1M_CONTEXT.md` - Qwen deployment guide
- ✅ `TEST_SUITE_ENHANCEMENTS.md` - Test documentation
- ✅ `docs/ARCHITECTURE.md` - System architecture
- ✅ `docs/TESTING.md` - Testing guide
- ✅ `docs/MEMORY_TROUBLESHOOTING.md` - Troubleshooting

### Logs
- ✅ `logs/` - Runtime logs (generated)

---

## ❌ What Will Be REMOVED (~41 files)

### Old Documentation (6 files)
- ❌ `CLEANUP_SUMMARY.md` - Old cleanup notes
- ❌ `QWEN36_DEPLOYMENT.md` - Superseded by QWEN36_1M_CONTEXT.md
- ❌ `VLLM_CUDA_COMPATIBILITY.md` - Issues resolved
- ❌ `CODE_OF_CONDUCT.md` - Not a public project
- ❌ `CONTRIBUTING.md` - Not a public project
- ❌ `~` - Backup file

### Old Docs (8 files)
- ❌ `docs/PHASE0_TEST_PLAN.md`
- ❌ `docs/README_TESTING.md`
- ❌ `docs/README_V3_EXTREME.md`
- ❌ `docs/REORGANIZATION.md`
- ❌ `docs/CLAUDE_CODE_COMPATIBILITY_FIXES.md`
- ❌ `docs/CLAUDE_CODE_SETUP.md`
- ❌ `docs/CLAUDE.md`
- ❌ `docs/API_COMPLIANCE_REVIEW.md`

### Setup Scripts (10 files)
- ❌ `scripts/setup/install_nvidia_driver.sh`
- ❌ `scripts/setup/install_nvidia_from_source.sh`
- ❌ `scripts/setup/upgrade_nvidia_driver.sh`
- ❌ `scripts/setup/test_cuda_install.sh`
- ❌ `scripts/setup/test_nvidia_prerequisites.sh`
- ❌ `scripts/setup/setup_claude_code_cli.sh`
- ❌ `scripts/setup/validate_claude_code_cli.sh`
- ❌ `scripts/setup/fix_paths_after_reorganization.sh`
- ❌ `scripts/setup/download_reasoning_parser.sh`
- ❌ `scripts/setup/run_claude_adapter.py`

### Testing Scripts (6 files + directory)
- ❌ `scripts/testing/` - Entire directory
- ❌ `scripts/test_deepseek_phase0.py`
- ❌ `scripts/run_phase0_test.sh`

### Old Utility Scripts (9 files)
- ❌ `scripts/cleanup.sh`
- ❌ `scripts/cleanup_project.py`
- ❌ `scripts/switch_model.sh`
- ❌ `scripts/find_python.sh`
- ❌ `scripts/install_python312.sh`
- ❌ `scripts/install_python312_pyenv.sh`
- ❌ `scripts/setup_venv.sh`
- ❌ `scripts/run_tests.sh`
- ❌ `scripts/check_system_compatibility.sh`

### Old Tests (2 files)
- ❌ `tests/test_config_system.py`
- ❌ `tests/test_qwen_adapter.py`

### Archive
- ❌ `archive/` - Entire deprecated directory

---

## 📊 Summary

| Category | Before | After | Removed |
|----------|--------|-------|---------|
| Root MD files | 9 | 3 | 6 |
| Config files | 9 | 9 | 0 ✅ KEPT ALL |
| Docs files | 11 | 3 | 8 |
| Setup scripts | 10 | 0 | 10 |
| Test scripts | 7 | 0 | 7 |
| Utility scripts | 9 | 0 | 9 |
| Old tests | 2 | 0 | 2 |
| **Total** | **~70** | **~29** | **~41** |

---

## 🎯 Final Structure After Cleanup

```
llm_adapter/
├── config/
│   ├── config.yaml
│   ├── config-adapter.yaml
│   ├── config-qwen36-27b.yaml  (active)
│   ├── config-qwen36-35b.yaml  (current)
│   ├── config-qwen.yaml        (kept)
│   ├── config-qwen-1m.yaml     (kept)
│   ├── config-nemotron.yaml    (kept)
│   ├── config-emergency-4k.yaml (kept)
│   └── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── TESTING.md
│   └── MEMORY_TROUBLESHOOTING.md
├── logs/
│   ├── nemo_gateway.log
│   └── vllm_replica_0.log
├── scripts/
│   ├── deployment/
│   │   ├── clean.sh
│   │   └── restart_gateway.sh
│   ├── setup/
│   │   ├── llm_manager.py
│   │   └── hf_downloader.py
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

**Clean, organized, production-ready! ✨**

---

## ✅ Ready to Execute

**Run:**
```bash
cd /home/asrirang/Coding/llm_adapter
./cleanup_execute.sh
```

**This will:**
1. Remove ~41 outdated/redundant files
2. Keep all 8 config files (per your request)
3. Preserve all essential application files
4. Show before/after file counts
5. Display final directory structure

**Safe to execute** - No essential files will be deleted!
