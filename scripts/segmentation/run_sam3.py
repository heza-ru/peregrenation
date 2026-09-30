"""Segmentation via SAM ViT (GPU when available). Entity point prompts + depth band masks."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline.cache import artifact_stale, mark_artifact, painting_dir  # noqa: E402
from pipeline.device import get_torch_device  # noqa: E402

SAM_MODEL = "facebook/sam-vit-base"
SEG_TAG = "sam-vit-base-gpu-v1"


def entity_to_pixel(entity: dict, comp: dict, w: int, h: int) -> tuple[int, int]:
    if "promptPoint" in entity:
        u, v = entity["promptPoint"]
        return int(u * w), int(v * h)
    pos = entity.get("position", [0, 0, 0])
    x, y = float(pos[0]), float(pos[1])
    pw, ph = comp.get("planeWidth", 16), comp.get("planeHeight", 9)
    u = 0.5 + x / pw
    v = 0.5 - y / ph
    return int(np.clip(u, 0, 1) * w), int(np.clip(v, 0, 1) * h)


def run(painting_id: str, force: bool = False) -> None:
    base = painting_dir(painting_id)
    manifest_path = base / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    masks_dir = base / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)
    stamp = masks_dir / ".complete"

    if not force and not artifact_stale(painting_id, stamp, "segmentationVersion"):
        print("Segmentation cache hit — skipping")
        return

    src = base / "painting.jpg"
    if not src.exists():
        raise SystemExit(f"Missing {src}")

    import torch
    from transformers import SamModel, SamProcessor

    device = get_torch_device()
    print(f"SAM on {device.type} ({SAM_MODEL})")

    image = Image.open(src).convert("RGB")
    w, h = image.size
    processor = SamProcessor.from_pretrained(SAM_MODEL)
    model = SamModel.from_pretrained(SAM_MODEL).to(device)

    comp = manifest.get("composition", {})

    for entity in manifest.get("entities", []):
        if not entity.get("interactive", True):
            continue
        eid = entity["id"]
        px, py = entity_to_pixel(entity, comp, w, h)
        input_points = [[[[px, py]]]]
        input_labels = [[[1]]]
        inputs = processor(
            image,
            input_points=input_points,
            input_labels=input_labels,
            return_tensors="pt",
        ).to(device)
        with torch.no_grad():
            outputs = model(**inputs)
        masks = processor.image_processor.post_process_masks(
            outputs.pred_masks.cpu(),
            inputs["original_sizes"].cpu(),
            inputs["reshaped_input_sizes"].cpu(),
        )[0]
        mask = masks[0, 0].numpy().astype(np.uint8) * 255
        Image.fromarray(mask, mode="L").save(masks_dir / f"entity-{eid}.png")
        entity["mask"] = f"masks/entity-{eid}.png"
        print(f"  mask entity-{eid} @ {px},{py}")

    depth_path = base / "depth" / "depth.png"
    if depth_path.exists():
        depth = np.array(Image.open(depth_path).convert("L"), dtype=np.float32) / 255.0
        bands = sorted({layer["depthBand"] for layer in manifest.get("layers", [])})
        if bands:
            qs = np.linspace(0, 1, len(bands) + 1)
            thresholds = np.quantile(depth, qs)
            for i, band in enumerate(bands):
                lo, hi = thresholds[i], thresholds[i + 1]
                band_mask = ((depth >= lo) & (depth <= hi if i == len(bands) - 1 else depth < hi))
                band_mask = (band_mask.astype(np.uint8) * 255)
                Image.fromarray(band_mask, mode="L").save(masks_dir / f"band-{band}.png")
                for layer in manifest.get("layers", []):
                    if layer.get("depthBand") == band and not layer.get("hero"):
                        layer["mask"] = f"masks/band-{band}.png"
                        layer["texture"] = "painting.jpg"

    manifest["segmentationVersion"] = SEG_TAG
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    stamp.write_text("ok", encoding="utf-8")
    mark_artifact(painting_id, "segmentationVersion")
    print(f"Wrote masks to {masks_dir}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("painting_id")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    run(args.painting_id, force=args.force)


if __name__ == "__main__":
    main()
