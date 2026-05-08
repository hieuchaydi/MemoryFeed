# Extension Permissions

MemoryFeed extension permissions are intentionally scoped to explicit targets.

## Permissions

- `storage`: Store local badge counters and last capture/debug status.
- `tabs`: Read active tab metadata for manual "Capture current tab" actions.
- `activeTab` (Chromium only): Temporary active-tab access for user-triggered capture.
- `scripting` (Chromium only): Inject lightweight extractor for manual capture on the active tab.

## Host Permissions

- `http://localhost:7749/*`: Send capture/search requests to the local MemoryFeed backend.
- `https://www.facebook.com/*`: Capture visible Facebook feed posts.
- `https://x.com/*`: Capture visible X feed posts.
- `https://twitter.com/*`: Capture visible legacy Twitter URLs.
- `https://www.youtube.com/*`: Capture YouTube watch context.
- `https://www.linkedin.com/*`: Capture LinkedIn feed posts.
- `https://www.tiktok.com/*`: Capture TikTok feed/video entries.

No wildcard `https://*/*` host permission is used.
