"""The Arnolfini chamber: a sealed room shell and its furniture, every face baked from the panel.

Each face is sampled texel-by-texel from the painter's eye (with occlusion by the furniture
and the figures' masks cut out). Every texel the painter never saw is rebuilt by
synth.complete (extrapolated painted light + quilted painted grain), region by region, so
plaster continues as plaster, boards as boards and the bed's red wool as red wool. No face
has holes: the shell is closed and all furniture boxes are closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import cv2
import numpy as np

from arnolfini_common import BACK_Z, CAM, CEIL_Y, EYE, FRONT_Z, LEFT_X, RIGHT_X, H, W, Source, project
from synth import complete, donor_detail, high_pass, tone_field

Region = Callable[[np.ndarray], np.ndarray]

# furniture (metres)
CHEST = {"x": (LEFT_X, LEFT_X + 0.5), "y": (0.0, 0.63), "z": (-4.2, -3.09)}
CHAIR_SEAT = {"x": (-0.2, 0.32), "y": (0.0, 0.62), "z": (BACK_Z, -4.0)}
CHAIR_BACK = {"x": (-0.2, 0.32), "y": (0.62, 1.22), "z": (BACK_Z, BACK_Z + 0.1)}
CHAIR_POST = {"x": (0.32, 0.39), "y": (0.0, 1.27), "z": (BACK_Z, -3.98)}
BED = {"x": (1.15, RIGHT_X), "y": (0.0, 1.05), "z": (BACK_Z, -1.9)}
# the valance flares out to the floor: its hem meets the boards at x ~1.07 (panel 1800-1880, 1980-2060)
BED_FOOT_X = 1.07
# the canopy (tester): its fringe runs from (1360, 290) to (1740, 20) on the panel; hung slightly
# skewed so its near-left corner sits further right than the back one
TESTER_Y = 2.72
TESTER_LEFT = ((0.82, BACK_Z), (1.12, -2.9))
DOOR = {"x": (-0.55, 0.45), "y": (0.0, 2.05), "z": (FRONT_Z - 0.035, FRONT_Z)}
DOOR_FRAME = 0.09
# back wall: the red hanging behind the bed starts at x 1370 on the panel
DOSSAL_X = 0.8


@dataclass
class Surf:
    id: str
    corners: np.ndarray  # p00, p10, p01, p11 (s right, t up in the texture)
    density: float  # texels per metre
    grain: str = "iso"
    period_m: float | None = None
    period_range: tuple[float, float] = (0.08, 0.45)
    synth: str = "quilt"  # quilt | joists (beams along t, cross-section folded from the paint)
    regions: Region | None = None  # int labels per texel; completes each label separately
    region_grain: dict[int, str] = field(default_factory=dict)
    occluder: bool = True
    donor: str | None = None  # "<surface id>:<region>" whose painted detail fills a paint-poor region
    tone: Callable[[np.ndarray], np.ndarray] | None = None  # explicit light for unpainted faces
    min_cos: float = 0.06
    paint: bool = True  # False: never sample the panel (surface the painter cannot see)
    patch_m: float = 0.16
    tess: int = 4
    split: tuple[int, int] = (1, 1)  # export tiles along (s, t); baked as one texture
    # filled during bake
    size: tuple[float, float] = (0.0, 0.0)
    tex: np.ndarray | None = None
    valid: np.ndarray | None = None
    labels: np.ndarray | None = None
    page: int = -1
    rect: tuple[int, int, int, int] = (0, 0, 0, 0)
    stats: dict = field(default_factory=dict)

    def __post_init__(self):
        c = self.corners
        self.size = (float(np.linalg.norm(c[1] - c[0])), float(np.linalg.norm(c[2] - c[0])))

    @property
    def texel_m(self) -> float:
        return 1.0 / self.density


def quad(sid, O, U, V, density, **kw) -> Surf:
    O, U, V = (np.array(v, float) for v in (O, U, V))
    return Surf(sid, np.stack([O, O + U, O + V, O + U + V]), density, **kw)


def floor(sid, x0, x1, z0, z1, y, d, **kw):
    return quad(sid, (x0, y, z1), (x1 - x0, 0, 0), (0, 0, z0 - z1), d, **kw)


def ceiling(sid, x0, x1, z0, z1, y, d, **kw):
    return quad(sid, (x0, y, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0), d, **kw)


def wall_front(sid, x0, x1, y0, y1, z, d, **kw):  # faces +z
    return quad(sid, (x0, y0, z), (x1 - x0, 0, 0), (0, y1 - y0, 0), d, **kw)


def wall_back(sid, x0, x1, y0, y1, z, d, **kw):  # faces -z
    return quad(sid, (x1, y0, z), (x0 - x1, 0, 0), (0, y1 - y0, 0), d, **kw)


def wall_px(sid, z0, z1, y0, y1, x, d, **kw):  # faces +x
    return quad(sid, (x, y0, z1), (0, 0, z0 - z1), (0, y1 - y0, 0), d, **kw)


def wall_nx(sid, z0, z1, y0, y1, x, d, **kw):  # faces -x
    return quad(sid, (x, y0, z0), (0, 0, z1 - z0), (0, y1 - y0, 0), d, **kw)


def box(sid, b: dict, faces: str, d, **kw) -> list[Surf]:
    """Closed box faces: f(+z) k(-z) t(+y) b(-y) l(-x) r(+x)."""
    (x0, x1), (y0, y1), (z0, z1) = b["x"], b["y"], b["z"]
    out = []
    if "f" in faces:
        out.append(wall_front(f"{sid}-f", x0, x1, y0, y1, z1, d, **kw))
    if "k" in faces:
        out.append(wall_back(f"{sid}-k", x0, x1, y0, y1, z0, d, **kw))
    if "t" in faces:
        out.append(floor(f"{sid}-t", x0, x1, z0, z1, y1, d, **kw))
    if "b" in faces:
        out.append(ceiling(f"{sid}-b", x0, x1, z0, z1, y0, d, **kw))
    if "l" in faces:
        out.append(wall_nx(f"{sid}-l", z0, z1, y0, y1, x0, d, **kw))
    if "r" in faces:
        out.append(wall_px(f"{sid}-r", z0, z1, y0, y1, x1, d, **kw))
    return out


def surface_points(s: Surf, S: np.ndarray, T: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    c = s.corners
    S3, T3 = S[..., None], T[..., None]
    P = (1 - S3) * (1 - T3) * c[0] + S3 * (1 - T3) * c[1] + (1 - S3) * T3 * c[2] + S3 * T3 * c[3]
    n = np.cross(c[1] - c[0], c[2] - c[0])
    n = n / np.linalg.norm(n)
    return P, np.broadcast_to(n, P.shape)


# ---------------------------------------------------------------- the room


def plaster_tone(level: float, warm: float = 0.0) -> Callable[[np.ndarray], np.ndarray]:
    """Light for plaster the painter never saw: brighter towards the window (x = LEFT_X side)."""

    def tone(P: np.ndarray) -> np.ndarray:
        base = np.array(ROOM_PLASTER, np.float32) * level
        # daylight from the window at z ~ -3.7 on the left wall; falls off across the room
        dz = np.abs(P[..., 2] + 3.7)
        k = 0.82 + 0.3 * np.exp(-dz / 2.2) * np.exp(-(P[..., 0] - LEFT_X) / 4.0)
        k = k * (0.9 + 0.1 * np.clip(P[..., 1] / 1.5, 0, 1))
        col = base[None, None] * k[..., None]
        col[..., 2] += warm
        return col

    return tone


ROOM_PLASTER = (120.0, 128.0, 126.0)  # BGR, replaced by the back wall's measured plaster after its bake


def wood_tone(bgr, level=1.0):
    def tone(P):
        return np.broadcast_to(np.array(bgr, np.float32) * level, P.shape).copy()

    return tone


def build_surfaces() -> list[Surf]:
    L: list[Surf] = []
    plaster = {"patch_m": 0.14}

    # Back wall: plaster, the red hanging behind the bed to the right
    def back_regions(P):
        return (P[..., 0] >= DOSSAL_X).astype(np.int32)

    # the hanging's folds fall vertically: rebuilt cloth keeps its source columns
    L.append(wall_front("back", LEFT_X, RIGHT_X, 0.0, CEIL_Y, BACK_Z, 1000.0, regions=back_regions, region_grain={1: "cols"}, **plaster))

    # Floor: boards running into the room (one bake, exported as two tiles)
    L.append(floor("floor", LEFT_X, RIGHT_X, BACK_Z, FRONT_Z, 0.0, 1000.0, grain="cols", patch_m=0.22, split=(1, 2)))

    # Left wall with the window (painted from z -3.0 to the corner); plaster elsewhere
    def left_regions(P):
        z, y = P[..., 2], P[..., 1]
        window = (z < -3.12) & (z > -4.42) & (y > 0.86)
        return window.astype(np.int32)

    L.append(wall_px("left", BACK_Z, FRONT_Z, 0.0, CEIL_Y, LEFT_X, 900.0, regions=left_regions, donor="back:0", tone=plaster_tone(1.05), split=(2, 1), **plaster))
    L.append(wall_nx("right", BACK_Z, FRONT_Z, 0.0, CEIL_Y, RIGHT_X, 650.0, donor="back:0", tone=plaster_tone(1.0), paint=False, **plaster))
    L.append(wall_back("front", LEFT_X, RIGHT_X, 0.0, CEIL_Y, FRONT_Z, 650.0, donor="back:0", tone=plaster_tone(0.92), paint=False, **plaster))
    # Ceiling: joists run into the room like the boards
    L.append(ceiling("ceiling", LEFT_X, RIGHT_X, BACK_Z, FRONT_Z, CEIL_Y, 750.0, grain="cols", split=(1, 2), period_range=(0.18, 0.45), synth="joists"))

    # Furniture
    wood = {"patch_m": 0.08}
    L += box("chest", CHEST, "ftr", 1100.0, **wood)
    L += box("chair-seat", CHAIR_SEAT, "ftlr", 1100.0, patch_m=0.08)
    L += box("chair-back", CHAIR_BACK, "ftlr", 1100.0, patch_m=0.06)
    L += box("chair-post", CHAIR_POST, "ftlr", 1100.0, patch_m=0.04)
    cloth = {"patch_m": 0.14}
    bed = box("bed", BED, "flt", 900.0, **cloth)
    for s in bed:
        if s.id == "bed-l":
            s.corners[[0, 1], 0] = BED_FOOT_X
        elif s.id == "bed-f":
            s.corners[0, 0] = BED_FOOT_X
        s.__post_init__()
    L += bed
    (lx0, lz0), (lx1, lz1) = TESTER_LEFT
    tb, tt = TESTER_Y, CEIL_Y
    # tester: underside (trapezoid), left side (skewed), front
    L.append(Surf("tester-b", np.array([[lx0, tb, lz0], [RIGHT_X, tb, lz0], [lx1, tb, lz1], [RIGHT_X, tb, lz1]], float), 800.0, tess=24, **cloth))
    L.append(Surf("tester-l", np.array([[lx1, tb, lz1], [lx0, tb, lz0], [lx1, tt, lz1], [lx0, tt, lz0]], float), 800.0, tess=8, **cloth))
    L.append(wall_front("tester-f", lx1, RIGHT_X, tb, tt, lz1, 800.0, **cloth))

    # Door in the front wall (seen in the mirror): a closed plank leaf in a frame
    fr = DOOR_FRAME
    (dx0, dx1), (dy0, dy1), (dz0, dz1) = DOOR["x"], DOOR["y"], DOOR["z"]
    door_wood = {"donor": "floor:0", "paint": False, "occluder": False, "grain": "rows", "patch_m": 0.2}
    L.append(wall_back("door-leaf", dx0, dx1, dy0, dy1, dz0, 900.0, tone=wood_tone((52, 66, 86)), **door_wood))
    frame_wood = {"donor": "chest-f:0", "paint": False, "occluder": False, "patch_m": 0.05}
    fz0 = FRONT_Z - 0.07
    for fid, b in (
        ("door-jamb-l", {"x": (dx0 - fr, dx0), "y": (0.0, dy1 + fr), "z": (fz0, FRONT_Z)}),
        ("door-jamb-r", {"x": (dx1, dx1 + fr), "y": (0.0, dy1 + fr), "z": (fz0, FRONT_Z)}),
        ("door-head", {"x": (dx0, dx1), "y": (dy1, dy1 + fr), "z": (fz0, FRONT_Z)}),
    ):
        L += box(fid, b, "klrb", 900.0, tone=wood_tone((40, 52, 68)), **frame_wood)
    return L


# ---------------------------------------------------------------- baking


TILE_MAX = 4070


def texture_size(s: Surf) -> tuple[int, int]:
    w = int(np.clip(round(s.size[0] * s.density), 8, TILE_MAX * s.split[0]))
    h = int(np.clip(round(s.size[1] * s.density), 8, TILE_MAX * s.split[1]))
    return w, h


def _quad_hit(D: np.ndarray, q: Surf) -> np.ndarray:
    """Ray EYE + t*D (t in (0, 1)) hits planar quad q."""
    c = q.corners
    n = np.cross(c[1] - c[0], c[2] - c[0])
    denom = D @ n
    with np.errstate(divide="ignore", invalid="ignore"):
        t = ((c[0] - EYE) @ n) / denom
    cand = (t > 1e-4) & (t < 0.9995) & np.isfinite(t)
    if not cand.any():
        return cand
    X = EYE + np.where(cand, t, 0)[..., None] * D
    hit = np.zeros_like(cand)
    # two triangles (p00, p10, p11) and (p00, p11, p01)
    for a, b, cc in ((c[0], c[1], c[3]), (c[0], c[3], c[2])):
        v0, v1 = b - a, cc - a
        v2 = X - a
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        d20, d21 = v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        v = (d11 * d20 - d01 * d21) / den
        w = (d00 * d21 - d01 * d20) / den
        hit |= (v >= -1e-6) & (w >= -1e-6) & (v + w <= 1 + 1e-6)
    return cand & hit


def occluded(P: np.ndarray, occluders: list[Surf], self_id: str) -> np.ndarray:
    D = P - EYE
    out = np.zeros(P.shape[:-1], bool)
    group = self_id.rsplit("-", 1)[0]
    for q in occluders:
        if q.id == self_id or q.id.rsplit("-", 1)[0] == group:
            continue
        out |= _quad_hit(D, q)
    return out


def sample_panel(src: Source, px: np.ndarray, py: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """2x2 supersampled, level chosen per texel from its footprint (in 1920 px)."""
    scales = sorted(src.levels)
    want = 1.0 / np.maximum(fp, 1e-4)  # source px per 1920 px needed
    lvl = np.full(px.shape, len(scales) - 1, int)
    for i in range(len(scales) - 1, -1, -1):
        lvl = np.where(scales[i] >= want * 0.75, i, lvl)
    # footprint direction is unknown per texel; jitter by a quarter texel in panel space
    out = np.zeros(px.shape + (3,), np.float32)
    dx = np.gradient(px, axis=1) * 0.25
    dy = np.gradient(py, axis=0) * 0.25
    dxt = np.gradient(px, axis=0) * 0.25
    dys = np.gradient(py, axis=1) * 0.25
    for i, s in enumerate(scales):
        sel = lvl == i
        if not sel.any():
            continue
        acc = np.zeros(px.shape + (3,), np.float32)
        for a, b in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            qx = px + a * dx + b * dxt
            qy = py + b * dy + a * dys
            acc += src.sample(qx, qy, s).astype(np.float32)
        out[sel] = acc[sel] / 4
    return out


def bake_surface(s: Surf, src: Source, kill: np.ndarray, occluders: list[Surf], by_id: dict[str, Surf]) -> None:
    w, h = texture_size(s)
    S, T = np.meshgrid((np.arange(w) + 0.5) / w, 1 - (np.arange(h) + 0.5) / h)
    P, N = surface_points(s, S, T)
    labels = s.regions(P) if s.regions else np.zeros((h, w), np.int32)
    img = np.zeros((h, w, 3), np.float32)
    valid = np.zeros((h, w), bool)
    if s.paint:
        px, py, d = project(P)
        inside = (d > 0.05) & (px >= 0.5) & (px <= W - 1.5) & (py >= 0.5) & (py <= H - 1.5)
        to_eye = EYE - P
        cosang = np.einsum("...k,...k", N, to_eye) / np.linalg.norm(to_eye, axis=-1)
        valid = inside & (cosang > s.min_cos)
        ix = np.clip(np.round(px), 0, W - 1).astype(int)
        iy = np.clip(np.round(py), 0, H - 1).astype(int)
        valid &= ~kill[iy, ix]
        if valid.any():
            step = 2
            sub = P[::step, ::step]
            occ = occluded(sub, occluders, s.id)
            occ = np.repeat(np.repeat(occ, step, 0), step, 1)[:h, :w]
            valid &= ~occ
        if valid.any():
            fpx = np.hypot(np.gradient(px, axis=1), np.gradient(py, axis=1))
            fpy = np.hypot(np.gradient(px, axis=0), np.gradient(py, axis=0))
            img = sample_panel(src, px, py, np.maximum(fpx, fpy))
            # the painted rim is often a blend with a masked neighbour: rebuild it too
            valid = cv2.erode(valid.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    if s.synth == "joists":
        s.tex = np.clip(joist_texture(s, img, valid, by_id), 0, 255).astype(np.uint8)
        s.valid, s.labels = valid, labels
        s.stats["painted"] = round(float(valid.mean()), 3)
        return
    tone_img = s.tone(P) if s.tone else None
    out = img.copy()
    for r in np.unique(labels):
        sel = labels == r
        v = valid & sel
        target = sel & ~v
        if not target.any():
            continue
        donor = None
        if s.donor:
            did, dr = s.donor.split(":")
            ds = by_id[did]
            dsel = ds.valid & (ds.labels == int(dr))
            if dsel.any():
                dd, dsel = donor_detail(ds.tex[..., :3].astype(np.float32), dsel, ds.texel_m)
                k = ds.texel_m / s.texel_m
                if abs(k - 1) > 0.02:
                    dd = cv2.resize(dd, None, fx=k, fy=k, interpolation=cv2.INTER_LINEAR)
                    dsel = cv2.resize(dsel.astype(np.uint8), (dd.shape[1], dd.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
                if s.grain == "rows" and ds.grain == "cols":
                    dd, dsel = np.rot90(dd).copy(), np.rot90(dsel).copy()
                donor = (dd, dsel)
        explicit = tone_img if (tone_img is not None and v.sum() < 0.02 * sel.sum()) else None
        if explicit is None and not v.any():
            explicit = tone_img if tone_img is not None else np.broadcast_to(np.array(ROOM_PLASTER, np.float32), img.shape).copy()
        grain = s.region_grain.get(int(r), s.grain)
        period = s.period_m if grain == s.grain else None
        filled = complete(
            out,
            v,
            s.texel_m,
            patch_m=s.patch_m,
            grain=grain,
            period_m=period,
            donor=donor,
            tone=explicit,
            seed=abs(hash(s.id)) % (2**31) + int(r),
            target=target,
        )
        out[target] = filled[target]
    s.tex = np.clip(out, 0, 255).astype(np.uint8)
    s.valid = valid
    s.labels = labels
    s.stats["painted"] = round(float(valid.mean()), 3)


def joist_texture(s: Surf, img: np.ndarray, valid: np.ndarray, by_id: dict[str, Surf]) -> np.ndarray:
    """A joisted ceiling the painter sees only as a thin strip over the back wall. The beams
    run along t, so a column looks the same along its whole length: every column the painter
    saw carries on from the painted strip's front edge. Columns he never saw (behind the
    tester) take the beam cross-section folded from the strip by the joist period. Each beam
    varies a little along its length; the grain comes from the painted floorboards. The strip
    itself stays as painted."""
    h, w = valid.shape
    per = s.period_m / s.texel_m
    cols = np.arange(w)
    phase = np.floor((cols % per) / per * 64).astype(int)
    v = valid.astype(np.float32)
    col_n = v.sum(axis=0)
    col_mean = (img * v[..., None]).sum(axis=0) / np.maximum(col_n, 1)[:, None]
    seen = col_n > 20
    # the strip's front edge (rows nearest the painter: smallest row index) per column
    edge_rows = int(0.08 / s.texel_m)
    first = np.where(seen, np.argmax(valid, axis=0), 0)
    rows = np.arange(h)[:, None]
    band = valid & (rows >= first[None, :]) & (rows < first[None, :] + edge_rows)
    bn = band.sum(axis=0)
    col_edge = (img * band[..., None]).sum(axis=0) / np.maximum(bn, 1)[:, None]
    seen &= bn > 10
    # thin things crossing the strip (the chandelier chain, a fleck) are not beams: a median
    # across columns narrower than a joist gap removes them and keeps the beams' edges
    k = int(0.02 / s.texel_m) | 1
    med = np.stack([cv2.medianBlur(np.clip(col_edge[:, c], 0, 255).astype(np.uint8).reshape(1, -1), k).ravel() for c in range(3)], -1).astype(np.float32)
    thin = np.abs(col_edge - med).mean(axis=1) > 5
    col_edge = np.where(thin[:, None], med, col_edge)
    # columns never seen (behind the tester) repeat the painted ones whole periods away
    if (~seen).any() and seen.any():
        src_col = np.full(w, -1)
        for kk in range(1, int(w / per) + 1):
            for sgn in (1, -1):
                cand = np.round(cols - sgn * kk * per).astype(int)
                ok_c = (src_col < 0) & ~seen & (cand >= 0) & (cand < w)
                ok_c[ok_c] &= seen[cand[ok_c]]
                src_col[ok_c] = cand[ok_c]
        fill = src_col >= 0
        beam_of = np.floor(cols / per).astype(int)
        own = 1 + 0.045 * np.random.default_rng(11).standard_normal(beam_of.max() + 1)
        col_edge[fill] = col_edge[src_col[fill]] * (own[beam_of[fill]] / own[beam_of[src_col[fill]]])[:, None]
        seen = seen | fill
    prof = np.zeros((64, 3), np.float32)
    for b in range(64):
        sel = seen & (phase == b)
        prof[b] = np.average(col_mean[sel], axis=0, weights=col_n[sel]) if sel.any() else np.nan
    good = ~np.isnan(prof[:, 0])
    idx = np.arange(64)
    for c in range(3):
        prof[:, c] = np.interp(idx, idx[good], prof[good, c], period=64)
    prof = cv2.GaussianBlur(np.tile(prof, (3, 1)).reshape(1, -1, 3), (0, 0), 1.0).reshape(-1, 3)[64:128]
    cross = prof[phase]  # (w, 3)
    # light across the room: the strip's column brightness against the folded profile
    ratio = np.where(seen, col_mean.mean(axis=1) / np.maximum(cross.mean(axis=1), 1.0), np.nan)
    ok = ~np.isnan(ratio)
    trend = np.interp(cols, cols[ok], cv2.GaussianBlur(ratio[ok].reshape(1, -1).astype(np.float32), (0, 0), 3 * per).ravel())
    rng = np.random.default_rng(7)
    beam = np.floor(cols / per).astype(int)
    jitter = 1 + 0.045 * rng.standard_normal(beam.max() + 1)
    unseen = cross * (trend * jitter[beam])[:, None]
    # seen columns exactly as painted at the edge, easing into the folded beams where the paint ends
    wseen = np.where(seen, cv2.GaussianBlur(seen.astype(np.float32).reshape(1, -1), (0, 0), per / 2).ravel(), 0.0)
    wseen = np.clip((wseen - 0.5) * 2, 0, 1)[:, None]
    line = col_edge * wseen + unseen * (1 - wseen)
    base = line[None].repeat(h, 0).astype(np.float32)
    # slow variation along each beam, its own for every beam
    along = cv2.GaussianBlur(rng.standard_normal((h // 32 + 2, beam.max() + 1)).astype(np.float32), (0, 0), 1.5)
    along = cv2.resize(along, (beam.max() + 1, h), interpolation=cv2.INTER_CUBIC)[:, beam]
    base *= (1 + 0.035 * along / max(float(along.std()), 1e-6))[..., None]
    # grain along the beams: the painted floorboards' detail (same wood, same direction)
    fl = by_id["floor"]
    ftex = fl.tex.astype(np.float32)
    win = int(1.2 / fl.texel_m)
    ab = cv2.cvtColor(fl.tex, cv2.COLOR_BGR2LAB).astype(np.float32)[..., 1:]
    best, crop = np.inf, None
    for y in range(0, ftex.shape[0] - win, win // 2):
        for x in range(0, ftex.shape[1] - win, win // 2):
            sd = float(ab[y : y + win, x : x + win].std(axis=(0, 1)).sum())
            if sd < best:
                best, crop = sd, (y, x)
    y, x = crop
    patch = ftex[y : y + win, x : x + win]
    lum_d = high_pass(patch, np.ones(patch.shape[:2], bool), fl.texel_m, 0.012).mean(axis=2)
    lum_d = np.clip(lum_d, -3 * lum_d.std(), 3 * lum_d.std()) / max(float(patch.mean()), 1.0)
    k = fl.texel_m / s.texel_m
    lum_d = cv2.resize(lum_d, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    # mirrored tiling: no seam where one copy meets the next
    tile = np.block([[lum_d, lum_d[:, ::-1]], [lum_d[::-1], lum_d[::-1, ::-1]]])
    grain = np.tile(tile, (h // tile.shape[0] + 1, w // tile.shape[1] + 1))[:h, :w]
    out = base * (1 + grain)[..., None]
    # the painted strip exactly, feathered into the synthesis
    if valid.any():
        sigma = 0.02 / s.texel_m
        dist = cv2.distanceTransform((~valid).astype(np.uint8), cv2.DIST_L2, 5) * s.texel_m
        a = np.exp(-dist / 0.06)[..., None]
        painted_light = tone_field(img, valid, sigma)
        synth_light = cv2.GaussianBlur(out, (0, 0), sigma)
        out = np.where(valid[..., None], img, out + (painted_light - synth_light) * a)
    return out


def measure_board_period(s: Surf) -> float | None:
    """Board / joist width (m) from the column profiles along t: floor boards repeat in their dark
    seam lines (across-grain edge energy), ceiling joists in their lit faces against the dark
    gaps between them (luminance); whichever repeats more strongly gives the width."""
    img = s.tex.astype(np.float32)
    v = s.valid.astype(np.float32)
    rows = v.sum(axis=0)
    use = rows > max(40, 0.3 * rows.max())
    if use.sum() < 200:
        return None
    idx = np.nonzero(use)[0]
    g = high_pass(img, s.valid, s.texel_m, 0.03).mean(axis=2)
    edge = (np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)) * v).sum(axis=0) / np.maximum(rows, 1)
    lum = (img.mean(axis=2) * v).sum(axis=0) / np.maximum(rows, 1)
    lo, hi = int(s.period_range[0] / s.texel_m), int(s.period_range[1] / s.texel_m)
    best, best_l, best_kind = 0.1, None, ""
    for kind, prof in (("seam", edge), ("face", lum)):
        p = prof[idx[0] : idx[-1] + 1].astype(np.float32)
        p = p - cv2.GaussianBlur(p.reshape(1, -1), (0, 0), hi).ravel()
        p = (p - p.mean()) / (p.std() + 1e-6)
        lags = np.arange(max(2, lo - 1), min(hi, len(p) // 2) + 1)
        curve = np.array([float((p[:-lag] * p[lag:]).mean()) for lag in lags])
        # a period is an interior peak of the curve, not the edge of the search range
        for i in range(1, len(curve) - 1):
            if curve[i] >= curve[i - 1] and curve[i] >= curve[i + 1] and curve[i] > best:
                best, best_l, best_kind = float(curve[i]), int(lags[i]), kind
    print(f"    {best_kind} autocorr {best:.3f} at {best_l}")
    return best_l * s.texel_m if best_l else None


BAKE_ORDER = ["back", "floor", "chest-f", "chair-seat-f", "chair-back-f", "chair-post-f", "bed-l", "tester-b"]

# how a furniture face is lit relative to the painted face it borrows from (window on the left)
FACE_LIGHT = {"t": 1.05, "f": 1.0, "l": 1.05, "r": 0.78, "k": 0.7, "b": 0.6}


def borrow_from_group(s: Surf, by_id: dict[str, Surf], surfaces: list[Surf]) -> None:
    """A box face the painter barely saw takes its grain and light from the box's best-painted face."""
    group, face = s.id.rsplit("-", 1)
    painted = [q for q in surfaces if q.id.startswith(group + "-") and q.id != s.id and q.tex is not None and q.valid is not None and q.valid.mean() > 0.1]
    if not painted:
        return
    best = max(painted, key=lambda q: q.valid.sum())
    sel = best.valid & (best.labels == 0)
    med = np.median(best.tex[sel].reshape(-1, 3), axis=0)
    s.donor = f"{best.id}:0"
    s.tone = wood_tone(tuple(float(v) for v in med), FACE_LIGHT.get(face, 0.9))


