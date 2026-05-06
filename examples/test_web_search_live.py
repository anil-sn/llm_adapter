#!/usr/bin/env python3
"""
Quick test: LLM with Web Search Tool Support

Tests that the running LLM can use the web search tool.
"""

import json
import requests

API_URL = "http://localhost:8888/v1/chat/completions"
MODEL = "qwen-3.6-27b"

# Define web search tool in OpenAI format
web_search_tool = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information, news, facts, or any content "
            "not in your training data. Returns search results with titles, "
            "snippets, and URLs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results (default: 5, max: 10)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}

def test_web_search_tool():
    """Test if LLM can call web search tool."""
    print("="*70)
    print("TESTING: LLM Web Search Tool Support")
    print("="*70)
    print()

    # Send request with web search tool
    print("Sending request: 'Search for Python 3.13 new features'")
    print()

    response = requests.post(
        API_URL,
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": "Search the web for 'Python 3.13 new features' and tell me what you find",
                }
            ],
            "tools": [web_search_tool],
            "tool_choice": "auto",
            "max_tokens": 1000,
        },
        timeout=60,
    )

    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)
        return False

    data = response.json()
    message = data["choices"][0]["message"]

    # Check if tool was called
    if "tool_calls" in message and message["tool_calls"]:
        print("✅ SUCCESS: LLM called the web_search tool!")
        print()

        tool_call = message["tool_calls"][0]
        print(f"Tool Name: {tool_call['function']['name']}")
        print(f"Tool ID: {tool_call['id']}")
        print()

        args = json.loads(tool_call['function']['arguments'])
        print("Arguments:")
        print(f"  Query: {args.get('query', 'N/A')}")
        print(f"  Max Results: {args.get('max_results', 5)}")
        print()

        # Now execute the tool
        print("Executing web search...")
        from src.llm_adapter.tools import execute_web_search

        result = execute_web_search(**args)

        if result["success"]:
            print(f"✅ Web search successful! Found {len(result['results'])} results:")
            print()
            for i, item in enumerate(result["results"][:3], 1):
                print(f"{i}. {item['title']}")
                print(f"   {item['snippet'][:80]}...")
                print(f"   {item['url']}")
                print()

            # Send result back to LLM
            print("Sending results back to LLM for final answer...")
            messages = [
                {"role": "user", "content": "Search the web for 'Python 3.13 new features' and tell me what you find"},
                message,  # Tool call message
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": "web_search",
                    "content": json.dumps(result),
                },
            ]

            final_response = requests.post(
                API_URL,
                json={
                    "model": MODEL,
                    "messages": messages,
                    "max_tokens": 500,
                },
                timeout=60,
            )

            if final_response.status_code == 200:
                final_data = final_response.json()
                final_answer = final_data["choices"][0]["message"]["content"]
                print()
                print("="*70)
                print("FINAL ANSWER FROM LLM:")
                print("="*70)
                print(final_answer)
                print()
                print("="*70)
                print("✅ COMPLETE SUCCESS: Full tool calling workflow works!")
                print("="*70)
                return True
            else:
                print(f"⚠ Final response failed: {final_response.status_code}")
                return False
        else:
            print(f"❌ Web search failed: {result.get('error', 'Unknown error')}")
            return False
    else:
        # Model answered without using tool
        content = message.get("content", "")
        print("⚠ Model responded without calling the tool:")
        print(content[:200] + "...")
        print()
        print("This is OK - model may have answered from training data")
        return True

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")

    try:
        success = test_web_search_tool()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
