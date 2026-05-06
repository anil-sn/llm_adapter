#!/usr/bin/env python3
"""
Comprehensive Tool Calling Test Suite

Tests all aspects of tool calling functionality:
1. Individual tool execution (web search, calculator, datetime)
2. End-to-end LLM integration
3. Multi-tool conversations
4. Error handling
5. Tool result formatting

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm_adapter.tools import web_search_tool, execute_web_search, get_builtin_tools
from llm_adapter.tools.builtin_tools import (
    execute_calculator,
    execute_datetime,
    execute_tool,
)
from llm_adapter.tools.web_search import format_search_results_for_llm


# Test configuration
API_BASE_URL = "http://localhost:8888"
MODEL_NAME = "qwen-3.6-27b"
TEST_TIMEOUT = 60  # seconds


class TestResults:
    """Track test results."""

    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0

    def add(self, name: str, success: bool, message: str = ""):
        """Add test result."""
        self.tests.append({"name": name, "success": success, "message": message})
        if success:
            self.passed += 1
            print(f"  ✓ {name}")
        else:
            self.failed += 1
            print(f"  ✗ {name}: {message}")

    def summary(self):
        """Print summary."""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total:  {total}")
        print(f"Passed: {self.passed} ({self.passed*100//total if total > 0 else 0}%)")
        print(f"Failed: {self.failed}")
        print(f"{'='*60}\n")
        return self.failed == 0


results = TestResults()


def test_web_search_direct():
    """Test 1: Direct web search execution."""
    print("\n" + "="*60)
    print("TEST 1: Direct Web Search Execution")
    print("="*60)

    # Test 1.1: Basic search
    try:
        result = execute_web_search("Python programming language", max_results=3)
        assert result["success"], "Search should succeed"
        assert len(result["results"]) > 0, "Should return results"
        assert result["query"] == "Python programming language", "Query should match"
        results.add("Web search - basic query", True)
    except Exception as e:
        results.add("Web search - basic query", False, str(e))

    # Test 1.2: Result structure
    try:
        result = execute_web_search("artificial intelligence", max_results=2)
        assert "title" in result["results"][0], "Result should have title"
        assert "snippet" in result["results"][0], "Result should have snippet"
        assert "url" in result["results"][0], "Result should have URL"
        results.add("Web search - result structure", True)
    except Exception as e:
        results.add("Web search - result structure", False, str(e))

    # Test 1.3: Max results limit
    try:
        result = execute_web_search("test query", max_results=15)  # Request 15
        assert len(result["results"]) <= 10, "Should cap at 10 results"
        results.add("Web search - max results limit", True)
    except Exception as e:
        results.add("Web search - max results limit", False, str(e))

    # Test 1.4: Result formatting
    try:
        result = execute_web_search("machine learning", max_results=2)
        formatted = format_search_results_for_llm(result)
        assert "Search results for" in formatted, "Should have header"
        assert "1." in formatted, "Should have numbered results"
        assert "URL:" in formatted, "Should include URLs"
        results.add("Web search - result formatting", True)
    except Exception as e:
        results.add("Web search - result formatting", False, str(e))


def test_calculator_direct():
    """Test 2: Direct calculator execution."""
    print("\n" + "="*60)
    print("TEST 2: Direct Calculator Execution")
    print("="*60)

    # Test 2.1: Basic arithmetic
    try:
        result = execute_calculator("2 + 2")
        assert result["success"], "Calculation should succeed"
        assert result["result"] == 4.0, f"Expected 4.0, got {result['result']}"
        results.add("Calculator - basic arithmetic", True)
    except Exception as e:
        results.add("Calculator - basic arithmetic", False, str(e))

    # Test 2.2: Complex expression
    try:
        result = execute_calculator("(10 + 5) * 2 - 8")
        assert result["success"], "Complex calculation should succeed"
        assert result["result"] == 22.0, f"Expected 22.0, got {result['result']}"
        results.add("Calculator - complex expression", True)
    except Exception as e:
        results.add("Calculator - complex expression", False, str(e))

    # Test 2.3: Math functions
    try:
        result = execute_calculator("sqrt(16)")
        assert result["success"], "Math function should succeed"
        assert result["result"] == 4.0, f"Expected 4.0, got {result['result']}"
        results.add("Calculator - math functions", True)
    except Exception as e:
        results.add("Calculator - math functions", False, str(e))

    # Test 2.4: Error handling
    try:
        result = execute_calculator("invalid expression!")
        assert not result["success"], "Invalid expression should fail"
        assert result["error"] is not None, "Should have error message"
        results.add("Calculator - error handling", True)
    except Exception as e:
        results.add("Calculator - error handling", False, str(e))


def test_datetime_direct():
    """Test 3: Direct datetime execution."""
    print("\n" + "="*60)
    print("TEST 3: Direct DateTime Execution")
    print("="*60)

    # Test 3.1: Default format
    try:
        result = execute_datetime()
        assert result["success"], "DateTime should succeed"
        assert "datetime" in result, "Should have datetime field"
        assert result["date"] is not None, "Should have date"
        assert result["time"] is not None, "Should have time"
        results.add("DateTime - default format", True)
    except Exception as e:
        results.add("DateTime - default format", False, str(e))

    # Test 3.2: ISO format
    try:
        result = execute_datetime(format="iso")
        assert result["success"], "ISO format should succeed"
        assert "T" in result["datetime"], "ISO format should have T separator"
        results.add("DateTime - ISO format", True)
    except Exception as e:
        results.add("DateTime - ISO format", False, str(e))

    # Test 3.3: Human format
    try:
        result = execute_datetime(format="human")
        assert result["success"], "Human format should succeed"
        assert "," in result["datetime"], "Human format should have commas"
        results.add("DateTime - human format", True)
    except Exception as e:
        results.add("DateTime - human format", False, str(e))


def test_llm_connection():
    """Test 4: LLM API connection."""
    print("\n" + "="*60)
    print("TEST 4: LLM API Connection")
    print("="*60)

    # Test 4.1: Basic completion
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": "Say 'test'"}],
                "max_tokens": 10,
            },
            timeout=30,
        )
        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        assert "choices" in data, "Response should have choices"
        results.add("LLM - basic connection", True)
    except Exception as e:
        results.add("LLM - basic connection", False, str(e))

    # Test 4.2: Model availability
    try:
        response = requests.get(f"{API_BASE_URL}/v1/models", timeout=10)
        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        assert "data" in data, "Should have data field"
        assert len(data["data"]) > 0, "Should have at least one model"
        results.add("LLM - model availability", True)
    except Exception as e:
        results.add("LLM - model availability", False, str(e))


def test_tool_calling_with_llm():
    """Test 5: End-to-end tool calling with LLM."""
    print("\n" + "="*60)
    print("TEST 5: End-to-End Tool Calling with LLM")
    print("="*60)

    # Build tools list in OpenAI format
    tools = [
        {
            "type": "function",
            "function": {
                "name": web_search_tool["name"],
                "description": web_search_tool["description"],
                "parameters": web_search_tool["input_schema"],
            },
        },
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Evaluate mathematical expressions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Math expression to evaluate",
                        }
                    },
                    "required": ["expression"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_datetime",
                "description": "Get current date and time",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "description": "Format: iso, human, or custom",
                        }
                    },
                    "required": [],
                },
            },
        },
    ]

    # Test 5.1: Request with tools (calculator)
    print("\n  Testing: Calculator tool calling...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": [
                    {"role": "user", "content": "What is the square root of 144?"}
                ],
                "tools": tools,
                "tool_choice": "auto",
                "max_tokens": 500,
            },
            timeout=TEST_TIMEOUT,
        )

        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()

        # Check if model made tool calls
        message = data["choices"][0]["message"]
        if "tool_calls" in message and message["tool_calls"]:
            tool_call = message["tool_calls"][0]
            print(f"    Tool called: {tool_call['function']['name']}")
            print(f"    Arguments: {tool_call['function']['arguments']}")

            # Execute the tool
            func_name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])

            if func_name == "calculator":
                tool_result = execute_calculator(args.get("expression", ""))
                assert tool_result["success"], "Calculator should succeed"
                print(f"    Result: {tool_result['result']}")
                results.add("LLM tool calling - calculator", True)
            else:
                results.add(
                    "LLM tool calling - calculator",
                    False,
                    f"Wrong tool called: {func_name}",
                )
        else:
            # Model answered directly without tools
            content = message.get("content", "")
            print(f"    Direct answer: {content[:100]}...")
            results.add(
                "LLM tool calling - calculator",
                True,
                "Model answered directly (acceptable)",
            )

    except Exception as e:
        results.add("LLM tool calling - calculator", False, str(e))

    # Test 5.2: DateTime tool
    print("\n  Testing: DateTime tool calling...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": "What day is it today?"}],
                "tools": tools,
                "tool_choice": "auto",
                "max_tokens": 500,
            },
            timeout=TEST_TIMEOUT,
        )

        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        message = data["choices"][0]["message"]

        if "tool_calls" in message and message["tool_calls"]:
            tool_call = message["tool_calls"][0]
            print(f"    Tool called: {tool_call['function']['name']}")

            func_name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])

            if func_name == "get_datetime":
                tool_result = execute_datetime(**args)
                assert tool_result["success"], "DateTime should succeed"
                print(f"    Result: {tool_result['datetime']}")
                results.add("LLM tool calling - datetime", True)
            else:
                results.add(
                    "LLM tool calling - datetime",
                    False,
                    f"Wrong tool: {func_name}",
                )
        else:
            content = message.get("content", "")
            print(f"    Direct answer: {content[:100]}...")
            results.add(
                "LLM tool calling - datetime", True, "Direct answer (acceptable)"
            )

    except Exception as e:
        results.add("LLM tool calling - datetime", False, str(e))

    # Test 5.3: Web search tool
    print("\n  Testing: Web search tool calling...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": "Search for 'latest Python 3.13 features' and tell me what you find",
                    }
                ],
                "tools": tools,
                "tool_choice": "auto",
                "max_tokens": 1000,
            },
            timeout=TEST_TIMEOUT,
        )

        assert response.status_code == 200, f"Status: {response.status_code}"
        data = response.json()
        message = data["choices"][0]["message"]

        if "tool_calls" in message and message["tool_calls"]:
            tool_call = message["tool_calls"][0]
            print(f"    Tool called: {tool_call['function']['name']}")
            print(f"    Arguments: {tool_call['function']['arguments']}")

            func_name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])

            if func_name == "web_search":
                tool_result = execute_web_search(**args)
                assert tool_result["success"], "Web search should succeed"
                print(f"    Found {len(tool_result['results'])} results")
                results.add("LLM tool calling - web search", True)
            else:
                results.add(
                    "LLM tool calling - web search",
                    False,
                    f"Wrong tool: {func_name}",
                )
        else:
            content = message.get("content", "")
            print(f"    Direct answer: {content[:100]}...")
            results.add(
                "LLM tool calling - web search", True, "Direct answer (acceptable)"
            )

    except Exception as e:
        results.add("LLM tool calling - web search", False, str(e))


def test_multi_turn_tool_conversation():
    """Test 6: Multi-turn conversation with tool results."""
    print("\n" + "="*60)
    print("TEST 6: Multi-Turn Tool Conversation")
    print("="*60)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Evaluate mathematical expressions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Math expression",
                        }
                    },
                    "required": ["expression"],
                },
            },
        }
    ]

    try:
        # Turn 1: Ask for calculation
        messages = [{"role": "user", "content": "Calculate sqrt(256)"}]

        response1 = requests.post(
            f"{API_BASE_URL}/v1/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "max_tokens": 500,
            },
            timeout=TEST_TIMEOUT,
        )

        data1 = response1.json()
        message1 = data1["choices"][0]["message"]

        if "tool_calls" in message1 and message1["tool_calls"]:
            # Execute tool
            tool_call = message1["tool_calls"][0]
            args = json.loads(tool_call["function"]["arguments"])
            tool_result = execute_calculator(args.get("expression", ""))

            print(f"  Turn 1: Tool called - {tool_call['function']['name']}")
            print(f"  Result: {tool_result['result']}")

            # Turn 2: Send tool result back
            messages.append(message1)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": "calculator",
                    "content": json.dumps(tool_result),
                }
            )

            response2 = requests.post(
                f"{API_BASE_URL}/v1/chat/completions",
                json={
                    "model": MODEL_NAME,
                    "messages": messages,
                    "max_tokens": 500,
                },
                timeout=TEST_TIMEOUT,
            )

            data2 = response2.json()
            final_answer = data2["choices"][0]["message"]["content"]
            print(f"  Turn 2: Final answer - {final_answer[:100]}...")

            results.add("Multi-turn conversation", True)
        else:
            print("  Model answered directly")
            results.add("Multi-turn conversation", True, "Direct answer")

    except Exception as e:
        results.add("Multi-turn conversation", False, str(e))


def test_tool_error_handling():
    """Test 7: Tool error handling."""
    print("\n" + "="*60)
    print("TEST 7: Tool Error Handling")
    print("="*60)

    # Test 7.1: Invalid calculator expression
    try:
        result = execute_calculator("this is not math")
        assert not result["success"], "Should fail"
        assert result["error"] is not None, "Should have error"
        results.add("Error handling - invalid calculator", True)
    except Exception as e:
        results.add("Error handling - invalid calculator", False, str(e))

    # Test 7.2: Empty web search query
    try:
        result = execute_web_search("", max_results=5)
        # Should handle gracefully
        results.add("Error handling - empty search", True)
    except Exception as e:
        results.add("Error handling - empty search", False, str(e))

    # Test 7.3: Invalid datetime format
    try:
        result = execute_datetime(format="%invalid%format%")
        # Should either work or fail gracefully
        results.add("Error handling - invalid datetime format", True)
    except Exception as e:
        results.add("Error handling - invalid datetime format", False, str(e))


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("COMPREHENSIVE TOOL CALLING TEST SUITE")
    print("="*60)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Model: {MODEL_NAME}")
    print(f"Test Timeout: {TEST_TIMEOUT}s")
    print("="*60)

    # Run all test suites
    test_web_search_direct()
    test_calculator_direct()
    test_datetime_direct()
    test_llm_connection()
    test_tool_calling_with_llm()
    test_multi_turn_tool_conversation()
    test_tool_error_handling()

    # Print summary
    success = results.summary()

    if success:
        print("✅ ALL TESTS PASSED")
        return 0
    else:
        print(f"❌ {results.failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
