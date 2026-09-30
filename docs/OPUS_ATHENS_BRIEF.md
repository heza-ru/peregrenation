# Opus Athens — true 3D replica brief

**Model:** Claude Opus 5.5 · **Effort:** high (visual + spatial coding)  
**Open only these.** Do not reload prior chats or the whole repo.

## Goal

Build a **walkable first-person 3D replica** of Raphael’s *School of Athens* at `/world/school-of-athens`.

The visitor must feel they entered the painted hall: real floor, steps, columns, vault, niches; figures as solid meshes in depth; painting appearance preserved via textures. **Not** parallax planes, **not** camera-facing sprites, **not** a flat fresco with overlays.

## Explicitly forbidden (name and avoid)

- `PaintingLayers` / depth-band parallax stacks as the explore world  
- Camera-billboard figures (`rotation.y = atan2` toward camera)  
- Ghost / 5–12% opacity architecture  
- “Hero match then slide layers” as the product  
- Inventing rooms behind the fresco that contradict the painting  

## Allowed / required approach

1. **Read the painting carefully.** If a column, step edge, or figure foot is unclear, crop/zoom that region (PIL/OpenCV or Cursor image tools), re-inspect, then decide.  
2. **Author a coherent Three.js / R3F hall** whose perspective matches the fresco’s vanishing point (center, mid height).  
3. **Solid meshes only** for architecture: planes, boxes, vaults, drum/dome. Textures are **baked offline per surface** from the full-resolution original (`scripts/pipeline/athens_arch.py`) — no runtime projection, no procedural stand-in patterns.  
4. **Figures:** inflated rounded bodies from the silhouettes (`scripts/pipeline/athens_figures.py`), fixed in world space, standing where their feet are. No extruded slabs.  
5. **Optional selective GLB** under `data/paintings/school-of-athens/assets/` only for props that benefit (not a full generative mesh of the fresco).  
6. **Camera:** eye-height FPS on the floor; clamp to hall bounds; spawn on the forecourt inside the painting (no vestibule) looking to the vanishing point.  
7. Keep curiosities / `facts.json` entity `id`s working via proximity in 3D.

## Files

| Role | Path |
|------|------|
| Painting | `data/paintings/school-of-athens/painting.jpg` |
| Depth (aid, not the world) | `data/paintings/school-of-athens/depth/depth.png` |
| Masks | `data/paintings/school-of-athens/masks/` |
| Manifest / facts | `manifest.json`, `facts.json` |
| Ban parallax | `src/world/worldMode.ts` |
| Replace / rewrite | `src/world/AthensHall3D.tsx`, figure placement, `WorldScene` Athens branch |
| Route | `/world/school-of-athens` |

## Success checklist (do not stop until all pass)

- [ ] No `PaintingLayers` in Athens path  
- [ ] Walk up steps; Y stays on floor (walkMode)  
- [ ] Columns/vault are volumetric; orbiting changes silhouette  
- [ ] Plato/Aristotle are approachable 3D solids, not sprites  
- [ ] Fresco look preserved (textures), not a grey blockout  
- [ ] `npm run build` succeeds  
- [ ] Visual check at `/world/school-of-athens`  

## Standing agent rule (Opus 5.5)

Do not end a turn with “next I will…” while work remains. Put status in the same message as the next edit/tool call and continue until the checklist is done or you are blocked on a missing user decision.
