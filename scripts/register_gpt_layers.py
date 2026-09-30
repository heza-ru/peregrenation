"""Register GPT-generated layers in parallax/ onto HeroBase.png and report fit quality.

Cutouts (Adam, God) are matched with SIFT features to HeroBase and mapped with a
similarity transform (uniform scale + rotation + translation), then compared with the
SAM masks. Registered results are written to scripts/.registered/.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "HeroBase.png"
SRC = ROOT / "parallax"
MASKS = ROOT / "scripts" / ".masks"
OUT = ROOT / "scripts" / ".registered"

CUTOUTS = {"Adam": ["adam"], "God": ["god"]}


def gray(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)


def match_similarity(src_rgb, src_mask, dst_rgb, dst_mask):
    sift = cv2.SIFT_create(nfeatures=8000)
    k1, d1 = sift.detectAndCompute(gray(src_rgb), src_mask)
    k2, d2 = sift.detectAndCompute(gray(dst_rgb), dst_mask)
    matches = cv2.BFMatcher(cv2.NORM_L2).knnMatch(d1, d2, k=2)
    good = [m for m, n in matches if m.distance < 0.8 * n.distance]
    p1 = np.float32([k1[m.queryIdx].pt for m in good])
    p2 = np.float32([k2[m.trainIdx].pt for m in good])
    M, inliers = cv2.estimateAffinePartial2D(p1, p2, method=cv2.RANSAC, ransacReprojThreshold=6)
    return M, int(inliers.sum()) if inliers is not None else 0, len(good)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    return float((a & b).sum() / max((a | b).sum(), 1))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = np.asarray(Image.open(BASE).convert("RGB"))
    h, w, _ = base.shape

    for name, mask_names in CUTOUTS.items():
        rgba = np.asarray(Image.open(SRC / f"{name}.png").convert("RGBA"))
        rgb, alpha = rgba[..., :3], rgba[..., 3]
        sam = np.zeros((h, w), np.uint8)
        for m in mask_names:
            sam |= (np.asarray(Image.open(MASKS / f"{m}.png").convert("L")) > 127).astype(np.uint8)
        search = cv2.dilate(sam, np.ones((61, 61), np.uint8)) * 255

        M, inl, good = match_similarity(rgb, (alpha > 128).astype(np.uint8) * 255, base, search)
        scale = float(np.hypot(M[0, 0], M[1, 0]))
        angle = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
        warped = cv2.warpAffine(rgba, M, (w, h), flags=cv2.INTER_LANCZOS4, borderValue=(0, 0, 0, 0))
        wa = (warped[..., 3] > 128).astype(np.uint8)
        region = wa & sam
        diff = np.abs(warped[..., :3].astype(np.float32) - base.astype(np.float32)).mean(axis=2)
        print(
            f"{name}: {inl}/{good} inlier matches, scale {scale:.3f}, rotation {angle:.2f} deg, "
            f"offset ({M[0, 2]:.0f},{M[1, 2]:.0f}); IoU vs SAM mask {iou(wa, sam):.3f}; "
            f"colour diff on overlap {diff[region > 0].mean():.1f}/255"
        )
        Image.fromarray(warped, "RGBA").save(OUT / f"{name}.png")
        np.save(OUT / f"{name}.npy", M)

        over = base.astype(np.float32) * 0.45
        a = warped[..., 3:4].astype(np.float32) / 255
        over = over * (1 - a) + warped[..., :3] * a
        edge = cv2.morphologyEx(sam, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
        over[edge] = (0, 255, 255)
        Image.fromarray(over.astype(np.uint8)).resize((1024, 441)).save(OUT / f"_check-{name}.png")

    bg = np.asarray(Image.open(SRC / "Background.png").convert("RGB"))
    bg = cv2.resize(bg, (w, h), interpolation=cv2.INTER_LANCZOS4) if bg.shape[:2] != (h, w) else bg
    figures = np.zeros((h, w), np.uint8)
    for m in ("adam", "god"):
        figures |= (np.asarray(Image.open(MASKS / f"{m}.png").convert("L")) > 127).astype(np.uint8)
    keep = cv2.erode(1 - figures, np.ones((41, 41), np.uint8)) * 255
    M, inl, good = match_similarity(bg, keep, base, keep)
    print(
        f"Background: {inl}/{good} inlier matches, scale {np.hypot(M[0, 0], M[1, 0]):.4f}, "
        f"offset ({M[0, 2]:.1f},{M[1, 2]:.1f})"
    )
    diff = np.abs(bg.astype(np.float32) - base.astype(np.float32)).mean(axis=2)
    print(f"Background: colour diff outside figures {diff[keep > 0].mean():.1f}/255 (as delivered)")
    Image.fromarray(bg).save(OUT / "Background.png")
    Image.fromarray((np.abs(bg.astype(np.int16) - base).clip(0, 255) * 2).clip(0, 255).astype(np.uint8)).resize(
        (1024, 441)
    ).save(OUT / "_diff-Background.png")


if __name__ == "__main__":
    main()
