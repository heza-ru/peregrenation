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

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor':'#221b15','primaryTextColor':'#efe6d6','primaryBorderColor':'#c9a24a','secondaryColor':'#1a1612','secondaryTextColor':'#efe6d6','secondaryBorderColor':'#a8843c','tertiaryColor':'#15120f','tertiaryTextColor':'#efe6d6','tertiaryBorderColor':'#3a2a1c','lineColor':'#c9a24a','textColor':'#efe6d6','clusterBkg':'#1a1612','clusterBorder':'#a8843c','titleColor':'#c9a24a','edgeLabelBackground':'#15120f','fontFamily':'Georgia, serif'}}}%%
flowchart TB
  opus["Claude Opus<br/>scene manifest and entity ids"]
  py["Python pipeline<br/>masks, depth, baked meshes"]
  files["data/paintings/id"]

  opus --> py --> files

  subgraph browser ["Browser"]
    direction LR
    subgraph door ["Doorway · /"]
      direction TB
      pre["Preloader"]
      engine["SceneEngine · WebGL2"]
      lenis["Lenis · desktop"]
      enter["Enter painting"]
    end
    subgraph explore ["Explore · /world/id · lazy"]
      direction TB
      hall["3D hall<br/>Athens, Arnolfini"]
      wander["2D wander<br/>the other works"]
      hud["HUD · proximity facts and sources"]
    end
    door -->|"unmount, then load"| explore
  end

  files --> door
  files --> explore
```

Opus decides what a world contains. Code executes that decision. Nothing calls a model per frame, per step, or when someone uploads a scan.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor':'#221b15','primaryTextColor':'#efe6d6','primaryBorderColor':'#c9a24a','lineColor':'#c9a24a','textColor':'#efe6d6','clusterBkg':'#1a1612','clusterBorder':'#a8843c','titleColor':'#c9a24a','fontFamily':'Georgia, serif'}}}%%
flowchart LR
  subgraph src ["src"]
    direction TB
    app["app · routes and world shell"]
    boot["boot · doorway preloader"]
    components["components · landing and gallery"]
    scene["scene · WebGL2 chapters"]
    world["world · halls, figures, wander"]
    camera["camera · walk, look, collision"]
    painting["painting · manifest and recognition"]
    knowledge["knowledge · facts and sources"]
    ui["ui/world · explore HUD"]
  end
  subgraph disk ["On disk"]
    direction TB
    data["data/paintings/id<br/>source of truth"]
    public["public/data<br/>what the browser fetches"]
    scripts["scripts/pipeline<br/>offline bake"]
    docsnode["docs"]
  end
  scripts --> data --> public
```

**Authoring**, once per painting:

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor':'#221b15','primaryTextColor':'#efe6d6','primaryBorderColor':'#c9a24a','lineColor':'#c9a24a','textColor':'#efe6d6','fontFamily':'Georgia, serif'}}}%%
flowchart LR
  paint["Painting"] --> manifest["Opus manifest"] --> bake["Masks, depth,<br/>layers, baked textures"] --> store["data/paintings/id"] --> served["public/data"] --> ship["Shipped with the app"]
```

**Runtime.** A scan is matched to the catalog. It never starts a new bake.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {'primaryColor':'#221b15','primaryTextColor':'#efe6d6','primaryBorderColor':'#c9a24a','lineColor':'#c9a24a','textColor':'#efe6d6','fontFamily':'Georgia, serif'}}}%%
flowchart LR
  pick["Gallery pick<br/>or a dropped scan"] --> match["recognizePainting"] --> route["/world/id"] --> static["Static files only"]
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
