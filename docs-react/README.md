# MemoryFeed Docs React

`docs-react/` là project tài liệu độc lập cho MemoryFeed. Nội dung đã bao gồm:

- Tổng quan sản phẩm và kiến trúc.
- Quickstart local/public web.
- Active Feed, heat, decay, resurfacing và archive flow.
- API endpoints đầy đủ.
- CLI commands đầy đủ.
- MCP tools cho Claude/Cursor/agents.
- Browser extension load flow.
- Storage, logging, privacy và provider env vars.
- Deploy docs trên Vercel.

## Chạy local

```bash
npm install
npm run dev
```

Default URL: `http://localhost:4173`

## Build

```bash
npm run build
```

Output: `dist/`

## Preview production build

```bash
npm run preview
```

## Vercel settings

Nếu deploy từ monorepo hiện tại:

- Framework Preset: `Vite`
- Root Directory: `docs-react`
- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: `npm install`

Nếu đã tách `docs-react/` thành repo riêng:

- Framework Preset: `Vite`
- Root Directory: `./`
- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: `npm install`

## Cập nhật nội dung

- Nội dung chính nằm ở `src/content/docsContent.ts`.
- Layout nằm ở `src/App.tsx`.
- Theme/style nằm ở `src/styles.css`.
- Assets public nằm ở `public/`.

## Không commit

- `node_modules/`
- `dist/`
