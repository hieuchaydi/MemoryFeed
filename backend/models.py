from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


Platform = Literal["facebook", "twitter", "youtube", "linkedin", "instagram", "unknown"]
ContentType = Literal["post", "video", "image", "article"]


class CaptureRequest(BaseModel):
    url: str = Field(min_length=3, max_length=2000)
    platform: Platform = "unknown"
    content_type: ContentType | None = None
    text_content: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    author: str | None = None
    dwell_seconds: float = Field(default=0.0, ge=0.0, le=3600.0)
    captured_at: datetime | None = None


class StoredItem(BaseModel):
    id: str
    url: str
    platform: Platform
    content_type: ContentType
    text_content: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    image_captions: list[str] = Field(default_factory=list)
    author: str | None = None
    captured_at: datetime
    dwell_seconds: float = 0.0
    embedding_done: bool = False
    vision_done: bool = False


class SearchResult(BaseModel):
    id: str
    url: str
    platform: Platform
    text_excerpt: str
    thumbnail: str | None = None
    author: str | None = None
    captured_at: datetime
    score: float


class TimelineItem(BaseModel):
    id: str
    url: str
    platform: Platform
    content_type: ContentType
    text_content: str | None = None
    image_urls: list[str] = Field(default_factory=list)
    author: str | None = None
    captured_at: datetime
    dwell_seconds: float = 0.0
    starred: bool = False
    note: str | None = None
    tags: list[str] = Field(default_factory=list)


class PlatformStat(BaseModel):
    key: str
    count: int


class StatsResponse(BaseModel):
    total: int
    by_platform: list[PlatformStat]
    by_type: list[PlatformStat]
    today: int


class CaptureResponse(BaseModel):
    status: Literal["stored", "duplicate"]
    id: str | None = None


class ItemMetaPatch(BaseModel):
    starred: bool | None = None
    note: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = None


class ImportPayload(BaseModel):
    items: list[dict]
