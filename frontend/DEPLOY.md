# MemoryFeed Web Deploy (React + TypeScript)

## 1) Local dev

```bash
cd frontend
npm install
npm run dev
```

Open: `http://localhost:5173`

## 2) Type safety check

```bash
cd frontend
npm run typecheck
```

## 3) Production build

```bash
cd frontend
npm run build
```

Output folder: `frontend/dist`

## 4) Public deploy (single URL with backend)

From project root:

```bash
memoryfeed serve-web --host 0.0.0.0 --port 7749
```

Or script:

- Windows: `.\deploy_web.ps1`
- Linux/macOS: `bash deploy_web.sh`

Public URL:

`http://<server-ip>:7749`
