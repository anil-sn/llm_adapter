#!/usr/bin/env python3
"""
LLM Orchestrator Gateway v7.0 - Model-Agnostic Router
- Multi-model support via layered configuration
- Protocol translation (Anthropic → OpenAI)
- Dynamic adapter routing
- Load balancing with pulse scheduling

Author: Anil Srirangapatna Nagesh
Version: 2.0
"""

import hashlib
import json
import uvicorn
import httpx
import logging
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pathlib import Path

from llm_adapter.adapters.factory import get_adapter
from llm_adapter.scheduler.pulse_scheduler import PulseScheduler
from llm_adapter.utils.config_loader import load_config, ConfigError
from llm_adapter.utils.user_detector import get_user_detector
from llm_adapter.middleware.auth import require_user_identification
from llm_adapter.middleware.api_key_auth import get_api_key_manager, require_api_key

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("llm-gateway")

# Project root is 3 levels up: gateway/ -> llm_adapter/ -> src/ -> project/
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Load configuration using layered config system
try:
    config = load_config(project_root=PROJECT_ROOT, validate=True)
    logger.info(f"Configuration loaded: {config['model']['id']}")
except ConfigError as e:
    logger.error(f"Configuration error: {e}")
    logger.error("Hint: Set LLM_CONFIG environment variable")
    raise
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise

app = FastAPI()
client = httpx.AsyncClient(timeout=None)

MAX_BATCH = config.get("inference", {}).get("max_num_seqs", 64)
scheduler = PulseScheduler(max_batch_size=MAX_BATCH)

SERVED_MODEL = config["model"].get("served_model_name", "nemotron-3-super")

# Initialize user detector
user_detector = get_user_detector(PROJECT_ROOT)
logger.info("User detection initialized")

# Initialize API key manager
api_key_manager = get_api_key_manager(PROJECT_ROOT)
logger.info("API key authentication initialized")

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
            "owned_by": "llm-adapter",
            "root": config["model"]["id"],
            "max_model_len": config["inference"]["max_model_len"],
        }]
    }

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_router(request: Request, path: str):
    # ENFORCE API KEY AUTHENTICATION for all POST requests (GPU access)
    # GET requests (like /v1/models) are allowed without authentication
    if request.method == "POST":
        try:
            user = require_api_key(request, api_key_manager)
            # Log the API key used for this request (for audit trail)
            api_key = None
            auth_header = request.headers.get("Authorization")
            if auth_header:
                if auth_header.startswith("Bearer "):
                    api_key = auth_header[7:].strip()
                else:
                    api_key = auth_header.strip()
            if not api_key:
                api_key = request.headers.get("X-API-Key") or request.headers.get("ANTHROPIC_API_KEY")

            # Store API key info in request state for logging
            if api_key:
                request.state.api_key = f"{api_key[:15]}..." if len(api_key) > 15 else api_key
            else:
                request.state.api_key = "localhost-bypass"
        except Exception as e:
            # Return error response (JSONResponse already imported at top)
            if hasattr(e, 'status_code') and hasattr(e, 'detail'):
                return JSONResponse(status_code=e.status_code, content=e.detail)
            else:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "authentication_required",
                        "message": "Valid API key required to access GPU",
                        "example": "curl -H 'Authorization: Bearer sk-your-key' ..."
                    }
                )
    else:
        # For GET requests, use optional detection (for logging purposes)
        user = user_detector.detect_user(request)

    replica_idx = 0
    body_bytes = await request.body()
    try:
        body = json.loads(body_bytes) if body_bytes else {}
    except (json.JSONDecodeError, ValueError):
        body = {}

    # Protocol detection
    is_anthropic = "messages" in path and "chat" not in path
    if is_anthropic:
        body["__protocol__"] = "anthropic"

    is_chat_path = "chat/completions" in path or "messages" in path

    if request.method == "POST" and is_chat_path:
        # Log request with API key info
        api_key_info = getattr(request.state, 'api_key', 'unknown')
        logger.info(f"[{user}] Request: {body.get('model', SERVED_MODEL)} - Stream: {body.get('stream', False)} - Key: {api_key_info}")

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
            logger.warning(f"[{user}] Validation Error: {e}")
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
            logger.error(f"[{user}] Adapter Error: {e}")
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
                        logger.error(f"[{user}] Stream Error: {e}")
                    finally:
                        pass
                return StreamingResponse(stream_wrapper(), media_type="text/event-stream")
            else:
                try:
                    resp = await client.post(target_url, json=refined_request, timeout=None)
                    if resp.status_code != 200:
                        logger.error(f"[{user}] vLLM Error: HTTP {resp.status_code} - {resp.text[:300]}")
                        # Log the exact request that caused the error
                        logger.error(f"Request body sent: {json.dumps(refined_request, indent=2)[:2000]}")
                        return JSONResponse(resp.json() if resp.text else {"error": resp.text}, status_code=resp.status_code)
                    resp_json = resp.json()
                    # Normalize response through adapter for proper format
                    resp_json = adapter.normalize_response(resp_json)
                    usage = resp_json.get("usage", {})
                    api_key_info = getattr(request.state, 'api_key', 'unknown')
                    logger.info(f"[{user}] Response: {usage.get('total_tokens', 0)} tokens - Input: {usage.get('prompt_tokens', 0)}, Output: {usage.get('completion_tokens', 0)} - Key: {api_key_info}")
                    return JSONResponse(resp_json)
                except Exception as e:
                    logger.error(f"[{user}] Request Error: {e}")
                    error_response = {
                        "type": "error",
                        "error": {
                            "type": "api_error",
                            "message": str(e)
                        }
                    }
                    return JSONResponse(error_response, status_code=500)
        except Exception as e:
            logger.error(f"[{user}] Unexpected Error: {e}")
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
        logger.error(f"[{user}] Passthrough Error: {e}")
        return JSONResponse({"error": f"Passthrough Error: {str(e)}"}, status_code=502)

if __name__ == "__main__":
    port = config["cluster"]["gateway_port"]
    logger.info(f"Nemo-Gateway ACTIVE on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
