const input = document.getElementById("q");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const debugBox = document.getElementById("debugBox");
const btnSelfTest = document.getElementById("btnSelfTest");
const btnCaptureNow = document.getElementById("btnCaptureNow");
const btnRefreshDebug = document.getElementById("btnRefreshDebug");
const ext = typeof browser !== "undefined" ? browser : chrome;

let timer = null;

function platformEmoji(platform) {
  return {
    twitter: "🐦",
    facebook: "👥",
    youtube: "📺",
    linkedin: "💼",
    instagram: "📸",
    tiktok: "🎵",
    unknown: "🧠",
  }[platform] || "🧠";
}

function renderResults(results) {
  resultsEl.innerHTML = "";
  if (!results.length) {
    statusEl.textContent = "Không có kết quả.";
    return;
  }

  const ordered = [...results].sort((a, b) => {
    const aVideo = isVideoItem(a);
    const bVideo = isVideoItem(b);
    if (aVideo !== bVideo) return bVideo ? 1 : -1;
    if (aVideo && bVideo) {
      return toEpoch(b.captured_at) - toEpoch(a.captured_at);
    }
    return 0;
  });

  statusEl.textContent = `Tìm thấy ${results.length} kết quả`;

  for (const item of ordered) {
    const a = document.createElement("a");
    a.className = "item";
    a.href = item.url;
    a.target = "_blank";

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = `${platformEmoji(item.platform)} ${item.platform} • ${item.captured_at}`;

    const text = document.createElement("div");
    text.className = "text";
    text.textContent = item.text_excerpt || item.text_content?.slice(0, 150) || "(Không có nội dung văn bản)";

    a.appendChild(meta);
    a.appendChild(text);
    resultsEl.appendChild(a);
  }
}

function isVideoItem(item) {
  const type = String(item?.content_type || "").toLowerCase();
  if (type === "video") return true;
  const platform = String(item?.platform || "").toLowerCase();
  if (platform === "youtube" || platform === "tiktok") return true;
  return /\/video\/\d+/.test(String(item?.url || ""));
}

function toEpoch(value) {
  const ts = Date.parse(String(value || ""));
  return Number.isFinite(ts) ? ts : 0;
}

function renderDebug(status) {
  if (!status) {
    debugBox.textContent = "Chưa có log.";
    return;
  }

  const lines = [];
  lines.push(`Kết nối: ${status.ok ? "thành công" : "thất bại"}`);
  if (status.status) lines.push(`Trạng thái ghi nhận: ${status.status}`);
  if (status.platform) lines.push(`Nền tảng: ${status.platform}`);
  if (status.url) lines.push(`URL: ${status.url}`);
  if (status.error) lines.push(`Lỗi: ${status.error}`);
  if (status.self_test) lines.push("Nguồn log: tự kiểm tra");
  if (status.at) lines.push(`Thời điểm: ${status.at}`);
  debugBox.textContent = lines.join("\n");
}

async function refreshDebugStatus() {
  const keys = await ext.storage.local.get(["memoryfeed_last_status"]);
  renderDebug(keys.memoryfeed_last_status);
}

async function runSearch(query) {
  if (!query.trim()) {
    resultsEl.innerHTML = "";
    statusEl.textContent = "Nhập từ khóa để tìm trong MemoryFeed cục bộ.";
    return;
  }

  statusEl.textContent = "Đang tìm...";

  try {
    const res = await fetch(`http://localhost:7749/api/search?q=${encodeURIComponent(query)}&limit=12`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderResults(data.results || []);
  } catch (err) {
    statusEl.textContent = "Không kết nối được backend. Hãy chạy: memoryfeed serve";
    resultsEl.innerHTML = "";
  }
}

input.addEventListener("input", () => {
  clearTimeout(timer);
  timer = setTimeout(() => runSearch(input.value), 300);
});

btnSelfTest.addEventListener("click", () => {
  ext.runtime.sendMessage({ type: "MEMORYFEED_SELF_TEST" }, async (resp) => {
    if (chrome.runtime.lastError) {
      debugBox.textContent = `Lỗi runtime: ${chrome.runtime.lastError.message}`;
      return;
    }
    if (!resp?.ok) {
      debugBox.textContent = `Tự kiểm tra thất bại: ${resp?.error || "không rõ lỗi"}`;
      await refreshDebugStatus();
      return;
    }
    await refreshDebugStatus();
  });
});

btnRefreshDebug.addEventListener("click", () => {
  void refreshDebugStatus();
});

btnCaptureNow.addEventListener("click", () => {
  ext.runtime.sendMessage({ type: "MEMORYFEED_CAPTURE_ACTIVE_TAB" }, async (resp) => {
    if (chrome.runtime.lastError) {
      debugBox.textContent = `Lỗi runtime: ${chrome.runtime.lastError.message}`;
      return;
    }
    if (!resp?.ok) {
      debugBox.textContent = `Ghi tab thất bại: ${resp?.error || "không rõ lỗi"}`;
      await refreshDebugStatus();
      return;
    }
    debugBox.textContent = "Đã gửi dữ liệu tab hiện tại lên backend.";
    await refreshDebugStatus();
  });
});

void refreshDebugStatus();
