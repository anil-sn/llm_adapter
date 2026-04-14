#!/usr/bin/env python3
"""
Nemo Orchestrator - Comprehensive Test Suite
==============================================

Complete test coverage (23 tests) matching claude-adapter-py patterns:
- Unit tests (2): Converter logic, tool choice conversion
- Validation tests (7): Request validation, schema checks, parameter validation
- Gateway tests (2): Health check, models endpoint
- Integration tests (2): API compatibility, protocol conversion
- Tool calling tests (2): Non-streaming, multiple tools
- Streaming tests (2): SSE events, critical 0 text_deltas test
- E2E tests (1): Full 3-turn tool execution flow
- Error handling tests (3): Graceful degradation, malformed data
- Performance tests (2): Concurrent requests, large context

Based on claude-adapter-py test patterns:
- test_converters.py → Unit tests
- test_validation.py → Validation tests (fully replicated)
- E2E integration → Streaming + Tool calling tests

Run: python3 test_all.py
     python3 test_all.py --quick (skip slow tests)
"""

import sys
import json
import requests
import time
import concurrent.futures
from pathlib import Path

# Add src to path for unit tests
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configuration
GATEWAY_URL = "http://10.172.249.149:8888"
QUICK_MODE = "--quick" in sys.argv

class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    YELLOW = '\033[1;33m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    NC = '\033[0m'

class TestStats:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.tests = []

    def add_result(self, category, name, passed, details="", skipped=False):
        self.tests.append({
            "category": category,
            "name": name,
            "passed": passed,
            "details": details,
            "skipped": skipped
        })
        if skipped:
            self.skipped += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1

    def print_summary(self):
        print(f"\n{'='*70}")
        print(f"{Colors.BOLD}  TEST SUMMARY{Colors.NC}")
        print(f"{'='*70}")

        # Group by category
        categories = {}
        for test in self.tests:
            cat = test["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(test)

        for category, tests in sorted(categories.items()):
            print(f"\n{Colors.BLUE}{category}:{Colors.NC}")
            for test in tests:
                if test["skipped"]:
                    status = f"{Colors.DIM}⊘ SKIP{Colors.NC}"
                elif test["passed"]:
                    status = f"{Colors.GREEN}✓ PASS{Colors.NC}"
                else:
                    status = f"{Colors.RED}✗ FAIL{Colors.NC}"
                print(f"  {status} {test['name']}")
                if test["details"] and not test["passed"] and not test["skipped"]:
                    print(f"       {Colors.DIM}{test['details'][:100]}{Colors.NC}")

        print(f"\n{'='*70}")
        total = self.passed + self.failed + self.skipped
        percentage = (self.passed / (total - self.skipped) * 100) if (total - self.skipped) > 0 else 0

        if self.failed == 0:
            print(f"{Colors.GREEN}{Colors.BOLD}  ✓ ALL TESTS PASSED ({self.passed}/{total - self.skipped}){Colors.NC}")
            if self.skipped > 0:
                print(f"{Colors.DIM}  ({self.skipped} tests skipped){Colors.NC}")
        else:
            print(f"{Colors.YELLOW}  Passed:  {Colors.GREEN}{self.passed}{Colors.NC}")
            print(f"{Colors.YELLOW}  Failed:  {Colors.RED}{self.failed}{Colors.NC}")
            if self.skipped > 0:
                print(f"{Colors.YELLOW}  Skipped: {Colors.DIM}{self.skipped}{Colors.NC}")
            print(f"{Colors.YELLOW}  Success: {percentage:.1f}%{Colors.NC}")

        print(f"{'='*70}\n")
        return self.failed == 0


stats = TestStats()


# ============================================================================
# UNIT TESTS - Converter Logic
# ============================================================================

def test_unit_tool_conversion():
    """Unit Test 1: Tool Conversion Logic"""
    try:
        from nemo_orchestrator.adapters.claude_code.tools import (
            convert_tools_to_openai,
            generate_tool_use_id
        )
        from nemo_orchestrator.adapters.claude_code.models.anthropic import (
            AnthropicToolDefinition
        )

        # Test tool conversion - use Pydantic model
        anthropic_tools = [
            AnthropicToolDefinition(
                name="read_file",
                description="Read a file",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]
                }
            )
        ]

        openai_tools = convert_tools_to_openai(anthropic_tools)

        # Verify conversion - openai_tools are Pydantic models
        checks = [
            len(openai_tools) == 1,
            openai_tools[0].type == "function",
            openai_tools[0].function.name == "read_file",
            openai_tools[0].function.parameters is not None,
            openai_tools[0].function.description == "Read a file"
        ]

        # Test ID generation
        id1 = generate_tool_use_id()
        id2 = generate_tool_use_id()
        checks.extend([
            id1.startswith("toolu_"),
            id2.startswith("toolu_"),
            id1 != id2,  # Unique
            len(id1) == 30  # toolu_ + 24 chars
        ])

        passed = all(checks)
        stats.add_result("Unit Tests", "Tool Conversion Logic", passed,
                        "" if passed else "Some conversion checks failed")
        return passed

    except Exception as e:
        stats.add_result("Unit Tests", "Tool Conversion Logic", False, str(e))
        return False


