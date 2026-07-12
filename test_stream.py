import json
import time
import httpx
import asyncio

async def main():
    url = "http://127.0.0.1:8888/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer EDGE-AI-ADMIN"
    }
    
    data = {
        "model": "llm-235b-moe",
        "messages": [
            {"role": "user", "content": "hi"}
        ],
        "stream": True
    }
    
    print("Sending request to gateway...")
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream("POST", url, headers=headers, json=data) as response:
                print(f"Response status: {response.status_code}")
                async for line in response.aiter_lines():
                    if line.strip():
                        elapsed = time.time() - start_time
                        print(f"[{elapsed:.2f}s] {line}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
