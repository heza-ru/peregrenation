"""Shared camera model, source pyramid, atlas packing and binary export for the Athens build."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PID = "school-of-athens"
DATA = ROOT / "data" / "paintings" / PID
PUBLIC = ROOT / "public" / "data" / "paintings" / PID
CACHE = DATA / "_cache"

# Measured on painting.jpg (1920x1339); all image coordinates below are in this space.
CAM = {"f": 1600.0, "cx": 1017.0, "cy": 760.0, "eyeY": 2.87, "eyeZ": 10.3, "width": 1920, "height": 1339}
W, H = CAM["width"], CAM["height"]
EYE = np.array([0.0, CAM["eyeY"], CAM["eyeZ"]])

STEP_FRONTS = [0.0, -0.4, -0.8, -1.2]
STEP_RISE = 0.25
PLATFORM_Y = 1.0


def floor_y(z: float) -> float:
    if z > STEP_FRONTS[0]:
        return 0.0
    for i, front in enumerate(STEP_FRONTS[1:], start=1):
        if z > front:
            return STEP_RISE * i
    return PLATFORM_Y


def raymarch(px: float, py: float) -> float:
    f, cy, ey, ez = CAM["f"], CAM["cy"], CAM["eyeY"], CAM["eyeZ"]
    if py <= cy + 2:
        return 40.0
    d = 7.0
    while d < 60.0:
        y = ey - (py - cy) * d / f
        if y <= floor_y(ez - d):
            return d
        d += 0.01
    return 60.0


def back_project(px, py, d):
    f, cx, cy, ey, ez = CAM["f"], CAM["cx"], CAM["cy"], CAM["eyeY"], CAM["eyeZ"]
    return ((px - cx) * d / f, ey - (py - cy) * d / f, ez - d)


def project(P: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """World points (..., 3) -> painting px, py (1920 space) and view distance d."""
    d = CAM["eyeZ"] - P[..., 2]
    ds = np.where(np.abs(d) < 1e-6, 1e-6, d)
    px = CAM["cx"] + P[..., 0] * CAM["f"] / ds
    py = CAM["cy"] - (P[..., 1] - CAM["eyeY"]) * CAM["f"] / ds
    return px, py, d


LUNETTE = (194.0, 1794.0, 879.0, 176.0)  # inner edge of the frame: x0, x1, spring y, crown y


def in_lunette(xx: np.ndarray, yy: np.ndarray) -> np.ndarray:
    """Inside the fresco's painted lunette (any pixel coordinates, also beyond the frame)."""
    x0, x1, spring, crown = LUNETTE
    a, b, cxm = (x1 - x0) / 2, spring - crown, (x0 + x1) / 2
    inside = ((xx >= x0) & (xx <= x1) & (yy >= spring)) | (((xx - cxm) / a) ** 2 + ((yy - spring) / b) ** 2 <= 1.0)
    inside &= ~((xx < 392) & (yy > 1146))  # real doorway, bottom-left
    inside &= ~((xx > 1800) & (yy > 884))  # real pilaster, bottom-right
    return inside