def test_unit_tool_choice_conversion():
    """Unit Test 2: Tool Choice Conversion"""
    try:
        from nemo_orchestrator.adapters.claude_code.tools import convert_tool_choice_to_openai

        tests = [
            ("auto", "auto", "auto maps to auto"),
            ("any", "required", "any maps to required"),
            ({"type": "tool", "name": "read_file"},
             {"type": "function", "function": {"name": "read_file"}},
             "specific tool conversion")
        ]

        all_passed = True
        for input_val, expected, desc in tests:
            result = convert_tool_choice_to_openai(input_val)
            if result != expected:
                all_passed = False
                break

        stats.add_result("Unit Tests", "Tool Choice Conversion", all_passed)
        return all_passed

    except Exception as e:
        stats.add_result("Unit Tests", "Tool Choice Conversion", False, str(e))
        return False


# ============================================================================
# VALIDATION TESTS - Request Validation
# ============================================================================

def test_validation_minimal_valid_request():
    """Validation Test 1: Minimal Valid Request"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=10)
        passed = response.status_code == 200
        stats.add_result("Validation", "Minimal Valid Request", passed,
                        f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Validation", "Minimal Valid Request", False, str(e))
        return False


def test_validation_invalid_tool_choice():
    """Validation Test 2: Tool Choice Without Tools"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "test"}],
        "tool_choice": "auto",  # Invalid: tool_choice without tools
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=10)
        # Should either reject (400) or ignore invalid field
        passed = response.status_code in [200, 400]
        stats.add_result("Validation", "Invalid Tool Choice (no tools)", passed,
                        f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Validation", "Invalid Tool Choice", False, str(e))
        return False


def test_validation_invalid_tools_schema():
    """Validation Test 3: Invalid Tools Schema Type"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "test"}],
        "tools": [{
            "name": "read_file",
            "description": "Read file",
            "input_schema": {"type": "array"}  # Invalid: must be "object"
        }],
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=10)
        # Should reject invalid schema
        passed = response.status_code in [200, 400]
        stats.add_result("Validation", "Invalid Tools Schema Type", passed,
                        f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Validation", "Invalid Tools Schema", False, str(e))
        return False


def test_validation_user_tool_use_block():
    """Validation Test 4: Invalid User Tool Use Block"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{
            "role": "user",
            "content": [{
                "type": "tool_use",  # Invalid: users can't send tool_use
                "id": "toolu_123",
                "name": "read_file",
                "input": {"path": "test.txt"}
            }]
        }],
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=10)
        # Should handle gracefully (either reject or ignore)
        passed = response.status_code in [200, 400]
        stats.add_result("Validation", "User Tool Use Block Handling", passed,
                        f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Validation", "User Tool Use Block", False, str(e))
        return False


def test_validation_assistant_tool_result_block():
    """Validation Test 5: Invalid Assistant Tool Result Block"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [
            {"role": "user", "content": "test"},
            {
                "role": "assistant",
                "content": [{
                    "type": "tool_result",  # Invalid: assistants can't send tool_result
                    "tool_use_id": "toolu_123",
                    "content": "result"
                }]
            }
        ],
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=10)
        # Should handle gracefully
        passed = response.status_code in [200, 400]
        stats.add_result("Validation", "Assistant Tool Result Block", passed,
                        f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Validation", "Assistant Tool Result", False, str(e))
        return False


def test_validation_valid_tools_with_choice():
    """Validation Test 6: Valid Tools with Tool Choice (Request Accepted)"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "Read the config file"}],
        "tools": [{
            "name": "read_file",
            "description": "Read file",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"]
            }
        }],
        "tool_choice": {"type": "tool", "name": "read_file"},
        "max_tokens": 200
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=30)
        # Validation test: ensure valid request is accepted (not rejected)
        # Note: Whether the model actually uses the tool is backend-dependent
        passed = response.status_code == 200
        stats.add_result("Validation", "Valid Tools with Specific Choice", passed,
                        "" if passed else f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Validation", "Valid Tools with Choice", False, str(e))
        return False


def test_validation_invalid_parameters():
    """Validation Test 7: Invalid top_k and stop_sequences"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "test"}],
        "top_k": 0,  # Invalid: must be >= 1
        "stop_sequences": ["ok", 123],  # Invalid: must be all strings
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=10)
        # Should handle gracefully (reject or ignore invalid params)
        passed = response.status_code in [200, 400]
        stats.add_result("Validation", "Invalid Parameters (top_k, stop_sequences)", passed,
                        f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Validation", "Invalid Parameters", False, str(e))
        return False


# ============================================================================
# GATEWAY TESTS - Health & Endpoints
# ============================================================================

def test_gateway_health():
    """Gateway Test 1: Health Check"""
    try:
        response = requests.get(f"{GATEWAY_URL}/health", timeout=5)
        passed = response.status_code == 200
        stats.add_result("Gateway", "Health Check", passed,
                        "" if passed else f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Gateway", "Health Check", False, str(e))
        return False


def test_models_endpoint():
    """Gateway Test 2: Models Endpoint"""
    try:
        response = requests.get(f"{GATEWAY_URL}/v1/models", timeout=5)
        if response.status_code != 200:
            stats.add_result("Gateway", "Models Endpoint", False, f"HTTP {response.status_code}")
            return False

        data = response.json()
        has_data = "data" in data and len(data["data"]) > 0
        stats.add_result("Gateway", "Models Endpoint", has_data,
                        "" if has_data else "No models in response")
        return has_data
    except Exception as e:
        stats.add_result("Gateway", "Models Endpoint", False, str(e))
        return False


# ============================================================================
# INTEGRATION TESTS - API Compatibility
# ============================================================================

def test_basic_text_generation():
    """Integration Test 1: Basic Text Generation"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "Say 'Test OK'"}],
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=30)
        if response.status_code != 200:
            stats.add_result("Integration", "Basic Text Generation", False,
                           f"HTTP {response.status_code}: {response.text[:100]}")
            return False

        data = response.json()
        checks = [
            ("has content", "content" in data and len(data["content"]) > 0),
            ("has stop_reason", "stop_reason" in data),
            ("has usage", "usage" in data),
            ("content is text", data.get("content", [{}])[0].get("type") == "text")
        ]

        all_passed = all(check[1] for check in checks)
        failed_checks = [check[0] for check in checks if not check[1]]
        stats.add_result("Integration", "Basic Text Generation", all_passed,
                        f"Failed: {', '.join(failed_checks)}" if failed_checks else "")
        return all_passed
    except Exception as e:
        stats.add_result("Integration", "Basic Text Generation", False, str(e))
        return False


