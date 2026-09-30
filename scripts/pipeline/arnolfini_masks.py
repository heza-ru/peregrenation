"""Object masks for the Arnolfini room (run once; cached under data/.../masks/).

SAM ViT-H on each object's crop (authored box + point prompts, 1920-space coordinates),
then a GrabCut refinement in a narrow band around the SAM boundary at the full 3840 px
source, so silhouettes follow the painted edge to the source pixel.

Usage: python scripts/pipeline/arnolfini_masks.py [--only id,id] [--preview]
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from arnolfini_common import DATA, H, W, load_hd  # noqa: E402

MASKS = DATA / "masks"

# box (x0, y0, x1, y1), positive points, negative points - all in 1920 space
PROMPTS: dict[str, dict] = {
    "giovanni": {
        "box": (120, 270, 1110, 2440),
        "pos": [
            (540, 560), (530, 340), (500, 1400), (470, 880), (500, 2330), (250, 1980), (850, 1000), (700, 1900),
            (1030, 1110), (860, 1250), (875, 1500), (880, 1750), (930, 1900), (900, 1150),
        ],
        "neg": [(700, 700), (100, 1600), (300, 2200), (150, 600), (1000, 1300), (1000, 1550), (990, 2000), (960, 1700)],
    },
    "bride": {
        "box": (1000, 440, 1920, 2610),
        "pos": [(1450, 640), (1540, 560), (1500, 1500), (1500, 2450), (1300, 1150), (1560, 1040), (1160, 2150), (1750, 2300), (1620, 1400)],
        "neg": [(1850, 1400), (980, 1400), (1100, 2450), (950, 2400), (1300, 300), (1880, 700), (1080, 1830)],
    },
    "dog": {
        "box": (680, 2160, 1120, 2627),
        "pos": [(960, 2350), (800, 2450), (1060, 2330), (760, 2560)],
        "neg": [(650, 2600), (1150, 2450), (700, 2200)],
    },
    "chandelier": {
        "box": (690, 0, 1280, 650),
        "pos": [(975, 400), (975, 150), (760, 400), (1200, 330), (805, 200), (1085, 240), (990, 600), (975, 40)],
        "neg": [(1100, 560), (700, 120), (880, 110), (1180, 150), (900, 560)],
    },
    "clogs": {
        "box": (0, 2240, 330, 2627),
        "pos": [(150, 2330), (60, 2480), (230, 2360), (90, 2580)],
        "neg": [(250, 2500), (300, 2280), (160, 2600)],
    },
    "slippers": {
        "box": (880, 1625, 1075, 1725),
        "pos": [(930, 1680), (1030, 1680)],
        "neg": [(980, 1720), (980, 1600)],
    },
    "curtain-bag": {
        "box": (1745, 0, 1920, 690),
        "pos": [(1830, 300), (1830, 600), (1830, 60)],
        "neg": [(1720, 400), (1830, 740)],
    },
    "mirror": {
        "box": (800, 615, 1135, 955),
        "pos": [(965, 785), (870, 700), (1060, 870), (965, 640)],
        "neg": [(780, 785), (1150, 785), (965, 970)],
    },
    "rosary": {
        "box": (752, 625, 818, 845),
        "pos": [(785, 700), (785, 780), (790, 820)],
        "neg": [(760, 900), (820, 700), (750, 700)],
    },
    "brush": {
        "box": (1135, 455, 1245, 775),
        "pos": [(1190, 700), (1195, 560), (1200, 480)],
        "neg": [(1130, 700), (1250, 600), (1190, 790)],
    },
    "hands": {
        "box": (948, 1028, 1200, 1178),
        "pos": [(1000, 1100), (1050, 1080), (1100, 1112), (1150, 1085), (1020, 1158), (968, 1100)],
        "neg": [(1000, 1182), (1100, 1040), (1160, 1150), (1195, 1120), (950, 1170)],
    },
    # her dagged hanging sleeve, falling between the rug and the gown
    "bride-sleeve": {
        "box": (1086, 1385, 1150, 1885),
        "pos": [
            (1118, 1410), (1115, 1500), (1110, 1600), (1112, 1700), (1118, 1800), (1120, 1860),
            (1104, 1480), (1101, 1580), (1100, 1680), (1103, 1780),
        ],
        "neg": [(1070, 1700), (1075, 1550), (1060, 1850)],
    },
    # skin the back shells replace: faces (-> hair / veil) and hands laid on the body
    "giovanni-face": {
        "box": (440, 440, 640, 700),
        "pos": [(538, 560), (505, 600), (580, 580), (540, 640), (515, 505)],
        "neg": [(540, 430), (430, 560), (660, 560), (540, 720)],
    },
    "giovanni-hand": {
        "box": (430, 750, 545, 1000),
        "pos": [(486, 870), (472, 820), (500, 920), (478, 785)],
        "neg": [(432, 900), (540, 900), (500, 1000)],
    },
    "bride-face": {
        "box": (1330, 480, 1530, 790),
        "pos": [(1427, 600), (1400, 560), (1450, 650), (1420, 690), (1470, 600), (1440, 735)],
        "neg": [(1515, 560), (1330, 620), (1427, 478), (1440, 790)],
    },
    "bride-hand": {
        "box": (1270, 955, 1450, 1045),
        "pos": [(1330, 1000), (1380, 995), (1420, 1000)],
        "neg": [(1300, 1042), (1380, 958), (1462, 1000)],
    },
    "oranges-chest": {
        "box": (140, 1352, 282, 1442),
        "pos": [(175, 1400), (235, 1405), (268, 1380)],
        "neg": [(150, 1450), (120, 1390), (200, 1350)],
    },
    "orange-sill": {
        "box": (185, 1160, 240, 1216),
        "pos": [(212, 1190)],
        "neg": [(190, 1225), (240, 1160)],
    },
}


def sam_masks(ids: list[str], img_bgr: np.ndarray) -> dict[str, np.ndarray]:
    import torch
    from transformers import SamModel, SamProcessor

    torch.set_num_threads(max(1, torch.get_num_threads()))
    proc = SamProcessor.from_pretrained("facebook/sam-vit-huge")
    model = SamModel.from_pretrained("facebook/sam-vit-huge").eval()
    S = img_bgr.shape[1] / W
    out = {}
    for oid in ids:
        p = PROMPTS[oid]
        x0, y0, x1, y1 = p["box"]
        mx, my = int(0.08 * (x1 - x0)) + 20, int(0.08 * (y1 - y0)) + 20
        cx0, cy0 = max(0, x0 - mx), max(0, y0 - my)
        cx1, cy1 = min(W, x1 + mx), min(H, y1 + my)
        crop = img_bgr[int(cy0 * S) : int(cy1 * S), int(cx0 * S) : int(cx1 * S)]
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        k = S

        def loc(pt):
            return [(pt[0] - cx0) * k, (pt[1] - cy0) * k]

        points = [loc(q) for q in p["pos"]] + [loc(q) for q in p["neg"]]
        labels = [1] * len(p["pos"]) + [0] * len(p["neg"])
        box = [loc((x0, y0)) + loc((x1, y1))]
        inputs = proc(
            images=rgb,
            input_points=[[points]],
            input_labels=[[labels]],
            input_boxes=[box],
            return_tensors="pt",
        )
        with torch.no_grad():
            res = model(**inputs, multimask_output=True)
        masks = proc.image_processor.post_process_masks(
            res.pred_masks, inputs["original_sizes"], inputs["reshaped_input_sizes"], binarize=False
        )[0][0]
        scores = res.iou_scores[0, 0].numpy()
        best = int(np.argmax(scores))
        logit = masks[best].numpy()
        print(f"  sam {oid}: iou {scores.round(3)} -> {best}")
        full = np.full(img_bgr.shape[:2], -20.0, np.float32)
        full[int(cy0 * S) : int(cy0 * S) + logit.shape[0], int(cx0 * S) : int(cx0 * S) + logit.shape[1]] = logit
        # nothing outside the authored box
        bx = np.zeros_like(full, bool)
        bx[int(y0 * S) : int(y1 * S), int(x0 * S) : int(x1 * S)] = True
        full[~bx] = -20.0
        out[oid] = full
    return out


def refine(img: np.ndarray, logit: np.ndarray, band: int) -> np.ndarray:
    """GrabCut in a band around the SAM edge at full resolution; returns a soft alpha (0..1)."""
    hard = (logit > 0).astype(np.uint8)
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(hard)
    if n > 1:
        keep = 1 + np.argsort(-stats[1:, cv2.CC_STAT_AREA])
        big = stats[keep[0], cv2.CC_STAT_AREA]
        hard = np.isin(lbl, [i for i in keep if stats[i, cv2.CC_STAT_AREA] > 0.004 * big]).astype(np.uint8)
    ys, xs = np.nonzero(hard)
    pad = band * 3
    y0, y1 = max(0, ys.min() - pad), min(img.shape[0], ys.max() + pad)
    x0, x1 = max(0, xs.min() - pad), min(img.shape[1], xs.max() + pad)
    sub = img[y0:y1, x0:x1]
    h = hard[y0:y1, x0:x1]
    k = np.ones((2 * band + 1, 2 * band + 1), np.uint8)
    sure_fg = cv2.erode(h, k)
    sure_bg = 1 - cv2.dilate(h, k)
    gc = np.full(h.shape, cv2.GC_PR_BGD, np.uint8)
    gc[h > 0] = cv2.GC_PR_FGD
    gc[sure_fg > 0] = cv2.GC_FGD
    gc[sure_bg > 0] = cv2.GC_BGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(sub, gc, None, bgd, fgd, 4, cv2.GC_INIT_WITH_MASK)
    m = ((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD)).astype(np.uint8)
    # fill pinholes, keep the silhouette's own components
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(m)
    big = max(cv2.contourArea(c) for c in cnts)
    for c in cnts:
        if cv2.contourArea(c) > 0.004 * big:
            cv2.drawContours(filled, [c], -1, 1, -1)
    soft = cv2.GaussianBlur(filled.astype(np.float32), (0, 0), 0.7)
    out = np.zeros(img.shape[:2], np.float32)
    out[y0:y1, x0:x1] = soft
    return out


def main() -> None:
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only"):
            only = a.split("=", 1)[1].split(",")
    ids = [i for i in PROMPTS if only is None or i in only]
    img = load_hd()
    MASKS.mkdir(parents=True, exist_ok=True)
    logits = sam_masks(ids, img)
    bands = {"chandelier": 3, "slippers": 3, "clogs": 4, "mirror": 4}
    for oid in ids:
        alpha = refine(img, logits[oid], bands.get(oid, 7))
        cv2.imwrite(str(MASKS / f"{oid}.png"), np.clip(alpha * 255, 0, 255).astype(np.uint8))
        print(f"  mask {oid}: {float((alpha > 0.5).mean()):.4f} of frame")
    if "--preview" in sys.argv:
        prev = Path(__file__).resolve().parents[2] / ".cache-crops"
        prev.mkdir(exist_ok=True)
        small = cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA).astype(np.float32)
        colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 0, 255), (255, 255, 0), (0, 128, 255), (255, 128, 0)]
        for i, oid in enumerate(PROMPTS):
            p = MASKS / f"{oid}.png"
            if not p.exists():
                continue
            a = cv2.resize(cv2.imread(str(p), cv2.IMREAD_GRAYSCALE), (W // 2, H // 2), interpolation=cv2.INTER_AREA) / 255.0
            small = small * (1 - 0.45 * a[..., None]) + np.array(colors[i % len(colors)], np.float32) * 0.45 * a[..., None]
            edge = cv2.Canny((a > 0.5).astype(np.uint8) * 255, 50, 150) > 0
            small[edge] = colors[i % len(colors)]
        cv2.imwrite(str(prev / "arn_masks.jpg"), small.astype(np.uint8))


if __name__ == "__main__":
    main()