SHELL = ("back", "floor", "left", "right", "front", "ceiling")


def paint_only(s: Surf, src: Source, kill: np.ndarray, occluders: list[Surf]) -> Surf:
    """The painted texels alone (no completion), e.g. to measure a board width."""
    pre = Surf(s.id, s.corners, s.density, occluder=False, split=s.split, min_cos=s.min_cos, period_range=s.period_range)
    w, h = texture_size(pre)
    S, T = np.meshgrid((np.arange(w) + 0.5) / w, 1 - (np.arange(h) + 0.5) / h)
    P, N = surface_points(pre, S, T)
    px, py, d = project(P)
    inside = (d > 0.05) & (px >= 0.5) & (px <= W - 1.5) & (py >= 0.5) & (py <= H - 1.5)
    ix = np.clip(np.round(px), 0, W - 1).astype(int)
    iy = np.clip(np.round(py), 0, H - 1).astype(int)
    pre.valid = inside & ~kill[iy, ix]
    pre.tex = src.sample(px, py, 1.0)
    return pre


def bake_all(src: Source, kill: np.ndarray, only: set[str] | None = None) -> list[Surf]:
    global ROOM_PLASTER
    surfaces = build_surfaces()
    by_id = {s.id: s for s in surfaces}
    occluders = [s for s in surfaces if s.occluder and not s.id.startswith(SHELL)]
    order = [by_id[i] for i in BAKE_ORDER] + [s for s in surfaces if s.id not in BAKE_ORDER]
    for s in order:
        if only and s.id not in only and s.id not in BAKE_ORDER:
            continue
        if s.grain == "cols" and s.paint and s.period_m is None:
            # boards / joists: measure their width on the paint, then complete locked in phase
            s.period_m = measure_board_period(paint_only(s, src, kill, occluders))
            print(f"  {s.id} period: {s.period_m}")
        if s.paint and s.donor is None and s.tone is None and s.id.rsplit("-", 1)[0] != s.id:
            borrow_from_group(s, by_id, surfaces)
        bake_surface(s, src, kill, occluders, by_id)
        if s.id == "back":
            sel = s.valid & (s.labels == 0)
            ROOM_PLASTER = tuple(float(v) for v in np.median(s.tex[sel].reshape(-1, 3), axis=0))
            print(f"  plaster BGR {ROOM_PLASTER}")
        print(f"  bake {s.id:<16} {s.tex.shape[1]}x{s.tex.shape[0]} painted={s.stats['painted']}")
    return [s for s in surfaces if s.tex is not None]


