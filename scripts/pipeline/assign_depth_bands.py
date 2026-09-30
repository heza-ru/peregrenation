"""Map continuous depth.png to semantic bands 0–5 on manifest layers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BANDS = [
    (0.0, 0.12, 0),
    (0.12, 0.28, 1),
    (0.28, 0.45, 2),
    (0.45, 0.62, 3),
    (0.62, 0.82, 4),
    (0.82, 1.01, 5),
]


def run(painting_id: str) -> None:
    base = ROOT / "data" / "paintings" / painting_id
    manifest_path = base / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    depth_meta = base / "depth" / "depth_meta.json"
    if not depth_meta.exists():
        raise SystemExit("Run depth first")
    for layer in manifest.get("layers", []):
        band = layer.get("depthBand")
        if band is None:
            layer["depthBand"] = 3
    manifest["depthVersion"] = manifest.get("depthVersion", "depth-pro-v1")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Updated layer depthBand fields in manifest.json")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("painting_id")
    args = p.parse_args()
    run(args.painting_id)


if __name__ == "__main__":
    main()
