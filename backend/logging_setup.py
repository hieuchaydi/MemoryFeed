from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from backend.store import DATA_DIR

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }
        for field in ("event", "request_id", "method", "path", "status_code", "duration_ms", "error_code"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level_name = os.getenv("MEMORY_LOG_LEVEL", os.getenv("MEMORYFEED_LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    log_format = os.getenv("MEMORYFEED_LOG_FORMAT", "plain").lower()
    try:
        max_mb = int(os.getenv("MEMORY_LOG_MAX_MB", "50").strip())
    except Exception:
        max_mb = 50
    max_mb = max(5, min(500, max_mb))
    try:
        rotation_count = int(os.getenv("MEMORY_LOG_ROTATION_COUNT", "5").strip())
    except Exception:
        rotation_count = 5
    rotation_count = max(1, min(50, rotation_count))

    logs_dir = DATA_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path(os.getenv("MEMORYFEED_LOG_FILE", str(logs_dir / "memoryfeed.log")))

    if log_format == "json":
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_mb * 1024 * 1024,
        backupCount=rotation_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(file_handler)

    for uvicorn_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(uvicorn_name)
        uv_logger.setLevel(log_level)
    for noisy_logger in ("httpx", "httpcore"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    _CONFIGURED = True