# ---------------------------------------------------------------- export


@dataclass
class Tile:
    surf: Surf
    s0: float
    s1: float
    t0: float
    t1: float
    tex: np.ndarray
    inner: tuple[int, int, int, int]  # x, y, w, h of the tile's own texels inside tex
    page: int = -1
    rect: tuple[int, int, int, int] = (0, 0, 0, 0)


def tiles_of(s: Surf, margin: int = 3) -> list[Tile]:
    """Split a surface texture into export tiles that overlap by a few texels (seamless filtering)."""
    h, w = s.tex.shape[:2]
    ns, nt = s.split
    out = []
    for j in range(nt):
        # t runs up, texture rows run down
        r0, r1 = round(h * (nt - 1 - j) / nt), round(h * (nt - j) / nt)
        for i in range(ns):
            c0, c1 = round(w * i / ns), round(w * (i + 1) / ns)
            a0, a1 = max(0, r0 - margin), min(h, r1 + margin)
            b0, b1 = max(0, c0 - margin), min(w, c1 + margin)
            sub = s.tex[a0:a1, b0:b1]
            inner = (c0 - b0, r0 - a0, c1 - c0, r1 - r0)
            out.append(Tile(s, c0 / w, c1 / w, 1 - r1 / h, 1 - r0 / h, sub, inner))
    return out


