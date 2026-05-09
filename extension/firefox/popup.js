const input = document.getElementById("q");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

let timer = null;

function platformEmoji(platform) {
  return {
    twitter: "🐦",
    facebook: "👥",
    youtube: "📺",
    linkedin: "💼",
    instagram: "📸",
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
    text.textContent = item.text_excerpt || item.text_content?.slice(0, 150) || "(Không có text)";

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

async function runSearch(query) {
  if (!query.trim()) {
    resultsEl.innerHTML = "";
    statusEl.textContent = "Nhập từ khóa để tìm trong MemoryFeed local.";
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

