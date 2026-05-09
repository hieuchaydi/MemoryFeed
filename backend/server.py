from __future__ import annotations

import asyncio
import collections
import logging
import os
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any
import json

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.capture import normalize_capture
from backend.crypto_at_rest import AtRestCrypto
from backend.debug import explain_archival_decision, explain_confidence_reduction, explain_duplicate_decision
from backend.import_export import export_payload, import_payload
from backend.indexer import IndexerService
from backend.interest import InterestEngine
from backend.benchmarking import evaluate_memory_retrieval, load_default_benchmark_dataset
from backend.logging_setup import configure_logging
from backend.maintenance import MaintenanceScheduler
from backend.memory_lifecycle import MemoryLifecycleEngine
from backend.llm_clients import provider_runtime_state
from backend.privacy_guard import verify_local_only_mode
from backend.models import (
    ArchiveItemsRequest,
    CaptureRequest,
    CaptureResponse,
    ImportPayload,
    ItemMetaPatch,
    ResurfaceRequest,
    SurfaceItemsRequest,
)
from backend.native_accel import status as native_status
from backend.runtime_config import is_localhost_client, load_runtime_config
from backend.searcher import Searcher
from backend.stats import build_reliability_dashboard
from backend.store import DATA_DIR, IMAGE_CACHE_DIR, Store
from backend.vision import VisionService
from memoryfeed.__version__ import __version__

configure_logging()
logger = logging.getLogger("memoryfeed")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

app = FastAPI(title="MemoryFeed", version=__version__)

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
interest = InterestEngine(store, searcher)
maintenance = MaintenanceScheduler(store)
lifecycle = MemoryLifecycleEngine(store.db_path)
capture_metrics = collections.defaultdict(lambda: {"attempts": 0, "stored": 0, "duplicates": 0, "missing": 0})
rate_limit_windows: dict[str, collections.deque[float]] = collections.defaultdict(collections.deque)
rate_limit_lock = asyncio.Lock()
crypto = AtRestCrypto()

if IMAGE_CACHE_DIR.exists() and not crypto.enabled:
    app.mount("/images", StaticFiles(directory=str(IMAGE_CACHE_DIR)), name="images")


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    value = authorization.strip()
    if not value.lower().startswith("bearer "):
        return None
    token = value[7:].strip()
    return token or None


