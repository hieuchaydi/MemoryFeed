(() => {
  const MIN_DWELL_MS = 3000;
  const TIKTOK_DWELL_MS = 1800;
  const ext = typeof browser !== "undefined" ? browser : chrome;
  const visibilityMap = new Map();
  const capturedKeys = new Set();
  const capturedElements = new WeakSet();

  const platform = detectPlatform(window.location.hostname);

  const CONFIG = {
    facebook: {
      candidate: '[role="article"], .x1iorvi4',
      text: ['[data-ad-preview]', '.xdj266r', '[data-ad-comet-preview="message"]'],
      authorName: ['h3 a[role="link"]', 'a[role="link"] strong', 'strong'],
      authorHandle: ['a[href*="facebook.com/"]'],
      url: ['a[href*="/posts/"]', 'a[href*="/permalink/"]', 'a[href*="story_fbid="]'],
      media: ['img[referrerpolicy]', 'video source', 'video']
    },
    twitter: {
      candidate: 'article[data-testid="tweet"]',
      text: ['[data-testid="tweetText"]', '[lang]'],
      authorName: ['div[data-testid="User-Name"] span', 'a[role="link"] span'],
      authorHandle: ['a[href^="/"][role="link"]'],
      url: ['a[href*="/status/"]'],
      media: ['img[src*="pbs.twimg.com"]', 'video source', 'video']
    },
    youtube: {
      candidate: 'ytd-watch-flexy, ytd-backstage-post-thread-renderer, ytd-rich-item-renderer, #primary',
      text: ['#description-inline-expander', '#description-inner', 'h1.ytd-watch-metadata', 'h1.title'],
      authorName: ['#owner-name a', 'ytd-channel-name a', '#author-text'],
      authorHandle: ['#owner-name a[href*="/@"]', 'ytd-channel-name a[href*="/@"]'],
      url: ['link[rel="canonical"]'],
      media: ['meta[property="og:image"]', 'img[src*="ytimg.com"]', 'video source']
    },
    linkedin: {
      candidate: '.feed-shared-update-v2, .scaffold-finite-scroll__content article',
      text: ['.feed-shared-text', '.update-components-text', '.update-components-update-v2__commentary'],
      authorName: ['.update-components-actor__name', '.feed-shared-actor__name', '.feed-shared-actor__title span'],
      authorHandle: ['a[href*="/in/"]'],
      url: ['a[href*="/feed/update/"]', 'a[href*="/posts/"]'],
      media: ['img', 'video source', 'video']
    },
    tiktok: {
      candidate:
        '[data-e2e="recommend-list-item"], [data-e2e="search_top-item"], [data-e2e*="video-item"], [data-e2e="feed-video"], [data-e2e="search-card-item"]',
      text: ['[data-e2e="new-desc-span"]', '[data-e2e="video-desc"]', '[data-e2e="browse-video-desc"]'],
      authorName: ['[data-e2e="video-author-uniqueid"]', '[data-e2e="video-author"]', 'a[href^="/@"]'],
      authorHandle: ['a[href^="/@"]'],
      url: ['a[href*="/video/"]', 'link[rel="canonical"]', 'meta[property="og:url"]'],
      media: ['meta[property="og:image"]', 'img', 'video source', 'video']
    },
    unknown: {
      candidate: 'article, main, section',
      text: ['meta[name="description"]', 'p'],
      authorName: [],
      authorHandle: [],
      url: ['link[rel="canonical"]'],
      media: ['img']
    }
  };

  ext.runtime.sendMessage({
    type: "MEMORYFEED_PING",
    payload: {
      platform,
      url: window.location.href
    }
  });

  const observer = new IntersectionObserver(onIntersect, {
    root: null,
    threshold: [0.25, 0.5, 0.75]
  });

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
    return platform === "tiktok" ? TIKTOK_DWELL_MS : MIN_DWELL_MS;
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
    el.dataset.memoryfeedObserved = "1";
    observer.observe(el);
  }

  async function maybeCapture(el, startMs) {
    const dwellMs = Date.now() - startMs;
    if (dwellMs < minDwellMsForPlatform()) return;
    if (platform !== "tiktok" && capturedElements.has(el)) return;

    const payload = await capturePost(el, platform, dwellMs / 1000);
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
          const timer = setTimeout(() => {
            void maybeCapture(el, startedAt);
          }, minDwellMsForPlatform() + 100);
          visibilityMap.set(el, { startedAt, timer });
        }
      } else {
        const state = visibilityMap.get(el);
        if (state) {
          visibilityMap.delete(el);
          clearTimeout(state.timer);
          void maybeCapture(el, state.startedAt);
        }
      }
    }
  }

  async function capturePost(element, detectedPlatform, dwellSeconds) {
    try {
      return extractByPlatform(element, detectedPlatform, dwellSeconds);
    } catch (error) {
      console.debug("MemoryFeed capture error:", error);
      return null;
    }
  }

  function firstText(selectors, roots) {
    for (const selector of selectors || []) {
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

  function firstUrl(selectors, roots) {
    for (const selector of selectors || []) {
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

  function collectUrls(selectors, roots) {
    const seen = new Set();
    const output = [];
    const selectorUsed = [];
    for (const selector of selectors || []) {
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
    ["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid", "igshid", "si"].forEach((k) => {
      params.delete(k);
    });

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
          parsed.search = `?v=${encodeURIComponent(videoId)}`;
        }
      } else if (parsed.pathname === "/watch") {
        const v = params.get("v");
        parsed.search = v ? `?v=${encodeURIComponent(v)}` : "";
      } else if (parsed.pathname.startsWith("/shorts/")) {
        const shortId = parsed.pathname.split("/shorts/")[1]?.split("/")[0];
        parsed.pathname = shortId ? `/shorts/${shortId}` : "/shorts";
        parsed.search = "";
      }
    } else if (platformName === "linkedin") {
      const match = parsed.pathname.match(/^\/feed\/update\/([^/?#]+)/);
      if (match) {
        parsed.pathname = `/feed/update/${match[1]}`;
      }
      parsed.search = "";
    } else if (platformName === "facebook") {
      if (parsed.pathname.includes("/posts/") || parsed.pathname.includes("/permalink/")) {
        parsed.search = "";
      } else {
        const story = params.get("story_fbid");
        const id = params.get("id");
        const keep = new URLSearchParams();
        if (story) keep.set("story_fbid", story);
        if (id) keep.set("id", id);
        parsed.search = keep.toString() ? `?${keep.toString()}` : "";
      }
    } else if (platformName === "tiktok") {
      const match = parsed.pathname.match(/^\/@([^/]+)\/video\/(\d+)/);
      if (match) {
        parsed.pathname = `/@${match[1]}/video/${match[2]}`;
      }
      parsed.search = "";
    } else {
      parsed.search = params.toString() ? `?${params.toString()}` : "";
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

  function extractByPlatform(element, platformName, dwellSeconds) {
    const cfg = CONFIG[platformName] || CONFIG.unknown;
    const roots = [element, document];

    const textData = firstText(cfg.text, roots);
    const authorNameData = firstText(cfg.authorName, roots);
    const authorHandleData = firstText(cfg.authorHandle, roots);
    const urlData = firstUrl(cfg.url, roots);
    const mediaData = collectUrls(cfg.media, roots);

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
      capture_debug: {
        selector_used: {
          text: textData.selector || "fallback:meta/doctype",
          author_name: authorNameData.selector || "fallback:none",
          author_handle: authorHandleData.selector || "fallback:none",
          canonical_url: urlData.selector || "fallback:canonical/window.location",
          media_urls: mediaData.selectors
        },
        missing_fields: missingFields,
        page_url: window.location.href
      },
      dwell_seconds: dwellSeconds,
      captured_at: new Date().toISOString()
    };
  }

  const mutationObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node instanceof Element) observeCandidates(node);
      }
    }
  });

  observeCandidates(document);
  mutationObserver.observe(document.body, { childList: true, subtree: true });

  if (platform === "tiktok") {
    let lastHref = window.location.href;
    setInterval(() => {
      if (window.location.href !== lastHref) {
        lastHref = window.location.href;
      }
      void maybeCapture(document.body, Date.now() - minDwellMsForPlatform() - 200);
    }, 2500);
  }

  window.addEventListener(
    "beforeunload",
    () => {
      for (const [el, state] of visibilityMap.entries()) {
        clearTimeout(state.timer);
        void maybeCapture(el, state.startedAt);
      }
      visibilityMap.clear();
    },
    { passive: true }
  );
})();
