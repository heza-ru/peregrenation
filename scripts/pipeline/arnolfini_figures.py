"""Figures, props and wall reliefs of the Arnolfini room as closed solids.

Every object is its silhouette (SAM + full-resolution refinement) inflated along the painter's
rays with a circular cross-section, so limbs are round and bodies have depth:

- standing / lying objects bend onto their support (floor, chest top, sill) where the
  silhouette drops below it: the bride's train lies on the boards, the pattens lie flat;
- hanging objects (chandelier, the bed curtain's bag) keep one plane;
- reliefs (mirror, rosary, brush) rise from the back wall and are sealed against it.

Front and back shells share their rim vertices, and the inflation reaches zero exactly on
the side outline (the alpha = 0.5 contour with tuft notches closed), so a shell edge never
shows a gap or a groove. UVs are the vertices' own projection into the panel, so the
painter's view is reproduced pixel for pixel: there the painted alpha cuts the notches.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np
from scipy import ndimage

from arnolfini_common import BACK_Z, CAM, EYE, H, W, back_project, floor_depth, load_mask, load_mask_hd, project
from synth import complete

PAD = 160  # canvas margin beyond the panel (1920 px) for bodies the frame cuts
TEX_SCALE_MAX = 2.0  # atlas px per 1920 px (the 3840 source's full resolution)


@dataclass
class Obj:
    id: str
    kind: str  # stand | lie | hang | relief
    r: float  # inflation radius (m)
    grid: int  # mesh spacing in 1920 px
    d: float | None = None  # plane depth; None = from the lowest silhouette row on the support
    support: float = 0.0  # support height (m) for stand / lie
    lie_t: float = 0.05  # thickness of parts lying on the support
    back_ratio: float = 0.9
    minus: tuple[str, ...] = ()  # masks of nearer objects to subtract
    amodal: tuple[str, ...] = ()  # nearer objects whose pixels this body continues behind
    plus: tuple[tuple[str, tuple[str, ...]], ...] = ()  # (mask, masks it loses to) added to the body
    close_box: tuple[int, int, int, int, int] | None = None  # local closing (x0, y0, x1, y1, px) that joins them
    # depth bends (x0, x1, y0, y1, offset at x0, offset at x1) added to d: an arm reaching across
    warp: tuple[tuple[float, float, float, float, float, float], ...] = ()
    face_fill: str = "dark"  # what covers the back of the head: dark hair / light veil
    holes: bool = False  # see-through filigree (plaster-coloured pixels inside the silhouette)
    relief_profile: str = "round"  # round | mirror
    back_face: str | None = None  # face mask: hair / veil on the back shell
    back_hide: tuple[str, ...] = ()  # skin masks the body hides from behind: garment on the back shell
    back_tone: float = 0.82
    # closing (m) of the silhouette the body is inflated from: notches between painted tufts
    # (fur, hair) are cut by alpha from the painter's eye but must not groove the solid
    side_close: float = 0.015
    # filled
    alpha: np.ndarray | None = None  # soft alpha on the padded canvas (1920 px + PAD)
    hard: np.ndarray | None = None
    side: np.ndarray | None = None  # hard silhouette closed by side_close: the solid's outline
    tex: np.ndarray | None = None
    rim_tex: np.ndarray | None = None  # the silhouette rim rebuilt from the body (seen from the side)
    back_tex: np.ndarray | None = None
    box: tuple[int, int, int, int] = (0, 0, 0, 0)  # x0, y0, x1, y1 in canvas px
    scale: float = TEX_SCALE_MAX
    stats: dict = field(default_factory=dict)


OBJECTS = [
    # his left hand (and her fingers' underside) belong to him; both forearms reach to ~2.1 m
    Obj(
        "giovanni", "stand", 0.23, 6, back_face="giovanni-face", back_hide=("giovanni-hand",),
        plus=(("hands", ("bride",)),), close_box=(930, 1030, 1210, 1185, 15),
        warp=((820.0, 1110.0, 960.0, 1190.0, 0.0, 0.12),),
    ),
    Obj(
        "bride", "stand", 0.27, 6, d=2.3, lie_t=0.045, amodal=("dog",), face_fill="light",
        back_face="bride-face", back_hide=("bride-hand",), plus=(("bride-sleeve", ()),),
        close_box=(1120, 1020, 1230, 1120, 11),
        warp=((990.0, 1330.0, 950.0, 1190.0, -0.2, 0.0),),
    ),
    Obj("dog", "stand", 0.11, 4),
    Obj("chandelier", "hang", 0.07, 3, d=3.0, holes=True, back_tone=0.9, side_close=0.0),
    Obj("curtain-bag", "hang", 0.1, 4, d=3.2),
    Obj("clogs", "lie", 0.04, 2, lie_t=0.04),
    Obj("slippers", "stand", 0.035, 2, lie_t=0.03),
    Obj("oranges-chest", "stand", 0.045, 2, support=0.63, minus=("giovanni",)),
    # on the sill just inside the window reveal
    Obj("orange-sill", "stand", 0.04, 2, d=3.7, support=0.945),
    Obj("mirror", "relief", 0.035, 2, relief_profile="mirror"),
    Obj("rosary", "relief", 0.012, 2),
    Obj("brush", "relief", 0.028, 2),
]

MIRROR = {"cx": 967.0, "cy": 788.0, "glass_px": 90.0, "frame_h": 0.03, "bulge": 0.045}
WALL_EPS = 0.0015


def canvas(a: np.ndarray, fill=0) -> np.ndarray:
    return cv2.copyMakeBorder(a, PAD, PAD, PAD, PAD, cv2.BORDER_CONSTANT, value=fill)


def extend_beyond_frame(alpha: np.ndarray, taper_px: int = PAD - 10) -> np.ndarray:
    """Bodies cut by the panel's side / bottom edge continue beyond it, each cut run closing
    with a rounded 45-degree taper instead of ending in a flat wall."""
    out = alpha.copy()
    x0, x1, y1 = PAD, PAD + W, PAD + H
    for side in ("left", "right", "bottom"):
        if side == "left":
            edge = out[:, x0] > 0.5
        elif side == "right":
            edge = out[:, x1 - 1] > 0.5
        else:
            edge = out[y1 - 1, :] > 0.5
        if not edge.any():
            continue
        line = edge.astype(np.uint8)[:, None]
        for k in range(1, taper_px + 1):
            run = cv2.erode(line, np.ones((2 * k + 1, 1), np.uint8)).ravel().astype(np.float32)
            if not run.any():
                break
            if side == "left":
                out[:, x0 - k] = np.maximum(out[:, x0 - k], run)
            elif side == "right":
                out[:, x1 - 1 + k] = np.maximum(out[:, x1 - 1 + k], run)
            else:
                out[y1 - 1 + k, :] = np.maximum(out[y1 - 1 + k, :], run)
    return out


def own_alpha(o: Obj, get, px_scale: float, box_origin: tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
    """The object's own painted silhouette: its mask, plus borrowed masks, minus nearer ones,
    with the local closing that joins borrowed parts (cuffs) - at any resolution.
    get(name) -> soft alpha; px_scale = array px per 1920 px; box_origin = 1920-px origin of the array."""
    a = get(o.id).copy()
    for name, loses_to in o.plus:
        add = get(name)
        for m in loses_to:
            add = add * (1 - get(m))
        a = np.maximum(a, add)
    for m in o.minus:
        a = a * (1 - get(m))
    if o.close_box:
        x0, y0, x1, y1, k = o.close_box
        ox, oy = box_origin
        c0, r0 = int(max(0, (x0 - ox) * px_scale)), int(max(0, (y0 - oy) * px_scale))
        c1, r1 = int(min(a.shape[1], (x1 - ox) * px_scale)), int(min(a.shape[0], (y1 - oy) * px_scale))
        if c1 > c0 and r1 > r0:
            kk = max(3, int(k * px_scale) | 1)
            sub = (a[r0:r1, c0:c1] > 0.5).astype(np.uint8)
            closed = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kk, kk)))
            a[r0:r1, c0:c1] = np.maximum(a[r0:r1, c0:c1], closed.astype(np.float32))
    return a


def load_alpha(o: Obj) -> np.ndarray:
    a = own_alpha(o, lambda n: load_mask(n, soft=True), 1.0)
    if o.amodal:
        hard = a > 0.5
        near = cv2.dilate(hard.astype(np.uint8), np.ones((61, 61), np.uint8)) > 0
        for m in o.amodal:
            other = load_mask(m, soft=True) > 0.5
            behind = other & near
            closed = cv2.morphologyEx((hard | behind).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8)) > 0
            fill = closed & behind
            a = np.maximum(a, fill.astype(np.float32))
            o.stats[f"amodal_{m}"] = int(fill.sum())
    a = canvas(a)
    if o.kind in ("stand", "lie"):
        a = extend_beyond_frame(a)
    return a


def plane_depth(o: Obj, hard: np.ndarray) -> float:
    if o.d is not None:
        return o.d
    ys, xs = np.nonzero(hard[PAD : PAD + H, PAD : PAD + W])
    if o.kind == "lie":
        ytop = ys.min()
        return float((CAM["eyeY"] - o.support) * CAM["f"] / max(ytop - CAM["cy"], 1.0))
    ybot = ys.max()
    return float((CAM["eyeY"] - o.support) * CAM["f"] / max(ybot - CAM["cy"], 1.0))


def inflation(hard_crop: np.ndarray, k_m_per_px: float, r: float) -> np.ndarray:
    """Circular-profile height (m) from the distance to the silhouette; exactly 0 on the contour."""
    dist = cv2.distanceTransform(hard_crop.astype(np.uint8), cv2.DIST_L2, 5)
    x = np.clip((dist - 0.5) * k_m_per_px, 0, r)
    h = np.sqrt(np.maximum(0.0, 2 * r * x - x * x))
    return cv2.GaussianBlur(h, (0, 0), 1.0) * (dist > 0.5)


def build_texture(o: Obj, src) -> None:
    """Front texture: the panel at up to full source resolution inside the object's box."""
    ys, xs = np.nonzero(o.alpha > 0.02)
    pad = o.grid * 2 + 4
    x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
    x1, y1 = min(o.alpha.shape[1], xs.max() + pad + 1), min(o.alpha.shape[0], ys.max() + pad + 1)
    bw, bh = x1 - x0, y1 - y0
    o.scale = min(TEX_SCALE_MAX, 4080 / bh, 4080 / bw)
    tw, th = int(round(bw * o.scale)), int(round(bh * o.scale))
    # texel centres -> panel px (canvas px minus PAD); beyond the panel: mirrored
    gx = x0 + (np.arange(tw) + 0.5) / o.scale - PAD
    gy = y0 + (np.arange(th) + 0.5) / o.scale - PAD
    GX, GY = np.meshgrid(gx, gy)
    GX = np.where(GX < 0, -GX, np.where(GX > W - 1, 2 * (W - 1) - GX, GX))
    GY = np.where(GY < 0, -GY, np.where(GY > H - 1, 2 * (H - 1) - GY, GY))
    rgb = src.sample(GX.astype(np.float32), GY.astype(np.float32), o.scale).astype(np.float32)
    cx_ = x0 + (np.arange(tw) + 0.5) / o.scale
    cy_ = y0 + (np.arange(th) + 0.5) / o.scale
    inside = ((cx_ >= PAD) & (cx_ < PAD + W))[None, :] & ((cy_ >= PAD) & (cy_ < PAD + H))[:, None]

    def hd_alpha(name: str) -> np.ndarray:
        hd = load_mask_hd(name)
        s_hd = hd.shape[1] / W
        mx = ((GX + 0.5) * s_hd - 0.5).astype(np.float32)
        my = ((GY + 0.5) * s_hd - 0.5).astype(np.float32)
        return cv2.remap(hd, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    # inside the panel the silhouette edge comes from the full-resolution masks
    cache: dict[str, np.ndarray] = {}

    def get(name: str) -> np.ndarray:
        if name not in cache:
            cache[name] = hd_alpha(name)
        return cache[name]

    own = own_alpha(o, get, o.scale, (x0 - PAD, y0 - PAD))
    coarse = cv2.resize(o.alpha[y0:y1, x0:x1], (tw, th), interpolation=cv2.INTER_LINEAR)
    a_panel = np.maximum(own, np.where(own > 0.5, 0, coarse)) if o.amodal else own
    a = np.where(inside, a_panel, coarse)
    # texels showing the object's own paint; the rest (behind a nearer body, beyond the frame)
    # is rebuilt from its own fabric
    paint_ok = inside & (own > 0.5)
    for m in o.amodal:
        paint_ok &= get(m) < 0.5
    if o.holes:
        lab = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)
        soft = cv2.GaussianBlur(lab, (0, 0), 1.2)
        plaster = (np.abs(soft[..., 1] - 128) < 6) & (soft[..., 2] - 128 < 13) & (soft[..., 0] > 70) & (soft[..., 0] < 175)
        plaster = cv2.morphologyEx(plaster.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        n, lbl, st, _ = cv2.connectedComponentsWithStats(plaster)
        holes = np.zeros_like(plaster)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] > 30 * o.scale * o.scale:
                holes[lbl == i] = 1
        hs = cv2.GaussianBlur(holes.astype(np.float32), (0, 0), 0.8)
        a = a * (1 - hs)
        o.stats["hole_px"] = int(holes.sum())
    need = (a > 0.02) & ~paint_ok
    if need.any():
        texel_m = 0.001
        rgb = complete(rgb, paint_ok & (a > 0.5), texel_m, patch_m=0.05, target=need, tone_sigma_m=0.03)
    alpha8 = np.clip(a * 255, 0, 255).astype(np.uint8)
    o.tex = np.dstack([bleed(np.clip(rgb, 0, 255).astype(np.uint8), a > 0.5), alpha8])
    o.box = (x0, y0, x1, y1)
    o.stats["tex"] = (tw, th)
    a_side = a
    if o.kind != "relief" and not o.holes:
        # beyond the outline the mesh ends on it (snap_rim): the margin only keeps filtering clean
        g = 2 * (o.grid + 2) + 1
        cover = cv2.dilate(o.side[y0:y1, x0:x1].astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (g, g)))
        a_side = np.maximum(a, cv2.resize(cover.astype(np.float32), (tw, th), interpolation=cv2.INTER_LINEAR))
    side8 = np.clip(a_side * 255, 0, 255).astype(np.uint8)
    o.rim_tex = np.dstack([bleed(np.clip(rim_rebuilt(o, rgb, a, a_side), 0, 255).astype(np.uint8), a_side > 0.5), side8])
    parts = {n: get(n) > 0.5 for n in ((o.back_face,) if o.back_face else ()) + o.back_hide}
    o.back_tex = back_texture(o, parts)


