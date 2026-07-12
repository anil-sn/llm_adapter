import json
import requests

def test_vllm_direct_non_stream():
    print("=== Testing direct vLLM Non-Stream (port 8000) ===")
    url = "http://127.0.0.1:8000/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    
    tools = [
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
        }
    ]
    
    data = {
        "model": "llm-235b-moe",
        "messages": [
            {"role": "user", "content": "What day is it today?"}
        ],
        "tools": tools,
        "tool_choice": "auto",
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_vllm_direct_non_stream()
