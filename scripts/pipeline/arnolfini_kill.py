"""Which panel pixels belong to modelled objects (figures, reliefs, props) rather than the room."""

from __future__ import annotations

import cv2
import numpy as np

from arnolfini_common import load_hd, load_mask

OBJECTS = [
    "giovanni",
    "bride",
    "bride-sleeve",
    "dog",
    "chandelier",
    "clogs",
    "slippers",
    "curtain-bag",
    "mirror",
    "rosary",
    "brush",
    "oranges-chest",
    "orange-sill",
]
RELIEFS = ("mirror", "rosary", "brush")


def _norm_blur(x: np.ndarray, w: np.ndarray, sigma: float) -> np.ndarray:
    num = cv2.GaussianBlur(x * w[..., None], (0, 0), sigma)
    return num / np.maximum(cv2.GaussianBlur(w, (0, 0), sigma), 1e-6)[..., None]


def stray_paint(kill: np.ndarray, halo_px: int = 14) -> np.ndarray:
    """Pixels just outside the masks still carrying the object's paint (a gown hem, a slipper's
    red): their hue is nearer the object beside them than the room around them. Shadows keep
    the room's hue and stay."""
    img = cv2.resize(load_hd(), (kill.shape[1], kill.shape[0]), interpolation=cv2.INTER_AREA)
    ab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)[..., 1:]
    k = 2 * halo_px + 1
    halo = (cv2.dilate(kill.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))) > 0) & ~kill
    obj = _norm_blur(ab, kill.astype(np.float32), 6.0)
    room = _norm_blur(ab, (~kill & ~halo).astype(np.float32), 12.0)
    d_obj = np.linalg.norm(ab - obj, axis=-1)
    d_room = np.linalg.norm(ab - room, axis=-1)
    stray = halo & (d_obj < d_room) & (d_room > 5.0)
    return cv2.dilate(stray.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0


def kill_mask(dilate_px: int = 3) -> np.ndarray:
    """Union of every object's soft mask (any coverage), grown so edge halos are rebuilt too,
    plus the object paint that strays just past a mask's edge."""
    k = 2 * dilate_px + 1

    def union(names) -> np.ndarray:
        m = np.zeros_like(load_mask("giovanni", soft=True), dtype=bool)
        for name in names:
            m |= load_mask(name, soft=True) > 0.02
        return cv2.dilate(m.astype(np.uint8), np.ones((k, k), np.uint8)) > 0

    m = union(OBJECTS)
    # reliefs hang on the wall: the dark just past them is their own shadow on the plaster
    free = union([n for n in OBJECTS if n not in RELIEFS])
    return m | stray_paint(free)
