# Offline pipeline

## Steps

1. Acquire image + record rights in `sources.json`
2. `scripts/preprocess/normalize_image.py`
3. Opus 5.5 → structured `manifest.json` (composition, entities, architecture)
4. `scripts/segmentation/run_sam3.py` → `masks/`
5. `scripts/depth/run_depth_pro.py` → `depth/` (fallback: Depth Anything V2 Small)
6. `scripts/pipeline/assign_depth_bands.py` → semantic bands 0–5
7. `scripts/pipeline/build_layers.py` → `layers/`
8. Optional selective TRELLIS GLB → `assets/` (never full painting)
9. Copy runtime derivatives to `public/data/paintings/<id>/`

## Cache keys (`manifest.json`)

```json
{
  "paintingId": "school-of-athens",
  "pipelineVersion": "0.1.0",
  "sceneAnalysisVersion": "opus-5-5-v1",
  "segmentationVersion": "sam3-v1",
  "depthVersion": "depth-pro-v1"
}
```

Regenerate only when source image or a version field changes. See `scripts/pipeline/cache.py`.

## Opus offline prompt

See [prompts/opus-scene-manifest.md](prompts/opus-scene-manifest.md) and [OPUS_ATHENS_BRIEF.md](OPUS_ATHENS_BRIEF.md).

Athens runbook after Opus writes `manifest.json`:

```text
1. python scripts/pipeline/validate_manifest.py school-of-athens
2. python scripts/run_painting_pipeline.py school-of-athens --force
3. Visual QA → /world/school-of-athens
```

## SAM 3

Text/visual/exemplar prompts from manifest entity labels. Interactive refinement documented in script help.

## Depth

Use depth for parallax and layer ordering — not raw mesh extrusion of every pixel.
