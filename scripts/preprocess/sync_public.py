"""Copy data/paintings/<id> runtime files to public/data/paintings/<id>."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

GLOB_COPY = [
    "painting.jpg",
    "manifest.json",
    "facts.json",
    "sources.json",
]


def sync(painting_id: str) -> None:
    src = ROOT / "data" / "paintings" / painting_id
    dst = ROOT / "public" / "data" / "paintings" / painting_id
    dst.mkdir(parents=True, exist_ok=True)
    for name in GLOB_COPY:
        f = src / name
        if f.exists():
            shutil.copy2(f, dst / name)
    for sub in ("layers", "depth", "masks"):
        s = src / sub
        if s.is_dir():
            t = dst / sub
            if t.exists():
                shutil.rmtree(t)
            shutil.copytree(s, t)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("painting_id")
    args = p.parse_args()
    sync(args.painting_id)
    print(f"Synced public/data/paintings/{args.painting_id}")


if __name__ == "__main__":
    main()
