const API_BASE = "http://localhost:7749";
const BADGE_KEY = "memoryfeed_captured_today";
const DATE_KEY = "memoryfeed_badge_date";
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

ext.runtime.onInstalled.addListener(() => {
  syncBadgeFromBackend();
});

if (ext.runtime.onStartup) {
  ext.runtime.onStartup.addListener(() => {
    syncBadgeFromBackend();
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
    })
    .catch((error) => {
      console.debug("MemoryFeed backend unavailable:", error);
      sendResponse({ ok: false, error: String(error) });
    });

  return true;
});
