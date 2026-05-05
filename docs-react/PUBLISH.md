# Publish Docs In 2 Minutes

## 1. Nếu dùng monorepo hiện tại

Import repo hiện tại vào Vercel và dùng settings:

- Framework Preset: `Vite`
- Root Directory: `docs-react`
- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: `npm install`

## 2. Nếu muốn tách docs thành repo riêng

Từ trong folder `docs-react/`:

```bash
git init
git add .
git commit -m "init standalone docs"
git branch -M master
git remote add origin <your-github-repo-url>
git push -u origin master
```

Sau đó import repo mới vào Vercel và dùng settings:

- Framework Preset: `Vite`
- Root Directory: `./`
- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: `npm install`

## 3. Nếu build fail với Vite permission issue

Build script đã xử lý bằng:

```bash
node ./node_modules/vite/bin/vite.js build
```

## 4. Khi cập nhật MemoryFeed core

Cần cập nhật lại `src/content/docsContent.ts` nếu thay đổi một trong các phần sau:

- API endpoint.
- CLI command.
- MCP tool.
- Active Feed/Interest Graph behavior.
- Storage path hoặc env var.
- Extension load flow.
- Deploy flow.
