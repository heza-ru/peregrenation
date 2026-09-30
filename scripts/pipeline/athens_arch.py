"""Authored School of Athens architecture + per-surface texture bakes.

Every surface is baked into its own texture from the full-resolution fresco, seen from
the painter's eye (with occlusion). Texels the painter never saw are filled from the
hall's mirror symmetry, then its periodic structure (bays, coffers, pavement), then an
inpaint clamped to the surface's own marble tone. Surfaces therefore hold real painted pixels
in their own UV space and look right from any viewpoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import cv2
import numpy as np

from athens_common import CAM, EYE, H, STEP_FRONTS, STEP_RISE, W, Atlas, Source, in_lunette, project

HALL = 8.6
NAVE = 2.55
SPRING = 5.45
TOP = SPRING + NAVE  # 8.0
PIER_Z = -3.3
# Measured on the fresco: bay 1's end arch (crown px 300, half-width 227 px) -> z -7.7,
# spring 5.49; bay 2's front arch (crown 440, half-width 155) -> z -16.0; bay 2's end
# arch (crown 540, half-width 102) -> z -29.5. Drum windows sit at y 9.0-10.2.
BAY1_END = -7.7
CROSS_END = -16.0
CROSS_HALF = 4.2
CROSS_TOP = 8.8
BAY2_END = -29.5
FAR_Z = -32.0
FAR_OPEN = 2.1
FAR_SPRING = 3.5
# The ornamental entrance: the real Stanza wall around the lunette (Greek-key arch, grotesque
# panels, doorway) stands at this plane; seen from the painter's eye its opening is exactly the
# fresco's frame. Visitors start on a landing in front of it, out in a dark void.
PORTAL_Z = 3.0
PORTAL_HALF, PORTAL_TOP = 11.0, 16.0
LANDING_END = 10.5
FORE_TOP = 10.5
DRUM_R = 3.6
DRUM_Z = (BAY1_END + CROSS_END) / 2
PY = 1.0

NEAR, MID, FAR = 220.0, 128.0, 90.0

Hole = Callable[[np.ndarray], np.ndarray]


@dataclass
class Surf:
    id: str
    kind: str  # quad | vault | drum | dome
    p: dict
    density: float
    fill: str = "inpaint"  # rows | tile | inpaint
    period: tuple[float | None, float | None] = (None, None)  # metres along (s, t) for tile fill
    hole: Hole | None = None
    occluder: bool = True
    share: str | None = None  # reuse another surface's texture rect
    # stray figure paint rejection: "masonry" (colour), "floor" (colour + dark specks), "none"
    stray: str = "masonry"
    row_outliers: float = 0.0  # >0: texels this far (luma) from their row's median are stray paint
    min_cos: float = 0.07  # reject texels the painter saw at a steeper grazing angle
    valid_above: float | None = None  # below this height the fresco only shows (unmasked) figures
    tile_all: bool = False  # replace every texel with the clean pattern unit (tile fill)
    custom: str | None = None  # texture made by a dedicated generator instead of the painter's-eye bake
    # filled during bake
    size: tuple[float, float] = (0.0, 0.0)
    tex: np.ndarray | None = None
    page: int = -1
    rect: tuple[int, int, int, int] = (0, 0, 0, 0)
    stats: dict = field(default_factory=dict)


# ---------------------------------------------------------------- geometry helpers


def quad(sid, O, U, V, density, **kw) -> Surf:
    O, U, V = (np.array(v, float) for v in (O, U, V))
    s = Surf(sid, "quad", {"O": O, "U": U, "V": V}, density, **kw)
    s.size = (float(np.linalg.norm(U)), float(np.linalg.norm(V)))
    return s


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


def box(sid, x, y, z, faces: str, d, **kw) -> list[Surf]:
    (x0, x1), (y0, y1), (z0, z1) = x, y, z
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


def mbox(sid, x, y, z, faces: str, d, **kw) -> list[Surf]:
    """Right-side box plus its mirror on the left (inner/outer faces swap l<->r)."""
    swap = faces.translate(str.maketrans("lr", "rl"))
    return box(f"{sid}-R", x, y, z, faces, d, **kw) + box(f"{sid}-L", (-x[1], -x[0]), y, z, swap, d, **kw)


def arch_hole(half: float, spring: float) -> Hole:
    def hole(P):
        x, y = P[..., 0], P[..., 1]
        return (np.abs(x) < half) & ((y < spring) | (x**2 + (y - spring) ** 2 < half**2))

    return hole


def circle_hole(r: float, zc: float) -> Hole:
    return lambda P: P[..., 0] ** 2 + (P[..., 2] - zc) ** 2 < r**2


def surface_points(s: Surf, S: np.ndarray, T: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(S, T) in [0,1] -> world points and unit normals facing the visitor."""
    p = s.p
    if s.kind == "quad":
        n = np.cross(p["U"], p["V"])
        n = n / np.linalg.norm(n)
        P = p["O"] + S[..., None] * p["U"] + T[..., None] * p["V"]
        return P, np.broadcast_to(n, P.shape)
    if s.kind == "vault":
        th = np.pi * S
        z = p["zn"] + T * (p["zf"] - p["zn"])
        P = np.stack([p["r"] * np.cos(th), p["cy"] + p["r"] * np.sin(th), z], -1)
        N = np.stack([-np.cos(th), -np.sin(th), np.zeros_like(th)], -1)
        return P, N
    if s.kind == "drum":
        ph = 2 * np.pi * S
        P = np.stack([p["r"] * np.cos(ph), p["y0"] + T * (p["y1"] - p["y0"]), p["zc"] + p["r"] * np.sin(ph)], -1)
        N = np.stack([-np.cos(ph), np.zeros_like(ph), -np.sin(ph)], -1)
        return P, N
    if s.kind == "dome":
        az, el = 2 * np.pi * S, 0.5 * np.pi * T
        C = np.array([0.0, p["y0"], p["zc"]])
        D = np.stack([np.cos(el) * np.cos(az), np.sin(el), np.cos(el) * np.sin(az)], -1)
        return C + p["r"] * D, -D
    raise ValueError(s.kind)


