# Opus 5.5 — School of Athens scene manifest

**Model:** Claude Opus 5.5 (high thinking for this pass).  
**Output:** JSON only. No prose, no markdown fences.

## Inputs to attach

1. `data/paintings/school-of-athens/painting.jpg`
2. Current `data/paintings/school-of-athens/manifest.json` (preserve entity ids + facts linkage)
3. Shape reference: `data/paintings/school-of-athens/manifest.schema.example.json`

## Task

Produce a complete `manifest.json` for Raphael’s *School of Athens* as a spatial interpretation:

- Match composition to the painting (aspect, horizon, vanishing point, FOV, plane size).
- Author **layers** (depth bands 0–5) with `z` / `parallax`; exactly one `hero: true` plate using `painting.jpg`.
- Keep/enrich **entities** (interactive curiosities): each needs `promptPoint` UV `[u,v]` top-left origin 0–1, `importance`, `evidence` ∈ `observed|strongly_inferred|weakly_inferred`, optional `mask` path `masks/entity-<id>.png`, optional `cutoutWidth` / `cutoutHeight` (world units).
- Author **architecture** primitives (floor, columns, steps, vault proxies) in world space aligned to the vanishing point — types: `plane` | `cylinder` | `box`.
- Set `assets: []` for this pass (selective GLB later).
- Lighting + palette warm fresco.
- Set versions: `pipelineVersion` `0.2.0`, `sceneAnalysisVersion` `opus-5-5-v1`. Leave `segmentationVersion` / `depthVersion` as in current file unless you know they change.

## Constraints

- Do **not** invent unseen rooms behind the fresco.
- Do **not** repaint faces/clothing/palette.
- Prefer observed structure; mark inference honestly via `evidence`.
- Preserve existing entity `id`s when possible so `facts.json` stays linked.
- Positions may stay `[0,0,0]` if `promptPoint` is set (runtime maps UV → plane).

## Output

Single JSON object matching the example schema fields: `schemaVersion`, `paintingId`, versions, `painting`, `composition`, `layers`, `entities`, `architecture`, `assets`, `lighting`, `palette`.
