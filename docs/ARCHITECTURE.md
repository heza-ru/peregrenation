# Architecture

## Five boundaries

| Layer | Responsibility | Runtime |
|-------|----------------|---------|
| AI processing | Scene manifest, entity IDs, historical synthesis | Offline (Opus); Q&A with retrieval later |
| Asset processing | Normalize, segment, depth, layers, optional GLB | Python scripts |
| World data | `manifest.json`, masks, depth, facts, sources | Static files under `data/paintings/<id>/` |
| World rendering | R3F scene, layers, architecture, lighting | `/world/:paintingId` only |
| Runtime interaction | Controls, proximity, fact panels | Zustand + UI |

Opus makes decisions; code executes them. Do not call Opus per frame or per camera move.

## Routes

```
/                    Doorway App + EnterPainting overlay
/world/:paintingId   Explore (lazy-loaded R3F)
```

Only one WebGL stack active: unmount doorway when on `/world/*`.

## Repo map

```
src/
  app/           Routes, world shell, session store
  components/    Doorway UI (EnterPainting = build)
  painting/      Manifest types + loader
  world/         R3F scene
  camera/        Hero + explore controls
  knowledge/     Fact types + loaders
  ui/world/      Explore HUD
  scene/         Doorway WebGL SceneEngine (unchanged role)

data/paintings/<id>/   Source of truth for painting worlds
public/data/...        Runtime-served copies (Vite static)

scripts/preprocess|segmentation|depth|pipeline/
docs/
```

## Data flow

**Authoring (offline, once per curated painting):**

```
painting.jpg → Opus manifest (+ CV) → masks / depth / layers / facts
     → data/paintings/<id>/ → public/data/… → shipped with the app
```

**Runtime:**

```
gallery pick OR upload/scan
  → recognizePainting (hash / filename vs curated catalog)
  → /world/:paintingId loads static assets
  → no Opus, no SAM, no new geometry generation
```

## Explore UX

Game-like HUD + proximity inspect; still mirror [LearnSection](../src/components/Sections.tsx) curiosity intent (facts with sources).
