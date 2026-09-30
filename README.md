# Pérégrination

Landing + explorable worlds for **Pérégrination — Le Voyage des Curiosités**: turn a Renaissance painting into a world you can walk through.

## Develop

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
npm run preview
```

Production assets ship from `public/` (copied into `dist/` on build). Offline bake caches, design zips, and full-res frescoes stay out of git via `.gitignore`.

## Deploy (GitHub → Vercel or Cloudflare)

### Vercel
1. Import the GitHub repo.
2. Framework preset: **Vite** (or leave auto).
3. Build command: `npm run build` · Output: `dist`
4. `vercel.json` already sets long-cache headers for `/assets` and `/data`, plus SPA rewrites.

### Cloudflare Pages
1. Connect the repo.
2. Build command: `npm run build` · Output directory: `dist`
3. `public/_headers` and `public/_redirects` are copied into `dist` for cache + SPA routing.
4. Optional: `wrangler.toml` sets `pages_build_output_dir = "dist"`.

### Performance notes
- Landing JS stays free of Three.js; `/world/*` lazy-loads the 3D chunk.
- Hero LCP planes are preloaded; secondary parallax / videos use lazy / `preload="none"`.
- Touch / low-power devices use a lite Arnolfini / Athens path (capped textures, unlit materials).
- Fonts load non-blocking (`display=swap` + preload-as-style).

Product and architecture: [docs/PROJECT.md](docs/PROJECT.md).