def vault(sid, zn, zf, r, cy, d, **kw):
    s = Surf(sid, "vault", {"zn": zn, "zf": zf, "r": r, "cy": cy}, d, **kw)
    s.size = (np.pi * r, abs(zf - zn))
    return s


# ---------------------------------------------------------------- the hall


def build_surfaces() -> list[Surf]:
    L: list[Surf] = []
    fronts = STEP_FRONTS
    # Forecourt, steps, platform
    flr = {"stray": "floor"}
    step = {"stray": "floor", "fill": "rows", "row_outliers": 16.0}
    # Raphael's pavement is one repeating unit: rebuild all of it from its cleanest painted unit
    L.append(floor("forecourt", -HALL, HALL, fronts[0], PORTAL_Z, 0.0, NEAR, fill="tile", period=(1.61, 0.92), tile_all=True, **flr))
    for i, zf in enumerate(fronts):
        L.append(wall_front(f"riser-{i}", -HALL, HALL, i * STEP_RISE, (i + 1) * STEP_RISE, zf, NEAR, **step))
    for i in range(3):
        L.append(floor(f"tread-{i}", -HALL, HALL, fronts[i + 1], fronts[i], (i + 1) * STEP_RISE, NEAR, **step))
    L.append(floor("platform", -HALL, HALL, PIER_Z, fronts[3], PY, NEAR, fill="tile", row_outliers=22.0, **flr))
    L += box("heraclitus-block", (-0.65, 0.01), (0.0, 0.62), (0.23, 0.83), "ftlrk", NEAR)

    # Front piers (painted face with Apollo / Athena niches) and their relief
    L.append(wall_front("pier-L", -HALL, -NAVE, PY, FORE_TOP, PIER_Z, NEAR))
    L.append(wall_front("pier-R", NAVE, HALL, PY, FORE_TOP, PIER_Z, NEAR))
    L.append(wall_front("spandrel", -NAVE, NAVE, SPRING, FORE_TOP, PIER_Z, NEAR, hole=arch_hole(NAVE, SPRING)))
    for x in ((2.65, 3.75), (5.3, 6.2)):
        L += mbox(f"pilaster{x[0]}", x, (PY, 6.6), (PIER_Z, PIER_Z + 0.2), "flr", NEAR)
    for x in ((2.55, 3.9), (5.15, 6.35)):
        L += mbox(f"base{x[0]}", x, (PY, PY + 0.35), (PIER_Z, PIER_Z + 0.3), "ftlr", NEAR)
        L += mbox(f"capital{x[0]}", x, (6.6, 6.95), (PIER_Z, PIER_Z + 0.3), "ftblr", NEAR)
    L += mbox("entablature", (NAVE, HALL), (6.95, 7.5), (PIER_Z, PIER_Z + 0.38), "ftbl", NEAR)
    L += mbox("plinth", (3.95, 5.05), (3.55, 3.85), (PIER_Z, PIER_Z + 0.45), "ftblr", NEAR)

    # First bay: painted walls and coffered barrel vault
    nave_wall = {"valid_above": 2.9, "fill": "columns"}
    L.append(wall_px("bay1-L", BAY1_END, PIER_Z, PY, SPRING, -NAVE, MID, **nave_wall))
    L.append(wall_nx("bay1-R", BAY1_END, PIER_Z, PY, SPRING, NAVE, MID, **nave_wall))
    coffers = {"fill": "tile", "period": (0.96, 0.95), "min_cos": 0.2}
    L.append(vault("vault-1", PIER_Z, BAY1_END, NAVE - 0.005, SPRING, MID, **coffers))

    # Crossing with drum and cupola
    # the fresco only shows the crossing's far face; its near face is the same architecture
    L.append(wall_back("cross-back", -CROSS_HALF, CROSS_HALF, PY, CROSS_TOP, BAY1_END, MID, share="cross-front", hole=arch_hole(NAVE, SPRING)))
    L.append(wall_front("cross-front", -CROSS_HALF, CROSS_HALF, PY, CROSS_TOP, CROSS_END, MID, hole=arch_hole(NAVE, SPRING)))
    L.append(wall_px("cross-L", CROSS_END, BAY1_END, PY, CROSS_TOP, -CROSS_HALF, MID))
    L.append(wall_nx("cross-R", CROSS_END, BAY1_END, PY, CROSS_TOP, CROSS_HALF, MID))
    L.append(ceiling("cross-ceil", -CROSS_HALF, CROSS_HALF, CROSS_END, BAY1_END, CROSS_TOP, MID, hole=circle_hole(DRUM_R, DRUM_Z)))
    L.append(floor("cross-floor-R", NAVE, CROSS_HALF, CROSS_END, BAY1_END, PY, MID, **flr))
    L.append(floor("cross-floor-L", -CROSS_HALF, -NAVE, CROSS_END, BAY1_END, PY, MID, **flr))
    drum = Surf("drum", "drum", {"r": DRUM_R, "zc": DRUM_Z, "y0": CROSS_TOP, "y1": CROSS_TOP + 2.0}, MID, fill="tile", stray="none")
    drum.size = (2 * np.pi * DRUM_R, 2.0)
    dome = Surf("dome", "dome", {"r": DRUM_R, "zc": DRUM_Z, "y0": CROSS_TOP + 2.0}, MID)
    dome.size = (2 * np.pi * DRUM_R, np.pi * DRUM_R / 2)
    L += [drum, dome]

    # Second bay
    L.append(wall_px("bay2-L", BAY2_END, CROSS_END, PY, SPRING, -NAVE, FAR, **nave_wall))
    L.append(wall_nx("bay2-R", BAY2_END, CROSS_END, PY, SPRING, NAVE, FAR, **nave_wall))
    # the far vault is only ever seen obliquely from the painter's eye
    L.append(vault("vault-2", CROSS_END, BAY2_END, NAVE - 0.005, SPRING, FAR, **{**coffers, "min_cos": 0.1}))
    L.append(wall_back("bay2-end", -CROSS_HALF, CROSS_HALF, PY, CROSS_TOP, BAY2_END, FAR, share="cross-front", hole=arch_hole(NAVE, SPRING)))

    # Open court, far screen wall with its arch, ground and sky beyond
    L.append(floor("nave-floor", -NAVE, NAVE, FAR_Z, PIER_Z, PY, MID, fill="tile", **flr))
    L.append(wall_px("court-L", FAR_Z, BAY2_END, PY, 6.6, -NAVE, FAR))
    L.append(wall_nx("court-R", FAR_Z, BAY2_END, PY, 6.6, NAVE, FAR))
    L.append(floor("court-top-L", -4.2, -NAVE, FAR_Z, BAY2_END, 6.6, FAR))
    L.append(floor("court-top-R", NAVE, 4.2, FAR_Z, BAY2_END, 6.6, FAR))
    L.append(wall_front("far-wall", -6.5, 6.5, PY, 6.6, FAR_Z, FAR, hole=arch_hole(FAR_OPEN, FAR_SPRING)))
    L += box("far-ent", (-6.5, 6.5), (6.6, 7.1), (FAR_Z - 0.7, FAR_Z + 0.1), "ftb", FAR)
    L.append(vault("far-arch", FAR_Z, FAR_Z - 0.6, FAR_OPEN, FAR_SPRING, FAR))
    L.append(wall_px("far-jamb-L", FAR_Z - 0.6, FAR_Z, PY, FAR_SPRING, -FAR_OPEN, FAR))
    L.append(wall_nx("far-jamb-R", FAR_Z - 0.6, FAR_Z, PY, FAR_SPRING, FAR_OPEN, FAR))
    L.append(floor("ground", -40, 40, -58, FAR_Z - 0.6, PY, 12.0, fill="rows", stray="none"))
    L.append(wall_front("sky", -30, 30, PY, 40, -58, 30.0, fill="rows", occluder=False, stray="none"))

    # Forecourt side walls (beyond the fresco's frame), dressed with the piers' painted marble
    L.append(wall_px("fore-side-L", PIER_Z, PORTAL_Z, 0.0, FORE_TOP, -HALL, NEAR, share="pier-L", occluder=False))
    L.append(wall_nx("fore-side-R", PIER_Z, PORTAL_Z, 0.0, FORE_TOP, HALL, NEAR, share="pier-R", occluder=False))

    # The ornamental entrance and the landing in front of it
    out = {"occluder": False, "stray": "none"}
    L.append(wall_front("portal", -PORTAL_HALF, PORTAL_HALF, 0.0, PORTAL_TOP, PORTAL_Z, 170.0, custom="portal", **out))
    L.append(wall_back("portal-inner", -HALL, HALL, 0.0, FORE_TOP, PORTAL_Z - 0.06, 60.0, custom="portal-inner", **out))
    L.append(floor("landing", -HALL, HALL, PORTAL_Z, LANDING_END, 0.0, 150.0, custom="landing", **out))
    return L


