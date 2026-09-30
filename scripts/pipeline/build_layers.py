"""Build RGBA layer cutouts from painting + masks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def run(painting_id: str) -> None:
    base = ROOT / "data" / "paintings" / painting_id
    layers_dir = base / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    src = Image.open(base / "painting.jpg").convert("RGBA")
    arr = np.array(src)
    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))

    for layer in manifest.get("layers", []):
        lid = layer["id"]
        mask_rel = layer.get("mask")
        if not mask_rel or layer.get("hero"):
            continue
        mask_path = base / mask_rel.replace("/", "\\") if "\\" not in mask_rel else base / mask_rel
        if not mask_path.exists():
            mask_path = base / Path(mask_rel)
        if not mask_path.exists():
            continue
        mask = np.array(Image.open(mask_path).convert("L").resize(src.size))
        cut = arr.copy()
        cut[:, :, 3] = mask
        out = layers_dir / f"{lid}.webp"
        Image.fromarray(cut).save(out, "WEBP", quality=88)
        layer["texture"] = f"layers/{lid}.webp"
        print(f"  layer {lid} -> {out.name}")

    (base / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("painting_id")
    args = p.parse_args()
    run(args.painting_id)


if __name__ == "__main__":
    main()