def scene_mask() -> np.ndarray:
    """Pixels that belong to the fresco's pictorial space, kept clear of the ornamental frame band."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    return cv2.erode(in_lunette(xx, yy).astype(np.uint8), np.ones((25, 25), np.uint8)) > 0


@dataclass
class Source:
    """The fresco at several scales (scale = pixels per 1920-space pixel)."""

    levels: dict[float, np.ndarray] = field(default_factory=dict)

    def best(self, want: float) -> tuple[float, np.ndarray]:
        scales = sorted(self.levels)
        for s in scales:
            if s >= want:
                return s, self.levels[s]
        return scales[-1], self.levels[scales[-1]]

    def sample(self, px: np.ndarray, py: np.ndarray, want: float) -> np.ndarray:
        s, img = self.best(want)
        sy = img.shape[0] / H
        sx = img.shape[1] / W
        mx = (px * sx - 0.5 + 0.5 * sx).astype(np.float32)
        my = (py * sy - 0.5 + 0.5 * sy).astype(np.float32)
        return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def load_source() -> Source:
    base = cv2.imread(str(DATA / "painting.jpg"))
    assert base.shape[:2] == (H, W), base.shape
    src = Source({1.0: base})
    for name in ("painting-original.jpg", "painting-hd-src.jpg"):
        p = CACHE / name
        if not p.exists():
            continue
        big = cv2.imread(str(p))
        if big is None:
            continue
        print(f"source: {name} {big.shape[1]}x{big.shape[0]}")
        top = big.shape[1] / W
        for s in (2.0, 4.0):
            if s <= top + 1e-3:
                src.levels[s] = cv2.resize(big, (int(W * s), int(round(H * s))), interpolation=cv2.INTER_AREA)
        if top > 4.5:
            src.levels[top] = big
        break
    print("source levels:", sorted(src.levels))
    return src


class Atlas:
    """Shelf packer into fixed-width pages; each rect gets a 4px edge-extended gutter."""

    PAD = 4

    def __init__(self, name: str, page: int = 4096):
        self.name = name
        self.page = page
        self.pages: list[np.ndarray] = []
        self._cursor: list[list[int]] = []  # per page: [x, y, shelf_h]

    def _new_page(self, channels: int) -> int:
        self.pages.append(np.zeros((self.page, self.page, channels), np.uint8))
        self._cursor.append([0, 0, 0])
        return len(self.pages) - 1

    def add(self, img: np.ndarray) -> tuple[int, tuple[int, int, int, int]]:
        """Returns (page, (x, y, w, h)) pixel rect of the image inside the page."""
        h, w = img.shape[:2]
        P = self.PAD
        assert w + 2 * P <= self.page and h + 2 * P <= self.page, (w, h)
        placed = None
        for pi, cur in enumerate(self._cursor):
            x, y, sh = cur
            if x + w + 2 * P > self.page:
                x, y, sh = 0, y + sh, 0
            if y + h + 2 * P <= self.page:
                placed = (pi, x, y, sh)
                break
        if placed is None:
            pi = self._new_page(img.shape[2])
            placed = (pi, 0, 0, 0)
        pi, x, y, sh = placed
        padded = cv2.copyMakeBorder(img, P, P, P, P, cv2.BORDER_REPLICATE)
        self.pages[pi][y : y + h + 2 * P, x : x + w + 2 * P] = padded
        self._cursor[pi] = [x + w + 2 * P, y, max(sh, h + 2 * P)]
        return pi, (x + P, y + P, w, h)

    def finish(self) -> list[np.ndarray]:
        """Pages cropped to their used height (multiple of 4)."""
        out = []
        for page, (_, y, sh) in zip(self.pages, self._cursor):
            used = min(self.page, ((y + sh + 3) // 4) * 4)
            out.append(page[:used])
        self.final = out
        return out

    def uv(self, pi: int, rect: tuple[int, int, int, int], s: np.ndarray, t: np.ndarray) -> np.ndarray:
        """Map local (s, t) in [0,1] (t up) inside a rect to GL uv (v up) on the finished page."""
        x, y, w, h = rect
        ph, pw = self.final[pi].shape[:2]
        u = (x + s * w) / pw
        v = 1 - (y + (1 - t) * h) / ph
        return np.stack([u, v], -1).astype(np.float32)


class BinWriter:
    def __init__(self):
        self.chunks: list[bytes] = []
        self.offset = 0

    def add(self, arr: np.ndarray) -> list[int]:
        b = np.ascontiguousarray(arr).tobytes()
        pad = (-len(b)) % 4
        start = self.offset
        self.chunks.append(b + b"\0" * pad)
        self.offset += len(b) + pad
        return [start, int(arr.size)]

    def write(self, path: Path) -> None:
        path.write_bytes(b"".join(self.chunks))


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")
