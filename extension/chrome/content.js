(() => {
  const MIN_DWELL_MS = 3000;
  const visibilityMap = new Map();
  const capturedKeys = new Set();

  const platform = detectPlatform(window.location.hostname);
  const observer = new IntersectionObserver(onIntersect, {
    root: null,
    threshold: [0.25, 0.5, 0.75],
  });

  function detectPlatform(hostname) {
    const host = (hostname || "").toLowerCase();
    if (host.includes("facebook.com")) return "facebook";
    if (host.includes("twitter.com") || host.includes("x.com")) return "twitter";
    if (host.includes("youtube.com")) return "youtube";
    if (host.includes("linkedin.com")) return "linkedin";
    return "unknown";
  }

  function getCandidates() {
    if (platform === "facebook") return document.querySelectorAll('[role="article"], .x1iorvi4');
    if (platform === "twitter") return document.querySelectorAll('article[data-testid="tweet"]');
    if (platform === "youtube") return document.querySelectorAll('ytd-watch-flexy, #primary');
    if (platform === "linkedin") return document.querySelectorAll('.feed-shared-update-v2');
    return document.querySelectorAll('article, main, section');
  }

  function observeCandidates(root = document) {
    const list = root === document ? getCandidates() : root.querySelectorAll('*');
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
    if (platform === "facebook") return el.matches('[role="article"], .x1iorvi4');
    if (platform === "twitter") return el.matches('article[data-testid="tweet"]');
    if (platform === "youtube") return el.matches('ytd-watch-flexy, #primary');
    if (platform === "linkedin") return el.matches('.feed-shared-update-v2');
    return el.matches('article, main, section');
  }

  function observeOne(el) {
    if (!(el instanceof Element)) return;
    if (el.dataset.memoryfeedObserved === "1") return;
    el.dataset.memoryfeedObserved = "1";
    observer.observe(el);
  }

  async function maybeCapture(el, startMs) {
    const dwellMs = Date.now() - startMs;
    if (dwellMs < MIN_DWELL_MS) return;

    const payload = await capturePost(el, platform, dwellMs / 1000);
    if (!payload || !payload.url) return;

    const text = (payload.text_content || "").slice(0, 100);
    const dedupeKey = `${payload.url}|${text}`;
    if (capturedKeys.has(dedupeKey)) return;
    capturedKeys.add(dedupeKey);

    chrome.runtime.sendMessage({ type: "MEMORYFEED_CAPTURE", payload });
  }

  function onIntersect(entries) {
    for (const entry of entries) {
      const el = entry.target;
      if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
        if (!visibilityMap.has(el)) visibilityMap.set(el, Date.now());
      } else {
        const startedAt = visibilityMap.get(el);
        if (startedAt) {
          visibilityMap.delete(el);
          void maybeCapture(el, startedAt);
        }
      }
    }
  }

  async function capturePost(element, platform, dwellSeconds) {
    try {
      if (platform === "facebook") return extractFacebook(element, dwellSeconds);
      if (platform === "twitter") return extractTwitter(element, dwellSeconds);
      if (platform === "youtube") return extractYouTube(element, dwellSeconds);
      if (platform === "linkedin") return extractLinkedIn(element, dwellSeconds);
      return extractFallback(element, dwellSeconds);
    } catch (error) {
      console.debug("MemoryFeed capture error:", error);
      return null;
    }
  }

  function extractFacebook(element, dwellSeconds) {
    const textNode = element.querySelector('[data-ad-preview], .xdj266r');
    const text = textNode ? textNode.innerText : "";
    const images = [...element.querySelectorAll('img[referrerpolicy]')]
      .map((img) => img.src)
      .filter(Boolean)
      .slice(0, 6);
    const author = element.querySelector('h3, strong, a[role="link"]')?.innerText?.trim() || null;
    const url = element.querySelector('a[href*="/posts/"], a[href*="/permalink/"]')?.href || window.location.href;

    return {
      url,
      platform: "facebook",
      content_type: images.length ? "image" : "post",
      text_content: text,
      image_urls: images,
      author,
      dwell_seconds: dwellSeconds,
    };
  }

  function extractTwitter(element, dwellSeconds) {
    const text = element.querySelector('[data-testid="tweetText"]')?.innerText || "";
    const images = [...element.querySelectorAll('img[src*="pbs.twimg.com"]')]
      .map((img) => img.src)
      .filter(Boolean)
      .slice(0, 6);
    const url = element.querySelector('a[href*="/status/"]')?.href || window.location.href;
    const author = element.querySelector('a[role="link"] span')?.innerText?.trim() || null;

    return {
      url,
      platform: "twitter",
      content_type: images.length ? "image" : "post",
      text_content: text,
      image_urls: images,
      author,
      dwell_seconds: dwellSeconds,
    };
  }

  function extractYouTube(element, dwellSeconds) {
    const title = document.querySelector('h1.ytd-watch-metadata, h1.title')?.innerText || document.title;
    const desc = document.querySelector('#description-inner')?.innerText || "";
    const text = `${title}\n${desc}`.trim();
    const author = document.querySelector('#owner-name a, ytd-channel-name a')?.innerText?.trim() || null;

    const ogImage = document.querySelector('meta[property="og:image"]')?.content || null;
    const thumbnails = [...document.querySelectorAll('img[src*="ytimg.com"]')]
      .map((img) => img.src)
      .filter(Boolean);
    const images = [...new Set([ogImage, ...thumbnails].filter(Boolean))].slice(0, 6);

    return {
      url: window.location.href,
      platform: "youtube",
      content_type: "video",
      text_content: text,
      image_urls: images,
      author,
      dwell_seconds: dwellSeconds,
    };
  }

  function extractLinkedIn(element, dwellSeconds) {
    const text = element.querySelector('.feed-shared-text, .update-components-text')?.innerText || "";
    const images = [...element.querySelectorAll('img')]
      .map((img) => img.src)
      .filter(Boolean)
      .slice(0, 6);
    const author = element.querySelector('.update-components-actor__name, .feed-shared-actor__name')?.innerText?.trim() || null;
    const url = element.querySelector('a[href*="/feed/update/"]')?.href || window.location.href;

    return {
      url,
      platform: "linkedin",
      content_type: images.length ? "image" : "post",
      text_content: text,
      image_urls: images,
      author,
      dwell_seconds: dwellSeconds,
    };
  }

  function extractFallback(element, dwellSeconds) {
    const title = document.title || "";
    const description = document.querySelector('meta[name="description"]')?.content || "";
    const largestParagraphs = [...document.querySelectorAll('p')]
      .map((p) => p.innerText.trim())
      .filter(Boolean)
      .sort((a, b) => b.length - a.length)
      .slice(0, 3)
      .join("\n");
    const text = [title, description, largestParagraphs].filter(Boolean).join("\n");
    const images = [...document.querySelectorAll('img')]
      .map((img) => img.src)
      .filter(Boolean)
      .slice(0, 3);

    return {
      url: window.location.href,
      platform: "unknown",
      content_type: images.length ? "image" : "article",
      text_content: text,
      image_urls: images,
      author: null,
      dwell_seconds: dwellSeconds,
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

  window.addEventListener(
    "beforeunload",
    () => {
      for (const [el, startedAt] of visibilityMap.entries()) {
        void maybeCapture(el, startedAt);
      }
      visibilityMap.clear();
    },
    { passive: true }
  );
})();
