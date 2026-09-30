"""Validate a painting manifest before running the CV pipeline."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = {"observed", "strongly_inferred", "weakly_inferred"}
ARCH_TYPES = {"plane", "cylinder", "box"}


def err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def validate(painting_id: str) -> int:
    path = ROOT / "data" / "paintings" / painting_id / "manifest.json"
    if not path.exists():
        err(f"missing {path}")
        return 1
    man = json.loads(path.read_text(encoding="utf-8"))
    failures = 0

    for key in (
        "paintingId",
        "pipelineVersion",
        "sceneAnalysisVersion",
        "segmentationVersion",
        "depthVersion",
        "composition",
        "layers",
        "entities",
        "architecture",
        "lighting",
        "palette",
    ):
        if key not in man:
            err(f"missing top-level key: {key}")
            failures += 1

    if man.get("paintingId") != painting_id:
        err(f"paintingId {man.get('paintingId')!r} != folder {painting_id!r}")
        failures += 1

    comp = man.get("composition") or {}
    for key in ("aspectRatio", "horizon", "vanishingPoint", "cameraFov", "planeWidth", "planeHeight"):
        if key not in comp:
            err(f"composition missing {key}")
            failures += 1

    layers = man.get("layers") or []
    heroes = [L for L in layers if L.get("hero")]
    if len(heroes) != 1:
        err(f"expected exactly one hero layer, found {len(heroes)}")
        failures += 1
    elif heroes[0].get("texture") != "painting.jpg":
        err("hero layer texture should be painting.jpg")
        failures += 1

    entities = man.get("entities") or []
    interactive = [e for e in entities if e.get("interactive")]
    if not interactive:
        err("no interactive entities")
        failures += 1
    for e in interactive:
        eid = e.get("id", "?")
        uv = e.get("promptPoint")
        if not (isinstance(uv, list) and len(uv) == 2):
            err(f"entity {eid}: missing promptPoint [u,v]")
            failures += 1
        elif not (0 <= float(uv[0]) <= 1 and 0 <= float(uv[1]) <= 1):
            err(f"entity {eid}: promptPoint out of 0–1")
            failures += 1
        if e.get("evidence") not in EVIDENCE:
            err(f"entity {eid}: bad evidence {e.get('evidence')!r}")
            failures += 1

    arch = man.get("architecture") or []
    if not arch:
        err("architecture[] is empty — hall needs floor/columns/steps proxies")
        failures += 1
    for a in arch:
        if a.get("type") not in ARCH_TYPES:
            err(f"architecture {a.get('id')}: bad type {a.get('type')!r}")
            failures += 1
        if "position" not in a:
            err(f"architecture {a.get('id')}: missing position")
            failures += 1

    assets = man.get("assets")
    if assets is not None and not isinstance(assets, list):
        err("assets must be an array when present")
        failures += 1

    if painting_id == "school-of-athens":
        # Soft guidance for Opus target — warn only
        if man.get("sceneAnalysisVersion") != "opus-5-5-v1":
            print("NOTE: sceneAnalysisVersion is not opus-5-5-v1 yet (expected after Opus pass)")
        if man.get("pipelineVersion") != "0.2.0":
            print("NOTE: pipelineVersion is not 0.2.0 yet (expected after Opus pass)")

    if failures:
        err(f"{failures} validation failure(s)")
        return 1
    print(f"OK {painting_id}: {len(layers)} layers, {len(interactive)} curiosities, {len(arch)} arch")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("painting_id")
    args = p.parse_args()
    raise SystemExit(validate(args.painting_id))


if __name__ == "__main__":
    main()
