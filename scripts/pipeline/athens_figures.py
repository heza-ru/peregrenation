"""School of Athens figures as inflated, rounded 3D bodies.

Each silhouette is inflated with a circular cross-section profile (arms become round
limbs, torsos cap at a body-like depth), so figures read as volumes from every side
instead of extruded slabs. Front and back shells meet exactly on the silhouette; the
front carries the full-resolution fresco, the back a softened, shaded version of it.
"""

from __future__ import annotations

import cv2
import numpy as np

from athens_common import CAM, DATA, EYE, H, W, Atlas, Source, back_project, floor_y, raymarch, scene_mask

MIN_PLANE_D = 8.22
# Figure canvases extend below the fresco so bodies cut by its lower edge can reach the floor
HE = H + 420
BODY_R = 0.2
STATUE_R = 0.24
BACK_RATIO = 0.9
GRID = 5  # px (1920 space) between mesh vertices
TEX_SCALE = 4.0  # atlas px per 1920-space px

NAMED = [
    "plato",
    "aristotle",
    "socrates",
    "pythagoras",
    "averroes",
    "hypatia",
    "epicurus",
    "heraclitus",
    "diogenes",
    "ptolemy",
    "raphael-self",
]
STATUES = {
    # niche rects (x0, y0, x1, y1); statues stand proud of the pier face
    "apollo-statue": (405, 320, 575, 665),
    "athena-statue": (1455, 350, 1620, 700),
}
PIER_FACE_Z = -3.3


def load_mask(name: str) -> np.ndarray:
    m = cv2.imread(str(DATA / "masks" / f"entity-{name}.png"), cv2.IMREAD_GRAYSCALE)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_NEAREST)
    return m > 127


def clean(mask: np.ndarray, open_k: int = 5, close_k: int = 9) -> np.ndarray:
    m = mask.astype(np.uint8) * 255
    m = cv2.GaussianBlur(m, (7, 7), 0)
    m = (m > 127).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((open_k, open_k), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((close_k, close_k), np.uint8))
    return m > 0


def largest_filled(mask: np.ndarray) -> np.ndarray:
    m = mask.astype(np.uint8) * 255
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(m)
    if cnts:
        c = max(cnts, key=cv2.contourArea)
        cv2.drawContours(out, [c], -1, 255, thickness=-1)
    return out > 0