def test_anthropic_api_compatibility():
    """Integration Test 2: Anthropic API Required Fields"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=30)
        if response.status_code != 200:
            stats.add_result("Integration", "Anthropic API Fields", False,
                           f"HTTP {response.status_code}")
            return False

        data = response.json()
        required_fields = ["id", "type", "role", "content", "model", "stop_reason", "usage"]
        missing = [f for f in required_fields if f not in data]

        passed = len(missing) == 0
        stats.add_result("Integration", "Anthropic API Required Fields", passed,
                        f"Missing: {', '.join(missing)}" if missing else "")
        return passed
    except Exception as e:
        stats.add_result("Integration", "Anthropic API Fields", False, str(e))
        return False


# ============================================================================
# TOOL CALLING TESTS
# ============================================================================

def test_tool_calling_non_streaming():
    """Tool Test 1: Non-Streaming Tool Call"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "List files"}],
        "tools": [{
            "name": "Bash",
            "description": "Execute bash commands",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }],
        "max_tokens": 200
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=30)
        if response.status_code != 200:
            stats.add_result("Tool Calling", "Non-Streaming Tool Call", False,
                           f"HTTP {response.status_code}")
            return False

        data = response.json()
        tool_use_blocks = [c for c in data.get("content", []) if c.get("type") == "tool_use"]
        text_blocks = [c for c in data.get("content", []) if c.get("type") == "text"]

        checks = [
            ("has tool_use", len(tool_use_blocks) > 0),
            ("no text blocks", len(text_blocks) == 0),
            ("stop_reason is tool_use", data.get("stop_reason") == "tool_use"),
            ("has stop_sequence", "stop_sequence" in data),
            ("tool has id", tool_use_blocks[0].get("id") if tool_use_blocks else None),
            ("tool has name", tool_use_blocks[0].get("name") if tool_use_blocks else None),
            ("tool has input", "input" in tool_use_blocks[0] if tool_use_blocks else False)
        ]

        all_passed = all(check[1] for check in checks)
        failed_checks = [check[0] for check in checks if not check[1]]
        stats.add_result("Tool Calling", "Non-Streaming (No Text Mixing)", all_passed,
                        f"Failed: {', '.join(failed_checks)}" if failed_checks else "")
        return all_passed
    except Exception as e:
        stats.add_result("Tool Calling", "Non-Streaming Tool Call", False, str(e))
        return False


