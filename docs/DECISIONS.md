# Decisions

## ADR-001: Doorway WebGL vs R3F

**Decision:** Keep custom WebGL2 `SceneEngine` for scroll chapter transitions on `/`. Use React Three Fiber only for `/world/:paintingId`.

**Reason:** Avoid merging two render paradigms; route change unmounts doorway canvas.

## ADR-002: Enter Painting is build UI

**Decision:** No separate `/build` route. Extend `EnterPainting.tsx` in place.

**Reason:** Begin CTAs already open this modal; matches shipped UX.

## ADR-003: Process once

**Decision:** All expensive CV/AI work writes to `data/paintings/<id>/`; browser never reconstructs on upload in MVP except loading prepared bundles.

## ADR-004: Serving data

**Decision:** `data/` is source of truth; `public/data/` holds files the dev server and production build serve. Sync via script or manual copy for large binaries.

## ADR-005: Camera phasing

1. Depth + parallax + limited movement (MVP)
2. Selective geometry (columns, floor)
3. Unseen regions / inpainting — later

## ADR-006: Characters

Textured cutout quads for figures in MVP; no full rigged bodies.

## ADR-007: Curated worlds + recognition (not live reconstruction)

**Decision:** Ship prepared worlds for a fixed selection. Uploads / scans are matched to that catalog (`recognizePainting`) and open `/world/:id`. Do not run Opus or CV at runtime to invent new worlds.

**Reason:** Cost control; quality bar for game-like exploration; Opus authors worlds offline when ready. New paintings outside the set simply do not open a world until we add them to the selection.

## ADR-008: Opus timing

**Decision:** School of Athens is the first Opus-assisted spatial world. Other catalog paintings wait until Athens proves the recipe. Avoid Opus for runtime exploration, matching, or UI.

**Authoring context:** Use `docs/OPUS_ATHENS_BRIEF.md` + `docs/prompts/opus-scene-manifest.md` only — not full chat transcripts.

## ADR-009: Athens explore = walkable 3D hall

**Decision:** Runtime for School of Athens is a constructed first-person 3D hall (`AthensHall3D` + figure billboards + floor-clamped camera). Parallax painting layers are not the explore world.

**Reason:** Users need to feel they stepped inside a room; stacked fresco planes read as overlays, not space.