# ---------------------------------------------------------------- baking


def texture_size(s: Surf) -> tuple[int, int]:
    w = int(np.clip(round(s.size[0] * s.density), 8, 4096))
    h = int(np.clip(round(s.size[1] * s.density), 8, 4096))
    return w, h


def occluded(P: np.ndarray, occluders: list[Surf], self_id: str) -> np.ndarray:
    D = P - EYE
    out = np.zeros(P.shape[:-1], bool)
    for q in occluders:
        if q.id == self_id or q.kind != "quad":
            continue
        O, U, V = q.p["O"], q.p["U"], q.p["V"]
        n = np.cross(U, V)
        denom = D @ n
        with np.errstate(divide="ignore", invalid="ignore"):
            t = ((O - EYE) @ n) / denom
        cand = (t > 1e-3) & (t < 0.995) & np.isfinite(t)
        if not cand.any():
            continue
        t = np.where(cand, t, 0.0)
        X = EYE + t[..., None] * D
        R = X - O
        a = (R @ U) / (U @ U)
        b = (R @ V) / (V @ V)
        hit = cand & (a >= 0) & (a <= 1) & (b >= 0) & (b <= 1)
        if q.hole is not None and hit.any():
            hit &= ~q.hole(X)
        out |= hit
    return out


def bake_view(s: Surf, P, N, src: Source, scene: np.ndarray, kill: np.ndarray, occluders, occ_step: int = 3):
    px, py, d = project(P)
    inside = (d > 0.5) & (px >= 1) & (px < W - 2) & (py >= 1) & (py < H - 2)
    ix = np.clip(px, 0, W - 1).astype(int)
    iy = np.clip(py, 0, H - 1).astype(int)
    valid = inside & scene[iy, ix] & ~kill[iy, ix]
    to_eye = EYE - P
    cosang = np.einsum("...k,...k", N, to_eye) / np.linalg.norm(to_eye, axis=-1)
    valid &= cosang > s.min_cos
    if s.valid_above is not None:
        valid &= P[..., 1] >= s.valid_above
    # occlusion on a coarse grid, upsampled
    sub = P[::occ_step, ::occ_step]
    occ = occluded(sub, occluders, s.id)
    occ = np.repeat(np.repeat(occ, occ_step, 0), occ_step, 1)[: P.shape[0], : P.shape[1]]
    valid &= ~occ
    if valid.any():
        want = float(np.median((s.density * d[valid] / CAM["f"]) / np.maximum(cosang[valid], 0.2)))
    else:
        want = 1.0
    color = src.sample(px, py, max(want, 1.0))
    lab = cv2.cvtColor(color, cv2.COLOR_BGR2LAB).astype(np.int16)
    if s.stray != "none":
        # judge colour on a smoothed image and ignore isolated specks: pigment noise is not a figure
        soft = cv2.cvtColor(cv2.GaussianBlur(color, (0, 0), 2.0), cv2.COLOR_BGR2LAB).astype(np.int16)
        chroma = np.hypot(soft[..., 1] - 128, soft[..., 2] - 128)
        stray = cv2.morphologyEx((chroma > 30).astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        if s.stray == "floor":
            stray |= (soft[..., 0] < 70).astype(np.uint8)  # thin dark staffs / compasses the masks missed
        valid &= ~(cv2.dilate(stray, np.ones((5, 5), np.uint8)) > 0)
    if s.row_outliers > 0:
        luma = lab[..., 0].astype(np.float32)
        for r in range(luma.shape[0]):
            v = valid[r]
            if v.sum() >= 8:
                med = np.median(luma[r][v])
                valid[r] &= np.abs(luma[r] - med) < s.row_outliers
    return color, valid, cosang


def estimate_period(gray: np.ndarray, valid: np.ndarray, axis: int, lo: int, hi: int) -> int | None:
    g = gray.astype(np.float32)
    best, best_l = 0.3, None
    for lag in range(max(lo, 2), min(hi, g.shape[axis] // 2)):
        if axis == 1:
            a, b, va, vb = g[:, :-lag], g[:, lag:], valid[:, :-lag], valid[:, lag:]
        else:
            a, b, va, vb = g[:-lag], g[lag:], valid[:-lag], valid[lag:]
        m = va & vb
        if m.sum() < 400:
            continue
        x, y = a[m], b[m]
        x = x - x.mean()
        y = y - y.mean()
        c = float((x * y).mean() / (x.std() * y.std() + 1e-6))
        if c > best:
            best, best_l = c, lag
    return best_l


def fill_tile(img, valid, ps: int | None, pt: int | None):
    img, valid = img.copy(), valid.copy()
    for axis, per in ((1, ps), (0, pt)):
        if not per:
            continue
        for k in (1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6):
            if valid.all():
                break
            sh = np.roll(img, k * per, axis=axis)
            sv = np.roll(valid, k * per, axis=axis)
            # no wrap-around
            if axis == 1:
                if k > 0:
                    sv[:, : k * per] = False
                else:
                    sv[:, k * per :] = False
            else:
                if k > 0:
                    sv[: k * per] = False
                else:
                    sv[k * per :] = False
            take = ~valid & sv
            img[take] = sh[take]
            valid |= take
    return img, valid


def median_unit(img, valid, by: int, bx: int, ps: int, pt: int, reach: int = 2) -> np.ndarray:
    """Per-texel median over the neighbouring painted copies of a pattern unit: residue left by
    figures on any single copy disappears, the painted pattern itself survives."""
    h, w = valid.shape
    copies, masks = [], []
    for i in range(-reach, reach + 1):
        y = by + i * pt
        if y < 0 or y + pt > h:
            continue
        for j in range(-reach, reach + 1):
            x = bx + j * ps
            if x < 0 or x + ps > w:
                continue
            copies.append(img[y : y + pt, x : x + ps].astype(np.float32))
            masks.append(valid[y : y + pt, x : x + ps].astype(np.float32))
    base = img[by : by + pt, bx : bx + ps].astype(np.float32)
    # register every copy on the base unit (the painted period is not a whole number of texels)
    g0 = base.mean(axis=2)
    for n, c in enumerate(copies):
        (dx, dy), _ = cv2.phaseCorrelate(g0, c.mean(axis=2))
        if abs(dx) > ps / 4 or abs(dy) > pt / 4:
            continue
        M = np.float32([[1, 0, -dx], [0, 1, -dy]])
        copies[n] = cv2.warpAffine(c, M, (ps, pt), borderMode=cv2.BORDER_REFLECT)
        masks[n] = cv2.warpAffine(masks[n], M, (ps, pt), borderValue=0)
    stack = np.stack(copies)
    stack[np.stack(masks) < 0.99] = np.nan
    med = np.nanmedian(stack, axis=0)
    return np.where(np.isnan(med), base, med).astype(img.dtype)


def fill_tile_block(img, valid, ps: int, pt: int, replace_all: bool = False, info: dict | None = None):
    """Fill with one clean, fully painted pattern unit, phase-aligned to the painted floor."""
    h, w = valid.shape
    if ps >= w or pt >= h:
        return img, valid
    gray = cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    dark = (gray < 70).astype(np.uint8)
    vi, di = cv2.integral(valid.astype(np.uint8)), cv2.integral(dark)

    def box_sum(ii, y, x):
        return ii[y + pt, x + ps] - ii[y, x + ps] - ii[y + pt, x] + ii[y, x]

    best, pos = None, None
    for y in range(0, h - pt + 1, max(1, pt // 6)):
        for x in range(0, w - ps + 1, max(1, ps // 6)):
            cover = box_sum(vi, y, x) / (ps * pt)
            if cover < 0.985:
                continue
            score = box_sum(di, y, x)
            if best is None or score < best:
                best, pos = score, (y, x)
    if pos is None:
        return fill_tile(img, valid, ps, pt)
    by, bx = pos
    block = median_unit(img, valid, by, bx, ps, pt)
    if info is not None:
        info.update(block=block, origin=(by, bx))
    rr = (np.arange(h) - by) % pt
    cc = (np.arange(w) - bx) % ps
    tiled = block[rr][:, cc]
    if replace_all:
        return tiled.astype(img.dtype), np.ones_like(valid)
    out = img.copy()
    out[~valid] = tiled[~valid]
    return out, np.ones_like(valid)


def fill_columns_down(img, valid, band: int = 80):
    """Continue each column's lowest painted band downward (pilasters and panels run to the floor)."""
    out, got = img.copy(), valid.copy()
    h = img.shape[0]
    for c in range(img.shape[1]):
        rows = np.nonzero(valid[:, c])[0]
        if len(rows) < 8:
            continue
        last = rows.max()
        b = min(band, len(rows))
        for r in range(last + 1, h):
            if got[r, c]:
                continue
            k = (r - last - 1) % (2 * b)
            src = last - k if k < b else last - (2 * b - 1 - k)
            if valid[src, c]:
                out[r, c] = img[src, c]
                got[r, c] = True
    return out, got


def fill_rows(img, valid):
    out = img.copy()
    h = img.shape[0]
    med = np.zeros((h, 3), np.float32)
    has = np.zeros(h, bool)
    for r in range(h):
        v = valid[r]
        if v.sum() >= 3:
            med[r] = np.median(img[r][v], axis=0)
            has[r] = True
    if not has.any():
        return out, valid
    idx = np.arange(h)
    for c in range(3):
        med[:, c] = np.interp(idx, idx[has], med[has, c])
    fillimg = np.broadcast_to(med[:, None, :], img.shape).astype(np.float32)
    out[~valid] = fillimg[~valid]
    return out, np.ones_like(valid)


def fill_inpaint(img, valid):
    h, w = valid.shape
    scale = min(1.0, 384.0 / max(h, w))
    sw, sh = max(4, int(w * scale)), max(4, int(h * scale))
    small = cv2.resize(img.astype(np.uint8), (sw, sh), interpolation=cv2.INTER_AREA)
    smask = cv2.resize((~valid).astype(np.uint8) * 255, (sw, sh), interpolation=cv2.INTER_NEAREST)
    small_valid = cv2.resize(valid.astype(np.uint8), (sw, sh), interpolation=cv2.INTER_AREA) > 0
    if not small_valid.any():
        return img, valid
    smask = cv2.dilate(smask, np.ones((3, 3), np.uint8))
    filled = cv2.inpaint(small, smask, 6, cv2.INPAINT_TELEA)
    filled = cv2.GaussianBlur(filled, (0, 0), 2.0).astype(np.float32)
    # stay close to the surface's own marble tone: no colour blobs from neighbouring figures
    base = np.median(small[small_valid].reshape(-1, 3), axis=0).astype(np.float32)
    # continuous with the paint at the boundary, settling to the plain marble tone further in
    reach = cv2.distanceTransform((~small_valid).astype(np.uint8), cv2.DIST_L2, 5)
    fade = np.exp(-reach / max(6.0, 0.04 * max(sw, sh)))[..., None]
    filled = base + np.clip(filled - base, -12, 12) * fade
    big = cv2.resize(filled, (w, h), interpolation=cv2.INTER_CUBIC)
    out = img.copy()
    out[~valid] = big[~valid]
    return out, np.ones_like(valid)


def bake_surface(s: Surf, src: Source, scene, kill, occluders) -> None:
    w, h = texture_size(s)
    S, T = np.meshgrid((np.arange(w) + 0.5) / w, 1 - (np.arange(h) + 0.5) / h)
    P, N = surface_points(s, S, T)
    color, valid, _ = bake_view(s, P, N, src, scene, kill, occluders)
    img = color.astype(np.float32)
    own = valid.copy()

    hole = s.hole(P) if s.hole is not None else np.zeros_like(valid)
    need = ~valid & ~hole
    if need.any():
        mP = P * np.array([-1.0, 1, 1])
        mN = N * np.array([-1.0, 1, 1])
        mcolor, mvalid, _ = bake_view(s, mP, mN, src, scene, kill, occluders)
        take = need & mvalid
        img[take] = mcolor[take]
        valid |= take

    if s.fill == "columns":
        img, valid = fill_columns_down(img, valid)
    valid_or_hole = valid | hole
    if not valid_or_hole.all():
        if s.fill == "rows":
            img, valid = fill_rows(img, valid)
        else:
            if s.fill == "tile":
                k = min(1.0, 256.0 / max(w, h))
                sw, sh = max(8, int(w * k)), max(8, int(h * k))
                gray = cv2.cvtColor(cv2.resize(np.clip(img, 0, 255).astype(np.uint8), (sw, sh), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
                sval = cv2.resize(valid.astype(np.uint8), (sw, sh), interpolation=cv2.INTER_NEAREST) > 0
                ps = int(round(s.period[0] * w / s.size[0])) if s.period[0] else None
                pt = int(round(s.period[1] * h / s.size[1])) if s.period[1] else None
                if ps is None:
                    e = estimate_period(gray, sval, 1, int(0.06 * sw), int(0.5 * sw))
                    ps = int(round(e * w / sw)) if e else None
                if pt is None:
                    e = estimate_period(gray, sval, 0, int(0.06 * sh), int(0.5 * sh))
                    pt = int(round(e * h / sh)) if e else None
                if ps and pt:
                    img, valid = fill_tile_block(img, valid, ps, pt, s.tile_all, s.stats)
                else:
                    img, valid = fill_tile(img, valid, ps, pt)
                s.stats["period"] = (ps, pt)
            img, valid = fill_inpaint(img, valid | hole)
    # soften seams between painted and filled texels
    soft = cv2.GaussianBlur(own.astype(np.float32), (0, 0), 1.5)
    blur = cv2.GaussianBlur(img, (0, 0), 1.0)
    img = img * soft[..., None] + blur * (1 - soft[..., None]) * 0.35 + img * (1 - soft[..., None]) * 0.65
    rgba = np.dstack([np.clip(img, 0, 255).astype(np.uint8), np.where(hole, 0, 255).astype(np.uint8)])
    s.tex = rgba
    s.stats["painted"] = round(float(own.mean()), 3)


def portal_opening(P: np.ndarray) -> np.ndarray:
    """Texels of an entrance-plane surface that lie inside the lunette as seen from the painter's eye."""
    px, py, _ = project(P)
    return in_lunette(px, py)


def portal_texture(s: Surf, src: Source) -> np.ndarray:
    """The Stanza wall around the fresco, straight from the photograph, fading into the void."""
    w, h = texture_size(s)
    S, T = np.meshgrid((np.arange(w) + 0.5) / w, 1 - (np.arange(h) + 0.5) / h)
    P, _ = surface_points(s, S, T)
    px, py, _ = project(P)

    def fold(v, lo, strip):
        """Reflect coordinates beyond an image edge back into the ornament strip along it."""
        m = np.mod(v - lo, 2 * strip)
        return lo + np.where(m < strip, m, 2 * strip - m)

    # beyond the photograph, repeat only the frame ornament that runs along each edge
    qx = np.where(px < 0, fold(-px, 0, 180), np.where(px > W, W - fold(px - W, 0, 110), px))
    qy = np.where(py < 0, fold(-py, 0, 170), np.where(py > H, H - fold(py - H, 0, 150), py))
    rgb = src.sample(qx.astype(np.float32), qy.astype(np.float32), 1.5).astype(np.float32)
    # distance (m) outside the photographed area: the continued ornament dims into the void
    k = (CAM["eyeZ"] - PORTAL_Z) / CAM["f"]
    ox = np.maximum(0, np.maximum(-px, px - W)) * k
    oy = np.maximum(0, np.maximum(-py, py - H)) * k
    fade = 0.06 + 0.94 * np.exp(-np.hypot(ox, oy) / 1.6)
    rgb *= fade[..., None]
    alpha = np.where(portal_opening(P), 0, 255).astype(np.uint8)
    return np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), alpha])


def portal_inner_texture(s: Surf, marble: np.ndarray) -> np.ndarray:
    """The entrance wall seen from inside the hall: the hall's marble, shaded around the opening."""
    w, h = texture_size(s)
    S, T = np.meshgrid((np.arange(w) + 0.5) / w, 1 - (np.arange(h) + 0.5) / h)
    P, _ = surface_points(s, S, T)
    opening = portal_opening(P)
    edge = cv2.distanceTransform((~opening).astype(np.uint8), cv2.DIST_L2, 5) / s.density
    shade = (0.78 + 0.22 * np.clip(edge / 0.6, 0, 1)) * (0.86 + 0.14 * T)
    rgb = marble[None, None, :] * shade[..., None]
    alpha = np.where(opening, 0, 255).astype(np.uint8)
    return np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), alpha])


def landing_texture(s: Surf, forecourt: Surf) -> np.ndarray:
    """Raphael's pavement continuing out through the entrance, phase-continuous with the forecourt."""
    w, h = texture_size(s)
    S, T = np.meshgrid((np.arange(w) + 0.5) / w, 1 - (np.arange(h) + 0.5) / h)
    P, _ = surface_points(s, S, T)
    block, (by, bx) = forecourt.stats["block"], forecourt.stats["origin"]
    pt, ps = block.shape[:2]
    fz0 = forecourt.p["O"][2] + forecourt.p["V"][2]  # forecourt far edge = its texture row 0
    fx0 = forecourt.p["O"][0]
    col = ((P[..., 0] - fx0) * forecourt.density).astype(int)
    row = np.round((P[..., 2] - fz0) * forecourt.density).astype(int)
    rgb = block[(row - by) % pt, (col - bx) % ps]
    return np.dstack([np.clip(rgb, 0, 255).astype(np.uint8), np.full((h, w), 255, np.uint8)])


def bake_all(src: Source, scene: np.ndarray, kill: np.ndarray) -> list[Surf]:
    surfaces = build_surfaces()
    by_id = {s.id: s for s in surfaces}
    occluders = [s for s in surfaces if s.occluder]
    for s in surfaces:
        if s.share or s.custom:
            continue
        bake_surface(s, src, scene, kill, occluders)
        print(f"  bake {s.id:<24} {s.tex.shape[1]}x{s.tex.shape[0]} painted={s.stats.get('painted')} {s.stats.get('period', '')}")
    marble = np.median(by_id["pier-L"].tex[..., :3].reshape(-1, 3), axis=0).astype(np.float32)
    for s in surfaces:
        if s.custom == "portal":
            s.tex = portal_texture(s, src)
        elif s.custom == "portal-inner":
            s.tex = portal_inner_texture(s, marble)
        elif s.custom == "landing":
            s.tex = landing_texture(s, by_id["forecourt"])
    return surfaces


# ---------------------------------------------------------------- export


def tessellation(s: Surf) -> tuple[int, int]:
    return {"quad": (1, 1), "vault": (48, 1), "drum": (64, 1), "dome": (48, 12)}[s.kind]


def export_meshes(surfaces: list[Surf], atlas: Atlas) -> dict[int, dict[str, np.ndarray]]:
    by_id = {s.id: s for s in surfaces}
    for s in sorted((s for s in surfaces if s.tex is not None), key=lambda s: -s.tex.shape[0]):
        s.page, s.rect = atlas.add(s.tex)
    atlas.finish()
    per_page: dict[int, dict[str, list]] = {}
    for s in surfaces:
        tex_src = by_id[s.share] if s.share else s
        nu, nv = tessellation(s)
        S, T = np.meshgrid(np.linspace(0, 1, nu + 1), np.linspace(0, 1, nv + 1))
        P, _ = surface_points(s, S, T)
        uv = atlas.uv(tex_src.page, tex_src.rect, S, T)
        idx = []
        for j in range(nv):
            for i in range(nu):
                a = j * (nu + 1) + i
                b, c, d = a + 1, a + nu + 1, a + nu + 2
                idx += [a, b, d, a, d, c]
        bucket = per_page.setdefault(tex_src.page, {"pos": [], "uv": [], "idx": [], "n": 0})
        base = bucket["n"]
        bucket["pos"].append(P.reshape(-1, 3).astype(np.float32))
        bucket["uv"].append(uv.reshape(-1, 2))
        bucket["idx"].append(np.array(idx, np.uint32) + base)
        bucket["n"] += P.shape[0] * P.shape[1]
    return {
        pi: {
            "position": np.concatenate(b["pos"]),
            "uv": np.concatenate(b["uv"]),
            "index": np.concatenate(b["idx"]),
        }
        for pi, b in per_page.items()
    }