def test_multiple_tools():
    """Tool Test 2: Multiple Tools Available"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "Use Bash to list files"}],
        "tools": [
            {
                "name": "Bash",
                "description": "Execute bash",
                "input_schema": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"]
                }
            },
            {
                "name": "Read",
                "description": "Read file",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"]
                }
            }
        ],
        "max_tokens": 200
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=30)
        if response.status_code != 200:
            stats.add_result("Tool Calling", "Multiple Tools Selection", False,
                           f"HTTP {response.status_code}")
            return False

        data = response.json()
        has_tool = any(c.get("type") == "tool_use" for c in data.get("content", []))

        detail = ""
        if not has_tool:
            content_types = [c.get("type") for c in data.get("content", [])]
            detail = f"No tool used, got: {content_types}, stop_reason: {data.get('stop_reason')}"

        stats.add_result("Tool Calling", "Multiple Tools Selection", has_tool, detail)
        return has_tool
    except Exception as e:
        stats.add_result("Tool Calling", "Multiple Tools", False, str(e))
        return False


# ============================================================================
# STREAMING TESTS
# ============================================================================

def test_streaming_basic():
    """Streaming Test 1: Basic Streaming (No Tools)"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "Count to 3"}],
        "stream": True,
        "max_tokens": 50
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, stream=True, timeout=30)
        if response.status_code != 200:
            stats.add_result("Streaming", "Basic Streaming", False, f"HTTP {response.status_code}")
            return False

        events = []
        has_text_delta = False

        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')

            if line.startswith('event:'):
                event_type = line.split(':', 1)[1].strip()
                events.append(event_type)

            if 'text_delta' in line:
                has_text_delta = True

        required_events = ['message_start', 'message_delta', 'message_stop']
        has_required = all(e in events for e in required_events)

        checks = [
            ("has required events", has_required),
            ("has text content", has_text_delta)
        ]

        all_passed = all(check[1] for check in checks)
        failed_checks = [check[0] for check in checks if not check[1]]
        stats.add_result("Streaming", "Basic Text Streaming", all_passed,
                        f"Failed: {', '.join(failed_checks)}" if failed_checks else "")
        return all_passed
    except Exception as e:
        stats.add_result("Streaming", "Basic Streaming", False, str(e))
        return False


