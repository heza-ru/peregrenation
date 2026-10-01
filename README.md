# Pérégrination

**Le Voyage des Curiosités.** Turn a Renaissance painting into a world you can walk through, and uncover its curiosities as you go.

Built during **Opus Build Day, Bangalore**.

Live: [peregrenation.vercel.app](https://peregrenation.vercel.app/)

<p>
  <img src="docs/images/hero.jpg" alt="Landing page. Michelangelo’s Creation of Adam, with the title Le Voyage des Curiosités." width="100%">
</p>

The doorway is a scroll through the painting. The worlds on the other side are prepared once, offline, and then explored in the browser. Claude Opus authors the scene. The app only plays it back.

## The app

<table>
  <tr>
    <td width="50%">
      <img src="docs/images/curiosities.jpg" alt="Curiosity cards over an Annunciation, beside a panel that invites you to walk the painting.">
      <br>
      <sub>Curiosities sit on the painting, with a source for each one.</sub>
    </td>
    <td width="50%">
      <img src="docs/images/athens.jpg" alt="First-person view inside Raphael’s School of Athens, with a WASD hint and a found counter.">
      <br>
      <sub>The School of Athens as a hall you can walk. WASD, look, and 21 curiosities.</sub>
    </td>
  </tr>
</table>

<img src="docs/images/gallery.jpg" alt="Gallery titled Choose your voyage, showing The School of Athens and The Last Supper." width="100%">

<sub>Choose a voyage from the gallery, or drop a scan. A scan is matched to a prepared world. It does not build a new one.</sub>

| | |
|---|---|
| Doorway | Full-viewport landing. A construction-drawing preloader gathers a point of light between the fingers, then the hero burns in out of the same starfield used between chapters. |
| Chapters | How it works, curiosities, gallery, export. Each chapter hands off with a fire front, line art, and glitter. |
| Worlds | `/world/:paintingId`. The School of Athens and the Arnolfini Portrait are walkable 3D rooms. The other curated works open as a 2D wander. |
| Share card | Pasting the link in WhatsApp uses [`public/og.jpg`](public/og.jpg). |

## Architecture

Two WebGL stacks, and only one of them is mounted at a time. The doorway uses a custom WebGL2 engine. A world unmounts that canvas and lazy-loads React Three Fiber, so Three.js never sits in the landing bundle.

```
                    ┌─────────────────────────────────────────┐
                    │  Offline, once per painting             │
                    │  Opus  →  scene manifest, entity ids    │
                    │  Python  →  masks, depth, baked meshes  │
                    └──────────────────┬──────────────────────┘
                                       │  data/paintings/<id>/
                                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  Browser                                                         │
│                                                                  │
│   /                          /world/:paintingId                  │
│   Doorway                    Explore (lazy)                      │
│   ├─ preloader               ├─ 3D hall   Athens, Arnolfini      │
│   ├─ SceneEngine (WebGL2)    ├─ 2D wander  the other works       │
│   ├─ Lenis (desktop)         └─ HUD, proximity facts, sources    │
│   └─ Enter painting                                              │
└──────────────────────────────────────────────────────────────────┘
```

Opus decides what a world contains. Code executes that decision. Nothing calls a model per frame, per step, or when someone uploads a scan.

```
src/
  app/          routes, world shell
  boot/         doorway preloader
  components/   landing, gallery, Enter painting
  scene/        WebGL2 chapter engine and shaders
  world/        R3F halls, figures, layered wander
  camera/       walk, look, collision
  painting/     manifest types, recognize a scan
  knowledge/    facts and sources
  ui/world/     explore HUD

data/paintings/<id>/     source of truth (manifest, facts, meshes)
public/data/...          the copy the browser actually fetches
scripts/pipeline/        offline bake (Athens hall, figures, textures)
docs/                    product, decisions, pipeline
```

**Authoring**

```
painting → Opus manifest → masks / depth / layers / baked textures
        → data/paintings/<id>/ → public/data → shipped with the app
```

**Runtime**

```
gallery pick, or a dropped scan
  → recognizePainting (match against the curated catalog)
  → /world/:id loads static files
  → no Opus, no segmentation, no new geometry
```

Deeper notes: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/PROJECT.md](docs/PROJECT.md), [docs/DECISIONS.md](docs/DECISIONS.md), [docs/PIPELINE.md](docs/PIPELINE.md).

## Stack

React 19, TypeScript, Vite, React Router. Lenis for desktop scroll. A hand-written WebGL2 composite for the doorway. React Three Fiber and Three.js for the worlds. Zustand for the explore session.

On a phone the doorway drops the custom cursor, smooth-scroll, figure shadows, and the full-resolution backdrop, and holds the last frame once scrolling stops.

## Develop

```bash
npm install
npm run dev
```

```bash
npm run build
npm run preview
```

`npm run dev` mounts React twice, which releases the doorway’s WebGL context. Judge the preloader and the chapter transitions with `npm run preview` or on the live site.

Production files ship from `public/` into `dist/`. Offline bake caches, design dumps, and full-resolution frescoes stay out of git.

## Deploy

**Vercel.** Import the repo, framework Vite, build `npm run build`, output `dist`. [`vercel.json`](vercel.json) sets long-cache headers for `/assets` and `/data`, and the SPA rewrite.

**Cloudflare Pages.** Same build and output. `public/_headers` and `public/_redirects` are copied into `dist`. [`wrangler.toml`](wrangler.toml) points Pages at `dist`.
