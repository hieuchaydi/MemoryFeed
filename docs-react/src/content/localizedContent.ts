import {
  hero as viHero,
  navItems as viNavItems,
  sections as viSections,
  type CommandBlock,
  type DocsSection,
  type InfoCard,
} from "./docsContent";

export type { CommandBlock, DocsSection, InfoCard } from "./docsContent";

export type Locale = "vi" | "en" | "zh";

type DocsContent = {
  hero: {
    title: string;
    description: string;
    badges: string[];
  };
  navItems: Array<{ id: string; label: string }>;
  sections: DocsSection[];
};

const viContent: DocsContent = {
  hero: viHero,
  navItems: viNavItems,
  sections: viSections,
};

const enContent: DocsContent = {
  hero: {
    title: "MemoryFeed Docs",
    description:
      "Standalone production documentation for MemoryFeed: local-first memory, lifecycle engine, namespace isolation, encryption modes, MCP, API, CLI, extension, and operations.",
    badges: ["Local-first", "Lifecycle", "Namespace Isolation", "Encryption Ready", "MCP Ready"],
  },
  navItems: [
    { id: "overview", label: "Overview" },
    { id: "quickstart", label: "Quickstart" },
    { id: "architecture", label: "Architecture" },
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
  ],
  sections: [
    {
      id: "overview",
      title: "Product Overview",
      kicker: "MemoryFeed is not only storage. It proactively resurfaces memory at the right moment.",
      body: [
        "MemoryFeed captures social content after dwell time, normalizes data, stores locally in SQLite, and builds semantic indexes with LanceDB.",
        "The latest release adds Active Feed: each memory has heat, decay, resurfacing metadata and can be brought back from current context via web app, CLI, MCP, or external integrations.",
        "User data stays on local machine. Gemini/Groq is used only when API keys are configured for vision or rewrite/summarization; text capture still works when providers fail.",
      ],
      cards: [
        { title: "Capture", lines: ["Chrome/Edge/Brave and Firefox extensions send capture after 3 seconds of dwell."] },
        { title: "Retrieve", lines: ["Hybrid search combines FTS5 BM25 and semantic vectors, merged by Reciprocal Rank Fusion."] },
        { title: "Resurface", lines: ["Active Feed and /api/resurface proactively pull memory relevant to current context."] },
      ],
    },
    {
      id: "quickstart",
      title: "Quickstart",
      kicker: "Run local dev or public web with one command.",
      commands: [
        { title: "Windows", code: ".\\quickstart.ps1" },
        { title: "macOS / Linux", code: "bash quickstart.sh" },
        { title: "Public web", code: "bash deploy_web.sh\n# or Windows\n.\\deploy_web.ps1" },
        { title: "Manual dev", code: "memoryfeed serve\ncd frontend && npm run dev" },
        { title: "Encryption migrate", code: "memoryfeed encrypt-migrate --limit 2000" },
      ],
      checklist: [
        "Python 3.12+",
        "Node.js 20+",
        "GEMINI_API_KEY for vision/multimodal understanding",
        "GROQ_API_KEY for Qwen rewrite/summarization",
        "Visual Studio C++ Build Tools or GCC/Clang for native acceleration",
        "Production recommendation: MEMORY_ENCRYPTION_MODE=compat -> migrate -> strict",
      ],
    },
    {
      id: "architecture",
      title: "Architecture",
      kicker: "Modules are split clearly so capture, search, feed, and integration do not depend on UI.",
      cards: [
        { title: "extension/chrome", lines: ["Chromium extension captures posts, images, and metadata from browser."] },
        { title: "extension/firefox", lines: ["Firefox temporary add-on package."] },
        { title: "backend", lines: ["FastAPI server, capture normalization, SQLite store, searcher, indexer, vision queue, MCP server, metrics/readiness."] },
        { title: "frontend", lines: ["React + Vite operator console: Search, Active Feed, Timeline, Stats, Ops dashboard."] },
        { title: "native", lines: ["pybind11 C++ module for normalize text and RRF top-k acceleration."] },
        { title: "docs-react", lines: ["Standalone docs site, independently deployed on Vercel."] },
      ],
    },
    {
      id: "active-memory",
      title: "Active Memory and Interest Graph",
      kicker: "Move from passive archive to a second brain with heat, decay, and resurfacing.",
      body: [
        "Each memory has heat, last_surfaced, surfaced_count and archived_at. Heat rises when memory matches new capture or current context; heat drops daily for long-unsurfaced memory.",
        "GET /api/feed returns feed ranked by heat, recency, dwell time, star state, resurfacing gap and mode: default, focus, light, explore.",
        "POST /api/resurface accepts current context like code snippet, article, or draft email, then returns related memory and can bump heat.",
      ],
      cards: [
        { title: "Heat", lines: ["Personal priority value. Related memory is reheated instead of buried in timeline noise."] },
        { title: "Decay", lines: ["Daily decay job is tracked in meta database to avoid duplicate decay after server restart."] },
        { title: "Review", lines: ["Old, cold and long-unsurfaced memory is marked needs_review so users can archive or keep it."] },
      ],
    },
    {
      id: "api",
      title: "Core API",
      kicker: "FastAPI exposes API-first contract under /api/*.",
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
      kicker: "Use memoryfeed from terminal for operations, search, and resurfacing tests.",
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
      title: "MCP for Claude/Cursor/agents",
      kicker: "MCP is the foundation for ambient intelligence outside the web app.",
      commands: [
        { title: "Stdio", code: "memoryfeed mcp --transport stdio" },
        { title: "Streamable HTTP", code: "memoryfeed mcp --transport streamable-http --host 127.0.0.1 --port 7748 --path /mcp" },
        { title: "Tools", code: "detect_stack\ncheck_project_health\nget_memoryfeed_stats\nget_runtime_perf\nsearch_memory\ntimeline_memories\nactive_memory_feed\nresurface_memory_context" },
      ],
      body: [
        "Agents can call search_memory for manual retrieval, or resurface_memory_context to fetch memory related to current file/code/email context.",
      ],
    },
    {
      id: "extension",
      title: "Browser Extension",
      kicker: "Extension is the capture layer. Backend should run at http://localhost:7749.",
      checklist: [
        "Chromium: open chrome://extensions, enable Developer mode, Load unpacked, choose extension/chrome/.",
        "Edge: open edge://extensions and load extension/chrome/.",
        "Brave: open brave://extensions and load extension/chrome/.",
        "Firefox: open about:debugging#/runtime/this-firefox, Load Temporary Add-on, choose extension/firefox/manifest.json.",
        "Capture endpoint returns quickly; vision and embedding run in background queue.",
      ],
    },
    {
      id: "storage",
      title: "Storage, Logging, and Privacy",
      kicker: "By default all user data stays on local machine.",
      commands: [
        { title: "Storage paths", code: "~/.memoryfeed/memoryfeed.db\n~/.memoryfeed/lancedb/\n~/.memoryfeed/images/\n~/.memoryfeed/images_enc/\n~/.memoryfeed/keys/master.key" },
        { title: "Logging", code: "~/.memoryfeed/logs/memoryfeed.log\nMEMORYFEED_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR\nMEMORYFEED_LOG_FORMAT=plain|json" },
        { title: "Model env", code: "GEMINI_API_KEY=...\nGROQ_API_KEY=...\nMEMORYFEED_GEMINI_MODEL=gemini-2.5-flash\nMEMORYFEED_GROQ_MODEL=qwen/qwen3-32b" },
        { title: "Encryption env", code: "MEMORY_ENCRYPTION_MODE=off|compat|strict\nMEMORY_ENCRYPTION_KEY=<base64url-32-byte>\nMEMORY_ENCRYPTION_KEY_FILE=~/.memoryfeed/keys/master.key" },
      ],
      checklist: [
        "SQLite runs in WAL mode and FTS5.",
        "LanceDB stores semantic vectors locally.",
        "Image cache is stored under ~/.memoryfeed/images to avoid dead remote image links.",
        "No telemetry.",
        "If Gemini/Groq fails, text capture still persists and pipeline degrades gracefully.",
        "Queue retry/backoff + dead-letter persistence for indexer/vision.",
        "Readiness on /readyz and metrics on /metrics.",
      ],
    },
    {
      id: "ops",
      title: "Ops Dashboard and Reliability",
      kicker: "Monitor memory runtime health in real time.",
      body: [
        "The /ops page in frontend shows readiness, queue status, dead letters, heatmap cells, aging actions, and lifecycle events.",
        "GET /api/perf returns queue metrics, provider breaker states, and dead-letter snapshot.",
        "Dead-letter records are persisted in SQLite for audit and controlled replay.",
      ],
      commands: [
        { title: "Web Ops", code: "Frontend route: /ops" },
        { title: "Readiness", code: "GET /readyz" },
        { title: "Metrics", code: "GET /metrics" },
        { title: "Perf", code: "GET /api/perf" },
      ],
      checklist: [
        "Track queue backlog and dead-letter growth anomalies.",
        "Check provider circuit breaker state when Gemini/Groq fail repeatedly.",
        "Use MEMORYFEED_LOG_FORMAT=json in production for log pipeline ingestion.",
      ],
    },
    {
      id: "security",
      title: "Security and At-rest Encryption",
      kicker: "Production requires safe encryption rollout without downtime.",
      body: [
        "MemoryFeed supports off/compat/strict mode. Recommended rollout: compat first for legacy reads, migrate, then strict.",
        "Master key is loaded from OS keyring first; local key file is fallback only.",
        "Media migration endpoint moves cached images into encrypted storage in controlled batches and writes migration manifest.",
      ],
      commands: [
        { title: "Mode rollout", code: "MEMORY_ENCRYPTION_MODE=compat\nmemoryfeed serve\nPOST /api/admin/encryption/migrate\nPOST /api/admin/encryption/migrate-media\nMEMORY_ENCRYPTION_MODE=strict" },
        { title: "Encryption env", code: "MEMORY_ENCRYPTION_MODE=off|compat|strict\nMEMORY_ENCRYPTION_ALGO=xchacha20poly1305|chacha20poly1305\nMEMORY_ENCRYPTION_KEY=<base64url-32-byte>\nMEMORY_ENCRYPTION_KEY_FILE=~/.memoryfeed/keys/master.key" },
      ],
      checklist: [
        "Back up DB and image folders before migration.",
        "Run migration in batches to avoid IO spikes.",
        "Verify /api/stats.at_rest_encryption before and after rollout.",
        "Enable strict only after legacy plaintext is migrated.",
      ],
    },
    {
      id: "testing",
      title: "Testing and Evaluation",
      kicker: "v1.1.0 target is regression-safe behavior with measurable quality.",
      body: [
        "Unit tests cover capture normalization, selector registry, crypto, retention, safety, and ranking.",
        "Integration tests validate queues, dead letters, migration compatibility, and admin endpoints.",
        "Evaluation suite combines fixture replay and benchmark scenarios to catch capture/retrieval regressions before release.",
      ],
      commands: [
        { title: "Backend tests", code: "python -m pytest -q" },
        { title: "Targeted regression", code: "python -m pytest tests/test_crypto_at_rest.py tests/test_selector_registry.py tests/test_reliability_dashboard.py -q" },
        { title: "Frontend build check", code: "cd frontend && npm run build" },
        { title: "Research eval", code: "python -m pytest tests/test_research_eval.py tests/test_benchmark_evaluation.py -q" },
      ],
      checklist: [
        "Each PR should pass unit + integration + frontend build.",
        "Track capture confidence drift via fixture replay.",
        "Run regression suite on release branch before tagging.",
      ],
    },
    {
      id: "release",
      title: "CI/CD and Release Runbook",
      kicker: "Separate quality, migration, and rollback gates.",
      body: [
        "Recommended pipeline stages: lint/typecheck, tests, artifact builds, release-candidate smoke.",
        "Production rollout should follow blue/green or canary where multi-node deployments exist.",
        "Create release tags only after backup, migration verification, readiness/metrics, and extension replay checks pass.",
      ],
      commands: [
        { title: "Suggested workflow", code: ".github/workflows/ci.yml\n- backend-test\n- frontend-build\n- docs-build\n- fixture-replay\n- release-smoke" },
        { title: "Versioning", code: "v1.1.0-rc.1 -> v1.1.0\nUse Conventional Commits for feat/fix/docs" },
        { title: "Rollback", code: "1) set MEMORY_ENCRYPTION_MODE=compat\n2) restore latest backup snapshot\n3) restart memoryfeed serve\n4) verify /readyz + /metrics" },
      ],
      checklist: [
        "Keep PRODUCTION.md, MONITORING.md, BACKUP_STRATEGY.md updated with every release.",
        "Publish clear changelog with breaking/non-breaking notes.",
        "Run rollback drill before enabling public mode.",
      ],
    },
    {
      id: "deploy",
      title: "Deploy docs-react standalone",
      kicker: "docs-react is an independent project and can be published as a separate repo.",
      commands: [
        { title: "Local docs", code: "cd docs-react\nnpm install\nnpm run build\nnpm run preview" },
        { title: "Vercel settings", code: "Framework Preset: Vite\nRoot Directory: docs-react\nBuild Command: npm run build\nOutput Directory: dist\nInstall Command: npm install" },
        { title: "If split into dedicated repo", code: "git init\ngit add .\ngit commit -m \"init docs site\"\ngit branch -M master\ngit remote add origin <repo-url>\ngit push -u origin master" },
      ],
      checklist: [
        "Keep vercel.json in docs-react.",
        "Do not commit node_modules/ or dist/.",
        "Build script uses node ./node_modules/vite/bin/vite.js build to avoid permission issues on Linux CI.",
        "Demo assets are in public/assets/.",
      ],
    },
  ],
};

