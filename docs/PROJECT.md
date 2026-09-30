# Renaissance Worlds (Pérégrination)

Turn Renaissance paintings into explorable spatial interpretations — without losing the painting.

## Product journey

1. **Doorway** (`/`) — Lenis scroll, hero parallax, chapter WebGL transitions. Marketing and entry only.
2. **Build** — [EnterPainting](../src/components/EnterPainting.tsx): pick a curated masterpiece, or drop a scan that is **recognized** as one of our selection → open the **saved** world.
3. **Explore** (`/world/:paintingId`) — game-like R3F world: depth, WASD, proximity facts. Prebuilt for shipped paintings only.

The scroll **Build** chapter explains the pipeline; **Wander** (`#learn`) prototypes explore UX on a 2D panel.

## Shipping model

- The product ships with a **curated set of worlds** (School of Athens first, then the tier-1 list).
- Offline, Opus (+ CV) authors each world once into `data/paintings/<id>/`. That is the expensive step — stay cost-optimal until then.
- At runtime: **recognize** similar images → load the matching cached world. Arbitrary new paintings do **not** get a live 3D rebuild.
- Goal experience is **game-like exploration inside the painting world**, not a generic image viewer or on-demand reconstruction engine.

## MVP success (School of Athens)

User opens The School of Athens (gallery or recognized scan), sees the painting, gains subtle depth, moves into the space, approaches Plato (and others), reads sourced facts, experience still looks like Raphael.

## Principles

- **No runtime full-scene reconstruction for uploads.** Recognition → saved world.
- **Process once offline.** Opus scene analysis + segmentation + depth → cached assets.
- **Painting remains source of truth** for palette, faces, brushwork, composition.
- **Facts:** distinguish `documented`, `scholarly_interpretation`, `ai_inference` in UI.

## First painting

Raphael, *The School of Athens* (`school-of-athens`). Author complete worlds for the selection before treating upload as anything more than matching.

## Out of scope (until core works)

Auth, payments, social, multiplayer, VR, mobile controls, marketplace, analytics, CMS, export automation.

## Session discipline

Read [CURRENT_STATE.md](./CURRENT_STATE.md) before continuing work. Update it after each phase.