RIM_M = 0.004  # silhouette band whose paint blends with what lies behind the body


def rim_rebuilt(o: Obj, rgb: np.ndarray, a: np.ndarray, a_side: np.ndarray) -> np.ndarray:
    """The texture with its outermost band - and all the mesh covers beyond the painted edge -
    rebuilt from the body's own cloth. From the painter's eye that band is a pixel wide, and there it is
    the painted edge; seen from the side the inflated rim turns towards the camera and would
    stretch the edge's blend with the background (dark tuft tips, the wall between them) across
    the body's flank."""
    if o.kind == "relief":
        return rgb
    texel_m = o.stats["d"] / (CAM["f"] * o.scale)
    solid = a > 0.5
    inset = cv2.distanceTransform(solid.astype(np.uint8), cv2.DIST_L2, 5) * texel_m
    rim = (a_side > 0.02) & ((inset < RIM_M) | ~solid)
    body = solid & ~rim
    if not rim.any() or not body.any():
        return rgb
    out = complete(rgb, body, 0.001, patch_m=0.03, target=rim, tone_sigma_m=0.012)
    o.stats["rim_px"] = int(rim.sum())
    return out


def _fill_local(rgb: np.ndarray, valid: np.ndarray, target: np.ndarray, grow: int, **kw) -> np.ndarray:
    """complete() inside the target's grown bounding box, so each fill quilts from the cloth around it."""
    ys, xs = np.nonzero(target)
    y0, y1 = max(0, ys.min() - grow), min(rgb.shape[0], ys.max() + grow + 1)
    x0, x1 = max(0, xs.min() - grow), min(rgb.shape[1], xs.max() + grow + 1)
    if kw.get("tone") is not None:
        kw["tone"] = kw["tone"][y0:y1, x0:x1]
    sub = complete(rgb[y0:y1, x0:x1], valid[y0:y1, x0:x1], 0.001, target=target[y0:y1, x0:x1], **kw)
    out = rgb.copy()
    t = target[y0:y1, x0:x1]
    out[y0:y1, x0:x1][t] = sub[t]
    return out


