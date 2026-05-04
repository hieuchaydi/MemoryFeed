# Publish In 2 Minutes

## 1) Push this folder as its own repo

From inside this folder:

```bash
git init
git add .
git commit -m "init standalone docs"
git branch -M master
git remote add origin <your-github-repo-url>
git push -u origin master
```

## 2) Import repo on Vercel

Use these exact values:

- Application Preset: `Vite`
- Root Directory: `./`
- Build Command: `npm run build`
- Output Directory: `dist`
- Install Command: `npm install`

Then click Deploy.

## 3) If build fails with Vite permission issue

Already handled by build script:

```bash
node ./node_modules/vite/bin/vite.js build
```
