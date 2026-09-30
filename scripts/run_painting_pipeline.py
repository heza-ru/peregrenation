"""Run full offline pipeline for a painting (GPU depth + SAM when available)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PY = sys.executable


def run_step(script: str, painting_id: str, extra: list[str] | None = None) -> None:
    cmd = [PY, str(SCRIPTS / script), painting_id] + (extra or [])
    print(">", " ".join(cmd))
    subprocess.check_call(cmd)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("painting_id")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    force = ["--force"] if args.force else []

    run_step("preprocess/normalize_image.py", args.painting_id)
    run_step("depth/run_depth_pro.py", args.painting_id, force)
    run_step("pipeline/assign_depth_bands.py", args.painting_id)
    run_step("segmentation/run_sam3.py", args.painting_id, force)
    run_step("pipeline/build_layers.py", args.painting_id)
    run_step("preprocess/sync_public.py", args.painting_id)
    print("Pipeline complete.")


if __name__ == "__main__":
    main()