def require_sensitive_access(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    cfg = load_runtime_config()
    if cfg.admin_token:
        provided = _extract_bearer_token(authorization)
        if provided != cfg.admin_token:
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid admin token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return

    if not is_localhost_client(request.client.host if request.client else None):
        raise HTTPException(
            status_code=403,
            detail="Admin endpoints are disabled for non-local clients when MEMORYFEED_ADMIN_TOKEN is not set",
        )


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    cfg = load_runtime_config()
    if cfg.api_rate_limit_enabled and request.url.path.startswith("/api/"):
        client_host = request.client.host if request.client else "unknown"
        key = f"{client_host}:{request.url.path}"
        now_mono = time.monotonic()
        async with rate_limit_lock:
            window = rate_limit_windows[key]
            while window and (now_mono - window[0]) > cfg.api_rate_limit_window_seconds:
                window.popleft()
            if len(window) >= cfg.api_rate_limit_requests:
                return Response(
                    content='{"detail":"rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                )
            window.append(now_mono)

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
    cfg = load_runtime_config()
    privacy_report = verify_local_only_mode(cfg)
    if not privacy_report.local_only_verified:
        logger.warning("local_only_guard_failed violations=%s", ",".join(privacy_report.violations))
    bind_host = os.getenv("MEMORYFEED_BIND_HOST", "").strip()
    if bind_host and bind_host not in {"127.0.0.1", "localhost", "::1"} and not cfg.admin_token:
        logger.warning(
            "public_bind_without_admin_token host=%s public_mode=%s",
            bind_host,
            cfg.public_mode,
        )
    await indexer.start()
    await vision.start()
    await maintenance.start()
    logger.info("MemoryFeed started data_dir=%s", store.db_path.parent)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await maintenance.stop()
    await vision.stop()
    await indexer.stop()


@app.post("/capture", response_model=CaptureResponse)
@app.post("/api/capture", response_model=CaptureResponse)
async def capture_item(payload: CaptureRequest) -> CaptureResponse:
    item = normalize_capture(payload)
    platform = item.get("platform") or "unknown"
    quality_flags = item.get("quality_flags") or []
    capture_metrics[platform]["attempts"] += 1
    if any(flag.startswith("missing_") for flag in quality_flags):
        capture_metrics[platform]["missing"] += 1

    logger.info(
        "capture_attempt %s",
        json.dumps(
            {
                "platform": platform,
                "canonical_url": item.get("canonical_url"),
                "post_id": item.get("post_id"),
                "quality_flags": quality_flags,
                "missing_fields": [f[8:] for f in quality_flags if f.startswith("missing_")],
                "selector_used": (item.get("capture_debug") or {}).get("selector_used", {}),
            },
            ensure_ascii=False,
        ),
    )

    inserted, item_id = await asyncio.to_thread(store.insert_item, item)

    if not inserted:
        capture_metrics[platform]["duplicates"] += 1
        logger.info("capture duplicate id=%s url=%s", item_id, item.get("url"))
        return CaptureResponse(status="duplicate", id=item_id)

    capture_metrics[platform]["stored"] += 1
    memory_id = lifecycle.ensure_memory_for_item(item)
    lifecycle.summarize_memory(memory_id, str(item.get("text_content") or ""))
    lifecycle.apply_decay_cycle(item)
    lifecycle.infer_relations_for_item(item)
    if item.get("image_urls"):
        await vision.enqueue(item["id"])
    else:
        await indexer.enqueue(item["id"])
    searcher.bump_data_epoch()
    asyncio.create_task(_warm_related_memories(item["id"]))
    logger.info("capture stored id=%s platform=%s", item["id"], item.get("platform"))
    return CaptureResponse(status="stored", id=item["id"])


async def _warm_related_memories(item_id: str) -> None:
    try:
        await interest.warm_related_for_item(item_id)
    except Exception:
        logger.exception("interest warm failed item_id=%s", item_id)


def _guess_media_type(name: str) -> str:
    lowered = name.lower()
    if lowered.endswith(".png.menc") or lowered.endswith(".png"):
        return "image/png"
    if lowered.endswith(".webp.menc") or lowered.endswith(".webp"):
        return "image/webp"
    if lowered.endswith(".gif.menc") or lowered.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


@app.get("/api/search")
async def search_api(
    q: str = Query(default="", min_length=0),
    limit: int = Query(default=10, ge=1, le=100),
    days_back: int | None = Query(default=None, ge=1, le=3650),
    debug: bool = Query(default=False),
) -> dict[str, Any]:
    results = await searcher.search(query=q, limit=limit, days_back=days_back, debug=debug)
    for row in results:
        lifecycle.reinforce_memory(f"mem:{row['id']}", delta=0.03)
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/memory/lifecycle/timeline")
async def memory_lifecycle_timeline_api(limit: int = Query(default=200, ge=1, le=2000)) -> dict[str, Any]:
    rows = await asyncio.to_thread(lifecycle.timeline, limit)
    return {"count": len(rows), "events": rows}


@app.get("/api/memory/visualization/heatmap")
async def memory_heatmap_api(bucket_days: int = Query(default=7, ge=1, le=90)) -> dict[str, Any]:
    rows = await asyncio.to_thread(lifecycle.heatmap, bucket_days)
    return {"count": len(rows), "bucket_days": bucket_days, "cells": rows}


@app.get("/api/memory/visualization/reinforcement-graph")
async def memory_reinforcement_graph_api(limit: int = Query(default=300, ge=1, le=3000)) -> dict[str, Any]:
    payload = await asyncio.to_thread(lifecycle.reinforcement_graph, limit)
    return payload


@app.get("/api/memory/visualization/aging")
async def memory_aging_api(limit: int = Query(default=200, ge=1, le=2000)) -> dict[str, Any]:
    rows = await asyncio.to_thread(lifecycle.aging, limit)
    return {"count": len(rows), "items": rows}


@app.get("/api/memory/retrieval-trace")
async def memory_retrieval_trace_api(
    q: str = Query(default="", min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    rows = await searcher.search(query=q, limit=limit, debug=True)
    traces = [
        {
            "id": row.get("id"),
            "score": row.get("score"),
            "trace": ((row.get("search_debug") or {}).get("retrieval_trace") or {}),
            "matched_fields": ((row.get("search_debug") or {}).get("matched_fields") or []),
        }
        for row in rows
    ]
    return {"query": q, "count": len(traces), "results": traces}


@app.post("/api/memory/lifecycle/decay")
async def memory_lifecycle_decay_api(limit: int = Query(default=500, ge=1, le=5000)) -> dict[str, Any]:
    items = await asyncio.to_thread(store.list_items, limit, 0, None, False)
    for item in items:
        lifecycle.apply_decay_cycle(item)
    forgotten = lifecycle.forget_eligible()
    return {"ok": True, "processed": len(items), "forgotten": forgotten}


@app.post("/api/memory/lifecycle/conflict")
async def memory_lifecycle_conflict_api(
    memory_id: str = Query(min_length=5),
    field_name: str = Query(min_length=1),
    value_a: str = Query(default=""),
    value_b: str = Query(default=""),
    confidence_a: float = Query(default=0.5, ge=0.0, le=1.0),
    confidence_b: float = Query(default=0.5, ge=0.0, le=1.0),
) -> dict[str, Any]:
    conflict_id = lifecycle.report_conflict(memory_id, field_name, value_a, value_b, confidence_a, confidence_b)
    return {"ok": True, "conflict_id": conflict_id}


@app.post("/api/memory/lifecycle/merge")
async def memory_lifecycle_merge_api(
    primary_memory_id: str = Query(min_length=5),
    secondary_memory_id: str = Query(min_length=5),
    confidence: float = Query(default=0.8, ge=0.0, le=1.0),
) -> dict[str, Any]:
    edge_id = lifecycle.merge_memories(primary_memory_id, secondary_memory_id, confidence=confidence)
    return {"ok": True, "edge_id": edge_id}


@app.get("/api/memory/benchmarks/evaluate")
async def memory_benchmark_evaluate_api(limit: int = Query(default=300, ge=10, le=5000)) -> dict[str, Any]:
    dataset = load_default_benchmark_dataset()
    rows = await searcher.search(query="memory", limit=min(50, limit), debug=False)
    evaluated = evaluate_memory_retrieval(dataset=dataset, retrieved_items=rows)
    return evaluated


@app.get("/api/timeline")
async def timeline_api(
    date_str: str | None = Query(default=None, alias="date"),
    platform: str | None = Query(default=None),
) -> dict[str, Any]:
    selected_date = date_str or date.today().isoformat()
    items = await asyncio.to_thread(store.all_for_timeline, selected_date, platform)
    return {"date": selected_date, "platform": platform, "count": len(items), "items": items}


@app.get("/api/feed")
async def active_feed_api(
    limit: int = Query(default=20, ge=1, le=100),
    mode: str = Query(default="default", pattern="^(default|focus|light|explore)$"),
) -> dict[str, Any]:
    items = await interest.active_feed(limit=limit, mode=mode)
    return {"mode": mode, "count": len(items), "items": items}


@app.post("/api/resurface")
async def resurface_context_api(payload: ResurfaceRequest) -> dict[str, Any]:
    items = await interest.resurface_context(
        context=payload.context,
        limit=payload.limit,
        source_item_id=payload.source_item_id,
        bump_heat=payload.bump_heat,
    )
    return {"count": len(items), "items": items}


@app.post("/api/feed/surfaced")
async def mark_surfaced_api(payload: SurfaceItemsRequest) -> dict[str, Any]:
    count = await interest.mark_surfaced(payload.item_ids)
    return {"ok": True, "updated": count}


@app.post("/api/feed/archive")
async def archive_feed_items_api(payload: ArchiveItemsRequest) -> dict[str, Any]:
    count = await interest.archive(payload.item_ids)
    searcher.bump_data_epoch()
    return {"ok": True, "updated": count}


@app.get("/api/stats")
async def stats_api() -> dict[str, Any]:
    payload = await asyncio.to_thread(store.stats)
    payload["capture_reliability"] = [
        {
            "platform": platform,
            "attempts": stats["attempts"],
            "stored": stats["stored"],
            "duplicates": stats["duplicates"],
            "missing_required": stats["missing"],
            "success_rate": round((stats["stored"] / stats["attempts"]) if stats["attempts"] else 0.0, 4),
            "fail_rate": round((1 - (stats["stored"] / stats["attempts"])) if stats["attempts"] else 0.0, 4),
        }
        for platform, stats in sorted(capture_metrics.items(), key=lambda item: item[0])
    ]
    payload["queues"] = {
        "indexer": indexer.status(),
        "vision": vision.status(),
    }
    payload["at_rest_encryption"] = {
        "enabled": crypto.state.enabled,
        "provider": crypto.state.provider,
    }
    cfg = load_runtime_config()
    guard = verify_local_only_mode(cfg)
    payload["privacy_guard"] = {
        "local_only_verified": guard.local_only_verified,
        "violations": guard.violations,
    }
    payload["reliability_dashboard"] = build_reliability_dashboard(
        await asyncio.to_thread(store.all_items),
        capture_reliability=payload["capture_reliability"],
        replay_history=[],
    )
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
        "providers": provider_runtime_state(),
    }


@app.get("/api/debug/item/{item_id}")
async def debug_item_api(item_id: str) -> dict[str, Any]:
    item = await asyncio.to_thread(store.get_item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        "item_id": item_id,
        "duplicate_decision": explain_duplicate_decision(item),
        "archival_decision": explain_archival_decision(item),
        "confidence_reduction": explain_confidence_reduction(item),
        "prompt_risk_score": item.get("prompt_risk_score"),
        "prompt_risk_reason": item.get("prompt_risk_reason"),
    }


@app.get("/api/debug/capture/latest")
async def latest_capture_debug_api() -> dict[str, Any]:
    rows = await asyncio.to_thread(store.list_items, 1, 0, None, False)
    if not rows:
        return {"ok": False, "item": None}
    item = dict(rows[0])
    item["selector_used"] = (item.get("capture_debug") or {}).get("selector_used", {})
    return {"ok": True, "item": item}


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
async def export_data_api(_auth: None = Depends(require_sensitive_access)) -> dict[str, Any]:
    items = await asyncio.to_thread(store.export_items)
    export_path = DATA_DIR / "exports"
    export_path.mkdir(parents=True, exist_ok=True)
    target = export_path / f"memoryfeed-export-{date.today().isoformat()}.json"
    target.write_text(json.dumps(export_payload(items), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "file": str(target), "count": len(items)}


@app.post("/api/admin/import")
async def import_data_api(payload: ImportPayload, _auth: None = Depends(require_sensitive_access)) -> dict[str, Any]:
    inserted = 0
    duplicates = 0
    enqueued_vision = 0
    enqueued_index = 0

    items, warnings = import_payload({"schema_version": payload.schema_version, "items": payload.items})
    for item in items:
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
        "warnings": warnings,
    }
    logger.info("admin import inserted=%s duplicates=%s", inserted, duplicates)
    return report


@app.delete("/api/admin/reset")
async def reset_data_api(
    confirm: str = Query(default=""),
    _auth: None = Depends(require_sensitive_access),
) -> dict[str, Any]:
    if confirm != "RESET":
        raise HTTPException(status_code=400, detail="Set confirm=RESET to proceed")
    await asyncio.to_thread(store.delete_all)
    searcher.bump_data_epoch()
    logger.warning("admin reset executed")
    return {"ok": True}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/images/{name}")
async def encrypted_image_proxy(name: str) -> Response:
    if "/" in name or "\\" in name:
        raise HTTPException(status_code=400, detail="invalid image name")
    enc_path = (store.db_path.parent / "images_enc" / name).resolve()
    if not enc_path.exists() or not enc_path.is_file():
        raise HTTPException(status_code=404, detail="image not found")
    if not crypto.enabled:
        return FileResponse(enc_path)
    try:
        payload = enc_path.read_bytes()
        data = crypto.decrypt_bytes(payload, aad=b"memoryfeed:image")
    except Exception:
        raise HTTPException(status_code=500, detail="cannot decrypt image")
    return StreamingResponse(iter([data]), media_type=_guess_media_type(name))


@app.get("/readyz")
async def readyz() -> dict[str, Any]:
    index_status = indexer.status()
    vision_status = vision.status()
    ready = bool(index_status.get("running")) and bool(vision_status.get("running"))
    return {
        "ready": ready,
        "queues": {
            "indexer": index_status,
            "vision": vision_status,
        },
        "providers": provider_runtime_state(),
    }


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
        "api": ["/api/search", "/api/feed", "/api/resurface", "/api/timeline", "/api/stats", "/api/native/status", "/api/perf"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.server:app", host="127.0.0.1", port=7749, reload=False)