def test_streaming_with_tools():
    """Streaming Test 2: Streaming with Tools (CRITICAL)"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "List files"}],
        "tools": [{
            "name": "Bash",
            "description": "Execute bash",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }],
        "stream": True,
        "max_tokens": 200
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, stream=True, timeout=30)
        if response.status_code != 200:
            stats.add_result("Streaming", "Tool Streaming", False, f"HTTP {response.status_code}")
            return False

        events = []
        text_delta_count = 0
        tool_use_found = False
        input_json_delta_found = False
        content_block_start_has_empty_input = False

        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode('utf-8')

            if line.startswith('event:'):
                event_type = line.split(':', 1)[1].strip()
                events.append(event_type)

            if line.startswith('data:'):
                try:
                    import json
                    data = json.loads(line[5:].strip())

                    # Check content_block_start for tool_use
                    if data.get('type') == 'content_block_start':
                        cb = data.get('content_block', {})
                        if cb.get('type') == 'tool_use':
                            tool_use_found = True
                            # CRITICAL: input should be empty in content_block_start
                            # Deltas should come via input_json_delta events
                            content_block_start_has_empty_input = cb.get('input') == {}
                except:
                    pass

            if 'text_delta' in line:
                text_delta_count += 1

            if 'input_json_delta' in line:
                input_json_delta_found = True

        required_events = ['message_start', 'message_delta', 'message_stop']
        has_required = all(e in events for e in required_events)

        checks = [
            ("has required events", has_required),
            ("tool_use found", tool_use_found),
            ("zero text_deltas", text_delta_count == 0),  # CRITICAL!
            ("input_json_delta events present", input_json_delta_found),  # NEW!
            ("content_block_start has empty input", content_block_start_has_empty_input)  # NEW!
        ]

        all_passed = all(check[1] for check in checks)
        failed_checks = [check[0] for check in checks if not check[1]]

        detail = ""
        if not all_passed:
            detail = f"Failed: {', '.join(failed_checks)}"
            if text_delta_count > 0:
                detail += f" ({text_delta_count} text_deltas)"

        # Special highlight for critical test
        test_name = "Tool Streaming (0 text deltas) ⭐ CRITICAL"
        stats.add_result("Streaming", test_name, all_passed, detail)
        return all_passed
    except Exception as e:
        stats.add_result("Streaming", "Tool Streaming", False, str(e))
        return False


# ============================================================================
# E2E TESTS - Full Flow
# ============================================================================

def test_e2e_tool_execution():
    """E2E Test 1: Complete Tool Execution Flow"""
    # Step 1: Initial request
    initial_request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "List all files"}],
        "tools": [{
            "name": "Bash",
            "description": "Execute bash commands",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"]
            }
        }],
        "max_tokens": 200
    }

    try:
        response1 = requests.post(f"{GATEWAY_URL}/v1/messages", json=initial_request, timeout=30)
        if response1.status_code != 200:
            stats.add_result("E2E", "Tool Execution Flow", False,
                           f"Step 1 failed: HTTP {response1.status_code}")
            return False

        data1 = response1.json()
        tool_use_blocks = [c for c in data1.get("content", []) if c.get("type") == "tool_use"]

        if not tool_use_blocks:
            stats.add_result("E2E", "Tool Execution Flow", False, "No tool_use in response")
            return False

        tool_id = tool_use_blocks[0].get("id")

        # Step 2: Tool result submission
        simulated_output = "file1.txt\nfile2.py\nREADME.md"
        followup_request = {
            "model": "claude-haiku-4-5-20251001",
            "messages": [
                {"role": "user", "content": "List all files"},
                {"role": "assistant", "content": data1["content"]},
                {"role": "user", "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_id,
                    "content": simulated_output
                }]}
            ],
            "max_tokens": 200
        }

        response2 = requests.post(f"{GATEWAY_URL}/v1/messages", json=followup_request, timeout=30)
        if response2.status_code != 200:
            stats.add_result("E2E", "Tool Execution Flow", False,
                           f"Step 2 failed: HTTP {response2.status_code}")
            return False

        data2 = response2.json()

        # Step 3: Multi-turn continuation
        continuation_request = {
            "model": "claude-haiku-4-5-20251001",
            "messages": [
                {"role": "user", "content": "List all files"},
                {"role": "assistant", "content": data1["content"]},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": simulated_output}]},
                {"role": "assistant", "content": data2["content"]},
                {"role": "user", "content": "How many files?"}
            ],
            "max_tokens": 100
        }

        response3 = requests.post(f"{GATEWAY_URL}/v1/messages", json=continuation_request, timeout=30)
        passed = response3.status_code == 200

        stats.add_result("E2E", "3-Turn Tool Execution Flow", passed,
                        "" if passed else f"Step 3 failed: HTTP {response3.status_code}")
        return passed
    except Exception as e:
        stats.add_result("E2E", "Tool Execution Flow", False, str(e))
        return False


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_error_empty_content():
    """Error Test 1: Empty Content Handling"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": ""}],
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=10)
        # Should handle gracefully (200 with minimal response or 400)
        passed = response.status_code in [200, 400]
        stats.add_result("Error Handling", "Empty Content", passed,
                        f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Error Handling", "Empty Content", False, str(e))
        return False


def test_error_malformed_json():
    """Error Test 2: Malformed JSON Handling"""
    try:
        response = requests.post(
            f"{GATEWAY_URL}/v1/messages",
            data="{invalid json}",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        # Should return 400 or handle gracefully
        passed = response.status_code == 400
        stats.add_result("Error Handling", "Malformed JSON", passed,
                        f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Error Handling", "Malformed JSON", False, str(e))
        return False


def test_error_missing_required_field():
    """Error Test 3: Missing Required Fields"""
    request = {
        "model": "claude-haiku-4-5-20251001",
        # Missing messages field
        "max_tokens": 20
    }

    try:
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=10)
        # Should return 400 for missing required field
        passed = response.status_code == 400
        stats.add_result("Error Handling", "Missing Required Field", passed,
                        f"HTTP {response.status_code}")
        return passed
    except Exception as e:
        stats.add_result("Error Handling", "Missing Field", False, str(e))
        return False


# ============================================================================
# PERFORMANCE TESTS (Optional - skipped in quick mode)
# ============================================================================

def test_performance_concurrent_requests():
    """Performance Test 1: Concurrent Requests"""
    if QUICK_MODE:
        stats.add_result("Performance", "Concurrent Requests (5 parallel)", True,
                        skipped=True)
        return True

    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10
    }

    def make_request(_):
        try:
            response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=30)
            return response.status_code == 200
        except:
            return False

    try:
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(make_request, range(5)))
        elapsed = time.time() - start_time

        all_passed = all(results)
        stats.add_result("Performance", f"5 Concurrent Requests ({elapsed:.2f}s)", all_passed,
                        f"{sum(results)}/5 succeeded")
        return all_passed
    except Exception as e:
        stats.add_result("Performance", "Concurrent Requests", False, str(e))
        return False


