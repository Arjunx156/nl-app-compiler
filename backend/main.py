"""
FastAPI application entry point.
Exposes health check and all pipeline/generation/eval routes.
"""

from __future__ import annotations

import os
import sys

# Force pure-Python protobuf implementation (avoids C extension crashes on Linux)
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import json
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import structlog

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
from utils.logger import setup_logging  # noqa: E402

setup_logging()
logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# DB startup
# ---------------------------------------------------------------------------
from storage.database import init_db  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await init_db()
    logger.info("Database initialised")
    yield
    logger.info("Shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="NL App Compiler",
    description="Natural Language → Production-Ready App Schema",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: allow localhost for dev + any Vercel deployment
_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
# Add deployed frontend URL from env (set in Railway)
_frontend_url = os.getenv("FRONTEND_URL", "")
if _frontend_url:
    _allowed_origins.append(_frontend_url)
    # Also allow without trailing slash
    _allowed_origins.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Generation routes
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str


@app.post("/api/generate")
async def generate(req: GenerateRequest, request: Request):
    """
    Stream pipeline progress via Server-Sent Events.
    Final event type='complete' carries the full CompilationResult.
    """
    from pipeline.orchestrator import PipelineOrchestrator
    from storage.repository import save_generation
    from utils.gemini_client import GeminiClient
    from utils.cost_tracker import CostTracker

    api_key = os.getenv("GEMINI_API_KEY", "")
    client = GeminiClient(api_key=api_key)
    tracker = CostTracker()
    orchestrator = PipelineOrchestrator(client=client, tracker=tracker)

    event_queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(event: dict) -> None:
        await event_queue.put(event)

    async def run_pipeline() -> None:
        try:
            result = await orchestrator.compile(req.prompt, progress_callback)
            await save_generation(result)
            await event_queue.put({"type": "complete", "data": result.model_dump()})
        except Exception as exc:
            logger.error("Pipeline failed", error=str(exc))
            await event_queue.put({"type": "error", "data": {"message": str(exc)}})
        finally:
            await event_queue.put(None)  # sentinel

    asyncio.create_task(run_pipeline())

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            item = await event_queue.get()
            if item is None:
                break
            yield {"event": item.get("type", "progress"), "data": json.dumps(item, default=str)}

    return EventSourceResponse(event_generator())


@app.get("/api/generations")
async def list_generations(limit: int = 50, offset: int = 0, search: str = ""):
    from storage.repository import list_generations as repo_list, search_generations
    if search:
        records = await search_generations(search)
    else:
        records = await repo_list(limit=limit, offset=offset)
    return [r.to_summary_dict() for r in records]


@app.get("/api/generations/{gen_id}")
async def get_generation(gen_id: str):
    from storage.repository import get_generation as repo_get
    record = await repo_get(gen_id)
    if not record:
        raise HTTPException(status_code=404, detail="Generation not found")
    return json.loads(record.full_result_json)


@app.get("/api/generations/{gen_id}/download")
async def download_generation(gen_id: str):
    """Serve JSON as a downloadable file (platform-safe, no /tmp dependency)."""
    from storage.repository import get_generation as repo_get
    record = await repo_get(gen_id)
    if not record:
        raise HTTPException(status_code=404, detail="Generation not found")
    return Response(
        content=record.full_result_json,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="compilation_{gen_id}.json"'
        },
    )


# ---------------------------------------------------------------------------
# Evaluation routes
# ---------------------------------------------------------------------------
@app.post("/api/eval/run-all")
async def eval_run_all(request: Request):
    from evaluation.runner import EvaluationRunner
    from utils.gemini_client import GeminiClient
    from utils.cost_tracker import CostTracker

    api_key = os.getenv("GEMINI_API_KEY", "")
    client = GeminiClient(api_key=api_key)
    tracker = CostTracker()
    runner = EvaluationRunner(client=client, tracker=tracker)

    event_queue: asyncio.Queue = asyncio.Queue()

    async def progress_cb(event: dict) -> None:
        await event_queue.put(event)

    async def run_all() -> None:
        try:
            results = await runner.run_all(progress_cb)
            await event_queue.put({"type": "complete", "data": results})
        except Exception as exc:
            await event_queue.put({"type": "error", "data": {"message": str(exc)}})
        finally:
            await event_queue.put(None)

    asyncio.create_task(run_all())

    async def gen():
        while True:
            if await request.is_disconnected():
                break
            item = await event_queue.get()
            if item is None:
                break
            yield {"event": item.get("type", "progress"), "data": json.dumps(item, default=str)}

    return EventSourceResponse(gen())


@app.post("/api/eval/run/{test_id}")
async def eval_run_single(test_id: str):
    from evaluation.runner import EvaluationRunner
    from utils.gemini_client import GeminiClient
    from utils.cost_tracker import CostTracker

    api_key = os.getenv("GEMINI_API_KEY", "")
    client = GeminiClient(api_key=api_key)
    tracker = CostTracker()
    runner = EvaluationRunner(client=client, tracker=tracker)
    result = await runner.run_single(test_id)
    return result


@app.get("/api/eval/results")
async def get_eval_results():
    from storage.repository import list_eval_results
    records = await list_eval_results()
    return records
