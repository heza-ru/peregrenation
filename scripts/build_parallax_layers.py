"""Build the hero parallax planes from the GPT-generated sources in parallax/.

Pipeline:
  1. python scripts/register_gpt_layers.py   -> aligns Background / Adam / God to HeroBase
  2. python scripts/segment_hero.py --bg     -> SAM masks of rock, tree, land on Background
  3. python scripts/build_parallax_layers.py -> public/assets/parallax/*.webp

All planes share one canvas (HeroBase's framing at OUT_W wide), so they stay registered
when stacked. Background is split into far / clouds / landscape / rock; wherever a plane
sits behind a nearer one it is continued underneath with a smooth fill, so parallax
motion reveals scenery instead of holes.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "HeroBase.png"
SRC = ROOT / "parallax"
REG = ROOT / "scripts" / ".registered"
MASKS = ROOT / "scripts" / ".masks"
OUT = ROOT / "public" / "assets" / "parallax"

OUT_W = 2560

# GPT drew both pointing arms longer than the painting; nudging the figures apart
# restores the gap between the fingertips (px at HeroBase resolution).
ADAM_NUDGE_X = -45
GOD_NUDGE_X = 60

# Fractions of image size bracketing the mountains and city (kept on the far plate)
CITY_BAND = (0.66, 0.84, 0.5, 0.7)

# At OUT_W resolution; sized to cover the largest relative travel between planes
EXTEND_LAND = 150
EXTEND_CLOUDS = 110


def load_mask(name: str, size: tuple[int, int]) -> np.ndarray:
    m = Image.open(MASKS / f"{name}.png").convert("L").resize(size, Image.BILINEAR)
    return (np.asarray(m) > 127).astype(np.uint8)


def kernel(px: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (px * 2 + 1, px * 2 + 1))


def dilate(mask: np.ndarray, px: int) -> np.ndarray:
    return cv2.dilate(mask, kernel(px))


def erode(mask: np.ndarray, px: int) -> np.ndarray:
    return cv2.erode(mask, kernel(px))


def feather(mask: np.ndarray, sigma: float) -> np.ndarray:
    return cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sigma)


def blurred(weighted: np.ndarray, valid: np.ndarray, sigma: float, size: tuple[int, int]):
    """Gaussian blur of (weighted, valid); large sigmas run on a downscaled copy."""
    step = max(1, int(sigma // 8))
    small = (max(1, size[0] // step), max(1, size[1] // step))
    num = cv2.GaussianBlur(cv2.resize(weighted, small, interpolation=cv2.INTER_AREA), (0, 0), sigma / step)
    den = cv2.GaussianBlur(cv2.resize(valid, small, interpolation=cv2.INTER_AREA), (0, 0), sigma / step)
    num = cv2.resize(num, size, interpolation=cv2.INTER_LINEAR)
    den = cv2.resize(den, size, interpolation=cv2.INTER_LINEAR)
    if num.ndim == 2:
        num = num[..., None]
    return num, den


def smooth_fill(img: np.ndarray, hole: np.ndarray) -> np.ndarray:
    """Fill holes by multi-scale normalized convolution: local colour near the edge,
    progressively softer haze deeper inside. Avoids the radial streaks of Telea on big holes."""
    f = img.astype(np.float32)
    valid = (1 - hole).astype(np.float32)
    out = f.copy()
    pending = hole.astype(bool)
    h, w = hole.shape
    est = f
    for sigma in (6, 18, 48, 120, 300):
        num, den = blurred(f * valid[..., None], valid, sigma, (w, h))
        est = num / np.maximum(den, 1e-4)[..., None]
        take = pending & (den > 0.08)
        out[take] = est[take]
        pending &= ~take
    out[pending] = est[pending]
    wgt = feather(hole, 2.0)[..., None]
    return np.clip(f * (1 - wgt) + out * wgt, 0, 255).astype(np.uint8)


def mirror_fill(img: np.ndarray, own: np.ndarray, reach: int) -> np.ndarray:
    """Continue a plane's texture into the hole by reflecting its own pixels across the
    boundary (foliage stays foliage, rock stays rock). Beyond `reach` it falls back to the
    smooth haze fill, which is only ever seen through heavy parallax."""
    hole = (1 - own).astype(np.uint8)
    base = smooth_fill(img, hole)
    dist, labels = cv2.distanceTransformWithLabels(hole, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    own_coords = np.argwhere(hole == 0)  # label k -> own_coords[k - 1], row-major like OpenCV
    h, w = hole.shape
    yy, xx = np.nonzero(hole)
    near = own_coords[labels[yy, xx] - 1]
    ry = np.clip(2 * near[:, 0] - yy, 0, h - 1)
    rx = np.clip(2 * near[:, 1] - xx, 0, w - 1)
    # Where the reflection lands outside the plane (concave spots), keep the haze fill
    ok = own[ry, rx] > 0

    out = base.astype(np.float32)
    d = dist[yy, xx]
    wgt = (np.clip((reach - d) / (reach * 0.35), 0, 1) * ok)[:, None]
    out[yy, xx] = img[ry, rx].astype(np.float32) * wgt + out[yy, xx] * (1 - wgt)
    # Revealed texture reads as slightly out-of-focus, which hides mirror seams
    soft = cv2.GaussianBlur(out, (0, 0), 2.2)
    band = feather((hole & (dist < reach)).astype(np.uint8), 3.0)[..., None]
    out = out * (1 - band * 0.75) + soft * band * 0.75
    return np.clip(out, 0, 255).astype(np.uint8)


def cloud_alpha(rgb: np.ndarray) -> np.ndarray:
    """Soft alpha for painted clouds: clearly brighter and less blue than the sky,
    including the shadowed undersides."""
    f = rgb.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    brightness = np.clip((lum - 115) / 55, 0, 1)
    not_sky_blue = np.clip((50 - (b - r)) / 25, 0, 1)
    return brightness * not_sky_blue


def plane(rgb, own_alpha, own, occluders, extend, solid):
    """Content = the plane's own pixels continued outward from themselves; alpha continues
    underneath nearer planes following local coverage, so motion never uncovers a gap."""
    # Don't sample the nearer object's anti-aliased rim, or it rides along as a ghost outline
    source = own & (1 - dilate(occluders, 8))
    content = mirror_fill(rgb, source, extend * 2)
    valid = (1 - occluders).astype(np.float32)
    sigma = extend / 2
    num = cv2.GaussianBlur(own_alpha.astype(np.float32) * valid, (0, 0), sigma)
    den = cv2.GaussianBlur(valid, (0, 0), sigma)
    coverage = num / np.maximum(den, 1e-3)
    if solid:
        coverage = np.clip((coverage - 0.3) / 0.3, 0, 1)
    under = feather(dilate(occluders, 2) & dilate(own, extend), 2.0)
    # Grow the plane a few px under its occluders so the shared edge is fully opaque
    seam = feather(dilate(own, 4) & dilate(occluders, 1), 1.0)
    return content, np.maximum.reduce([own_alpha, coverage * under, seam])


def save_rgba(name: str, rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(OUT / name, "WEBP", quality=88, method=6)
    print(f"{name}: {(a > 16).mean() * 100:.1f}% opaque")
    return a


def figure(name: str, nudge_x: float, base_size: tuple[int, int], out_size: tuple[int, int]) -> np.ndarray:
    """Re-warp a GPT cutout straight from its source onto the output canvas (one resample)."""
    rgba = np.asarray(Image.open(SRC / f"{name}.png").convert("RGBA"))
    M = np.load(REG / f"{name}.npy")
    M = M.copy()
    M[0, 2] += nudge_x
    s = out_size[0] / base_size[0]
    M *= s
    warped = cv2.warpAffine(rgba, M, out_size, flags=cv2.INTER_LANCZOS4, borderValue=(0, 0, 0, 0))
    # Premultiplied-edge cleanup: drop faint fringe pixels GPT leaves around cutouts
    a = warped[..., 3].astype(np.float32) / 255
    a = np.clip((a - 0.04) / 0.92, 0, 1)
    warped[..., 3] = (a * 255).astype(np.uint8)
    return warped


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.webp"):
        stale.unlink()

    base_w, base_h = Image.open(BASE).size
    w, h = OUT_W, round(base_h * OUT_W / base_w)

    bg = np.asarray(Image.open(REG / "Background.png").convert("RGB").resize((w, h), Image.LANCZOS))
    ys = np.arange(h, dtype=np.float32)[:, None] / h
    xs = np.arange(w, dtype=np.float32)[None, :] / w
    y0, y1, x0, x1 = CITY_BAND
    city = feather((ys > y0) & (ys < y1) & (xs > x0) & (xs < x1), 0.02 * w)

    rock = load_mask("bg-rock", (w, h)) | load_mask("bg-tree", (w, h))
    # Close small gaps SAM leaves between tree masses and the rock
    land = cv2.morphologyEx(load_mask("bg-land", (w, h)) | rock, cv2.MORPH_CLOSE, kernel(18)) & (1 - rock)
    # Skip the bright halo GPT paints around tree silhouettes, or it rides with the clouds
    cloud_a = cloud_alpha(bg) * (1 - dilate(land | rock, 3)) * (1 - city)
    clouds = (cloud_a >= 0.35).astype(np.uint8)
    cloud_px = (cloud_a > 0.05).astype(np.uint8)

    far = mirror_fill(bg, 1 - (rock | land | clouds), 120)
    Image.fromarray(far).save(OUT / "1-far.webp", "WEBP", quality=86, method=6)
    print("1-far.webp: opaque plate")

    # Clouds sit behind the trees: they continue underneath the landscape and rock
    cloud_rgb, cloud_alpha_ext = plane(bg, cloud_a, cloud_px, rock | land, EXTEND_CLOUDS, solid=False)
    save_rgba("2-clouds.webp", cloud_rgb, cloud_alpha_ext)

    land_rgb, land_a = plane(bg, feather(land, 1.2), land, rock, EXTEND_LAND, solid=True)
    save_rgba("3-landscape.webp", land_rgb, land_a)

    save_rgba("4-rock.webp", bg, feather(erode(rock, 1), 1.0))

    for name, nudge, out_name in (("Adam", ADAM_NUDGE_X, "5-adam.webp"), ("God", GOD_NUDGE_X, "6-god.webp")):
        rgba = figure(name, nudge, (base_w, base_h), (w, h))
        Image.fromarray(rgba, "RGBA").save(OUT / out_name, "WEBP", quality=90, method=6)
        print(f"{out_name}: {(rgba[..., 3] > 16).mean() * 100:.1f}% opaque")

    print("layers ->", OUT, f"({w}x{h})")


if __name__ == "__main__":
    main()
