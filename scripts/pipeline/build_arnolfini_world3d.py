"""Build the walkable Arnolfini chamber (offline, once).

Outputs (data/paintings/arnolfini-portrait/, mirrored to public/):
  world3d.json          camera, room, colliders, lights, curiosity anchors
  scene/scene.json      mesh index into scene.bin
  scene/scene.bin       geometry (float32 positions / uvs, uint32 indices)
  scene/room-N.webp     baked room + furniture pages (opaque)
  scene/obj-N.webp      figure / prop / relief pages (front, with alpha), obj-back-N.webp

Prereq: python scripts/pipeline/arnolfini_masks.py (SAM masks, cached).
Usage:  python scripts/pipeline/build_arnolfini_world3d.py [--preview]
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from arnolfini_common import (  # noqa: E402
    BACK_Z,
    CAM,
    CEIL_Y,
    DATA,
    FRONT_Z,
    LEFT_X,
    PUBLIC,
    RIGHT_X,
    ROOT,
    back_project,
    load_source,
)
from arnolfini_kill import kill_mask  # noqa: E402
import arnolfini_figures as figs  # noqa: E402
import arnolfini_room as room  # noqa: E402
from athens_common import Atlas, BinWriter, write_json  # noqa: E402


class WideAtlas(Atlas):
    """Wider gutters: mip levels of neighbouring rects never meet."""

    PAD = 8


def save_webp(path: Path, img: np.ndarray, q: int) -> None:
    cv2.imwrite(str(path), img, [cv2.IMWRITE_WEBP_QUALITY, q])


def spans(binw: BinWriter, g: dict) -> dict:
    return {
        "position": binw.add(g["position"].astype(np.float32)),
        "uv": binw.add(g["uv"].astype(np.float32)),
        "index": binw.add(g["index"].astype(np.uint32)),
    }


def anchors(objs: dict[str, figs.Obj]) -> dict[str, list[float]]:
    def at(px, py, d, lift=(0.0, 0.0, 0.0)):
        x, y, z = back_project(px, py, d)
        return [round(float(x + lift[0]), 3), round(float(y + lift[1]), 3), round(float(z + lift[2]), 3)]

    d_wall = CAM["eyeZ"] - BACK_Z
    gio, bride = objs["giovanni"], objs["bride"]
    out = {
        "giovanni": at(540, 600, gio.stats["d"] - 0.2),
        "fur-robe": at(330, 1500, gio.stats["d"] - 0.22),
        "bride": at(1450, 700, bride.stats["d"] - 0.25),
        "joined-hands": at(1060, 1110, 2.05),
        "mirror": at(967, 788, d_wall - 0.09),
        "signature": at(975, 575, d_wall - 0.03),
        "chandelier": at(975, 360, objs["chandelier"].stats["d"] - 0.1),
        "dog": at(930, 2330, objs["dog"].stats["d"] - 0.12),
        "clogs": at(150, 2400, 1.95, (0.0, 0.06, 0.0)),
        "oranges": at(210, 1395, 3.05, (0.0, 0.05, 0.0)),
        "rosary": at(785, 740, d_wall - 0.03),
        "brush": at(1190, 640, d_wall - 0.05),
        "bed": [round(room.BED["x"][0] - 0.05, 3), 0.85, -3.0],
        "window": [round(LEFT_X + 0.08, 3), 1.75, -3.75],
        "carpet": [0.25, 0.03, -3.3],
    }
    return out


def colliders(objs: dict[str, figs.Obj]) -> list[dict]:
    def boxc(b, grow=0.0):
        return {"minX": b["x"][0] - grow, "maxX": b["x"][1] + grow, "minZ": b["z"][0] - grow, "maxZ": b["z"][1] + grow}

    out = [
        boxc(room.CHEST),
        boxc(room.CHAIR_SEAT),
        boxc(room.CHAIR_POST),
        boxc(room.BED),
    ]
    for o in objs.values():
        c = figs.collider(o)
        if c:
            out.append(c)
    return [{k: round(float(v), 3) for k, v in c.items()} for c in out]


def main() -> None:
    preview = "--preview" in sys.argv
    t0 = time.time()
    src = load_source()
    kill = kill_mask()

    print("room")
    surfaces = room.bake_all(src, kill)
    print(f"  {time.time() - t0:.0f}s")
    print("objects")
    objects = figs.build_all(src)
    by_id = {o.id: o for o in objects}
    print(f"  {time.time() - t0:.0f}s")

    out_dir = DATA / "scene"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    room_atlas = WideAtlas("room")
    room_meshes = room.export_meshes(surfaces, room_atlas)
    obj_atlas = WideAtlas("obj")
    obj_meshes = figs.export(objects, obj_atlas)

    binw = BinWriter()
    index: dict = {"version": 3, "room": [], "solids": [], "reliefs": [], "pages": {"room": [], "obj": [], "objBack": [], "objRim": []}}
    for pi, page in enumerate(room_atlas.final):
        name = f"room-{pi}.webp"
        save_webp(out_dir / name, page, 90)
        index["pages"]["room"].append(name)
    for pi, page in enumerate(obj_atlas.final):
        name, bname = f"obj-{pi}.webp", f"obj-back-{pi}.webp"
        save_webp(out_dir / name, page, 94)
        save_webp(out_dir / bname, obj_atlas.backs[pi][: page.shape[0]], 90)
        rname = f"obj-rim-{pi}.webp"
        save_webp(out_dir / rname, obj_atlas.rims[pi][: page.shape[0]], 90)
        index["pages"]["obj"].append(name)
        index["pages"]["objBack"].append(bname)
        index["pages"]["objRim"].append(rname)
    for pi, g in sorted(room_meshes.items()):
        index["room"].append({"page": pi, **spans(binw, g)})
    for (pi, kind), entry in sorted(obj_meshes.items()):
        rec = {"page": pi, "front": spans(binw, entry["front"])}
        if "back" in entry:
            rec["back"] = spans(binw, entry["back"])
        index["solids" if kind == "solid" else "reliefs"].append(rec)
    binw.write(out_dir / "scene.bin")
    write_json(out_dir / "scene.json", index)

    ch = by_id["chandelier"]
    ch_d = ch.stats["d"]
    ys, xs = np.nonzero(ch.hard)
    top = back_project(975.0, 0.0, ch_d)
    world = {
        "version": 1,
        "camera": {**CAM, "fovPainting": 2 * float(np.degrees(np.arctan(CAM["height"] / 2 / CAM["f"])))},
        # the painter's own eye: from here the room is the panel, pixel for pixel
        "spawn": {"position": [0.0, CAM["eyeY"], CAM["eyeZ"]], "look": list(back_project(960.0, 1313.5, 6.0))},
        "eyeHeight": 1.58,
        "room": {"minX": LEFT_X, "maxX": RIGHT_X, "minZ": BACK_Z, "maxZ": FRONT_Z, "ceiling": CEIL_Y},
        "colliders": colliders(by_id),
        "chain": {"from": [round(float(v), 3) for v in top], "to": [round(float(top[0]), 3), CEIL_Y, round(float(top[2]), 3)]},
        "candle": [round(float(v), 3) for v in back_project(805.0, 148.0, ch_d)],
        "window": {"center": [LEFT_X + 0.02, 1.9, -3.75], "size": [1.1, 1.9]},
        "anchors": anchors(by_id),
        "stats": {
            "surfaces": {s.id: s.stats for s in surfaces},
            "objects": {o.id: {k: v for k, v in o.stats.items() if k != "tex"} for o in objects},
        },
    }
    write_json(DATA / "world3d.json", world)

    PUBLIC.mkdir(parents=True, exist_ok=True)
    pub = PUBLIC / "scene"
    if pub.exists():
        shutil.rmtree(pub)
    shutil.copytree(out_dir, pub)
    for f in ("world3d.json", "manifest.json", "facts.json", "painting.jpg"):
        if (DATA / f).exists():
            shutil.copyfile(DATA / f, PUBLIC / f)
    size = sum(p.stat().st_size for p in out_dir.iterdir())
    print(f"wrote {len(index['pages']['room'])} room + {len(index['pages']['obj'])} object pages, {size / 1e6:.1f} MB, {time.time() - t0:.0f}s")

    if preview:
        prev = ROOT / ".cache-crops"
        for pi, page in enumerate(room_atlas.final):
            cv2.imwrite(str(prev / f"room-{pi}.jpg"), cv2.resize(page, (page.shape[1] // 4, page.shape[0] // 4), interpolation=cv2.INTER_AREA))
        for pi, page in enumerate(obj_atlas.final):
            cv2.imwrite(str(prev / f"obj-{pi}.jpg"), cv2.resize(page[..., :3], (page.shape[1] // 4, page.shape[0] // 4), interpolation=cv2.INTER_AREA))
            b = obj_atlas.backs[pi][: page.shape[0]]
            cv2.imwrite(str(prev / f"obj-back-{pi}.jpg"), cv2.resize(b[..., :3], (b.shape[1] // 4, b.shape[0] // 4), interpolation=cv2.INTER_AREA))


if __name__ == "__main__":
    main()
