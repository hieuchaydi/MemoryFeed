const API_BASE = import.meta.env.VITE_API_BASE || "";

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  return res.json();
}

export function searchFeed(query, { limit = 30, daysBack } = {}) {
  const params = new URLSearchParams();
  params.set("q", query);
  params.set("limit", String(limit));
  if (daysBack) params.set("days_back", String(daysBack));
  return apiFetch(`/api/search?${params.toString()}`);
}

export function fetchTimeline({ date, platform } = {}) {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  if (platform && platform !== "all") params.set("platform", platform);
  return apiFetch(`/api/timeline?${params.toString()}`);
}

export function fetchStats() {
  return apiFetch("/api/stats");
}

export function fetchNativeStatus() {
  return apiFetch("/api/native/status");
}

export function fetchQueues() {
  return apiFetch("/api/queues/status");
}

export function listItems({ limit = 50, offset = 0, platform, starredOnly = false } = {}) {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  if (platform && platform !== "all") params.set("platform", platform);
  if (starredOnly) params.set("starred_only", "true");
  return apiFetch(`/api/items?${params.toString()}`);
}

export function patchItem(itemId, payload) {
  return apiFetch(`/api/items/${encodeURIComponent(itemId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function exportData() {
  return apiFetch("/api/admin/export", { method: "POST" });
}

export function resetData() {
  return apiFetch("/api/admin/reset?confirm=RESET", { method: "DELETE" });
}