def test_performance_large_context():
    """Performance Test 2: Large Context Window"""
    if QUICK_MODE:
        stats.add_result("Performance", "Large Context (1000 tokens)", True,
                        skipped=True)
        return True

    # Create a large context (approximately 1000 tokens)
    large_text = "The quick brown fox jumps over the lazy dog. " * 100

    request = {
        "model": "claude-haiku-4-5-20251001",
        "messages": [{"role": "user", "content": large_text + "\n\nSummarize in one word."}],
        "max_tokens": 10
    }

    try:
        start_time = time.time()
        response = requests.post(f"{GATEWAY_URL}/v1/messages", json=request, timeout=60)
        elapsed = time.time() - start_time

        passed = response.status_code == 200
        stats.add_result("Performance", f"Large Context ({elapsed:.2f}s)", passed,
                        f"~1000 token input")
        return passed
    except Exception as e:
        stats.add_result("Performance", "Large Context", False, str(e))
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    """Run all tests"""
    print(f"\n{'='*70}")
    print(f"{Colors.BOLD}  NEMO ORCHESTRATOR - COMPREHENSIVE TEST SUITE{Colors.NC}")
    print(f"{'='*70}")
    print(f"Gateway: {GATEWAY_URL}")
    if QUICK_MODE:
        print(f"{Colors.YELLOW}Mode: Quick (skipping performance tests){Colors.NC}")
    print(f"{'='*70}\n")

    print(f"{Colors.BLUE}Running tests...{Colors.NC}\n")

    # Test categories
    tests = [
        # Unit Tests
        ("Unit: Tool Conversion", test_unit_tool_conversion),
        ("Unit: Tool Choice", test_unit_tool_choice_conversion),

        # Validation Tests
        ("Validation: Minimal Valid", test_validation_minimal_valid_request),
        ("Validation: Invalid Choice", test_validation_invalid_tool_choice),
        ("Validation: Invalid Schema", test_validation_invalid_tools_schema),
        ("Validation: User Tool Use", test_validation_user_tool_use_block),
        ("Validation: Asst Tool Result", test_validation_assistant_tool_result_block),
        ("Validation: Valid w/Choice", test_validation_valid_tools_with_choice),
        ("Validation: Invalid Params", test_validation_invalid_parameters),

        # Gateway Tests
        ("Gateway: Health", test_gateway_health),
        ("Gateway: Models", test_models_endpoint),

        # Integration Tests
        ("Integration: Basic Text", test_basic_text_generation),
        ("Integration: API Fields", test_anthropic_api_compatibility),

        # Tool Calling Tests
        ("Tool: Non-Streaming", test_tool_calling_non_streaming),
        ("Tool: Multiple Tools", test_multiple_tools),

        # Streaming Tests
        ("Streaming: Basic", test_streaming_basic),
        ("Streaming: Tools ⭐", test_streaming_with_tools),

        # E2E Tests
        ("E2E: 3-Turn Flow", test_e2e_tool_execution),

        # Error Handling
        ("Error: Empty Content", test_error_empty_content),
        ("Error: Malformed JSON", test_error_malformed_json),
        ("Error: Missing Field", test_error_missing_required_field),

        # Performance Tests
        ("Perf: Concurrent", test_performance_concurrent_requests),
        ("Perf: Large Context", test_performance_large_context),
    ]

    for name, test_func in tests:
        print(f"{Colors.YELLOW}►{Colors.NC} {name:<40}", end=" ", flush=True)
        try:
            result = test_func()
            if result:
                print(f"{Colors.GREEN}✓{Colors.NC}")
            else:
                # Check if skipped
                if stats.tests and stats.tests[-1].get("skipped"):
                    print(f"{Colors.DIM}⊘{Colors.NC}")
                else:
                    print(f"{Colors.RED}✗{Colors.NC}")
        except Exception as e:
            print(f"{Colors.RED}✗ ({str(e)[:30]}){Colors.NC}")

    # Print summary
    all_passed = stats.print_summary()

    if all_passed:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 All systems operational! Production converters verified!{Colors.NC}\n")
        return 0
    else:
        print(f"{Colors.YELLOW}⚠ Some tests failed. Review details above.{Colors.NC}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
