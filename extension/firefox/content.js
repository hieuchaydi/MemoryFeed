(() => {
  const MIN_DWELL_MS = 800;
  const TIKTOK_DWELL_MS = 600;
  const CAPTURE_DEBOUNCE_MS_DEFAULT = 300;
  const CAPTURE_MAX_ATTEMPTS_PER_MINUTE_DEFAULT = 200;
  const ext = typeof browser !== "undefined" ? browser : chrome;
  const visibilityMap = new Map();
  const capturedKeys = new Set();
  const capturedElements = new WeakSet();
  const nodeAttemptMap = new WeakMap();
  const captureAttemptTimeline = [];
  const cleanupRegistry = {
    observers: new Set(),
    intervals: new Set(),
    timeouts: new Set(),
    listeners: [],
  };
  const captureRuntime = {
    minVisibleMs: MIN_DWELL_MS,
    debounceMs: CAPTURE_DEBOUNCE_MS_DEFAULT,
    maxAttemptsPerMinute: CAPTURE_MAX_ATTEMPTS_PER_MINUTE_DEFAULT,
  };
  const TRACKING_QUERY_KEYS = new Set([
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "gclid",
    "fbclid",
    "igshid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
  ]);
  const SENSITIVE_QUERY_KEYS = new Set([
    "session",
    "sessionid",
    "sid",
    "phpsessid",
    "jsessionid",
    "token",
    "auth",
    "authorization",
    "bearer",
    "api_key",
    "apikey",
    "key",
  ]);

  const platform = detectPlatform(window.location.hostname);

  const DEFAULT_CONFIG = {
    facebook: {
      candidate: '[role="article"], .x1iorvi4',
      text: ['[data-ad-preview]', '.xdj266r', '[data-ad-comet-preview="message"]'],
      authorName: ['h3 a[role="link"]', 'a[role="link"] strong', 'strong'],
      authorHandle: ['a[href*="facebook.com/"]'],
      url: ['a[href*="/posts/"]', 'a[href*="/permalink/"]', 'a[href*="story_fbid="]'],
      media: ['img[referrerpolicy]', 'video source', 'video'],
      fallback: {
        text: ['meta[name="description"]'],
        authorName: [],
        authorHandle: [],
        url: ['link[rel="canonical"]', 'meta[property="og:url"]'],
        media: ['meta[property="og:image"]', 'img']
      }
    },
    twitter: {
      candidate: 'article[data-testid="tweet"]',
      text: ['[data-testid="tweetText"]', '[lang]'],
      authorName: ['div[data-testid="User-Name"] span', 'a[role="link"] span'],
      authorHandle: ['a[href^="/"][role="link"]'],
      url: ['a[href*="/status/"]'],
      media: ['img[src*="pbs.twimg.com"]', 'video source', 'video'],
      fallback: {
        text: ['meta[name="description"]', 'title'],
        authorName: [],
        authorHandle: [],
        url: ['link[rel="canonical"]', 'meta[property="og:url"]'],
        media: ['meta[property="og:image"]', 'img']
      }
    },
    youtube: {
      candidate: 'ytd-watch-flexy, ytd-backstage-post-thread-renderer, ytd-rich-item-renderer, #primary',
      text: ['#description-inline-expander', '#description-inner', 'h1.ytd-watch-metadata', 'h1.title'],
      authorName: ['#owner-name a', 'ytd-channel-name a', '#author-text'],
      authorHandle: ['#owner-name a[href*="/@"]', 'ytd-channel-name a[href*="/@"]'],
      url: ['link[rel="canonical"]'],
      media: ['meta[property="og:image"]', 'img[src*="ytimg.com"]', 'video source'],
      fallback: {
        text: ['meta[name="description"]', 'title'],
        authorName: [],
        authorHandle: [],
        url: ['meta[property="og:url"]'],
        media: ['img']
      }
    },
    linkedin: {
      candidate: '.feed-shared-update-v2, .scaffold-finite-scroll__content article',
      text: ['.feed-shared-text', '.update-components-text', '.update-components-update-v2__commentary'],
      authorName: ['.update-components-actor__name', '.feed-shared-actor__name', '.feed-shared-actor__title span'],
      authorHandle: ['a[href*="/in/"]'],
      url: ['a[href*="/feed/update/"]', 'a[href*="/posts/"]'],
      media: ['img', 'video source', 'video'],
      fallback: {
        text: ['meta[name="description"]', 'title'],
        authorName: [],
        authorHandle: [],
        url: ['link[rel="canonical"]', 'meta[property="og:url"]'],
        media: ['meta[property="og:image"]']
      }
    },
    tiktok: {
      candidate:
        '[data-e2e="recommend-list-item"], [data-e2e="search_top-item"], [data-e2e*="video-item"], [data-e2e="feed-video"], [data-e2e="search-card-item"]',
      text: ['[data-e2e="new-desc-span"]', '[data-e2e="video-desc"]', '[data-e2e="browse-video-desc"]'],
      authorName: ['[data-e2e="video-author-uniqueid"]', '[data-e2e="video-author"]', 'a[href^="/@"]'],
      authorHandle: ['a[href^="/@"]'],
      url: ['a[href*="/video/"]', 'link[rel="canonical"]', 'meta[property="og:url"]'],
      media: ['meta[property="og:image"]', 'img', 'video source', 'video'],
      fallback: {
        text: ['meta[name="description"]', 'title'],
        authorName: [],
        authorHandle: [],
        url: ['meta[property="og:url"]'],
        media: ['meta[property="og:image"]', 'img']
      }
    },
    unknown: {
      candidate: 'article, main, section',
      text: ['meta[name="description"]', 'p'],
      authorName: [],
      authorHandle: [],
      url: ['link[rel="canonical"]'],
      media: ['img'],
      fallback: {
        text: ['title'],
        authorName: [],
        authorHandle: [],
        url: ['meta[property="og:url"]'],
        media: []
      }
    }
  };

  let CONFIG = JSON.parse(JSON.stringify(DEFAULT_CONFIG));

  function normalizeArray(value) {
    if (!Array.isArray(value)) return [];
    return value.filter((v) => typeof v === "string" && v.trim()).map((v) => v.trim());
  }

  function warn(message) {
    try {
      console.warn(`[MemoryFeed] ${message}`);
    } catch (_) {
      // no-op
    }
  }

  function normalizeConfig(raw, fallbackCfg, platformName) {
    if (!raw || typeof raw !== "object") {
      warn(`selector config for ${platformName} is invalid, using defaults`);
      return JSON.parse(JSON.stringify(fallbackCfg));
    }
    if (typeof raw.platform === "string" && raw.platform.trim()) {
      const normalizedPlatform = raw.platform.trim().toLowerCase();
      if (normalizedPlatform !== platformName) {
        warn(`selector config platform mismatch for ${platformName}, using defaults`);
        return JSON.parse(JSON.stringify(fallbackCfg));
      }
    }

    const fallback = raw?.fallback_selectors && typeof raw.fallback_selectors === "object" ? raw.fallback_selectors : {};
    const candidate = typeof raw?.candidate_selector === "string" && raw.candidate_selector.trim() ? raw.candidate_selector.trim() : "";
    if (!candidate) {
      warn(`selector config missing candidate_selector for ${platformName}, using defaults`);
      return JSON.parse(JSON.stringify(fallbackCfg));
    }

    return {
      candidate,
      text: normalizeArray(raw?.text_selectors).length ? normalizeArray(raw?.text_selectors) : fallbackCfg.text,
      authorName: normalizeArray(raw?.author_selectors).length ? normalizeArray(raw?.author_selectors) : fallbackCfg.authorName,
      authorHandle: normalizeArray(raw?.author_handle_selectors).length ? normalizeArray(raw?.author_handle_selectors) : fallbackCfg.authorHandle,
      url: normalizeArray(raw?.canonical_url_selectors).length ? normalizeArray(raw?.canonical_url_selectors) : fallbackCfg.url,
      media: normalizeArray(raw?.media_selectors).length ? normalizeArray(raw?.media_selectors) : fallbackCfg.media,
      extractorVersion:
        typeof raw?.extractor_version === "string" && raw.extractor_version.trim()
          ? raw.extractor_version.trim().slice(0, 80)
          : `${platformName}_v3_1`,
      fallback: {
        text: normalizeArray(fallback?.text).length ? normalizeArray(fallback?.text) : fallbackCfg.fallback.text,
        authorName: normalizeArray(fallback?.author_name).length ? normalizeArray(fallback?.author_name) : fallbackCfg.fallback.authorName,
        authorHandle: normalizeArray(fallback?.author_handle).length ? normalizeArray(fallback?.author_handle) : fallbackCfg.fallback.authorHandle,
        url: normalizeArray(fallback?.canonical_url).length ? normalizeArray(fallback?.canonical_url) : fallbackCfg.fallback.url,
        media: normalizeArray(fallback?.media).length ? normalizeArray(fallback?.media) : fallbackCfg.fallback.media
      }
    };
  }

  async function loadSelectorJson(name) {
    try {
      const path = ext.runtime.getURL(`selectors/${name}.json`);
      const resp = await fetch(path, { cache: "no-store" });
      if (!resp.ok) return null;
      return await resp.json();
    } catch (_) {
      return null;
    }
  }

  async function loadSelectorRegistry() {
    const names = ["unknown", platform];
    for (const name of names) {
      const raw = await loadSelectorJson(name);
      if (!raw) continue;
      const fallbackCfg = DEFAULT_CONFIG[name] || DEFAULT_CONFIG.unknown;
      CONFIG[name] = normalizeConfig(raw, fallbackCfg, name);
    }
  }

  function registerObserver(instance) {
    cleanupRegistry.observers.add(instance);
    return instance;
  }

  function registerInterval(instance) {
    cleanupRegistry.intervals.add(instance);
    return instance;
  }

  function registerTimeout(instance) {
    cleanupRegistry.timeouts.add(instance);
    return instance;
  }

  function registerListener(target, name, handler, options) {
    target.addEventListener(name, handler, options);
    cleanupRegistry.listeners.push([target, name, handler, options]);
  }

  function clearAllRuntime() {
    for (const [el, state] of visibilityMap.entries()) {
      clearTimeout(state.timer);
      visibilityMap.delete(el);
    }
    for (const observerInstance of cleanupRegistry.observers) {
      try {
        observerInstance.disconnect();
      } catch (_) {
        // no-op
      }
    }
    cleanupRegistry.observers.clear();

    for (const intervalId of cleanupRegistry.intervals) {
      clearInterval(intervalId);
    }
    cleanupRegistry.intervals.clear();

    for (const timeoutId of cleanupRegistry.timeouts) {
      clearTimeout(timeoutId);
    }
    cleanupRegistry.timeouts.clear();

    for (const [target, name, handler, options] of cleanupRegistry.listeners) {
      try {
        target.removeEventListener(name, handler, options);
      } catch (_) {
        // no-op
      }
    }
    cleanupRegistry.listeners = [];
    for (const node of document.querySelectorAll('[data-memoryfeed-observed=\"1\"]')) {
      delete node.dataset.memoryfeedObserved;
    }
    observer = null;
  }

  async function loadCaptureRuntimeConfig() {
    if (!ext.storage || !ext.storage.local || !ext.storage.local.get) return;
    try {
      const raw = await ext.storage.local.get([
        "MEMORY_CAPTURE_MIN_VISIBLE_MS",
        "MEMORY_CAPTURE_DEBOUNCE_MS",
        "MEMORY_CAPTURE_MAX_ATTEMPTS_PER_MINUTE",
      ]);
      const minVisible = Number(raw.MEMORY_CAPTURE_MIN_VISIBLE_MS);
      const debounceMs = Number(raw.MEMORY_CAPTURE_DEBOUNCE_MS);
      const maxAttempts = Number(raw.MEMORY_CAPTURE_MAX_ATTEMPTS_PER_MINUTE);
      if (Number.isFinite(minVisible) && minVisible > 0) captureRuntime.minVisibleMs = Math.max(200, Math.round(minVisible));
      if (Number.isFinite(debounceMs) && debounceMs > 0) captureRuntime.debounceMs = Math.max(50, Math.round(debounceMs));
      if (Number.isFinite(maxAttempts) && maxAttempts > 0) {
        captureRuntime.maxAttemptsPerMinute = Math.max(20, Math.round(maxAttempts));
      }
    } catch (_) {
      // keep defaults
    }
  }

  ext.runtime.sendMessage({
    type: "MEMORYFEED_PING",
    payload: {
      platform,
      url: window.location.href
    }
  });

  let observer = null;

  function detectPlatform(hostname) {
    const host = (hostname || "").toLowerCase();
    if (host.includes("facebook.com")) return "facebook";
    if (host.includes("twitter.com") || host.includes("x.com")) return "twitter";
    if (host.includes("youtube.com") || host.includes("youtu.be")) return "youtube";
    if (host.includes("linkedin.com")) return "linkedin";
    if (host.includes("tiktok.com")) return "tiktok";
    return "unknown";
  }

  function minDwellMsForPlatform() {
    if (platform === "tiktok") return Math.max(TIKTOK_DWELL_MS, Math.round(captureRuntime.minVisibleMs * 0.6));
    return captureRuntime.minVisibleMs;
  }

  function getPlatformConfig() {
    return CONFIG[platform] || CONFIG.unknown;
  }

  function getCandidates() {
    return document.querySelectorAll(getPlatformConfig().candidate);
  }

  function observeCandidates(root = document) {
    const list = root === document ? getCandidates() : root.querySelectorAll("*");
    if (root !== document) {
      for (const node of list) {
        if (isCandidate(node)) observeOne(node);
      }
      if (isCandidate(root)) observeOne(root);
      return;
    }
    for (const el of list) observeOne(el);
  }

  function isCandidate(el) {
    if (!(el instanceof Element)) return false;
    return el.matches(getPlatformConfig().candidate);
  }

  function observeOne(el) {
    if (!(el instanceof Element)) return;
    if (el.dataset.memoryfeedObserved === "1") return;
    if (!observer) return;
    el.dataset.memoryfeedObserved = "1";
    observer.observe(el);
  }

  function allowCaptureAttempt(el) {
    const now = Date.now();
    const attemptState = nodeAttemptMap.get(el);
    if (attemptState && now - attemptState.lastAttemptMs < captureRuntime.debounceMs) {
      return false;
    }

    while (captureAttemptTimeline.length && now - captureAttemptTimeline[0] > 60_000) {
      captureAttemptTimeline.shift();
    }
    if (captureAttemptTimeline.length >= captureRuntime.maxAttemptsPerMinute) {
      return false;
    }

    captureAttemptTimeline.push(now);
    nodeAttemptMap.set(el, {
      lastAttemptMs: now,
      attempts: attemptState ? attemptState.attempts + 1 : 1,
    });
    return true;
  }

  async function maybeCapture(el, startMs, captureMethod = "intersection_observer") {
    const dwellMs = Date.now() - startMs;
    if (dwellMs < minDwellMsForPlatform()) return;
    if (platform !== "tiktok" && capturedElements.has(el)) return;
    if (!allowCaptureAttempt(el)) return;

    const payload = await capturePost(el, platform, dwellMs / 1000, captureMethod);
    if (!payload || !payload.url) return;

    const bucket = Math.floor(Date.now() / (2 * 60 * 60 * 1000));
    const dedupeKey = [
      payload.canonical_url || payload.url,
      payload.platform,
      (payload.text_content || "").slice(0, 240),
      (payload.author_name || payload.author || "").slice(0, 100),
      String(bucket)
    ].join("|");

    if (capturedKeys.has(dedupeKey)) return;
    capturedKeys.add(dedupeKey);

    if (platform !== "tiktok") {
      capturedElements.add(el);
    }

    ext.runtime.sendMessage({ type: "MEMORYFEED_CAPTURE", payload });
  }

  function onIntersect(entries) {
    for (const entry of entries) {
      const el = entry.target;
      if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
        if (!visibilityMap.has(el)) {
          const startedAt = Date.now();
          const timer = registerTimeout(
            setTimeout(() => {
              void maybeCapture(el, startedAt, "intersection_observer");
            }, minDwellMsForPlatform() + 100)
          );
          visibilityMap.set(el, { startedAt, timer });
        }
      } else {
        const state = visibilityMap.get(el);
        if (state) {
          visibilityMap.delete(el);
          clearTimeout(state.timer);
        }
      }
    }
  }

  async function capturePost(element, detectedPlatform, dwellSeconds, captureMethod) {
    try {
      return extractByPlatform(element, detectedPlatform, dwellSeconds, captureMethod);
    } catch (error) {
      console.debug("MemoryFeed capture error:", error);
      return null;
    }
  }

  function firstText(selectors, fallbackSelectors, roots) {
    for (const selector of [...(selectors || []), ...(fallbackSelectors || [])]) {
      for (const root of roots) {
        const node = findNode(root, selector);
        const value = readNodeText(node, selector);
        if (value) {
          return { value, selector };
        }
      }
    }
    return { value: "", selector: "" };
  }

  function firstUrl(selectors, fallbackSelectors, roots) {
    for (const selector of [...(selectors || []), ...(fallbackSelectors || [])]) {
      for (const root of roots) {
        const node = findNode(root, selector);
        const value = readNodeUrl(node, selector);
        if (value) {
          return { value, selector };
        }
      }
    }
    return { value: "", selector: "" };
  }

  function collectUrls(selectors, fallbackSelectors, roots) {
    const seen = new Set();
    const output = [];
    const selectorUsed = [];
    for (const selector of [...(selectors || []), ...(fallbackSelectors || [])]) {
      for (const root of roots) {
        const nodes = findNodes(root, selector);
        for (const node of nodes) {
          const raw = readNodeUrl(node, selector);
          const url = normalizeAbsoluteUrl(raw);
          if (url && !seen.has(url)) {
            seen.add(url);
            output.push(url);
            selectorUsed.push(selector);
            if (output.length >= 8) {
              return { urls: output, selectors: [...new Set(selectorUsed)] };
            }
          }
        }
      }
    }
    return { urls: output, selectors: [...new Set(selectorUsed)] };
  }

  function findNode(root, selector) {
    if (!root) return null;
    if (selector.startsWith("meta[") || selector.startsWith("link[")) {
      return document.querySelector(selector);
    }
    if (!(root instanceof Element) && root !== document) {
      return null;
    }
    return root.querySelector(selector);
  }

  function findNodes(root, selector) {
    if (!root) return [];
    if (selector.startsWith("meta[") || selector.startsWith("link[")) {
      const node = document.querySelector(selector);
      return node ? [node] : [];
    }
    if (!(root instanceof Element) && root !== document) {
      return [];
    }
    return [...root.querySelectorAll(selector)];
  }

  function readNodeText(node, selector) {
    if (!node) return "";
    if (selector.startsWith("meta[")) {
      return cleanText(node.getAttribute("content"));
    }
    return cleanText(node.innerText || node.textContent || "");
  }

  function readNodeUrl(node, selector) {
    if (!node) return "";
    if (selector.startsWith("meta[")) {
      return cleanText(node.getAttribute("content"));
    }
    if (selector.startsWith("link[")) {
      return cleanText(node.getAttribute("href"));
    }
    if (node.tagName === "A") {
      return cleanText(node.getAttribute("href") || node.href);
    }
    if (node.tagName === "IMG") {
      return cleanText(node.getAttribute("src") || node.currentSrc || node.src);
    }
    if (node.tagName === "SOURCE") {
      return cleanText(node.getAttribute("src") || node.src);
    }
    if (node.tagName === "VIDEO") {
      return cleanText(node.getAttribute("src") || node.src || node.getAttribute("poster"));
    }
    return cleanText(node.getAttribute("href") || node.getAttribute("src") || "");
  }

  function cleanText(value) {
    return (value || "").replace(/\s+/g, " ").trim();
  }

  function normalizeAbsoluteUrl(value) {
    if (!value) return "";
    try {
      return new URL(value, window.location.href).toString();
    } catch (_) {
      return "";
    }
  }

  function normalizeUrl(rawUrl, platformName) {
    const abs = normalizeAbsoluteUrl(rawUrl) || window.location.href;
    let parsed;
    try {
      parsed = new URL(abs);
    } catch (_) {
      return abs;
    }

    parsed.hash = "";
    const host = parsed.hostname.replace(/^www\./, "");
    const params = new URLSearchParams(parsed.search);
    const clean = new URLSearchParams();
    for (const [key, value] of params.entries()) {
      const lower = key.toLowerCase();
      if (TRACKING_QUERY_KEYS.has(lower) || SENSITIVE_QUERY_KEYS.has(lower)) continue;
      clean.append(key, value);
    }

    if (platformName === "twitter") {
      const match = parsed.pathname.match(/^\/([^/]+)\/status\/(\d+)/);
      if (match) {
        parsed.pathname = `/${match[1]}/status/${match[2]}`;
      }
      parsed.search = "";
    } else if (platformName === "youtube") {
      if (host === "youtu.be") {
        const videoId = parsed.pathname.replace(/^\//, "").split("/")[0];
        if (videoId) {
          parsed.hostname = "youtube.com";
          parsed.pathname = "/watch";
          clean.set("v", videoId);
        }
      }
      if (parsed.pathname === "/watch") {
        const keep = new URLSearchParams();
        const v = clean.get("v");
        if (v) keep.set("v", v);
        const t = clean.get("t") || clean.get("start") || clean.get("time_continue");
        if (t) keep.set("t", t);
        const list = clean.get("list");
        if (list) keep.set("list", list);
        const index = clean.get("index");
        if (index) keep.set("index", index);
        parsed.search = keep.toString() ? `?${keep.toString()}` : "";
      } else if (parsed.pathname.startsWith("/shorts/")) {
        const shortId = parsed.pathname.split("/shorts/")[1]?.split("/")[0];
        parsed.pathname = shortId ? `/shorts/${shortId}` : "/shorts";
        const keep = new URLSearchParams();
        const t = clean.get("t");
        if (t) keep.set("t", t);
        parsed.search = keep.toString() ? `?${keep.toString()}` : "";
      }
    } else if (platformName === "linkedin") {
      const match = parsed.pathname.match(/^\/feed\/update\/([^/?#]+)/);
      if (match) {
        parsed.pathname = `/feed/update/${match[1]}`;
      }
      parsed.search = clean.toString() ? `?${clean.toString()}` : "";
    } else if (platformName === "facebook") {
      if (parsed.pathname.includes("/posts/") || parsed.pathname.includes("/permalink/")) {
        const keep = new URLSearchParams();
        const commentId = clean.get("comment_id");
        if (commentId) keep.set("comment_id", commentId);
        parsed.search = keep.toString() ? `?${keep.toString()}` : "";
      } else {
        const story = clean.get("story_fbid");
        const id = clean.get("id");
        const keep = new URLSearchParams();
        if (story) keep.set("story_fbid", story);
        if (id) keep.set("id", id);
        const commentId = clean.get("comment_id");
        if (commentId) keep.set("comment_id", commentId);
        parsed.search = keep.toString() ? `?${keep.toString()}` : "";
      }
    } else if (platformName === "tiktok") {
      const match = parsed.pathname.match(/^\/@([^/]+)\/video\/(\d+)/);
      if (match) {
        parsed.pathname = `/@${match[1]}/video/${match[2]}`;
      }
      const keep = new URLSearchParams();
      const index = clean.get("index") || clean.get("i");
      if (index) keep.set("index", index);
      parsed.search = keep.toString() ? `?${keep.toString()}` : "";
    } else {
      parsed.search = clean.toString() ? `?${clean.toString()}` : "";
    }

    parsed.hostname = host;
    return parsed.toString().replace(/\/$/, "");
  }

  function extractPostId(url, platformName) {
    try {
      const parsed = new URL(url, window.location.href);
      const path = parsed.pathname;
      if (platformName === "twitter") {
        return path.match(/\/status\/(\d+)/)?.[1] || null;
      }
      if (platformName === "youtube") {
        if (path === "/watch") return parsed.searchParams.get("v");
        if (path.startsWith("/shorts/")) return path.split("/shorts/")[1]?.split("/")[0] || null;
      }
      if (platformName === "linkedin") {
        return path.match(/\/feed\/update\/([^/?#]+)/)?.[1] || null;
      }
      if (platformName === "facebook") {
        return (
          path.match(/\/posts\/([^/?#]+)/)?.[1] ||
          path.match(/\/permalink\/([^/?#]+)/)?.[1] ||
          parsed.searchParams.get("story_fbid") ||
          null
        );
      }
      if (platformName === "tiktok") {
        return path.match(/\/video\/(\d+)/)?.[1] || null;
      }
    } catch (_) {
      return null;
    }
    return null;
  }

  function inferContentType(platformName, mediaUrls) {
    if (platformName === "youtube" || platformName === "tiktok") return "video";
    return mediaUrls.length ? "image" : "post";
  }

  function computeConfidence(requiredFields, qualityFlags, selectorUsed) {
    let score = 1.0;
    const reasons = [];
    if (!requiredFields.text) {
      score -= 0.22;
      reasons.push("missing_text");
    }
    if (!requiredFields.author_name) {
      score -= 0.14;
      reasons.push("missing_author");
    }
    if (!requiredFields.canonical_url) {
      score -= 0.18;
      reasons.push("missing_canonical_url");
    }
    if (!requiredFields.post_id) {
      score -= 0.08;
      reasons.push("missing_post_id");
    }
    if (!Array.isArray(requiredFields.media_urls) || requiredFields.media_urls.length === 0) {
      score -= 0.08;
      reasons.push("missing_media");
    }
    if ((qualityFlags || []).some((flag) => String(flag).startsWith("missing_"))) {
      score -= 0.05;
      reasons.push("missing_required_fields");
    }
    for (const [key, value] of Object.entries(selectorUsed || {})) {
      if (typeof value === "string" && value.startsWith("fallback")) {
        score -= 0.04;
        reasons.push(`fallback_selector_used:${key}`);
      }
    }
    if (score < 0) score = 0;
    if (score > 1) score = 1;
    return {
      score: Math.round(score * 10000) / 10000,
      reasons: [...new Set(reasons)].sort(),
    };
  }

  function extractByPlatform(element, platformName, dwellSeconds, captureMethod) {
    const cfg = CONFIG[platformName] || CONFIG.unknown;
    const fallback = cfg.fallback || {};
    const roots = [element, document];

    const textData = firstText(cfg.text, fallback.text, roots);
    const authorNameData = firstText(cfg.authorName, fallback.authorName, roots);
    const authorHandleData = firstText(cfg.authorHandle, fallback.authorHandle, roots);
    const urlData = firstUrl(cfg.url, fallback.url, roots);
    const mediaData = collectUrls(cfg.media, fallback.media, roots);

    const titleFallback = cleanText(document.title || "");
    const descriptionFallback = cleanText(document.querySelector('meta[name="description"]')?.getAttribute("content") || "");
    const text = textData.value || descriptionFallback || titleFallback;

    const rawUrl = urlData.value || document.querySelector('link[rel="canonical"]')?.getAttribute("href") || window.location.href;
    const canonicalUrl = normalizeUrl(rawUrl, platformName);
    const postId = extractPostId(canonicalUrl, platformName);

    const mediaUrls = mediaData.urls.slice(0, 6);
    const thumbnailUrl = mediaUrls[0] || null;

    const requiredFields = {
      platform: platformName,
      canonical_url: canonicalUrl,
      author_name: authorNameData.value,
      text,
      media_urls: mediaUrls,
      post_id: postId,
      captured_at: new Date().toISOString()
    };

    const missingFields = Object.entries(requiredFields)
      .filter(([, value]) => {
        if (Array.isArray(value)) return value.length === 0;
        return !value;
      })
      .map(([key]) => key);

    const qualityFlags = missingFields.map((field) => `missing_${field}`);
    const selectorUsed = {
      text: textData.selector || "fallback:meta/doctype",
      author_name: authorNameData.selector || "fallback:none",
      author_handle: authorHandleData.selector || "fallback:none",
      canonical_url: urlData.selector || "fallback:canonical/window.location",
      media_urls: mediaData.selectors
    };
    const confidence = computeConfidence(requiredFields, qualityFlags, selectorUsed);

    return {
      url: canonicalUrl || window.location.href,
      canonical_url: canonicalUrl || window.location.href,
      platform: platformName,
      post_id: postId,
      content_type: inferContentType(platformName, mediaUrls),
      text_content: text || "",
      media_urls: mediaUrls,
      image_urls: mediaUrls,
      author: authorNameData.value || null,
      author_name: authorNameData.value || null,
      author_handle: authorHandleData.value || null,
      thumbnail_url: thumbnailUrl,
      source_context: window.location.pathname,
      quality_flags: qualityFlags,
      capture_confidence: confidence.score,
      confidence_reasons: confidence.reasons,
      capture_method: captureMethod || "mutation_observer",
      extractor_version: cfg.extractorVersion || `${platformName}_v3_1`,
      capture_source: "timeline_scroll",
      replay_source: null,
        capture_debug: {
        selector_used: selectorUsed,
        missing_fields: missingFields,
        page_url: `${window.location.origin}${window.location.pathname}`
      },
      dwell_seconds: dwellSeconds,
      captured_at: new Date().toISOString()
    };
  }

  function routeReinitialize() {
    for (const [el, state] of visibilityMap.entries()) {
      clearTimeout(state.timer);
      visibilityMap.delete(el);
    }
    for (const node of document.querySelectorAll('[data-memoryfeed-observed=\"1\"]')) {
      delete node.dataset.memoryfeedObserved;
    }
    capturedKeys.clear();
    observeCandidates(document);
  }

  function setupRouteHooks() {
    if (!window.__memoryfeedRouteHookInstalled) {
      window.__memoryfeedRouteHookInstalled = true;
      const wrap = (name) => {
        const original = history[name];
        if (typeof original !== "function") return;
        history[name] = function wrappedHistoryMethod(...args) {
          const result = original.apply(this, args);
          window.dispatchEvent(new Event("memoryfeed:route-change"));
          return result;
        };
      };
      wrap("pushState");
      wrap("replaceState");
      window.addEventListener("popstate", () => {
        window.dispatchEvent(new Event("memoryfeed:route-change"));
      }, { passive: true });
    }
    registerListener(window, "memoryfeed:route-change", routeReinitialize, { passive: true });
  }

  async function initializeCaptureRuntime() {
    await loadCaptureRuntimeConfig();

    observer = registerObserver(
      new IntersectionObserver(onIntersect, {
        root: null,
        threshold: [0.25, 0.5, 0.75]
      })
    );

    const mutationObserver = registerObserver(
      new MutationObserver((mutations) => {
        for (const mutation of mutations) {
          for (const node of mutation.addedNodes) {
            if (node instanceof Element) observeCandidates(node);
          }
        }
      })
    );

    observeCandidates(document);
    await loadSelectorRegistry();
    observeCandidates(document);

    if (document.body) {
      mutationObserver.observe(document.body, { childList: true, subtree: true });
    }

    if (platform === "tiktok") {
      let lastHref = window.location.href;
      registerInterval(setInterval(() => {
        if (window.location.href !== lastHref) {
          lastHref = window.location.href;
          routeReinitialize();
        }
        void maybeCapture(document.body, Date.now() - minDwellMsForPlatform() - 200, "tiktok_polling");
      }, 2500));
    }

    registerListener(
      window,
      "beforeunload",
      () => {
        clearAllRuntime();
      },
      { passive: true }
    );
    setupRouteHooks();
  }

  if (window.__memoryfeedLifecycle && typeof window.__memoryfeedLifecycle.destroy === "function") {
    window.__memoryfeedLifecycle.destroy("reinitialize");
  }
  window.__memoryfeedLifecycle = {
    destroy: clearAllRuntime,
  };

  void initializeCaptureRuntime();
})();
