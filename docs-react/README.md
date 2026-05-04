# MemoryFeed Docs (Standalone)

React + Vite docs site, ready to push as an independent repo and deploy on Vercel immediately.

## Quickstart

```bash
npm install
npm run dev
```

Default URL: `http://localhost:4173`

## Build

```bash
npm run build
```

Output: `dist`

## Vercel Settings (exact)

Use these values in Vercel:

1. `Application Preset`: `Vite`
2. `Root Directory`: `./`
3. `Build Command`: `npm run build`
4. `Output Directory`: `dist`
5. `Install Command`: `npm install`

`vercel.json` is already included at repo root.

## Lift This Folder Into Its Own Repo

If this folder is still inside a monorepo, copy only `docs-react/` out, then:

```bash
git init
git add .
git commit -m "init docs site"
git branch -M master
git remote add origin <your-repo-url>
git push -u origin master
```

Then import that repo into Vercel and deploy.

## Common Issues

- `node_modules/.bin/vite: Permission denied`: handled by build script using `node ./node_modules/vite/bin/vite.js build`.
- Build hangs at install: verify Vercel root is `./` for this standalone repo.
- Refresh 404: keep `rewrites` in `vercel.json`.
