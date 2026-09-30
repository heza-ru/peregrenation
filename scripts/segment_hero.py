"""Segment HeroBase.png into object masks with SAM point prompts.

Prompt coordinates are authored on a 1024px-wide preview and scaled to the source.
Masks are written to scripts/.masks/ for build_parallax_layers.py.
Pass mask names (e.g. `land`) to regenerate only those; `--bg` segments the
registered GPT Background plate instead, writing bg-<name>.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "HeroBase.png"
BG_SRC = ROOT / "scripts" / ".registered" / "Background.png"
MASKS = ROOT / "scripts" / ".masks"
PREVIEW_W = 1024

# (x, y, label) on the 1024px-wide preview
PROMPTS: dict[str, list[list[tuple[int, int, int]]]] = {
    "adam": [
        [(220, 240, 1), (225, 150, 1), (130, 235, 1), (380, 195, 1)],
        [(340, 300, 1), (400, 352, 1), (455, 372, 1), (250, 310, 1)],
        [(225, 132, 1), (245, 125, 1), (205, 150, 1)],
        [(365, 250, 1), (380, 232, 1), (355, 280, 1)],
        [(260, 300, 1), (300, 318, 1), (225, 320, 1), (320, 335, 1)],
        [(455, 183, 1), (440, 180, 1)],
    ],
    "god": [
        [(680, 110, 1), (740, 170, 1), (600, 178, 1), (870, 240, 1)],
        [(900, 70, 1), (830, 60, 1), (700, 60, 1), (960, 45, 1)],
        [(965, 160, 1), (860, 90, 1), (650, 220, 1)],
        [(760, 290, 1), (900, 330, 1), (820, 350, 1), (640, 260, 1)],
        [(615, 200, 1), (605, 230, 1), (625, 160, 1)],
        [(720, 200, 1), (760, 212, 1), (800, 195, 1), (900, 200, 1)],
        [(680, 75, 1), (700, 68, 1), (660, 90, 1)],
        [(800, 70, 1), (840, 58, 1), (770, 75, 1)],
        [(700, 250, 1), (680, 285, 1), (730, 300, 1)],
        [(760, 330, 1), (800, 360, 1), (930, 340, 1)],
        [(512, 186, 1), (540, 180, 1)],
        [(850, 140, 1), (900, 150, 1), (830, 122, 1)],
        [(955, 135, 1), (990, 150, 1), (975, 175, 1)],
        [(630, 195, 1), (642, 208, 1)],
        [(820, 105, 1), (832, 114, 1)],
        [(1012, 140, 1), (1015, 120, 1)],
    ],
    "rock": [
        [(80, 285, 1), (300, 400, 1), (480, 410, 1), (200, 370, 1)],
        [(60, 420, 1), (20, 330, 1), (140, 430, 1)],
    ],
    "tree": [
        [(80, 100, 1), (60, 40, 1), (200, 30, 1), (140, 120, 1), (20, 200, 1)],
    ],
    "land": [
        [(480, 300, 1), (505, 325, 1), (430, 255, 1), (455, 290, 1)],
        [(540, 352, 1), (590, 372, 1), (520, 340, 1)],
        [(600, 402, 1), (680, 406, 1), (740, 400, 1)],
        [(140, 110, 1), (125, 150, 1), (155, 95, 1)],
        [(305, 185, 1), (318, 175, 1)],
        [(600, 425, 1), (580, 410, 1)],
        [(930, 432, 1), (700, 385, 1)],
    ],
}

# Prompts for parallax/Background.png (the figure-free plate); written as bg-<name>.png
BG_PROMPTS: dict[str, list[list[tuple[int, int, int]]]] = {
    "rock": [
        [(100, 262, 1), (120, 300, 1), (130, 190, 1), (200, 250, 1)],
        [(360, 322, 1), (300, 380, 1), (480, 410, 1), (200, 400, 1)],
        [(60, 420, 1), (20, 330, 1), (140, 430, 1), (330, 395, 1)],
    ],
    "tree": [
        [(80, 100, 1), (60, 40, 1), (200, 30, 1), (140, 120, 1), (20, 200, 1)],
    ],
    "land": [
        [(300, 200, 1), (330, 222, 1), (220, 190, 1), (350, 260, 1)],
        [(140, 110, 1), (150, 160, 1)],
        [(410, 272, 1), (480, 320, 1), (505, 340, 1)],
        [(600, 370, 1), (700, 362, 1), (560, 350, 1)],
        [(650, 402, 1), (760, 400, 1)],
        [(600, 418, 1), (900, 390, 1), (990, 400, 1), (700, 430, 1)],
    ],
}


def fill_holes(mask: np.ndarray, max_hole_ratio: float = 0.0015) -> np.ndarray:
    """Close pinholes inside a mask; larger enclosed gaps are real background and stay open."""
    binary = (mask > 127).astype(np.uint8) * 255
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    count, labels, stats, _ = cv2.connectedComponentsWithStats(cv2.bitwise_not(binary), connectivity=4)
    max_area = binary.size * max_hole_ratio
    h, w = binary.shape
    for i in range(1, count):
        x, y, bw, bh, area = stats[i]
        touches_edge = x == 0 or y == 0 or x + bw == w or y + bh == h
        if not touches_edge and area < max_area:
            binary[labels == i] = 255
    return binary


def main() -> None:
    MASKS.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:]
    use_bg = "--bg" in args
    only = {a for a in args if not a.startswith("--")}
    image = Image.open(BG_SRC if use_bg else SRC).convert("RGB")
    prompts, prefix = (BG_PROMPTS, "bg-") if use_bg else (PROMPTS, "")
    scale = image.width / PREVIEW_W
    session = new_session("sam")

    for name, groups in prompts.items():
        if only and name not in only:
            continue
        combined = np.zeros((image.height, image.width), dtype=np.uint8)
        for group in groups:
            prompt = [
                {"type": "point", "data": [int(x * scale), int(y * scale)], "label": label}
                for x, y, label in group
            ]
            mask = remove(image, session=session, sam_prompt=prompt, only_mask=True)
            part = np.asarray(mask.convert("L"))
            if (part > 127).mean() > 0.35:
                print(f"  skipped runaway {name} prompt {group[0]}")
                continue
            combined = np.maximum(combined, part)
        combined = fill_holes(combined)
        Image.fromarray(combined).save(MASKS / f"{prefix}{name}.png")
        print(name, f"{(combined > 127).mean() * 100:.1f}% coverage")


if __name__ == "__main__":
    main()
