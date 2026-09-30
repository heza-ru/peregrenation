"""Offline build of the walkable School of Athens.

Outputs (data/ and public/ copies, under data/paintings/school-of-athens/):
  world3d.json          camera, figure metadata + colliders, entity anchors
  scene/scene.json      mesh/page index into scene.bin
  scene/scene.bin       architecture + figure geometry (float32 / uint32)
  scene/arch-N.webp     baked architecture texture pages
  scene/fig-N.webp      figure texture pages (front), fig-back-N.webp (back)

Source: _cache/painting-original.jpg (17402x12132 Commons original) when present,
else painting.jpg. Camera: VP px (1017, 760), f = 1600 px on the 1920 frame; eye
2.87 m above the forecourt at z = 10.3; four steps (0.25 rise, 0.40 tread) to a
1.0 m platform.

Usage: python scripts/pipeline/build_athens_world3d.py [--preview]
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent))

from athens_arch import bake_all, export_meshes  # noqa: E402
from athens_common import (  # noqa: E402
    CAM,
    DATA,
    PID,
    PUBLIC,
    ROOT,
    H,
    STEP_FRONTS,
    STEP_RISE,
    PLATFORM_Y,
    W,
    Atlas,
    BinWriter,
    back_project,
    load_source,
    raymarch,
    scene_mask,
    write_json,
)
from athens_figures import STATUES, back_page, build_figures, export_figures  # noqa: E402


def anchors_for(entities: dict, figs) -> dict[str, list[float]]:
    by_id = {f.id: f for f in figs}
    solid = [f for f in figs if f.tier != "statue"]

    def figure_at(px: int, py: int):
        for radius in (0, 8, 16, 28):
            y0, y1 = max(0, py - radius), min(H, py + radius + 1)
            x0, x1 = max(0, px - radius), min(W, px + radius + 1)
            for f in solid:
                if f.mask[y0:y1, x0:x1].any():
                    return f
        return None

    out: dict[str, list[float]] = {}
    for eid, e in entities.items():
        u, v = e["promptPoint"]
        px, py = int(u * W), int(v * H)
        if eid in STATUES and eid in by_id:
            out[eid] = [by_id[eid].center[0], 3.4, -3.3 + 0.35]
        elif eid in by_id:
            out[eid] = by_id[eid].center
        elif eid == "vault-perspective":
            out[eid] = [0.0, 3.4, -7.0]
        elif eid == "far-arch":
            out[eid] = [0.0, 2.8, -31.0]
        elif eid == "marble-steps":
            out[eid] = [0.0, 1.2, -0.6]
        else:
            f = None if eid.endswith("slate") else figure_at(px, py)
            d = f.d - f.r * 0.9 if f else raymarch(px, py)
            out[eid] = [round(float(c), 3) for c in back_project(px, py, d)]
    return out


def save_webp(path, img, q=90):
    cv2.imwrite(str(path), img, [cv2.IMWRITE_WEBP_QUALITY, q])


def main() -> None:
    preview = "--preview" in sys.argv
    t0 = time.time()
    src = load_source()
    img = src.levels[1.0]
    depth = cv2.resize(cv2.imread(str(DATA / "depth" / "depth.png"), cv2.IMREAD_GRAYSCALE), (W, H))
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    entities = {e["id"]: e for e in manifest["entities"]}

    figs, kill = build_figures(img, depth)
    print(f"figures: {len(figs)} ({time.time() - t0:.0f}s)")

    scene = scene_mask()
    surfaces = bake_all(src, scene, kill)
    print(f"architecture baked: {len(surfaces)} surfaces ({time.time() - t0:.0f}s)")

    arch_atlas = Atlas("arch")
    arch_meshes = export_meshes(surfaces, arch_atlas)
    fig_atlas = Atlas("fig")
    fig_meshes = export_figures(figs, src, fig_atlas)

    out_dir = DATA / "scene"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*"):
        old.unlink()
    binw = BinWriter()
    index: dict = {"version": 2, "arch": [], "figures": [], "pages": {"arch": [], "fig": [], "figBack": []}}
    for pi, page in enumerate(arch_atlas.final):
        name = f"arch-{pi}.webp"
        save_webp(out_dir / name, page, 88)
        index["pages"]["arch"].append(name)
    for pi, page in enumerate(fig_atlas.final):
        name, bname = f"fig-{pi}.webp", f"fig-back-{pi}.webp"
        save_webp(out_dir / name, page, 92)
        save_webp(out_dir / bname, back_page(page), 85)
        index["pages"]["fig"].append(name)
        index["pages"]["figBack"].append(bname)
    for pi, m in sorted(arch_meshes.items()):
        index["arch"].append({"page": pi, **{k: binw.add(v) for k, v in m.items()}})
    for pi, m in sorted(fig_meshes.items()):
        index["figures"].append(
            {
                "page": pi,
                "front": {k: binw.add(v) for k, v in m["front"].items()},
                "back": {k: binw.add(v) for k, v in m["back"].items()},
            }
        )
    binw.write(out_dir / "scene.bin")
    write_json(out_dir / "scene.json", index)

    world = {
        "version": 2,
        "paintingId": PID,
        "camera": CAM,
        "steps": {"fronts": STEP_FRONTS, "rise": STEP_RISE, "platformY": PLATFORM_Y},
        "figures": [
            {"id": f.id, "tier": f.tier, "crowd": f.crowd, "center": f.center, "collider": f.collider()}
            for f in figs
        ],
        "anchors": anchors_for(entities, figs),
    }
    write_json(DATA / "world3d.json", world)

    pub = PUBLIC / "scene"
    if pub.exists():
        shutil.rmtree(pub)
    shutil.copytree(out_dir, pub)
    shutil.copyfile(DATA / "world3d.json", PUBLIC / "world3d.json")
    shutil.copyfile(DATA / "manifest.json", PUBLIC / "manifest.json")
    for stale in (DATA / "painting-clean.webp", PUBLIC / "painting-clean.webp"):
        stale.unlink(missing_ok=True)

    size = sum(p.stat().st_size for p in out_dir.glob("*")) / 1e6
    print(f"wrote scene ({size:.1f} MB) in {time.time() - t0:.0f}s")

    if preview:
        prev = ROOT / ".cache-crops"
        prev.mkdir(exist_ok=True)
        for pi, page in enumerate(arch_atlas.final):
            cv2.imwrite(str(prev / f"arch-{pi}.jpg"), cv2.resize(page[..., :3], (page.shape[1] // 4, page.shape[0] // 4)))
        for pi, page in enumerate(fig_atlas.final):
            cv2.imwrite(str(prev / f"fig-{pi}.jpg"), cv2.resize(page[..., :3], (page.shape[1] // 4, page.shape[0] // 4)))
        for s in surfaces:
            if s.id in ("portal", "portal-inner", "landing", "forecourt", "pier-L", "vault-1", "bay1-R", "nave-floor", "platform", "riser-2", "drum", "sky", "far-wall", "cross-front", "spandrel", "vault-2"):
                cv2.imwrite(str(prev / f"surf-{s.id}.jpg"), s.tex[..., :3])


if __name__ == "__main__":
    main()
