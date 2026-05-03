import type {
  ExportResponse,
  ItemsResponse,
  NativeStatusResponse,
  QueueStatusResponse,
  ResetResponse,
  SearchResponse,
  StatsResponse,
  TimelineResponse,
} from "../types";

const API_BASE = import.meta.env.VITE_API_BASE || "";

interface SearchOptions {
  limit?: number;
  daysBack?: number;
}

interface TimelineOptions {
  date?: string;
  platform?: string;
}

interface ItemListOptions {
  limit?: number;
  offset?: number;
  platform?: string;
  starredOnly?: boolean;
}

interface ItemPatchPayload {
  starred?: boolean;
  note?: string;
  tags?: string[];
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  return (await res.json()) as T;
}

export function searchFeed(query: string, { limit = 30, daysBack }: SearchOptions = {}): Promise<SearchResponse> {
  const params = new URLSearchParams();
  params.set("q", query);
  params.set("limit", String(limit));
  if (daysBack) params.set("days_back", String(daysBack));
  return apiFetch<SearchResponse>(`/api/search?${params.toString()}`);
}

export function fetchTimeline({ date, platform }: TimelineOptions = {}): Promise<TimelineResponse> {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (platform && platform !== "all") params.set("platform", platform);
  return apiFetch<TimelineResponse>(`/api/timeline?${params.toString()}`);
}

export function fetchStats(): Promise<StatsResponse> {
  return apiFetch<StatsResponse>("/api/stats");
}

export function fetchNativeStatus(): Promise<NativeStatusResponse> {
  return apiFetch<NativeStatusResponse>("/api/native/status");
}

export function fetchQueues(): Promise<QueueStatusResponse> {
  return apiFetch<QueueStatusResponse>("/api/queues/status");
}

export function listItems({
  limit = 50,
  offset = 0,
  platform,
  starredOnly = false,
}: ItemListOptions = {}): Promise<ItemsResponse> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (platform && platform !== "all") params.set("platform", platform);
  if (starredOnly) params.set("starred_only", "true");
  return apiFetch<ItemsResponse>(`/api/items?${params.toString()}`);
}

export function patchItem(itemId: string, payload: ItemPatchPayload): Promise<{ item: unknown }> {
  return apiFetch<{ item: unknown }>(`/api/items/${encodeURIComponent(itemId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function exportData(): Promise<ExportResponse> {
  return apiFetch<ExportResponse>("/api/admin/export", { method: "POST" });
}

export function resetData(): Promise<ResetResponse> {
  return apiFetch<ResetResponse>("/api/admin/reset?confirm=RESET", { method: "DELETE" });
}
