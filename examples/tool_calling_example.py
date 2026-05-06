#!/usr/bin/env python3
"""
Tool Calling Example

Demonstrates how to use web search, calculator, and other tools
with the LLM adapter. Shows the complete flow:
1. Send request with tool definitions
2. Model responds with tool calls
3. Execute tools
4. Send results back to model
5. Get final response

Author: Anil Srirangapatna Nagesh
Version: 1.0
"""

import sys
import json
import requests
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm_adapter.tools import web_search_tool, execute_web_search, get_builtin_tools
from llm_adapter.tools.builtin_tools import execute_tool


def send_request_with_tools(
    message: str,
    tools: list,
    base_url: str = "http://localhost:8888",
    model: str = "qwen-3.6-35b",
):
    """
    Send a request to the LLM with tool definitions.

    Args:
        message: User message
        tools: List of tool definitions
        base_url: API base URL
        model: Model name

    Returns:
        API response
    """
    print(f"\n{'='*60}")
    print(f"Sending request with {len(tools)} tools available")
    print(f"Message: {message}")
    print(f"{'='*60}\n")

    response = requests.post(
        f"{base_url}/v1/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "tools": tools,
            "tool_choice": "auto",  # Let model decide if tools are needed
            "max_tokens": 2000,
        },
    )

    return response.json()


def handle_tool_calls(response: dict) -> dict:
    """
    Execute tool calls from model response.

    Args:
        response: API response with tool calls

    Returns:
        Dictionary mapping tool_call_id to execution result
    """
    choice = response["choices"][0]
    message = choice["message"]

    # Check if model wants to call tools
    tool_calls = message.get("tool_calls", [])
    if not tool_calls:
        print("No tool calls requested by model\n")
        return {}

    print(f"\nModel requested {len(tool_calls)} tool call(s):")

    results = {}

    for tool_call in tool_calls:
        tool_id = tool_call["id"]
        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])

        print(f"\n  Tool: {function_name}")
        print(f"  Args: {arguments}")

        # Execute the tool
        if function_name == "web_search":
            result = execute_web_search(**arguments)
        else:
            # Try built-in tools
            result = execute_tool(function_name, **arguments)

        results[tool_id] = {
            "tool_call_id": tool_id,
            "role": "tool",
            "name": function_name,
            "content": json.dumps(result),
        }

        print(f"  Result: {result.get('success', False)}")

    return results


def send_tool_results(
    original_messages: list,
    tool_call_message: dict,
    tool_results: dict,
    base_url: str = "http://localhost:8888",
    model: str = "qwen-3.6-35b",
):
    """
    Send tool execution results back to the model.

    Args:
        original_messages: Original conversation messages
        tool_call_message: Message with tool calls from model
        tool_results: Executed tool results
        base_url: API base URL
        model: Model name

    Returns:
        Final model response
    """
    print(f"\n{'='*60}")
    print("Sending tool results back to model...")
    print(f"{'='*60}\n")

    # Build conversation with tool results
    messages = original_messages + [tool_call_message] + list(tool_results.values())

    response = requests.post(
        f"{base_url}/v1/chat/completions",
        json={
            "model": model,
            "messages": messages,
            "max_tokens": 2000,
        },
    )

    return response.json()


def main():
    """
    Main example demonstrating tool calling flow.
    """
    # Define available tools
    tools = [
        web_search_tool,  # Web search
        *get_builtin_tools(),  # Calculator and datetime
    ]

    # Convert to OpenAI format (if needed by your adapter)
    # from llm_adapter.adapters.claude_code.tools import convert_tools_to_openai
    # tools = convert_tools_to_openai(tools)

    # Example 1: Web search
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Web Search")
    print("=" * 60)

    user_message = "What are the latest developments in Python 3.13?"
    messages = [{"role": "user", "content": user_message}]

    # First request with tools
    response1 = send_request_with_tools(user_message, tools)

    # Handle tool calls
    tool_results = handle_tool_calls(response1)

    if tool_results:
        # Send tool results back
        tool_call_msg = response1["choices"][0]["message"]
        final_response = send_tool_results(messages, tool_call_msg, tool_results)

        print("\nFinal Response:")
        print(final_response["choices"][0]["message"]["content"])
    else:
        # No tools needed, model answered directly
        print("\nDirect Response:")
        print(response1["choices"][0]["message"]["content"])

    # Example 2: Calculator
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Calculator")
    print("=" * 60)

    user_message2 = "What is the square root of 12345?"
    messages2 = [{"role": "user", "content": user_message2}]

    response2 = send_request_with_tools(user_message2, tools)
    tool_results2 = handle_tool_calls(response2)

    if tool_results2:
        tool_call_msg2 = response2["choices"][0]["message"]
        final_response2 = send_tool_results(messages2, tool_call_msg2, tool_results2)

        print("\nFinal Response:")
        print(final_response2["choices"][0]["message"]["content"])

    # Example 3: Multiple tools
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Multiple Tools")
    print("=" * 60)

    user_message3 = "Search for 'artificial intelligence breakthroughs' and tell me what day it is today"
    messages3 = [{"role": "user", "content": user_message3}]

    response3 = send_request_with_tools(user_message3, tools)
    tool_results3 = handle_tool_calls(response3)

    if tool_results3:
        tool_call_msg3 = response3["choices"][0]["message"]
        final_response3 = send_tool_results(messages3, tool_call_msg3, tool_results3)

        print("\nFinal Response:")
        print(final_response3["choices"][0]["message"]["content"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
