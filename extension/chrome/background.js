const API_BASE = "http://localhost:7749";
const BADGE_KEY = "memoryfeed_captured_today";
const DATE_KEY = "memoryfeed_badge_date";
const LAST_STATUS_KEY = "memoryfeed_last_status";
const ext = typeof browser !== "undefined" ? browser : chrome;

async function postCapture(payload) {
  const res = await fetch(`${API_BASE}/capture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`Capture failed with ${res.status}`);
  }
  return res.json();
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

async function setLastStatus(payload) {
  const data = {
    at: new Date().toISOString(),
    ...payload,
  };
  await ext.storage.local.set({ [LAST_STATUS_KEY]: data });
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
      await setLastStatus({
        ok: true,
        status: data.status,
        platform: message.payload?.platform || "unknown",
        url: message.payload?.url || "",
      });
      sendResponse({ ok: true, data });
    })
    .catch((error) => {
      console.debug("MemoryFeed backend unavailable:", error);
      void setLastStatus({
        ok: false,
        error: String(error),
        platform: message.payload?.platform || "unknown",
        url: message.payload?.url || "",
      });
      sendResponse({ ok: false, error: String(error) });
    });

  return true;
});

ext.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== "MEMORYFEED_CAPTURE_ACTIVE_TAB") return false;

  captureActiveTabNow()
    .then(async (payload) => {
      if (!payload || !payload.url) {
        throw new Error("Không đọc được nội dung tab hiện tại.");
      }
      const data = await postCapture(payload);
      await setLastStatus({
        ok: true,
        status: data.status || "stored",
        platform: payload.platform || "unknown",
        url: payload.url || "",
        manual_capture: true,
      });
      sendResponse({ ok: true, data });
    })
    .catch(async (error) => {
      await setLastStatus({
        ok: false,
        error: String(error),
        manual_capture: true,
      });
      sendResponse({ ok: false, error: String(error) });
    });

  return true;
});

async function captureActiveTabNow() {
  if (!ext.tabs || !ext.scripting) {
    throw new Error("Trình duyệt không hỗ trợ tabs/scripting API.");
  }

  const tabs = await ext.tabs.query({ active: true, currentWindow: true });
  const tab = tabs && tabs[0];
  if (!tab || typeof tab.id !== "number") {
    throw new Error("Không tìm thấy tab đang mở.");
  }

  const injected = await ext.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      const host = (location.hostname || "").toLowerCase();
      const platform = host.includes("tiktok.com")
        ? "tiktok"
        : host.includes("facebook.com")
          ? "facebook"
          : host.includes("x.com") || host.includes("twitter.com")
            ? "twitter"
            : host.includes("youtube.com")
              ? "youtube"
              : host.includes("linkedin.com")
                ? "linkedin"
                : "unknown";

      const safeText = (s) => (typeof s === "string" ? s.trim() : "");
      let text = "";
      let author = null;
      let contentType = "post";

      if (platform === "tiktok") {
        const directVideoLink =
          document.querySelector('a[href*="/video/"]')?.href ||
          Array.from(document.querySelectorAll('a[href*="/video/"]'))
            .map((a) => a.href)
            .find(Boolean) ||
          "";
        const ogUrl = safeText(document.querySelector('meta[property="og:url"]')?.content);
        const canonical = safeText(document.querySelector('link[rel="canonical"]')?.href);
        const videoUrl =
          directVideoLink ||
          (location.href.includes("/video/") ? location.href : "") ||
          (ogUrl.includes("/video/") ? ogUrl : "") ||
          (canonical.includes("/video/") ? canonical : "");

        text =
          safeText(
            document.querySelector('[data-e2e="new-desc-span"], [data-e2e="video-desc"], [data-e2e="browse-video-desc"]')
              ?.innerText
          ) ||
          safeText(document.querySelector('meta[property="og:description"]')?.content) ||
          safeText(document.querySelector('meta[name="description"]')?.content) ||
          safeText(document.title);
        author = safeText(
          document.querySelector('[data-e2e="video-author-uniqueid"], [data-e2e="video-author"], a[href^="/@"]')
            ?.innerText
        ) || null;
        contentType = "video";
      } else if (platform === "twitter") {
        text = safeText(document.querySelector('[data-testid="tweetText"]')?.innerText) || safeText(document.title);
      } else if (platform === "youtube") {
        const title = safeText(document.querySelector('h1.ytd-watch-metadata, h1.title')?.innerText) || safeText(document.title);
        const desc = safeText(document.querySelector('#description-inner')?.innerText);
        text = [title, desc].filter(Boolean).join("\n");
        contentType = "video";
      } else if (platform === "facebook") {
        text = safeText(document.querySelector('[data-ad-preview], .xdj266r')?.innerText) || safeText(document.title);
      } else if (platform === "linkedin") {
        text = safeText(document.querySelector('.feed-shared-text, .update-components-text')?.innerText) || safeText(document.title);
      } else {
        text = safeText(document.querySelector('meta[name="description"]')?.content) || safeText(document.title);
      }

      const images = Array.from(document.querySelectorAll("img"))
        .map((img) => img.src)
        .filter((v) => typeof v === "string" && /^https?:\/\//.test(v))
        .slice(0, 6);
      if (contentType !== "video" && images.length) {
        contentType = "image";
      }

      return {
        url:
          platform === "tiktok"
            ? document.querySelector('a[href*="/video/"]')?.href ||
              safeText(document.querySelector('meta[property="og:url"]')?.content) ||
              location.href
            : location.href,
        platform,
        content_type: contentType,
        text_content: text || "",
        image_urls: images,
        author,
        dwell_seconds: 2.0,
      };
    },
  });

  const first = Array.isArray(injected) ? injected[0] : null;
  return first?.result || null;
}

ext.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message && message.type === "MEMORYFEED_PING") {
    void setLastStatus({
      ok: true,
      status: "content_script_active",
      platform: message.payload?.platform || "unknown",
      url: message.payload?.url || "",
    });
    sendResponse({ ok: true });
    return false;
  }

  if (!message || message.type !== "MEMORYFEED_SELF_TEST") return false;

  const payload = {
    url: "https://local.memoryfeed/self-test",
    platform: "unknown",
    content_type: "post",
    text_content: `MemoryFeed tự kiểm tra lúc ${new Date().toISOString()}`,
    image_urls: [],
    author: "memoryfeed-extension",
    dwell_seconds: 1.0,
  };

  postCapture(payload)
    .then(async (data) => {
      await setLastStatus({
        ok: true,
        status: data.status,
        platform: "unknown",
        url: payload.url,
        self_test: true,
      });
      sendResponse({ ok: true, data });
    })
    .catch(async (error) => {
      await setLastStatus({
        ok: false,
        error: String(error),
        platform: "unknown",
        url: payload.url,
        self_test: true,
      });
      sendResponse({ ok: false, error: String(error) });
    });

  return true;
});
