# Standalone Deploy Checklist (Vercel)

This file assumes `docs-react` is already a standalone repo root.

## Required Vercel Configuration

1. Framework Preset: `Vite`
2. Root Directory: `./`
3. Build Command: `npm run build`
4. Output Directory: `dist`
5. Install Command: `npm install`
6. Node.js: `20.x` or newer

## Local Validation Before Push

```bash
npm install
npm run build
```

If build succeeds locally, Vercel should pass with the same commands.

## Why Build Script Uses Node Directly

`package.json` build script is:

```bash
node ./node_modules/vite/bin/vite.js build
```

This avoids Linux executable permission issues on `.bin/vite`.

## Deployment Files That Must Exist

- `package.json`
- `package-lock.json`
- `vercel.json`
- `index.html`
- `src/*`
- `public/*`

## Files That Must Not Be Committed

- `node_modules/`
- `dist/`

## Common Failures

### `node_modules/.bin/vite: Permission denied`
- Fixed by the direct-node build script above.

### App deploys but refresh gives 404
- Keep `rewrites` in `vercel.json`.

### Assets missing
- Keep all images/GIFs inside `public/`.
