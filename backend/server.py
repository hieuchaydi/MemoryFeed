from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any
import json

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.capture import normalize_capture
from backend.indexer import IndexerService
from backend.logging_setup import configure_logging
from backend.models import CaptureRequest, CaptureResponse, ImportPayload, ItemMetaPatch
from backend.native_accel import status as native_status
from backend.searcher import Searcher
from backend.store import DATA_DIR, IMAGE_CACHE_DIR, Store
from backend.vision import VisionService

configure_logging()
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


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "request_failed method=%s path=%s request_id=%s duration_ms=%s",
            request.method,
            request.url.path,
            request_id,
            elapsed_ms,
        )
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["x-request-id"] = request_id
    if request.url.path != "/healthz":
        logger.info(
            "request method=%s path=%s status=%s request_id=%s duration_ms=%s",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
            elapsed_ms,
        )
    return response


@app.on_event("startup")
async def startup_event() -> None:
    await indexer.start()
    await vision.start()
    logger.info("MemoryFeed started data_dir=%s", store.db_path.parent)


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
        logger.info("capture duplicate id=%s url=%s", item_id, item.get("url"))
        return CaptureResponse(status="duplicate", id=item_id)

    if item.get("image_urls"):
        await vision.enqueue(item["id"])
    else:
        await indexer.enqueue(item["id"])
    searcher.bump_data_epoch()
    logger.info("capture stored id=%s platform=%s", item["id"], item.get("platform"))
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
    payload = await asyncio.to_thread(store.stats)
    payload["queues"] = {
        "indexer": indexer.status(),
        "vision": vision.status(),
    }
    return payload


@app.get("/api/native/status")
async def native_status_api() -> dict[str, str | bool]:
    return native_status()


@app.get("/api/queues/status")
async def queue_status_api() -> dict[str, Any]:
    return {
        "indexer": indexer.status(),
        "vision": vision.status(),
    }


@app.get("/api/perf")
async def perf_api() -> dict[str, Any]:
    return {
        "searcher": searcher.perf_stats(),
        "indexer": indexer.status(),
        "vision": vision.status(),
        "native": native_status(),
    }


@app.get("/api/items")
async def list_items_api(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    platform: str | None = Query(default=None),
    starred_only: bool = Query(default=False),
) -> dict[str, Any]:
    items = await asyncio.to_thread(store.list_items, limit, offset, platform, starred_only)
    return {"count": len(items), "items": items}


@app.patch("/api/items/{item_id}")
async def patch_item_api(item_id: str, payload: ItemMetaPatch) -> dict[str, Any]:
    updated = await asyncio.to_thread(
        store.update_item_metadata,
        item_id,
        payload.starred,
        payload.note,
        payload.tags,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")
    searcher.bump_data_epoch()
    return {"item": updated}


@app.post("/api/admin/export")
async def export_data_api() -> dict[str, Any]:
    items = await asyncio.to_thread(store.export_items)
    export_path = DATA_DIR / "exports"
    export_path.mkdir(parents=True, exist_ok=True)
    target = export_path / f"memoryfeed-export-{date.today().isoformat()}.json"
    target.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "file": str(target), "count": len(items)}


@app.post("/api/admin/import")
async def import_data_api(payload: ImportPayload) -> dict[str, Any]:
    inserted = 0
    duplicates = 0
    enqueued_vision = 0
    enqueued_index = 0

    for item in payload.items:
        ok, item_id = await asyncio.to_thread(store.insert_item, item)
        if ok:
            inserted += 1
            if item.get("image_urls"):
                await vision.enqueue(item["id"])
                enqueued_vision += 1
            else:
                await indexer.enqueue(item["id"])
                enqueued_index += 1
        else:
            duplicates += 1
    if inserted:
        searcher.bump_data_epoch()

    report = {
        "ok": True,
        "inserted": inserted,
        "duplicates": duplicates,
        "enqueued_vision": enqueued_vision,
        "enqueued_index": enqueued_index,
    }
    logger.info("admin import inserted=%s duplicates=%s", inserted, duplicates)
    return report


@app.delete("/api/admin/reset")
async def reset_data_api(confirm: str = Query(default="")) -> dict[str, Any]:
    if confirm != "RESET":
        raise HTTPException(status_code=400, detail="Set confirm=RESET to proceed")
    await asyncio.to_thread(store.delete_all)
    searcher.bump_data_epoch()
    logger.warning("admin reset executed")
    return {"ok": True}


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
        "api": ["/api/search", "/api/timeline", "/api/stats", "/api/native/status", "/api/perf"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.server:app", host="127.0.0.1", port=7749, reload=False)
