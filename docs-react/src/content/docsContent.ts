export type InfoCard = {
  title: string;
  lines: string[];
};

export type CommandBlock = {
  title: string;
  code: string;
};

export type DocsSection = {
  id: string;
  title: string;
  kicker: string;
  body?: string[];
  cards?: InfoCard[];
  commands?: CommandBlock[];
  checklist?: string[];
};

export const hero = {
  title: "MemoryFeed Docs",
  description:
    "Tài liệu độc lập cho MemoryFeed production: local-first social memory, lifecycle engine, namespace isolation, encryption mode, MCP, API, CLI, extension và vận hành.",
  badges: ["Local-first", "Lifecycle", "Namespace Isolation", "Encryption Ready", "MCP Ready"],
};

export const navItems = [
  { id: "overview", label: "Tổng quan" },
  { id: "quickstart", label: "Quickstart" },
  { id: "architecture", label: "Kiến trúc" },
  { id: "active-memory", label: "Active Memory" },
  { id: "api", label: "API" },
  { id: "cli", label: "CLI" },
  { id: "mcp", label: "MCP" },
  { id: "extension", label: "Extension" },
  { id: "storage", label: "Storage" },
  { id: "ops", label: "Ops" },
  { id: "security", label: "Security" },
  { id: "testing", label: "Testing" },
  { id: "release", label: "Release" },
  { id: "deploy", label: "Deploy" },
];