const zhHero = {
  title: "MemoryFeed 文档",
  description:
    "MemoryFeed 独立文档：本地优先社交记忆、Active Feed、上下文重现、MCP、API、CLI、浏览器扩展与部署。",
  badges: ["本地优先", "Active Feed", "MCP 就绪", "React + FastAPI"],
};

const zhNavItems = [
  { id: "overview", label: "概览" },
  { id: "quickstart", label: "快速开始" },
  { id: "architecture", label: "架构" },
  { id: "active-memory", label: "主动记忆" },
  { id: "api", label: "API" },
  { id: "cli", label: "CLI" },
  { id: "mcp", label: "MCP" },
  { id: "extension", label: "扩展" },
  { id: "storage", label: "存储" },
  { id: "deploy", label: "部署" },
];

const zhContent: DocsContent = {
  hero: zhHero,
  navItems: zhNavItems,
  sections: [
    {
      id: "overview",
      title: "产品概览",
      kicker: "MemoryFeed 不只是存档，它会在合适时机主动唤回记忆。",
      body: [
        "MemoryFeed 在停留时间达到后抓取社交内容，标准化数据，存入本地 SQLite，并用 LanceDB 建立语义索引。",
        "新版本加入 Active Feed：每条记忆都有 heat、decay、resurfacing 元数据，可基于当前上下文在 Web、CLI、MCP 或外部集成中被重现。",
        "用户数据默认保存在本地。仅在配置 API key 时才会调用 Gemini/Groq 做视觉或改写/总结；即使模型失败，文本抓取仍可继续。",
      ],
      cards: [
        { title: "抓取", lines: ["Chrome/Edge/Brave 与 Firefox 扩展会在停留 3 秒后发送抓取。"] },
        { title: "检索", lines: ["混合搜索结合 FTS5 BM25 与语义向量，并通过 Reciprocal Rank Fusion 合并。"] },
        { title: "重现", lines: ["Active Feed 与 /api/resurface 会主动拉取与当前上下文相关的记忆。"] },
      ],
    },
    {
      id: "quickstart",
      title: "快速开始",
      kicker: "一条命令即可运行本地开发或公开网页。",
      commands: [
        { title: "Windows", code: ".\\quickstart.ps1" },
        { title: "macOS / Linux", code: "bash quickstart.sh" },
        { title: "公开网页", code: "bash deploy_web.sh\n# 或 Windows\n.\\deploy_web.ps1" },
        { title: "手动开发", code: "memoryfeed serve\ncd frontend && npm run dev" },
      ],
      checklist: [
        "Python 3.12+",
        "Node.js 20+",
        "GEMINI_API_KEY（视觉/多模态理解）",
        "GROQ_API_KEY（Qwen 改写/总结）",
        "若需原生加速：Visual Studio C++ Build Tools 或 GCC/Clang",
      ],
    },
    {
      id: "architecture",
      title: "架构",
      kicker: "模块职责清晰，capture、search、feed 与 integration 均不依赖 UI。",
      cards: [
        { title: "extension/chrome", lines: ["Chromium 扩展从浏览器抓取帖子、图片和元数据。"] },
        { title: "extension/firefox", lines: ["Firefox 临时插件包。"] },
        { title: "backend", lines: ["FastAPI 服务、抓取标准化、SQLite 存储、搜索器、索引器、视觉队列、MCP 服务。"] },
        { title: "frontend", lines: ["React + Vite 控制台：Search、Active Feed、Timeline、Stats。"] },
        { title: "native", lines: ["pybind11 C++ 模块用于文本标准化和 RRF top-k 加速。"] },
        { title: "docs-react", lines: ["独立文档站，可单独部署到 Vercel。"] },
      ],
    },
    {
      id: "active-memory",
      title: "主动记忆与兴趣图谱",
      kicker: "从被动归档升级为具备热度、衰减和重现能力的第二大脑。",
      body: [
        "每条记忆包含 heat、last_surfaced、surfaced_count、archived_at。与新抓取或当前上下文相关时 heat 上升；长期未重现则每日衰减。",
        "GET /api/feed 按 heat、新鲜度、停留时长、收藏状态、重现间隔与 mode（default/focus/light/explore）排序。",
        "POST /api/resurface 接收代码片段、阅读内容或邮件草稿等上下文，返回相关记忆并可提升 heat。",
      ],
      cards: [
        { title: "Heat", lines: ["个人优先级值。相关记忆会被重新加热，而不是淹没在时间线里。"] },
        { title: "Decay", lines: ["每日衰减任务记录在 meta 数据库，避免服务重启后重复衰减。"] },
        { title: "Review", lines: ["旧且冷、长期未重现的记忆会标记为 needs_review，供用户归档或保留。"] },
      ],
    },
    {
      id: "api",
      title: "核心 API",
      kicker: "FastAPI 在 /api/* 下提供 API-first 契约。",
      commands: [
        { title: "抓取", code: "POST /capture\nPOST /api/capture" },
        { title: "搜索", code: "GET /api/search?q=&limit=&days_back=" },
        { title: "Active Feed", code: "GET /api/feed?limit=20&mode=default\nPOST /api/resurface\nPOST /api/feed/surfaced\nPOST /api/feed/archive" },
        { title: "时间线与条目", code: "GET /api/timeline?date=&platform=\nGET /api/items?limit=&offset=&platform=&starred_only=\nPATCH /api/items/{id}" },
        { title: "运维", code: "GET /api/stats\nGET /api/native/status\nGET /api/queues/status\nGET /api/perf\nGET /healthz" },
        { title: "管理", code: "POST /api/admin/export\nPOST /api/admin/import\nDELETE /api/admin/reset?confirm=RESET" },
      ],
    },
    {
      id: "cli",
      title: "CLI",
      kicker: "使用 memoryfeed 在终端完成运维、搜索和重现测试。",
      commands: [
        { title: "服务", code: "memoryfeed serve\nmemoryfeed serve-web --host 0.0.0.0 --port 7749" },
        { title: "搜索", code: "memoryfeed search \"that angry cat meme last week\"\nmemoryfeed timeline\nmemoryfeed items --starred" },
        { title: "主动记忆", code: "memoryfeed feed --mode focus\nmemoryfeed resurface \"Docker networking CNI overlay Cilium\"" },
        { title: "运维", code: "memoryfeed stats\nmemoryfeed perf\nmemoryfeed models" },
        { title: "数据", code: "memoryfeed export\nmemoryfeed import --file ~/.memoryfeed/exports/memoryfeed-export-YYYY-MM-DD.json\nmemoryfeed reset" },
        { title: "构建", code: "memoryfeed build-native\nmemoryfeed build-frontend" },
      ],
    },
    {
      id: "mcp",
      title: "MCP（Claude/Cursor/agents）",
      kicker: "MCP 是 Web 应用之外环境智能能力的基础层。",
      commands: [
        { title: "Stdio", code: "memoryfeed mcp --transport stdio" },
        { title: "Streamable HTTP", code: "memoryfeed mcp --transport streamable-http --host 127.0.0.1 --port 7748 --path /mcp" },
        { title: "工具", code: "detect_stack\ncheck_project_health\nget_memoryfeed_stats\nget_runtime_perf\nsearch_memory\ntimeline_memories\nactive_memory_feed\nresurface_memory_context" },
      ],
      body: [
        "Agent 可以调用 search_memory 手动检索，或调用 resurface_memory_context 获取与当前文件/代码/邮件上下文相关的记忆。",
      ],
    },
    {
      id: "extension",
      title: "浏览器扩展",
      kicker: "扩展是 capture 层，后端需要运行在 http://localhost:7749。",
      checklist: [
        "Chromium：打开 chrome://extensions，开启 Developer mode，Load unpacked，选择 extension/chrome/。",
        "Edge：打开 edge://extensions，加载 extension/chrome/。",
        "Brave：打开 brave://extensions，加载 extension/chrome/。",
        "Firefox：打开 about:debugging#/runtime/this-firefox，Load Temporary Add-on，选择 extension/firefox/manifest.json。",
        "capture 接口快速返回；视觉和 embedding 在后台队列处理。",
      ],
    },
    {
      id: "storage",
      title: "存储、日志与隐私",
      kicker: "默认情况下，所有用户数据都保存在本地机器。",
      commands: [
        { title: "存储路径", code: "~/.memoryfeed/memoryfeed.db\n~/.memoryfeed/lancedb/\n~/.memoryfeed/images/" },
        { title: "日志", code: "~/.memoryfeed/logs/memoryfeed.log\nMEMORYFEED_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR\nMEMORYFEED_LOG_FORMAT=plain|json" },
        { title: "模型环境变量", code: "GEMINI_API_KEY=...\nGROQ_API_KEY=...\nMEMORYFEED_GEMINI_MODEL=gemini-2.5-flash\nMEMORYFEED_GROQ_MODEL=qwen/qwen3-32b" },
      ],
      checklist: [
        "SQLite 使用 WAL 模式与 FTS5。",
        "LanceDB 在本地保存语义向量。",
        "图片缓存位于 ~/.memoryfeed/images，避免远端图片失效。",
        "无遥测。",
        "即使 Gemini/Groq 出错，文本抓取仍会落库，流水线会优雅降级。",
      ],
    },
    {
      id: "deploy",
      title: "独立部署 docs-react",
      kicker: "docs-react 是独立项目，可以单独发布为仓库。",
      commands: [
        { title: "本地文档", code: "cd docs-react\nnpm install\nnpm run build\nnpm run preview" },
        { title: "Vercel 配置", code: "Framework Preset: Vite\nRoot Directory: docs-react\nBuild Command: npm run build\nOutput Directory: dist\nInstall Command: npm install" },
        { title: "拆分为独立仓库", code: "git init\ngit add .\ngit commit -m \"init docs site\"\ngit branch -M master\ngit remote add origin <repo-url>\ngit push -u origin master" },
      ],
      checklist: [
        "保留 docs-react/vercel.json。",
        "不要提交 node_modules/ 或 dist/。",
        "构建脚本使用 node ./node_modules/vite/bin/vite.js build，避免 Linux CI 权限问题。",
        "演示资源放在 public/assets/。",
      ],
    },
  ],
};

const docsContentByLocale: Record<Locale, DocsContent> = {
  vi: viContent,
  en: enContent,
  zh: zhContent,
};

export function getDocsContent(locale: Locale): DocsContent {
  return docsContentByLocale[locale] ?? viContent;
}