def crowd_mask(img: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(int)
    L, A, B = lab[..., 0], lab[..., 1] - 128, lab[..., 2] - 128
    chroma = np.sqrt(A**2 + B**2)
    fig = (chroma > 20) | (L < 135)
    pave = (A > 6) & (B < 14) & (L > 130)
    sky = (B < -8) & (L > 150)
    fig &= ~pave
    roi = np.zeros_like(fig)
    roi[680:H, 262:1772] = True
    roi[1045:H, :405] = False  # marble pedestal and doorway at bottom left
    fig &= roi
    sky_zone = np.zeros_like(fig)
    sky_zone[:800, 880:1150] = True
    fig &= ~(sky & sky_zone)
    return clean(fig, 7, 11)


def statue_mask(img: np.ndarray, rect: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = rect
    gc = np.zeros(img.shape[:2], np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    inset = (x0 + 12, y0 + 8, x1 - x0 - 24, y1 - y0 - 16)
    cv2.grabCut(img, gc, inset, bgd, fgd, 6, cv2.GC_INIT_WITH_RECT)
    m = (gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)
    return largest_filled(clean(m, 5, 9))


def foot_distance(mask: np.ndarray) -> float:
    ys, xs = np.nonzero(mask)
    y1 = ys.max()
    foot_px = float(xs[ys >= y1 - 6].mean())
    return max(raymarch(foot_px, float(y1)), MIN_PLANE_D)


def metric_depth(depth: np.ndarray, kill: np.ndarray) -> np.ndarray:
    """Relative depth map -> metres from the painter's eye, calibrated on visible floor pixels."""
    scene = scene_mask()
    yy, xx = np.mgrid[0:H, 0:W]
    floor_px = scene & ~kill & ((yy > 990) | ((yy > 790) & (xx > 720) & (xx < 1310)))
    ys, xs = np.nonzero(floor_px)
    pick = np.random.default_rng(0).choice(len(ys), min(4000, len(ys)), replace=False)
    ds = np.array([raymarch(float(xs[i]), float(ys[i])) for i in pick])
    dv = depth[ys[pick], xs[pick]].astype(np.float64)
    A = np.stack([np.ones_like(dv), dv], 1)
    coef = np.zeros(2)
    for _ in range(3):
        coef, *_ = np.linalg.lstsq(A, 1 / ds, rcond=None)
        res = np.abs(1 / (A @ coef) - ds)
        keep = res < np.percentile(res, 80)
        A, ds = A[keep], ds[keep]
    d = 1.0 / np.maximum(coef[0] + coef[1] * depth.astype(np.float64), 1e-3)
    return np.clip(d, 7.9, 40.0).astype(np.float32)


def segment(img: np.ndarray, depth: np.ndarray):
    """Masks for named figures, statues and the anonymous crowd (1920 space)."""
    named: dict[str, np.ndarray] = {}
    union = np.zeros((H, W), bool)
    for fid in NAMED:
        m = largest_filled(clean(load_mask(fid), 3, 9))
        m &= ~union  # earlier (more important) figures win overlaps
        named[fid] = m
        union |= m
    statues = {sid: statue_mask(img, rect) for sid, rect in STATUES.items()}
    crowd = crowd_mask(img) & ~union
    # forecourt vs platform groups, so one group never spans both levels
    near_px = depth >= 145
    parts: list[np.ndarray] = []
    for sel in (near_px, ~near_px):
        n, lbl, stats, _ = cv2.connectedComponentsWithStats(clean(crowd & sel, 5, 7).astype(np.uint8))
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] >= 1200:
                parts.append(largest_filled(lbl == i))
    return named, statues, crowd, parts


class Figure:
    def __init__(self, fid: str, tier: str, mask: np.ndarray, d: float, radius: float, crowd: bool = False):
        self.id, self.tier, self.d, self.r, self.crowd = fid, tier, max(d, 7.9), radius, crowd
        self.mask = np.zeros((HE, W), bool)
        self.mask[:H] = mask
        self.ext = np.zeros((HE, W), bool)  # occluded/out-of-frame body continued down to the floor
        self._set_bounds()

    def _set_bounds(self) -> None:
        ys, xs = np.nonzero(self.mask)
        pad = GRID * 2
        self.x0 = max(0, int(xs.min()) - pad)
        self.y0 = max(0, int(ys.min()) - pad)
        self.x1 = min(W, int(xs.max()) + pad + 1)
        self.y1 = min(HE, int(ys.max()) + pad + 1)
        self._set_center()

    def ground(self) -> None:
        """Continue the body below its lowest visible edge until it stands on the floor.

        From the painter's eye the continuation is hidden (behind a nearer figure or below the
        fresco's frame); from anywhere else the figure is whole instead of floating or severed."""
        ys, xs = np.nonzero(self.mask)
        ybot = int(ys.max())
        zc = CAM["eyeZ"] - self.d
        y_floor = CAM["cy"] + (CAM["eyeY"] - floor_y(zc)) * CAM["f"] / self.d
        y_floor = int(min(HE - GRID * 3, round(y_floor)))
        if y_floor <= ybot + 2:
            return
        band = ys >= ybot - max(6, int(0.06 * (ybot - ys.min())))
        a, b = int(xs[band].min()), int(xs[band].max())
        width = b - a
        # a robe hem: a little narrower than the lowest visible span, slightly flaring at the floor
        for y in range(ybot - 2, y_floor + 1):
            k = (y - ybot) / max(1, y_floor - ybot)
            inset = int(width * (0.12 - 0.08 * k))
            self.ext[y, a + inset : b - inset + 1] = True
        self.ext &= ~self.mask
        self.mask |= self.ext
        self._set_bounds()

    def _set_center(self) -> None:
        ys, xs = np.nonzero(self.mask)
        self.center = [round(float(v), 3) for v in back_project(float(xs.mean()), float(ys.mean()), self.d)]

    def collider(self) -> dict:
        ys, xs = np.nonzero(self.mask)
        low = ys >= ys.min() + 0.7 * (ys.max() - ys.min())
        a, b = float(xs[low].min()), float(xs[low].max())
        cx, half = (a + b) / 2, (b - a) / 2 * 0.8
        k = self.d / CAM["f"]
        x0, x1 = (cx - half - CAM["cx"]) * k, (cx + half - CAM["cx"]) * k
        zc = CAM["eyeZ"] - self.d
        return {"minX": round(x0, 3), "maxX": round(x1, 3), "minZ": round(zc - BACK_RATIO * self.r, 3), "maxZ": round(zc + self.r, 3)}

    def texture(self, src: Source) -> np.ndarray:
        s, img = src.best(TEX_SCALE)
        sx, sy = img.shape[1] / W, img.shape[0] / H
        bw, bh = self.x1 - self.x0, self.y1 - self.y0
        tw, th = int(round(bw * TEX_SCALE)), int(round(bh * TEX_SCALE))
        yr = min(self.y1, H)  # painted rows; below the fresco only the continuation exists
        crop = img[int(self.y0 * sy) : int(yr * sy), int(self.x0 * sx) : int(self.x1 * sx)]
        th_real = int(round((yr - self.y0) * TEX_SCALE))
        real = cv2.resize(crop, (tw, th_real), interpolation=cv2.INTER_AREA if crop.shape[1] > tw else cv2.INTER_CUBIC)
        rgb = np.zeros((th, tw, 3), np.uint8)
        rgb[:th_real] = real
        if self.ext.any():
            rgb = self._continue_robe(rgb)
        m = self.mask[self.y0 : self.y1, self.x0 : self.x1].astype(np.float32)
        m = cv2.GaussianBlur(m, (0, 0), 0.8)
        a = cv2.resize(m, (tw, th), interpolation=cv2.INTER_CUBIC)
        a = np.clip((a - 0.5) * 3.0 + 0.5, 0, 1)
        rgb = bleed(rgb, a > 0.5)
        return np.dstack([rgb, (a * 255).astype(np.uint8)])

    def _continue_robe(self, rgb: np.ndarray) -> np.ndarray:
        """Paint the continuation with the colours of the lowest visible cloth, falling into shade."""
        th, tw = rgb.shape[:2]
        crop = (slice(self.y0, self.y1), slice(self.x0, self.x1))
        own = cv2.resize((self.mask & ~self.ext)[crop].astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST) > 0
        ext = cv2.resize(self.ext[crop].astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST) > 0
        cols = np.nonzero(ext.any(axis=0))[0]
        hem = np.full((tw, 3), np.nan, np.float32)
        span = int(6 * TEX_SCALE)
        for c in cols:
            rows = np.nonzero(own[:, c])[0]
            if len(rows) == 0:
                continue
            r = rows.max()
            sel = rows[rows >= r - span]
            hem[c] = np.median(rgb[sel, c].astype(np.float32), axis=0)
        known = ~np.isnan(hem[:, 0])
        if not known.any():
            return rgb
        idx = np.arange(tw)
        for ch in range(3):
            hem[:, ch] = np.interp(idx, idx[known], hem[known, ch])
        hem = cv2.GaussianBlur(hem[None], (0, 0), sigmaX=2.0 * TEX_SCALE)[0]
        top = np.argmax(ext, axis=0)
        bottom = th - 1 - np.argmax(ext[::-1], axis=0)
        yy = np.arange(th)[:, None]
        k = np.clip((yy - top[None]) / np.maximum(1, bottom - top)[None], 0, 1)
        shade = 0.9 - 0.4 * k**1.5
        fill = hem[None] * shade[..., None]
        out = rgb.copy()
        out[ext] = np.clip(fill[ext], 0, 255).astype(np.uint8)
        return out

    def mesh(self) -> dict[str, np.ndarray]:
        sub = self.mask[self.y0 : self.y1, self.x0 : self.x1]
        k = self.d / CAM["f"]
        dist = cv2.distanceTransform(sub.astype(np.uint8), cv2.DIST_L2, 5) * k
        x = np.clip(dist - 1.2 * k, 0, self.r)
        hmap = np.sqrt(np.maximum(0.0, 2 * self.r * x - x * x))
        hmap = cv2.GaussianBlur(hmap, (0, 0), 1.0)
        cover = cv2.dilate(sub.astype(np.uint8), np.ones((3, 3), np.uint8))
        bh, bw = sub.shape
        nx, ny = (bw - 1) // GRID, (bh - 1) // GRID
        # cells touching the (slightly dilated) silhouette
        cells = np.zeros((ny, nx), bool)
        for j in range(ny):
            rows = cover[j * GRID : (j + 1) * GRID + 1]
            for i in range(nx):
                cells[j, i] = rows[:, i * GRID : (i + 1) * GRID + 1].any()
        used = np.zeros((ny + 1, nx + 1), bool)
        used[:-1, :-1] |= cells
        used[1:, :-1] |= cells
        used[:-1, 1:] |= cells
        used[1:, 1:] |= cells
        vid = -np.ones((ny + 1, nx + 1), np.int64)
        vid[used] = np.arange(int(used.sum()))
        jj, ii = np.nonzero(used)
        lx, ly = ii * GRID, jj * GRID
        h = hmap[ly, lx]
        px, py = self.x0 + lx, self.y0 + ly
        bx, by, bz = back_project(px.astype(float), py.astype(float), self.d)
        P0 = np.stack([bx, by, np.full_like(bx, bz)], -1)
        ray = P0 - EYE
        front = EYE + ray * ((self.d - h) / self.d)[:, None]
        back = EYE + ray * ((self.d + BACK_RATIO * h) / self.d)[:, None]
        s = lx / (self.x1 - self.x0)
        t = 1 - ly / (self.y1 - self.y0)
        ci = np.argwhere(cells)
        a = vid[ci[:, 0], ci[:, 1]]
        b = vid[ci[:, 0], ci[:, 1] + 1]
        c = vid[ci[:, 0] + 1, ci[:, 1]]
        dd = vid[ci[:, 0] + 1, ci[:, 1] + 1]
        f_idx = np.stack([a, c, dd, a, dd, b], -1).reshape(-1)
        b_idx = np.stack([a, dd, c, a, b, dd], -1).reshape(-1)
        return {"front": front, "back": back, "s": s, "t": t, "fidx": f_idx, "bidx": b_idx}


def bleed(rgb: np.ndarray, inside: np.ndarray, iters: int = 10) -> np.ndarray:
    """Extend figure colours outward so bilinear filtering at the cut edge never picks up wall."""
    out = rgb.astype(np.float32)
    m = inside.astype(np.float32)
    for _ in range(iters):
        acc = cv2.blur(out * m[..., None], (5, 5))
        wgt = cv2.blur(m, (5, 5))
        grow = (m == 0) & (wgt > 1e-3)
        out[grow] = acc[grow] / wgt[grow][:, None]
        m = np.where(grow, 1.0, m)
    return np.clip(out, 0, 255).astype(np.uint8)


def build_figures(img: np.ndarray, depth: np.ndarray):
    named, statues, crowd, parts = segment(img, depth)
    kill = crowd.copy()
    for m in list(named.values()) + list(statues.values()) + parts:
        kill |= m
    kill = cv2.dilate(kill.astype(np.uint8), np.ones((13, 13), np.uint8)) > 0
    dmetric = metric_depth(depth, kill)

    figs: list[Figure] = []
    for fid in NAMED:
        m = named[fid]
        if m.sum() < 500:
            print(f"skip {fid}: empty mask")
            continue
        d = foot_distance(m)
        figs.append(Figure(fid, "near" if d < 10.0 else "platform", m, d, BODY_R))
    everyone = crowd.copy()
    for m in list(named.values()) + parts:
        everyone |= m
    crowd_figs: list[Figure] = []
    for i, m in enumerate(parts):
        d = foot_distance(m)
        ys, xs = np.nonzero(m)
        ybot = ys.max()
        foot_cols = xs[ys >= ybot - 6]
        below = min(H - 1, ybot + 5)
        hidden = ybot >= H - 3 or (everyone & ~m)[below, foot_cols].mean() > 0.5
        if hidden:
            # the lowest visible edge is not a foot: it sits on a nearer figure or the frame
            d = min(d, float(np.median(dmetric[m])))
        crowd_figs.append(Figure(f"crowd-{i:02d}", "near" if d < 10.0 else "platform", m, d, BODY_R * 0.85, crowd=True))
    # heads/shoulders split off above a body read as "far": seat them on the body below
    solid = [f for f in figs + crowd_figs if f.d <= 16]
    for f in crowd_figs:
        if f.d > 16:
            below_figs = [g for g in solid if g.x0 < f.x1 and g.x1 > f.x0 and g.y0 <= f.y1 + 40 and g.y1 > f.y1]
            if not below_figs:
                print(f"drop {f.id}: floating far fragment")
                continue
            f.d = min(below_figs, key=lambda g: g.y0).d
            f._set_center()
        else:
            f.ground()
        figs.append(f)
    for f in figs:
        if not f.crowd:
            f.ground()
    grounded = [f.id for f in figs if f.ext.any()]
    print(f"grounded {len(grounded)} figures: {', '.join(grounded)}")
    pier_d = CAM["eyeZ"] - PIER_FACE_Z
    for sid, m in statues.items():
        figs.append(Figure(sid, "statue", m, pier_d - 0.25, STATUE_R))
    return figs, kill


def export_figures(figs: list[Figure], src: Source, atlas: Atlas):
    textures = [(f, f.texture(src)) for f in figs]
    placed = []
    for f, tex in sorted(textures, key=lambda ft: -ft[1].shape[0]):
        pi, rect = atlas.add(tex)
        placed.append((f, pi, rect))
    atlas.finish()
    per_page: dict[int, dict[str, list]] = {}
    for f, pi, rect in placed:
        m = f.mesh()
        uv = atlas.uv(pi, rect, m["s"], m["t"])
        b = per_page.setdefault(pi, {"fpos": [], "bpos": [], "uv": [], "fidx": [], "bidx": [], "n": 0})
        base = b["n"]
        b["fpos"].append(m["front"].astype(np.float32))
        b["bpos"].append(m["back"].astype(np.float32))
        b["uv"].append(uv)
        b["fidx"].append((m["fidx"] + base).astype(np.uint32))
        b["bidx"].append((m["bidx"] + base).astype(np.uint32))
        b["n"] += len(m["front"])
    out = {}
    for pi, b in per_page.items():
        out[pi] = {
            "front": {"position": np.concatenate(b["fpos"]), "uv": np.concatenate(b["uv"]), "index": np.concatenate(b["fidx"])},
            "back": {"position": np.concatenate(b["bpos"]), "uv": np.concatenate(b["uv"]), "index": np.concatenate(b["bidx"])},
        }
    return out


def back_page(page: np.ndarray) -> np.ndarray:
    """Back of the figures: same layout, softened (no painted faces) and in shade."""
    rgb = page[..., :3].astype(np.float32)
    small = cv2.resize(rgb, (page.shape[1] // 2, page.shape[0] // 2), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(small, (0, 0), 5)
    gray = blur.mean(axis=2, keepdims=True)
    tone = (blur * 0.7 + gray * 0.3) * 0.72
    alpha = cv2.resize(page[..., 3], (small.shape[1], small.shape[0]), interpolation=cv2.INTER_AREA)
    return np.dstack([np.clip(tone, 0, 255).astype(np.uint8), alpha])