def column_tone(img: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Light for a hole in hanging cloth: each column interpolated between the painted cloth just
    above and just below it, so vertical folds carry on through the hole."""
    w = valid.astype(np.float32)
    low = cv2.GaussianBlur(img * w[..., None], (0, 0), sigma) / np.maximum(cv2.GaussianBlur(w, (0, 0), sigma), 1e-6)[..., None]
    h = valid.shape[0]
    rows = np.arange(h)[:, None].repeat(valid.shape[1], 1)
    above = np.maximum.accumulate(np.where(valid, rows, -1), axis=0)
    below = np.flipud(np.minimum.accumulate(np.flipud(np.where(valid, rows, h)), axis=0))
    has_a, has_b = above >= 0, below < h
    ia, ib = np.clip(above, 0, h - 1), np.clip(below, 0, h - 1)
    cols = np.arange(valid.shape[1])[None, :].repeat(h, 0)
    ca, cb = low[ia, cols], low[ib, cols]
    t = np.where(has_a & has_b, (rows - above) / np.maximum(below - above, 1), np.where(has_a, 0.0, 1.0))[..., None]
    out = ca * (1 - t) + cb * t
    return cv2.GaussianBlur(out.astype(np.float32), (0, 0), sigmaX=max(1.0, sigma / 4), sigmaY=max(1.0, sigma / 2))


def back_texture(o: Obj, parts: dict[str, np.ndarray]) -> np.ndarray:
    """The unseen side: the same cloth at full resolution, in shade. Skin the body hides from
    behind (a hand laid on the chest or belly) becomes the garment under it; the face becomes
    hair / veil lit continuously with the rest of the head. Hands reaching out of the
    silhouette (the joined hands) stay skin: they are seen from behind too."""
    rgb = o.rim_tex[..., :3].astype(np.float32)
    a = o.tex[..., 3].astype(np.float32) / 255
    solid = a > 0.5
    texel_m = o.stats["d"] / (CAM["f"] * o.scale) if "d" in o.stats else 0.001
    shade = back_shade(o, o.rim_tex[..., 3] > 127, texel_m)
    if not parts:
        return np.dstack([np.clip(rgb * shade, 0, 255).astype(np.uint8), o.tex[..., 3]])
    grow_px = int(0.006 / texel_m) | 1
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (grow_px, grow_px))

    def grown(m: np.ndarray) -> np.ndarray:
        return (cv2.dilate(m.astype(np.uint8), ker) > 0) & (a > 0.02)

    def disk(m: float) -> np.ndarray:
        return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(m / texel_m) | 1,) * 2)

    def lab_of(img: np.ndarray) -> np.ndarray:
        return cv2.cvtColor(np.clip(img, 0, 255).astype(np.uint8), cv2.COLOR_BGR2LAB).astype(np.float32)

    face = grown(parts[o.back_face]) if o.back_face else np.zeros(solid.shape, bool)
    hidden = np.zeros(solid.shape, bool)
    for n in o.back_hide:
        # the hand's own contact shadow on the cloth goes with it
        hidden |= (cv2.dilate(parts[n].astype(np.uint8), disk(0.012)) > 0) & (a > 0.02)
    cloth = solid & ~face & ~hidden
    if hidden.any():
        # quilt only from the garment the hand lies on (not the sleeve it comes out of)
        lab = lab_of(rgb)
        n, lbl = cv2.connectedComponents(hidden.astype(np.uint8))
        for i in range(1, n):
            part = lbl == i
            ring = (cv2.dilate(part.astype(np.uint8), disk(0.05)) > 0) & cloth
            ab = lab[ring][:, 1:].astype(np.float32)
            crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
            _, lab_k, centres = cv2.kmeans(ab, 3, None, crit, 3, cv2.KMEANS_PP_CENTERS)
            main = centres[np.argmax(np.bincount(lab_k.ravel(), minlength=3))]
            same = cloth & (np.linalg.norm(lab[..., 1:] - main, axis=-1) < 12)
            tone = column_tone(rgb, same, 0.004 / texel_m)
            detail = rgb - cv2.GaussianBlur(rgb, (0, 0), 0.004 / texel_m)
            rgb = _fill_local(rgb, same, part, int(0.14 / texel_m), patch_m=0.05, tone=tone, donor=(detail, same))
        o.stats["hidden_skin_px"] = int(hidden.sum())
    if face.any():
        # what covers the back of the head: his dark hair (from the hat) / her white veil
        lab = lab_of(rgb)
        head = (cv2.dilate(face.astype(np.uint8), disk(0.2)) > 0) & cloth
        if o.face_fill == "dark":
            cover = head & (lab[..., 0] < 70)
        else:
            # plain linen only: the lace borders' pattern would tile into a lattice
            L = lab[..., 0]
            mu = cv2.GaussianBlur(L, (0, 0), 0.004 / texel_m)
            sd = np.sqrt(np.maximum(cv2.GaussianBlur(L * L, (0, 0), 0.004 / texel_m) - mu * mu, 0))
            cover = head & (L > 140) & (np.abs(lab[..., 1] - 128) < 10) & (np.abs(lab[..., 2] - 128) < 18) & (sd < 14)
        cover = cv2.erode(cover.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        # light: the cover's own light pulled across the face (no flat fill, no face-shaped edge)
        tone = cv2.GaussianBlur(rgb * cover[..., None], (0, 0), 0.03 / texel_m)
        wgt = cv2.GaussianBlur(cover.astype(np.float32), (0, 0), 0.03 / texel_m)[..., None]
        med = np.median(rgb[cover], axis=0)
        tone = np.where(wgt > 0.05, tone / np.maximum(wgt, 1e-6), med).astype(np.float32)
        detail = rgb - cv2.GaussianBlur(rgb, (0, 0), 0.006 / texel_m)
        rgb = _fill_local(rgb, np.zeros_like(face), face, int(0.2 / texel_m), patch_m=0.08, tone=tone, donor=(detail, cover), tone_sigma_m=0.012)
        o.stats["face_px"] = int(face.sum())
    return np.dstack([np.clip(rgb * shade, 0, 255).astype(np.uint8), o.tex[..., 3]])


def back_shade(o: Obj, solid: np.ndarray, texel_m: float) -> np.ndarray:
    """The back is in shade, but it meets the front at the rim: full light there, easing to
    back_tone a few centimetres in, so the two shells join without a step."""
    inset = cv2.distanceTransform(solid.astype(np.uint8), cv2.DIST_L2, 5) * texel_m
    k = np.clip(inset / 0.03, 0, 1)
    k = k * k * (3 - 2 * k)
    return (1 - (1 - o.back_tone) * k)[..., None].astype(np.float32)


def bleed(rgb: np.ndarray, inside: np.ndarray, iters: int = 12) -> np.ndarray:
    """Carry colours past the cut edge so filtering at the silhouette never picks up black."""
    out = rgb.astype(np.float32)
    m = inside.astype(np.float32)
    for _ in range(iters):
        acc = cv2.blur(out * m[..., None], (5, 5))
        wgt = cv2.blur(m, (5, 5))
        grow = (m == 0) & (wgt > 1e-3)
        out[grow] = acc[grow] / wgt[grow][:, None]
        m = np.where(grow, 1.0, m)
    return np.clip(out, 0, 255).astype(np.uint8)


def snap_rim(hard: np.ndarray, lx: np.ndarray, ly: np.ndarray, idx: np.ndarray, G: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Grid vertices outside the outline moved onto it. The inflation rises steeply just inside
    the contour, so a cell spanning it (zero outside, centimetres inside) would put the front and
    back cuts on opposite sides of the equator with a slot between them; on the contour both
    shells meet at zero height. A move that would fold a triangle is undone."""
    lxf, lyf = lx.astype(np.float64), ly.astype(np.float64)
    out = ~hard[ly, lx]
    _, (iy, ix) = ndimage.distance_transform_edt(~hard, return_indices=True)
    ty, tx = iy[ly, lx].astype(np.float64), ix[ly, lx].astype(np.float64)
    dy, dx = lyf - ty, lxf - tx
    dn = np.hypot(dx, dy)
    move = out & (dn > 0) & (dn <= 1.5 * G)
    # the alpha = 0.5 edge lies half a pixel out from the nearest inside pixel's centre
    nx = np.where(move, tx + 0.5 * dx / np.maximum(dn, 1e-9), lxf)
    ny = np.where(move, ty + 0.5 * dy / np.maximum(dn, 1e-9), lyf)
    tri = idx.reshape(-1, 3)

    def area(x: np.ndarray, y: np.ndarray) -> np.ndarray:
        a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
        return (x[b] - x[a]) * (y[c] - y[a]) - (x[c] - x[a]) * (y[b] - y[a])

    ref = np.sign(area(lxf, lyf))
    for _ in range(8):
        bad = np.sign(area(nx, ny)) * ref < 0
        if not bad.any():
            break
        undo = np.zeros(len(lxf), bool)
        undo[tri[bad].ravel()] = True
        undo &= move
        if not undo.any():
            break
        move &= ~undo
        nx = np.where(move, nx, lxf)
        ny = np.where(move, ny, lyf)
    return nx, ny, move


def build_mesh(o: Obj) -> dict[str, np.ndarray]:
    """Front / back shells (sharing rim vertices) or a single relief shell sealed on the wall."""
    x0, y0, x1, y1 = o.box
    hard = o.side[y0:y1, x0:x1]
    G = o.grid
    bh, bw = hard.shape
    nx, ny = (bw - 1) // G, (bh - 1) // G
    cover = cv2.dilate(hard.astype(np.uint8), np.ones((3, 3), np.uint8))
    cells = np.zeros((ny, nx), bool)
    csum = cv2.integral(cover)
    for j in range(ny):
        a0, a1 = j * G, (j + 1) * G + 1
        for i in range(nx):
            b0, b1 = i * G, (i + 1) * G + 1
            cells[j, i] = (csum[a1, b1] - csum[a0, b1] - csum[a1, b0] + csum[a0, b0]) > 0
    used = np.zeros((ny + 1, nx + 1), bool)
    used[:-1, :-1] |= cells
    used[1:, :-1] |= cells
    used[:-1, 1:] |= cells
    used[1:, 1:] |= cells
    vid = -np.ones((ny + 1, nx + 1), np.int64)
    vid[used] = np.arange(int(used.sum()))
    jj, ii = np.nonzero(used)
    lx, ly = ii * G, jj * G
    px = x0 + lx - PAD + 0.0
    py = y0 + ly - PAD + 0.0
    ci = np.argwhere(cells)
    a = vid[ci[:, 0], ci[:, 1]]
    b = vid[ci[:, 0], ci[:, 1] + 1]
    c = vid[ci[:, 0] + 1, ci[:, 1]]
    dd = vid[ci[:, 0] + 1, ci[:, 1] + 1]
    f_idx = np.stack([a, c, dd, a, dd, b], -1).reshape(-1)
    b_idx = np.stack([a, dd, c, a, b, dd], -1).reshape(-1)
    s = (lx + 0.0) / bw
    t = 1 - (ly + 0.0) / bh

    if o.kind == "relief":
        d_wall = CAM["eyeZ"] - BACK_Z
        k = d_wall / CAM["f"]
        h = inflation(hard, k, o.r)
        if o.relief_profile == "mirror":
            # flat frame of constant height with a rounded outer edge; convex glass in the middle
            dist = cv2.distanceTransform(hard.astype(np.uint8), cv2.DIST_L2, 5) * k
            frame = MIRROR["frame_h"] * np.sqrt(np.clip(dist / 0.008, 0, 1))
            gx = (np.arange(bw)[None] + x0 - PAD - MIRROR["cx"])
            gy = (np.arange(bh)[:, None] + y0 - PAD - MIRROR["cy"])
            rho = np.hypot(gx, gy) / MIRROR["glass_px"]
            glass = MIRROR["frame_h"] * 0.7 + MIRROR["bulge"] * np.sqrt(np.clip(1 - rho**2, 0, 1))
            h = np.where(rho < 1, np.maximum(frame, glass), frame) * (dist > 0)
        hv = h[ly, lx]
        X, Y, Z = back_project(px, py, d_wall)
        P0 = np.stack([X, Y, np.full_like(X, BACK_Z)], -1)
        # rise off the wall along the painter's ray (the texel stays on its pixel); per metre of
        # ray the wall distance shrinks by |ray.z|, so scale to get h off the wall
        toward = EYE - P0
        toward = toward / np.linalg.norm(toward, axis=1, keepdims=True)
        front = P0 + toward * ((hv + WALL_EPS) / np.abs(toward[:, 2]))[:, None]
        return {"front": front, "back": None, "s": s, "t": t, "fidx": f_idx, "bidx": None}

    d = o.stats["d"]
    k = d / CAM["f"]
    h = inflation(hard, k, o.r)
    hv = h[ly, lx]
    lxf, lyf, on_rim = snap_rim(hard, lx, ly, f_idx, G)
    hv = np.where(on_rim, 0.0, hv)
    px = x0 + lxf - PAD
    py = y0 + lyf - PAD
    s = lxf / bw
    t = 1 - lyf / bh
    dv = np.full(px.shape, d)
    for wx0, wx1, wy0, wy1, off0, off1 in o.warp:
        u = np.clip((px - wx0) / (wx1 - wx0), 0, 1)
        # full inside the band, easing out over 40 px above / below it
        fy = np.clip(1 - np.maximum(wy0 - py, py - wy1) / 40.0, 0, 1)
        fy = fy * fy * (3 - 2 * fy)
        dv += (off0 + (off1 - off0) * u) * fy
    X, Y, Z = back_project(px, py, dv)
    P0 = np.stack([X, Y, Z], -1)
    toward = EYE - P0
    toward = toward / np.linalg.norm(toward, axis=1, keepdims=True)
    if o.kind in ("stand", "lie"):
        below = P0[:, 1] < o.support
        if below.any():
            # the painter's ray through these pixels meets the support before the plane
            dsup = (CAM["eyeY"] - o.support) * CAM["f"] / np.maximum(py[below] - CAM["cy"], 0.5)
            Xs, _, Zs = back_project(px[below], py[below], dsup)
            P0[below] = np.stack([Xs, np.full_like(Xs, o.support), Zs], -1)
            t_b = EYE - P0[below]
            toward[below] = t_b / np.linalg.norm(t_b, axis=1, keepdims=True)
        # 1 at a quarter metre above the support, 0 on it: bodies thin out into what lies flat
        w = np.clip((P0[:, 1] - o.support) / 0.25, 0, 1)
        if o.kind == "lie":
            w[:] = 0
        # every offset runs along the painter's ray, so each vertex keeps its painted pixel;
        # lying parts rise by at most lie_t (ray length = height / sin(elevation))
        rise = np.maximum(toward[:, 1], 0.08)
        h_eff = w * hv + (1 - w) * np.minimum(hv, o.lie_t) / rise
        front = P0 + toward * h_eff[:, None]
        back = P0 - toward * (o.back_ratio * hv * w)[:, None]
        back[:, 1] = np.maximum(back[:, 1], o.support + 0.001)
    else:
        front = P0 + toward * hv[:, None]
        back = P0 - toward * (o.back_ratio * hv)[:, None]
    return {"front": front, "back": back, "s": s, "t": t, "fidx": f_idx, "bidx": b_idx}


def collider(o: Obj) -> dict | None:
    """Standing footprint in room metres (XZ) from the lower body."""
    if o.kind != "stand" or o.id.startswith("orange"):
        return None
    x0, y0, x1, y1 = o.box
    hard = o.alpha > 0.5
    ys, xs = np.nonzero(hard[: PAD + H, PAD : PAD + W])
    ys = ys - PAD
    low = ys >= ys.min() + 0.55 * (ys.max() - ys.min())
    d = o.stats["d"]
    a, b = xs[low].min(), xs[low].max()
    cx, half = (a + b) / 2, (b - a) / 2 * 0.72
    k = d / CAM["f"]
    zc = CAM["eyeZ"] - d
    return {
        "minX": round((cx - half - CAM["cx"]) * k, 3),
        "maxX": round((cx + half - CAM["cx"]) * k, 3),
        "minZ": round(zc - o.back_ratio * o.r * 1.1, 3),
        "maxZ": round(zc + o.r * 0.8, 3),
    }


def build_all(src) -> list[Obj]:
    out = []
    for o in OBJECTS:
        o.alpha = load_alpha(o)
        o.hard = o.alpha > 0.5
        o.side = o.hard
        if o.kind != "relief":
            o.stats["d"] = plane_depth(o, o.hard)
            if o.side_close > 0:
                kk = int(round(o.side_close * CAM["f"] / o.stats["d"])) | 1
                ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kk, kk))
                o.side = o.hard | (cv2.morphologyEx(o.hard.astype(np.uint8), cv2.MORPH_CLOSE, ker) > 0)
        build_texture(o, src)
        print(f"  object {o.id:<14} {o.kind:<6} tex={o.stats['tex']} d={o.stats.get('d', '-')} {o.stats}")
        out.append(o)
    return out


