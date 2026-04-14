#!/usr/bin/env python3
"""
Nemo-Gateway v6.0: Simple Direct Router
- Single model: nemotron-3-super
- No complex aliasing
- Direct passthrough with protocol translation
"""

import hashlib
import json
import uvicorn
import httpx
import yaml
import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pathlib import Path

from adapters.factory import get_adapter
from scheduler import PulseScheduler

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("nemo-gateway")

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yaml"

with open(CONFIG_FILE, "r") as f:
    config = yaml.safe_load(f)

app = FastAPI()
client = httpx.AsyncClient(timeout=None)

MAX_BATCH = config.get("inference", {}).get("max_num_seqs", 64)
scheduler = PulseScheduler(max_batch_size=MAX_BATCH)

SERVED_MODEL = config["model"].get("served_model_name", "nemotron-3-super")

@app.on_event("startup")
async def startup_event():
    scheduler.start()

REPLICAS = [
    f"http://127.0.0.1:{config['replicas']['base_port'] + i}"
    for i in range(config["replicas"]["count"])
]

@app.get("/v1/models")
async def list_models():
    import time
    return {
        "object": "list",
        "data": [{
            "id": SERVED_MODEL,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "nemo-orchestrator",
            "root": config["model"]["id"],
            "max_model_len": config["inference"]["max_model_len"],
        }]
    }

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_router(request: Request, path: str):
    replica_idx = 0
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes) if body_bytes else {}
    except:
        body = {}

    # Protocol detection
    is_anthropic = "messages" in path and "chat" not in path
    if is_anthropic:
        body["__protocol__"] = "anthropic"

    is_chat_path = "chat/completions" in path or "messages" in path

    if request.method == "POST" and is_chat_path:
        # Always use the single served model name for vLLM
        body["model"] = SERVED_MODEL

        # Use ClaudeAdapter for Anthropic requests, NemotronAdapter for OpenAI
        adapter = get_adapter("claude-haiku-4-5-20251001" if is_anthropic else SERVED_MODEL)

        vllm_path = "/v1/chat/completions" if is_anthropic else f"/{path.lstrip('/')}"
        target_url = f"{REPLICAS[replica_idx]}{vllm_path}"

        try:
            refined_request = adapter.build_request(body)

            # Log what we're sending to vLLM for debugging
            if "messages" not in refined_request:
                logger.error(f"WARNING: No messages in refined request! Original keys: {list(body.keys())}")
            is_streaming = body.get("stream", False)

        except ValueError as e:
            # Validation error - return Anthropic-formatted error
            logger.warning(f"Validation Error: {e}")
            error_response = {
                "type": "error",
                "error": {
                    "type": "invalid_request_error",
                    "message": str(e)
                }
            }
            return JSONResponse(error_response, status_code=400)
        except Exception as e:
            # Unexpected adapter error
            logger.error(f"Adapter Error: {e}")
            error_response = {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": str(e)
                }
            }
            return JSONResponse(error_response, status_code=500)

        # Process the request
        try:

            if is_streaming:
                async def stream_wrapper():
                    try:
                        async for chunk in adapter.stream(client, target_url, refined_request):
                            yield chunk
                    except Exception as e:
                        logger.error(f"Stream Error: {e}")
                    finally:
                        pass
                return StreamingResponse(stream_wrapper(), media_type="text/event-stream")
            else:
                try:
                    resp = await client.post(target_url, json=refined_request, timeout=None)
                    if resp.status_code != 200:
                        logger.error(f"vLLM Error: HTTP {resp.status_code} - {resp.text[:300]}")
                        # Log the exact request that caused the error
                        logger.error(f"Request body sent: {json.dumps(refined_request, indent=2)[:2000]}")
                        return JSONResponse(resp.json() if resp.text else {"error": resp.text}, status_code=resp.status_code)
                    resp_json = resp.json()
                    # Normalize response through adapter for proper format
                    resp_json = adapter.normalize_response(resp_json)
                    return JSONResponse(resp_json)
                except Exception as e:
                    logger.error(f"Request Error: {e}")
                    error_response = {
                        "type": "error",
                        "error": {
                            "type": "api_error",
                            "message": str(e)
                        }
                    }
                    return JSONResponse(error_response, status_code=500)
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            error_response = {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": str(e)
                }
            }
            return JSONResponse(error_response, status_code=500)

    # Direct passthrough
    target_url = f"{REPLICAS[replica_idx]}/{path}"
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    try:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body_bytes,
            params=request.query_params,
            timeout=30.0
        )
        return StreamingResponse(
            iter([response.content]),
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        logger.error(f"Passthrough Error: {e}")
        return JSONResponse({"error": f"Passthrough Error: {str(e)}"}, status_code=502)

if __name__ == "__main__":
    port = config["cluster"]["gateway_port"]
    logger.info(f"Nemo-Gateway ACTIVE on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
