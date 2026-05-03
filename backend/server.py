from __future__ import annotations

import asyncio
import logging
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.capture import normalize_capture
from backend.indexer import IndexerService
from backend.models import CaptureRequest, CaptureResponse
from backend.native_accel import status as native_status
from backend.searcher import Searcher
from backend.store import IMAGE_CACHE_DIR, Store
from backend.vision import VisionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memoryfeed")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

app = FastAPI(title="MemoryFeed", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5173",
        "http://localhost:7749",
        "http://127.0.0.1",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:7749",
    ],
    allow_origin_regex=r"(chrome-extension://.*|moz-extension://.*)",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = Store()
indexer = IndexerService(store)
vision = VisionService(store, indexer)
searcher = Searcher(store, indexer)

if IMAGE_CACHE_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(IMAGE_CACHE_DIR)), name="images")


@app.on_event("startup")
async def startup_event() -> None:
    await indexer.start()
    await vision.start()
    logger.info("MemoryFeed started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await vision.stop()
    await indexer.stop()


@app.post("/capture", response_model=CaptureResponse)
@app.post("/api/capture", response_model=CaptureResponse)
async def capture_item(payload: CaptureRequest) -> CaptureResponse:
    item = normalize_capture(payload)
    inserted, item_id = await asyncio.to_thread(store.insert_item, item)

    if not inserted:
        return CaptureResponse(status="duplicate", id=item_id)

    if item.get("image_urls"):
        await vision.enqueue(item["id"])
    else:
        await indexer.enqueue(item["id"])
    return CaptureResponse(status="stored", id=item["id"])


@app.get("/api/search")
async def search_api(
    q: str = Query(default="", min_length=0),
    limit: int = Query(default=10, ge=1, le=100),
    days_back: int | None = Query(default=None, ge=1, le=3650),
) -> dict[str, Any]:
    results = await searcher.search(query=q, limit=limit, days_back=days_back)
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/timeline")
async def timeline_api(
    date_str: str | None = Query(default=None, alias="date"),
    platform: str | None = Query(default=None),
) -> dict[str, Any]:
    selected_date = date_str or date.today().isoformat()
    items = await asyncio.to_thread(store.all_for_timeline, selected_date, platform)
    return {"date": selected_date, "platform": platform, "count": len(items), "items": items}


@app.get("/api/stats")
async def stats_api() -> dict[str, Any]:
    return await asyncio.to_thread(store.stats)


@app.get("/api/native/status")
async def native_status_api() -> dict[str, str | bool]:
    return native_status()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/{full_path:path}")
async def frontend_spa(full_path: str) -> Any:
    if FRONTEND_DIST.exists():
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

    return {
        "message": "Frontend not built yet",
        "hint": "Run: cd frontend && npm run build",
        "api": ["/api/search", "/api/timeline", "/api/stats", "/api/native/status"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.server:app", host="127.0.0.1", port=7749, reload=False)
