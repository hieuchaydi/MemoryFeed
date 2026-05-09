const API_BASE = "http://localhost:7749";
const BADGE_KEY = "memoryfeed_captured_today";
const DATE_KEY = "memoryfeed_badge_date";
const OUTBOX_KEY = "memoryfeed_capture_outbox";
const OUTBOX_LIMIT = 200;
const ext = typeof browser !== "undefined" ? browser : chrome;

async function postCapture(payload) {
  let lastErr = null;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const res = await fetch(`${API_BASE}/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error(`Capture failed with ${res.status}`);
      }
      return res.json();
    } catch (error) {
      lastErr = error;
      await new Promise((resolve) => setTimeout(resolve, Math.min(2000, 250 * (2 ** (attempt - 1)))));
    }
  }
  throw lastErr || new Error("Capture failed");
}

function todayLocal() {
  const now = new Date();
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

async function incrementBadge() {
  const today = todayLocal();
  const data = await ext.storage.local.get([BADGE_KEY, DATE_KEY]);
  let count = Number(data[BADGE_KEY] || 0);
  const storedDate = data[DATE_KEY];

  if (storedDate !== today) {
    count = 0;
  }
  count += 1;

  await ext.storage.local.set({ [BADGE_KEY]: count, [DATE_KEY]: today });
  ext.action.setBadgeBackgroundColor({ color: "#2563eb" });
  ext.action.setBadgeText({ text: String(count) });
}

async function syncBadgeFromBackend() {
  try {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) return;
    const data = await res.json();
    const todayCount = Number(data.today || 0);
    await ext.storage.local.set({ [BADGE_KEY]: todayCount, [DATE_KEY]: todayLocal() });
    ext.action.setBadgeBackgroundColor({ color: "#2563eb" });
    ext.action.setBadgeText({ text: todayCount > 0 ? String(todayCount) : "" });
  } catch (_) {
    // Backend may not be running; keep extension silent.
  }
}

async function getOutbox() {
  const data = await ext.storage.local.get([OUTBOX_KEY]);
  const rows = data[OUTBOX_KEY];
  return Array.isArray(rows) ? rows : [];
}

async function enqueueOutbox(payload, reason) {
  const rows = await getOutbox();
  rows.push({
    payload,
    reason: String(reason || "unknown"),
    created_at: new Date().toISOString(),
    attempts: 0,
  });
  const trimmed = rows.slice(-OUTBOX_LIMIT);
  await ext.storage.local.set({ [OUTBOX_KEY]: trimmed });
}

async function flushOutbox(limit = 20) {
  const rows = await getOutbox();
  if (!rows.length) return;
  let sent = 0;
  const next = [];
  for (const row of rows.slice(0, OUTBOX_LIMIT)) {
    if (sent >= limit) {
      next.push(row);
      continue;
    }
    try {
      await postCapture(row.payload);
      sent += 1;
    } catch (_) {
      next.push({ ...row, attempts: Math.min(999, Number(row.attempts || 0) + 1) });
    }
  }
  await ext.storage.local.set({ [OUTBOX_KEY]: next });
}

ext.runtime.onInstalled.addListener(() => {
  syncBadgeFromBackend();
  void flushOutbox(30);
});

if (ext.runtime.onStartup) {
  ext.runtime.onStartup.addListener(() => {
    syncBadgeFromBackend();
    void flushOutbox(30);
  });
}

ext.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "MEMORYFEED_CAPTURE") return false;

  postCapture(message.payload)
    .then(async (data) => {
      if (data.status === "stored") {
        await incrementBadge();
      }
      sendResponse({ ok: true, data });
      void flushOutbox(10);
    })
    .catch((error) => {
      console.debug("MemoryFeed backend unavailable:", error);
      void enqueueOutbox(message.payload, error);
      sendResponse({ ok: false, error: String(error) });
    });

  return true;
});