export const sections: DocsSection[] = [
  {
    id: "overview",
    title: "Tổng quan sản phẩm",
    kicker: "MemoryFeed không chỉ lưu trữ. Nó chủ động gợi lại memory đúng lúc.",
    body: [
      "MemoryFeed capture nội dung mạng xã hội sau dwell time, chuẩn hóa dữ liệu, lưu local trong SQLite và lập chỉ mục semantic bằng LanceDB.",
      "Phiên bản mới thêm Active Feed: mỗi memory có heat, decay, resurfacing metadata và có thể được gợi lại theo ngữ cảnh hiện tại từ web app, CLI, MCP hoặc integration bên ngoài.",
      "Dữ liệu người dùng nằm trên máy local. Gemini/Groq chỉ được dùng khi cấu hình API key cho vision hoặc rewrite/summarization; text capture vẫn chạy khi provider lỗi.",
    ],
    cards: [
      { title: "Capture", lines: ["Chrome/Edge/Brave và Firefox extension gửi capture sau 3 giây dwell."] },
      { title: "Retrieve", lines: ["Hybrid search kết hợp FTS5 BM25 và semantic vectors, merge bằng Reciprocal Rank Fusion."] },
      { title: "Resurface", lines: ["Active Feed và /api/resurface chủ động kéo memory liên quan đến ngữ cảnh hiện tại."] },
    ],
  },
  {
    id: "quickstart",
    title: "Quickstart",
    kicker: "Chạy local dev hoặc public web bằng một lệnh.",
    commands: [
      { title: "Windows", code: ".\\quickstart.ps1" },
      { title: "macOS / Linux", code: "bash quickstart.sh" },
      { title: "Public web", code: "bash deploy_web.sh\n# hoặc Windows\n.\\deploy_web.ps1" },
      { title: "Manual dev", code: "memoryfeed serve\ncd frontend && npm run dev" },
      { title: "Encryption migrate", code: "memoryfeed encrypt-migrate --limit 2000" },
    ],
    checklist: [
      "Python 3.12+",
      "Node.js 20+",
      "GEMINI_API_KEY nếu cần vision/multimodal understanding",
      "GROQ_API_KEY nếu cần Qwen rewrite/summarization",
      "Visual Studio C++ Build Tools hoặc GCC/Clang nếu muốn native acceleration",
      "Khuyến nghị production: MEMORY_ENCRYPTION_MODE=compat -> migrate -> strict",
    ],
  },
  {
    id: "architecture",
    title: "Kiến trúc",
    kicker: "Các module được tách rõ để capture, search, feed và integration không phụ thuộc UI.",
    cards: [
      { title: "extension/chrome", lines: ["Chromium extension capture bài viết, ảnh và metadata từ browser."] },
      { title: "extension/firefox", lines: ["Firefox temporary add-on package."] },
      { title: "backend", lines: ["FastAPI server, capture normalization, SQLite store, searcher, indexer, vision queue, MCP server, metrics/readiness."] },
      { title: "frontend", lines: ["React + Vite operator console: Search, Active Feed, Timeline, Stats, Ops dashboard."] },
      { title: "native", lines: ["pybind11 C++ module cho normalize text và RRF top-k acceleration."] },
      { title: "docs-react", lines: ["Standalone docs site, deploy độc lập trên Vercel."] },
    ],
  },
  {
    id: "active-memory",
    title: "Active Memory và Interest Graph",
    kicker: "Chuyển từ passive archive sang second brain có nhiệt, quên và gợi lại.",
    body: [
      "Mỗi memory có heat, last_surfaced, surfaced_count và archived_at. Heat tăng khi memory liên quan đến capture mới hoặc context hiện tại; heat giảm mỗi ngày cho memory lâu không surfaced.",
      "GET /api/feed trả về feed xếp hạng theo heat, độ mới, dwell time, star state, resurfacing gap và mode: default, focus, light, explore.",
      "POST /api/resurface nhận context hiện tại như đoạn code, bài đang đọc hoặc email đang viết, rồi trả về memory liên quan và có thể bump heat.",
    ],
    cards: [
      { title: "Heat", lines: ["Giá trị ưu tiên cá nhân. Memory liên quan được hâm nóng lại thay vì bị chôn trong timeline."] },
      { title: "Decay", lines: ["Job decay chạy theo ngày trong database meta để tránh decay lặp khi restart server."] },
      { title: "Review", lines: ["Memory cũ, nguội và lâu không surfaced được đánh dấu needs_review để user archive hoặc giữ lại."] },
    ],
  },
  {
    id: "api",
    title: "API chính",
    kicker: "FastAPI expose API-first contract dưới /api/*.",
    commands: [
      { title: "Capture", code: "POST /capture\nPOST /api/capture" },
      { title: "Search", code: "GET /api/search?q=&limit=&days_back=" },
      { title: "Active Feed", code: "GET /api/feed?limit=20&mode=default\nPOST /api/resurface\nPOST /api/feed/surfaced\nPOST /api/feed/archive" },
      { title: "Timeline & Items", code: "GET /api/timeline?date=&platform=\nGET /api/items?limit=&offset=&platform=&starred_only=\nPATCH /api/items/{id}" },
      { title: "Ops", code: "GET /api/stats\nGET /api/native/status\nGET /api/queues/status\nGET /api/perf\nGET /healthz\nGET /readyz\nGET /metrics" },
      { title: "Admin", code: "POST /api/admin/export\nPOST /api/admin/import\nGET /api/admin/dead-letters\nPOST /api/admin/encryption/migrate\nDELETE /api/admin/reset?confirm=RESET" },
    ],
  },
  {
    id: "cli",
    title: "CLI",
    kicker: "Dùng memoryfeed để vận hành, search và test resurfacing từ terminal.",
    commands: [
      { title: "Serve", code: "memoryfeed serve\nmemoryfeed serve-web --host 0.0.0.0 --port 7749" },
      { title: "Search", code: "memoryfeed search \"that angry cat meme last week\"\nmemoryfeed timeline\nmemoryfeed items --starred" },
      { title: "Active Memory", code: "memoryfeed feed --mode focus\nmemoryfeed resurface \"Docker networking CNI overlay Cilium\"" },
      { title: "Ops", code: "memoryfeed stats\nmemoryfeed perf\nmemoryfeed models\nmemoryfeed dead-letters --limit 100" },
      { title: "Data", code: "memoryfeed export\nmemoryfeed import --file ~/.memoryfeed/exports/memoryfeed-export-YYYY-MM-DD.json\nmemoryfeed reset" },
      { title: "Build", code: "memoryfeed build-native\nmemoryfeed build-frontend" },
      { title: "Security", code: "memoryfeed encrypt-migrate --limit 2000" },
    ],
  },
  {
    id: "mcp",
    title: "MCP cho Claude/Cursor/agents",
    kicker: "MCP là nền tảng cho ambient intelligence bên ngoài web app.",
    commands: [
      { title: "Stdio", code: "memoryfeed mcp --transport stdio" },
      { title: "Streamable HTTP", code: "memoryfeed mcp --transport streamable-http --host 127.0.0.1 --port 7748 --path /mcp" },
      { title: "Tools", code: "detect_stack\ncheck_project_health\nget_memoryfeed_stats\nget_runtime_perf\nsearch_memory\ntimeline_memories\nactive_memory_feed\nresurface_memory_context" },
    ],
    body: [
      "Agent có thể gọi search_memory để truy hồi thủ công, hoặc resurface_memory_context để lấy memory liên quan đến file/code/email/ngữ cảnh hiện tại.",
    ],
  },
  {
    id: "extension",
    title: "Browser Extension",
    kicker: "Extension là capture layer. Backend cần chạy ở http://localhost:7749.",
    checklist: [
      "Chromium: mở chrome://extensions, bật Developer mode, Load unpacked, chọn extension/chrome/.",
      "Edge: mở edge://extensions và load cùng thư mục extension/chrome/.",
      "Brave: mở brave://extensions và load cùng thư mục extension/chrome/.",
      "Firefox: mở about:debugging#/runtime/this-firefox, Load Temporary Add-on, chọn extension/firefox/manifest.json.",
      "Capture endpoint trả nhanh; vision và embedding chạy trong background queue.",
    ],
  },
  {
    id: "storage",
    title: "Storage, logging và privacy",
    kicker: "Mặc định mọi dữ liệu user ở local machine.",
    commands: [
      { title: "Storage paths", code: "~/.memoryfeed/memoryfeed.db\n~/.memoryfeed/lancedb/\n~/.memoryfeed/images/\n~/.memoryfeed/images_enc/\n~/.memoryfeed/keys/master.key" },
      { title: "Logging", code: "~/.memoryfeed/logs/memoryfeed.log\nMEMORYFEED_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR\nMEMORYFEED_LOG_FORMAT=plain|json" },
      { title: "Model env", code: "GEMINI_API_KEY=...\nGROQ_API_KEY=...\nMEMORYFEED_GEMINI_MODEL=gemini-2.5-flash\nMEMORYFEED_GROQ_MODEL=qwen/qwen3-32b" },
      { title: "Encryption env", code: "MEMORY_ENCRYPTION_MODE=off|compat|strict\nMEMORY_ENCRYPTION_KEY=<base64url-32-byte>\nMEMORY_ENCRYPTION_KEY_FILE=~/.memoryfeed/keys/master.key" },
    ],
    checklist: [
      "SQLite chạy WAL mode và FTS5.",
      "LanceDB lưu semantic vectors local.",
      "Image cache lưu dưới ~/.memoryfeed/images để tránh remote image chết.",
      "Không telemetry.",
      "Nếu Gemini/Groq lỗi, text capture vẫn lưu và pipeline degrade gracefully.",
      "Queue retry/backoff + dead-letter persistence cho indexer/vision.",
      "Readiness qua /readyz và metrics qua /metrics.",
    ],
  },
  {
    id: "ops",
    title: "Ops Dashboard và Reliability",
    kicker: "Giám sát trạng thái memory runtime theo thời gian thực.",
    body: [
      "Trang /ops trong frontend hiển thị readiness, queue status, dead-letters, heatmap cells, aging actions và lifecycle events.",
      "GET /api/perf trả queue metrics + provider breaker states + dead-letter snapshot.",
      "Dead-letter records lưu persistent trong SQLite để có thể audit và replay có kiểm soát.",
    ],
    commands: [
      { title: "Web Ops", code: "Frontend route: /ops" },
      { title: "Readiness", code: "GET /readyz" },
      { title: "Metrics", code: "GET /metrics" },
      { title: "Perf", code: "GET /api/perf" },
    ],
    checklist: [
      "Theo dõi queue backlog và dead-letter tăng bất thường.",
      "Kiểm tra provider circuit breaker nếu Gemini/Groq lỗi liên tục.",
      "Bật MEMORYFEED_LOG_FORMAT=json trong production để ingest vào log pipeline.",
    ],
  },
  {
    id: "security",
    title: "Security và At-rest Encryption",
    kicker: "Production cần mã hóa dữ liệu nhạy cảm + migration an toàn, không gián đoạn.",
    body: [
      "MemoryFeed hỗ trợ mode off/compat/strict. Khuyến nghị rollout qua compat trước để đọc được dữ liệu cũ, sau đó migrate rồi chuyển strict.",
      "Master key ưu tiên lấy từ OS keyring; nếu chưa có thì mới fallback key file local. Không commit key vào repo hoặc image.",
      "Media encryption migration có endpoint riêng để chuyển ảnh cache sang encrypted folder theo batch và có manifest theo dõi tiến trình.",
    ],
    commands: [
      { title: "Mode rollout", code: "MEMORY_ENCRYPTION_MODE=compat\nmemoryfeed serve\n# migrate dữ liệu text + media\nPOST /api/admin/encryption/migrate\nPOST /api/admin/encryption/migrate-media\n# sau khi hoàn tất\nMEMORY_ENCRYPTION_MODE=strict" },
      { title: "Encryption env", code: "MEMORY_ENCRYPTION_MODE=off|compat|strict\nMEMORY_ENCRYPTION_ALGO=xchacha20poly1305|chacha20poly1305\nMEMORY_ENCRYPTION_KEY=<base64url-32-byte>\nMEMORY_ENCRYPTION_KEY_FILE=~/.memoryfeed/keys/master.key" },
    ],
    checklist: [
      "Backup DB + images trước migration.",
      "Chạy migrate theo batch limit để tránh spike IO.",
      "Verify /api/stats.at_rest_encryption trước và sau rollout.",
      "Chỉ bật strict khi plaintext legacy đã xử lý xong.",
    ],
  },
  {
    id: "testing",
    title: "Testing và Evaluation",
    kicker: "Mục tiêu v1.1.0 là regression-safe, đo được quality và reliability.",
    body: [
      "Unit tests tập trung vào capture normalization, selector registry, crypto, retention, safety và search ranking.",
      "Integration tests kiểm tra queue behavior, dead-letter persistence, migration compatibility và admin endpoints.",
      "Evaluation suite dùng fixture replay + benchmark scenarios để phát hiện giảm chất lượng capture/retrieval trước khi release.",
    ],
    commands: [
      { title: "Backend tests", code: "python -m pytest -q" },
      { title: "Targeted regression", code: "python -m pytest tests/test_crypto_at_rest.py tests/test_selector_registry.py tests/test_reliability_dashboard.py -q" },
      { title: "Frontend build check", code: "cd frontend && npm run build" },
      { title: "Research eval", code: "python -m pytest tests/test_research_eval.py tests/test_benchmark_evaluation.py -q" },
    ],
    checklist: [
      "Mỗi PR phải pass unit + integration + build frontend.",
      "Capture confidence drift được theo dõi bằng fixture replay.",
      "Regression suite phải chạy trên branch release trước tag.",
    ],
  },
  {
    id: "release",
    title: "CI/CD và Release Runbook",
    kicker: "Tách rõ quality gate, migration gate và rollback gate.",
    body: [
      "Pipeline nên có 4 stage: lint/typecheck, tests, build artifacts, release candidate smoke.",
      "Release production nên dùng blue/green hoặc canary local cluster nếu có nhiều node sync.",
      "Tag release chỉ tạo sau khi pass checklist backup, migration verify, readiness/metrics và extension fixture replay.",
    ],
    commands: [
      { title: "Suggested workflow", code: ".github/workflows/ci.yml\n- backend-test\n- frontend-build\n- docs-build\n- fixture-replay\n- release-smoke" },
      { title: "Versioning", code: "v1.1.0-rc.1 -> v1.1.0\nfeat/fix/docs commit theo Conventional Commits" },
      { title: "Rollback", code: "1) switch MEMORY_ENCRYPTION_MODE=compat\n2) restore latest backup snapshot\n3) restart memoryfeed serve\n4) verify /readyz + /metrics" },
    ],
    checklist: [
      "Có PRODUCTION.md, MONITORING.md, BACKUP_STRATEGY.md cập nhật cùng release.",
      "Có changelog rõ breaking/non-breaking.",
      "Có rollback drill trước khi mở public mode.",
    ],
  },
  {
    id: "deploy",
    title: "Deploy docs-react độc lập",
    kicker: "docs-react là project riêng, có thể publish như repo độc lập.",
    commands: [
      { title: "Local docs", code: "cd docs-react\nnpm install\nnpm run build\nnpm run preview" },
      { title: "Vercel settings", code: "Framework Preset: Vite\nRoot Directory: docs-react\nBuild Command: npm run build\nOutput Directory: dist\nInstall Command: npm install" },
      { title: "Nếu tách thành repo riêng", code: "git init\ngit add .\ngit commit -m \"init docs site\"\ngit branch -M master\ngit remote add origin <repo-url>\ngit push -u origin master" },
    ],
    checklist: [
      "Giữ vercel.json trong docs-react.",
      "Không commit node_modules/ hoặc dist/.",
      "Build script dùng node ./node_modules/vite/bin/vite.js build để tránh lỗi permission trên Linux CI.",
      "Assets demo nằm trong public/assets/.",
    ],
  },
];

// Backward-compatible exports for older section components that may still be
// imported by local tooling or type checks.
export const introParagraphs = sections.find((section) => section.id === "overview")?.body ?? [];
export const introCards = sections.find((section) => section.id === "overview")?.cards ?? [];
export const quickstartCards =
  sections
    .find((section) => section.id === "quickstart")
    ?.commands?.map((command) => ({ title: command.title, lines: [command.code] })) ?? [];
export const demoIntro =
  "Demo nên thể hiện đủ vòng lặp: extension capture, search fuzzy, Active Feed và context resurfacing.";
export const demoSteps = [
  "Start backend and extension, then open a social feed tab.",
  "Pause on several posts for at least 3 seconds each.",
  "Open MemoryFeed Search and run a fuzzy query.",
  "Open Active Feed and test Resurface context.",
  "Verify that returned memories include source URL, platform, excerpt, heat, and reason.",
];
export const demoOutcome =
  "Expected outcome: users understand MemoryFeed as an active memory layer, not just a passive archive.";
export const deploySteps =
  sections.find((section) => section.id === "deploy")?.commands?.flatMap((command) => command.code.split("\\n")) ?? [];
export const reliabilityPoints = sections.find((section) => section.id === "storage")?.checklist ?? [];