def center_of(o: Obj) -> list[float]:
    ys, xs = np.nonzero(o.hard)
    px, py = xs.mean() - PAD, ys.mean() - PAD
    d = o.stats.get("d", CAM["eyeZ"] - BACK_Z - 0.05)
    return [round(float(v), 3) for v in back_project(px, py, d)]


def export(objs: list[Obj], atlas) -> dict[int, dict]:
    """Pack front textures (atlas) and assemble per-page geometry; back pages mirror the layout."""
    placed = []
    for o in sorted(objs, key=lambda o: -o.tex.shape[0]):
        pi, rect = atlas.add(o.tex)
        placed.append((o, pi, rect))
    atlas.finish()
    backs = [np.zeros_like(p) for p in atlas.final]
    rims = [np.zeros_like(p) for p in atlas.final]
    per_page: dict[int, dict[str, list]] = {}
    for o, pi, rect in placed:
        x, y, w, h = rect
        P = atlas.PAD
        for pages, tex in ((backs, o.back_tex), (rims, o.rim_tex)):
            padded = cv2.copyMakeBorder(tex, P, P, P, P, cv2.BORDER_REPLICATE)
            pages[pi][y - P : y + h + P, x - P : x + w + P] = padded[: h + 2 * P, : w + 2 * P]
        m = build_mesh(o)
        # vertices sit on their pixel's ray, so the grid position is the panel position
        uv_front = atlas.uv(pi, rect, m["s"], m["t"])
        uv_back = uv_front
        kind = "relief" if o.kind == "relief" else "solid"
        b = per_page.setdefault((pi, kind), {"fpos": [], "bpos": [], "fuv": [], "buv": [], "fidx": [], "bidx": [], "n": 0})
        base = b["n"]
        b["fpos"].append(m["front"].astype(np.float32))
        b["fuv"].append(uv_front)
        b["fidx"].append((m["fidx"] + base).astype(np.uint32))
        if m["back"] is not None:
            b["bpos"].append(m["back"].astype(np.float32))
            b["buv"].append(uv_back)
            b["bidx"].append((m["bidx"] + base).astype(np.uint32))
        b["n"] += len(m["front"])
        o.stats["verts"] = len(m["front"])
    out = {}
    for (pi, kind), b in per_page.items():
        entry = {"front": {"position": np.concatenate(b["fpos"]), "uv": np.concatenate(b["fuv"]), "index": np.concatenate(b["fidx"])}}
        if b["bpos"]:
            entry["back"] = {"position": np.concatenate(b["bpos"]), "uv": np.concatenate(b["buv"]), "index": np.concatenate(b["bidx"])}
        out[(pi, kind)] = entry
    atlas.backs = backs
    atlas.rims = rims
    return out
