# Current state

**Updated:** School of Athens is a **true walkable 3D hall** with **baked, surface-space textures** from the 17402×12132 Commons original. No parallax, no billboards, no runtime projection, no vestibule.

## Route

`/world/school-of-athens` → `WorldScene` → `AthensWorld` (never `LayeredWorld`; `worldMode.ts` still throws if Athens reaches the parallax path, so `PaintingLayers` never mounts for it).

## Measured perspective (painting.jpg 1920×1339 frame)

- Vanishing point px (1017, 760); painter's camera f = 1600 px, eye 2.87 m above the forecourt at z = 10.3.
- 4 steps, rise 0.25 m / tread 0.40 m, platform at 1.0 m.
- Nave 5.1 m wide, barrel vault spring 5.45 m / crown 8.0 m; pier face z −3.3.
- Arches measured on the fresco (circle fits, all consistent with spring ≈5.5): bay 1 end arch crown px 300 / half-width 227 → **z −7.7**; bay 2 front arch crown 440 / 155 → **z −16.0**; bay 2 end arch crown 540 / 102 → **z −29.5**. Crossing −7.7…−16.0, 8.4 m wide, ceiling 8.8, drum r 3.6 (windows at y 9.0–10.2) + cupola. Far wall with arch at −32.
- The forecourt is the hall's centre: the whole architecture repeats mirrored across **z = 3.6** behind the visitor (no invented back wall or room).
- Numbers live in `scripts/pipeline/athens_arch.py` (+ `athens_common.py` camera) and `src/world/athensHallConfig.ts` (walk/collision); keep them in sync.

## Runtime pieces

| Piece | File |
|-------|------|
| Architecture meshes (one merged mesh per atlas page), unlit baked textures, alpha-cut arch openings; sky dome | `src/world/AthensHall3D.tsx` |
| `scene.bin` / `scene.json` loader → BufferGeometries | `src/world/athensScene.ts` |
| Figures: inflated rounded bodies (circular cross-section from each silhouette, ≈0.4 m deep), full-res front atlas, softened shaded back atlas, soft key light | `src/world/AthensFigures.tsx` |
| Floor-clamped FPS (eye 1.7 m), wall + figure collision, mirrored hall | `src/camera/ExploreControls.tsx` (walkMode), `resolveAthensPosition` |
| Curiosity anchors in hall space (all 21 entity ids, proximity in 3D) | `world3d.json` → `EntityMarkers hallPositions` |

Spawn: forecourt (0, 1.7, 3.2) facing the vanishing point — already inside the painting.

## Offline build

```text
python scripts/pipeline/build_athens_world3d.py [--preview]
```

Needs `data/paintings/school-of-athens/_cache/painting-original.jpg` (Commons original, 207 MB, gitignored; falls back to `painting.jpg`). ~90 s. Writes `world3d.json` and `scene/` (`scene.bin`, `scene.json`, `arch-N.webp`, `fig-N.webp`, `fig-back-N.webp`) to data/ and public/.

How textures are made (`athens_arch.py`): each surface (plane / vault / drum / dome) is sampled texel-by-texel from the painter's eye with occlusion (ray vs. every other surface), figure masks, the lunette mask, a grazing-angle limit, and stray-paint rejection (chroma on masonry, dark specks on floors). Texels the painter never saw are filled, in order, from the mirror-symmetric point of the hall, then the surface's repeating unit (phase-aligned pavement / coffer block), then a median-clamped inpaint with real painted grain.

Figures (`athens_figures.py`): named figures sit on the floor at their feet; crowd groups likewise, falling back to the floor-calibrated depth map when their lowest edge is hidden.

## Known limits

- Surfaces the fresco never shows (e.g. lower pier faces behind the crowd, crossing side walls) are plain filled marble, not invented ornament.
- Painted pilasters and cornices on the nave walls are flat paint on flat walls.
- Figures are single-plane inflated bodies: convincing from the front half, thinner-looking edge-on; backs are a softened copy of the front.
- A few low-contrast figures aren't in the crowd mask and stay painted on the architecture behind them.