def export_meshes(surfaces: list[Surf], atlas) -> dict[int, dict[str, np.ndarray]]:
    tiles = [t for s in surfaces for t in tiles_of(s)]
    for t in sorted(tiles, key=lambda t: -t.tex.shape[0]):
        t.page, rect = atlas.add(t.tex)
        x, y, _, _ = rect
        ix, iy, iw, ih = t.inner
        t.rect = (x + ix, y + iy, iw, ih)
    atlas.finish()
    per_page: dict[int, dict[str, list]] = {}
    for t in tiles:
        s = t.surf
        n = max(1, s.tess // max(s.split))
        ls, lt = np.meshgrid(np.linspace(0, 1, n + 1), np.linspace(0, 1, n + 1))
        S, T = t.s0 + ls * (t.s1 - t.s0), t.t0 + lt * (t.t1 - t.t0)
        P, _ = surface_points(s, S, T)
        uv = atlas.uv(t.page, t.rect, ls, lt)
        idx = []
        for j in range(n):
            for i in range(n):
                a = j * (n + 1) + i
                b, c, d = a + 1, a + n + 1, a + n + 2
                idx += [a, b, d, a, d, c]
        bucket = per_page.setdefault(t.page, {"pos": [], "uv": [], "idx": [], "n": 0})
        base = bucket["n"]
        bucket["pos"].append(P.reshape(-1, 3).astype(np.float32))
        bucket["uv"].append(uv.reshape(-1, 2))
        bucket["idx"].append(np.array(idx, np.uint32) + base)
        bucket["n"] += P.shape[0] * P.shape[1]
    return {
        pi: {"position": np.concatenate(b["pos"]), "uv": np.concatenate(b["uv"]), "index": np.concatenate(b["idx"])}
        for pi, b in per_page.items()
    }
