import httpx
import json
import time
import logging
from fastapi import Request, HTTPException, Response
from fastapi.responses import StreamingResponse, JSONResponse
from .config import settings
from .database import AsyncSessionLocal
from .models import RequestLog

logger = logging.getLogger("proxy")

async def log_request_to_db(
    method: str,
    url: str,
    request_body: str | None,
    system_prompt: str | None,
    status_code: int,
    duration: float,
    error_message: str | None = None
):
    async with AsyncSessionLocal() as session:
        try:
            log_entry = RequestLog(
                method=method,
                url=url,
                request_body=request_body,
                system_prompt=system_prompt,
                response_status=status_code,
                duration=duration,
                error_message=error_message
            )
            session.add(log_entry)
            await session.commit()
        except Exception as e:
            logger.error(f"Failed to log request: {e}")

def extract_system_prompt(body_json: dict) -> str | None:
    try:
        if "messages" in body_json and isinstance(body_json["messages"], list):
            for msg in body_json["messages"]:
                if msg.get("role") == "system":
                    return msg.get("content")
    except Exception:
        pass
    return None

async def forward_request(request: Request, path: str):
    start_time = time.time()
    
    # 1. Prepare Request
    url = f"{settings.DEEPSEEK_API_BASE}/{path}"
    if request.query_params:
        url += f"?{request.query_params}"
        
    headers = dict(request.headers)
    # Remove headers that might cause issues or should be reset
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    # Handle Authentication
    if settings.DEEPSEEK_API_KEY:
        headers["authorization"] = f"Bearer {settings.DEEPSEEK_API_KEY}"
    
    body = await request.body()
    try:
        body_json = json.loads(body) if body else {}
        system_prompt = extract_system_prompt(body_json)
    except json.JSONDecodeError:
        body_json = {}
        system_prompt = None

    # 2. Execute Request with Retry
    client = httpx.AsyncClient(timeout=settings.TIMEOUT_SECONDS)

    try:
        for attempt in range(settings.MAX_RETRIES):
            try:
                req = client.build_request(
                    request.method,
                    url,
                    headers=headers,
                    content=body
                )

                r = await client.send(req, stream=True)
                break
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                if attempt == settings.MAX_RETRIES - 1:
                    await client.aclose()
                    raise e
                continue

        # 3. Handle Response

        duration = time.time() - start_time

        await log_request_to_db(
            method=request.method,
            url=str(request.url),
            request_body=body.decode("utf-8", errors="ignore"),
            system_prompt=system_prompt,
            status_code=r.status_code,
            duration=duration
        )

        async def stream_generator():
            try:
                async for chunk in r.aiter_raw():
                    yield chunk
            finally:
                await r.aclose()
                await client.aclose()

        # Filter out hop-by-hop headers
        excluded_headers = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        response_headers = {k: v for k, v in r.headers.items() if k.lower() not in excluded_headers}

        return StreamingResponse(
            stream_generator(),
            status_code=r.status_code,
            headers=response_headers
        )

    except Exception as e:
        duration = time.time() - start_time
        await log_request_to_db(
            method=request.method,
            url=str(request.url),
            request_body=body.decode("utf-8", errors="ignore"),
            system_prompt=system_prompt,
            status_code=500,
            duration=duration,
            error_message=str(e)
        )
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"Upstream error: {str(e)}")

