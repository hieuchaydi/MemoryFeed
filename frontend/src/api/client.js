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
