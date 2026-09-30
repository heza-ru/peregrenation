"""Camera, room dimensions and source sampling for the Arnolfini room build.

World: metres, y up, the painter's eye at the origin of the XZ plane looking down -z.
Image coordinates are in the 1920 x 2627 painting.jpg frame.

Measured on the panel: the floorboards run straight into the room (seams near-vertical at
x ~ 950); with Giovanni ~1.72 m tall (feet row 2400), the back wall's ceiling line at row 110
and its hidden base behind the chair (~row 1640), the horizon sits at row 1054 - the joined
hands - and the painter's eye 1.19 m above the floor. f = 2200 px puts the window (x 40-300)
1.2 m wide on the left wall, the bed's near corner at the right edge on floor row 2050, and
gives a 3.1 m ceiling and a 0.31 m dog. Van Eyck's upper orthogonals (canopy) converge
higher: textures are projected from this single eye, so the painting is exact from the
painter's spot and the geometry is plausible everywhere else.
Must stay in sync with src/world/arnolfiniRoomConfig.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PID = "arnolfini-portrait"
DATA = ROOT / "data" / "paintings" / PID
PUBLIC = ROOT / "public" / "data" / "paintings" / PID
CACHE = DATA / "_cache"

W, H = 1920, 2627
CAM = {"f": 2200.0, "cx": 955.0, "cy": 1054.0, "eyeY": 1.187, "eyeZ": 0.0, "width": W, "height": H}
EYE = np.array([0.0, CAM["eyeY"], CAM["eyeZ"]])

# Room shell
BACK_Z = -4.46
FRONT_Z = 1.1
LEFT_X = -1.307
RIGHT_X = 2.4
CEIL_Y = 3.1


def project(P: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """World points (..., 3) -> painting px, py (1920 space) and view depth d."""
    d = CAM["eyeZ"] - P[..., 2]
    ds = np.where(np.abs(d) < 1e-6, 1e-6, d)
    px = CAM["cx"] + P[..., 0] * CAM["f"] / ds
    py = CAM["cy"] - (P[..., 1] - CAM["eyeY"]) * CAM["f"] / ds
    return px, py, d


def back_project(px, py, d):
    f, cx, cy, ey, ez = CAM["f"], CAM["cx"], CAM["cy"], CAM["eyeY"], CAM["eyeZ"]
    return ((np.asarray(px) - cx) * d / f, ey - (np.asarray(py) - cy) * d / f, ez - np.asarray(d))


def floor_depth(py) -> np.ndarray:
    """View depth at which the painter's ray through row py meets the floor (inf above the horizon)."""
    dy = np.asarray(py, float) - CAM["cy"]
    return np.where(dy > 0.5, CAM["eyeY"] * CAM["f"] / np.maximum(dy, 0.5), np.inf)


def load_hd() -> np.ndarray:
    p = CACHE / "painting-original.jpg"
    if p.exists():
        img = cv2.imread(str(p))
        if img is not None:
            return img
    return cv2.imread(str(DATA / "painting.jpg"))


@dataclass
class Source:
    """The panel as a mip pyramid; scale = source px per 1920-space px."""

    levels: dict[float, np.ndarray] = field(default_factory=dict)

    def best(self, want: float) -> tuple[float, np.ndarray]:
        scales = sorted(self.levels)
        for s in scales:
            if s >= want:
                return s, self.levels[s]
        return scales[-1], self.levels[scales[-1]]

    def sample(self, px: np.ndarray, py: np.ndarray, want: float) -> np.ndarray:
        """Bilinear sample at the smallest level that still resolves `want` px per 1920 px."""
        _, img = self.best(want)
        sx, sy = img.shape[1] / W, img.shape[0] / H
        mx = (px * sx - 0.5).astype(np.float32)
        my = (py * sy - 0.5).astype(np.float32)
        return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def sample_adaptive(self, px: np.ndarray, py: np.ndarray, footprint: np.ndarray) -> np.ndarray:
        """Per-texel level choice: footprint = source 1920-px covered by one texel (>= ~1 means minify)."""
        out = np.zeros(px.shape + (3,), np.float32)
        scales = sorted(self.levels)
        # texel wants `1/footprint` px per 1920 px; pick the smallest level >= that, blend the neighbour
        want = 1.0 / np.maximum(footprint, 1e-3)
        lo = np.zeros(px.shape, int)
        for i, s in enumerate(scales):
            lo = np.where(want > s * 1.0001, min(i + 1, len(scales) - 1), lo)
        for i, s in enumerate(scales):
            sel = lo == i
            if sel.any():
                col = self.sample(px, py, s).astype(np.float32)
                out[sel] = col[sel]
        return out


def load_source() -> Source:
    base = cv2.imread(str(DATA / "painting.jpg"))
    assert base.shape[:2] == (H, W), base.shape
    src = Source({1.0: base})
    hd = CACHE / "painting-original.jpg"
    if hd.exists():
        big = cv2.imread(str(hd))
        if big is not None:
            print(f"source: {hd.name} {big.shape[1]}x{big.shape[0]}")
            src.levels[big.shape[1] / W] = big
    # coarser levels so minified texels never alias
    for s in (0.5, 0.25):
        src.levels[s] = cv2.resize(base, (int(W * s), int(round(H * s))), interpolation=cv2.INTER_AREA)
    print("source levels:", sorted(src.levels))
    return src


def load_mask(name: str, soft: bool = False) -> np.ndarray:
    """Mask in 1920 space (area-resampled from the full-resolution mask)."""
    m = cv2.imread(str(DATA / "masks" / f"{name}.png"), cv2.IMREAD_GRAYSCALE)
    m = cv2.resize(m, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    return m if soft else m > 0.5


def load_mask_hd(name: str) -> np.ndarray:
    m = cv2.imread(str(DATA / "masks" / f"{name}.png"), cv2.IMREAD_GRAYSCALE)
    return m.astype(np.float32) / 255.0
