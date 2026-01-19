from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from .database import init_db
from .proxy import forward_request

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database on startup
    await init_db()
    yield

app = FastAPI(title="DeepSeek Proxy", lifespan=lifespan)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def proxy(request: Request, path: str):
    # Health check endpoint
    if path == "health":
        return {"status": "ok"}
        
    return await forward_request(request, path)
