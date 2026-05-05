# Standalone Deploy Checklist (Vercel)

Tài liệu này dùng cho `docs-react/`, dù folder còn nằm trong monorepo hay đã tách thành repo riêng.

## Deploy từ monorepo hiện tại

1. Framework Preset: `Vite`
2. Root Directory: `docs-react`
3. Build Command: `npm run build`
4. Output Directory: `dist`
5. Install Command: `npm install`
6. Node.js: `20.x` hoặc mới hơn

## Deploy sau khi tách thành repo riêng

1. Framework Preset: `Vite`
2. Root Directory: `./`
3. Build Command: `npm run build`
4. Output Directory: `dist`
5. Install Command: `npm install`
6. Node.js: `20.x` hoặc mới hơn

## Validate local trước khi push

```bash
npm install
npm run build
npm run preview
```

## Vì sao build script gọi Vite qua Node

`package.json` dùng:

```bash
node ./node_modules/vite/bin/vite.js build
```

Cách này tránh lỗi `node_modules/.bin/vite: Permission denied` trên Linux CI/Vercel.

## File bắt buộc

- `package.json`
- `package-lock.json`
- `vercel.json`
- `index.html`
- `src/*`
- `public/*`

## File không commit

- `node_modules/`
- `dist/`

## Lỗi thường gặp

### `node_modules/.bin/vite: Permission denied`

Đã xử lý bằng build script gọi Vite qua `node`.

### Refresh page bị 404

Giữ cấu hình `rewrites` trong `vercel.json`.

### Thiếu ảnh/GIF

Đặt assets trong `public/`, ví dụ `public/assets/quickstart-demo.gif`.

### Docs thiếu nội dung sau khi core app thay đổi

Cập nhật `src/content/docsContent.ts`, rồi chạy `npm run build` để xác nhận.
