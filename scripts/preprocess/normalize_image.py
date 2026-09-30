"""Normalize source painting to painting.jpg (max width, JPEG quality)."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def normalize(painting_id: str, max_width: int = 2560, quality: int = 88) -> Path:
    base = ROOT / "data" / "paintings" / painting_id
    src = base / "painting.jpg"
    if not src.exists():
        raise SystemExit(f"Missing {src}")
    img = Image.open(src).convert("RGB")
    w, h = img.size
    if w > max_width:
        nh = int(h * (max_width / w))
        img = img.resize((max_width, nh), Image.Resampling.LANCZOS)
    out = base / "painting.jpg"
    img.save(out, "JPEG", quality=quality, optimize=True)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("painting_id")
    p.add_argument("--max-width", type=int, default=2560)
    args = p.parse_args()
    path = normalize(args.painting_id, max_width=args.max_width)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
