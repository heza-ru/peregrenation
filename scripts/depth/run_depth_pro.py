"""Monocular depth: Depth Anything V2 (GPU when available). Writes depth/depth.png + meta."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline.cache import artifact_stale, mark_artifact, painting_dir  # noqa: E402
from pipeline.device import get_torch_device  # noqa: E402

MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"
MODEL_TAG = "depth-anything-v2-small-hf"


def run(painting_id: str, force: bool = False) -> None:
    base = painting_dir(painting_id)
    depth_dir = base / "depth"
    depth_dir.mkdir(parents=True, exist_ok=True)
    out = depth_dir / "depth.png"
    manifest_path = base / "manifest.json"

    if not force and not artifact_stale(painting_id, out, "depthVersion"):
        print("Depth cache hit — skipping")
        return

    src = base / "painting.jpg"
    if not src.exists():
        raise SystemExit(f"Missing {src}")

    from PIL import Image
    import numpy as np
    import torch
    from transformers import pipeline

    device = get_torch_device()
    device_index = 0 if device.type == "cuda" else -1
    if device.type == "mps":
        device_index = "mps"

    print(f"Depth estimation on {device.type} using {MODEL_ID}")
    img = Image.open(src).convert("RGB")
    w, h = img.size

    pipe = pipeline(
        task="depth-estimation",
        model=MODEL_ID,
        device=device_index,
        dtype=torch.float16 if device.type == "cuda" else torch.float32,
    )
    result = pipe(img)
    depth_img = result["depth"].convert("L")
    depth_img.save(out)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["depthVersion"] = MODEL_TAG
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    meta = {
        "width": w,
        "height": h,
        "model": MODEL_ID,
        "modelTag": MODEL_TAG,
        "device": device.type,
        "units": "relative",
    }
    (depth_dir / "depth_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    mark_artifact(painting_id, "depthVersion")
    print(f"Wrote {out}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("painting_id")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    run(args.painting_id, force=args.force)


if __name__ == "__main__":
    main()
