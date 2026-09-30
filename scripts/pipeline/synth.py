"""Gap-free texture completion for baked surfaces.

A surface's texels the painter never saw are rebuilt, not blurred:

    texture = tone + detail

- tone: the painted light (low frequencies) extrapolated smoothly by pull-push, so light
  falloff and colour carry on across the unseen area without seams;
- detail: real painted grain (craquelure, wood grain, plaster, weave) quilted from the same
  surface in overlapping patches chosen to agree with their already-filled neighbours. For
  boards and joists the source column is locked to the same board phase, so seams run on
  straight and unbroken.
"""

from __future__ import annotations

import cv2
import numpy as np


def pull_push(img: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """Fill where weight == 0 with a smooth membrane from the weighted pyramid (pulled to 1x1)."""
    img = img.astype(np.float32)
    w = weight.astype(np.float32)
    if img.ndim == 2:
        img = img[..., None]
    levels = [(img * w[..., None], w)]
    while max(levels[-1][1].shape) > 1:
        c, cw = levels[-1]
        h2, w2 = (c.shape[0] + 1) // 2, (c.shape[1] + 1) // 2
        c2 = cv2.resize(c, (w2, h2), interpolation=cv2.INTER_AREA)
        if c2.ndim == 2:
            c2 = c2[..., None]
        cw2 = cv2.resize(cw, (w2, h2), interpolation=cv2.INTER_AREA)
        levels.append((c2, cw2))
    c, cw = levels[-1]
    est = c / np.maximum(cw[..., None], 1e-6)
    if (cw <= 1e-6).all():
        est[:] = 0
    for c, cw in reversed(levels[:-1]):
        up = cv2.resize(est, (c.shape[1], c.shape[0]), interpolation=cv2.INTER_LINEAR)
        if up.ndim == 2:
            up = up[..., None]
        a = np.clip(cw, 0, 1)[..., None]
        own = c / np.maximum(cw[..., None], 1e-6)
        est = own * a + up * (1 - a)
    return est if est.shape[-1] > 1 else est[..., 0]


def tone_field(img: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Low-frequency light of the painted texels, extrapolated everywhere."""
    v = valid.astype(np.float32)
    k = max(1, int(sigma * 3)) | 1
    num = cv2.GaussianBlur(img.astype(np.float32) * v[..., None], (k, k), sigma)
    den = cv2.GaussianBlur(v, (k, k), sigma)
    known = den > 0.25
    local = num / np.maximum(den[..., None], 1e-6)
    filled = pull_push(local, known.astype(np.float32))
    # soften the membrane where it was extrapolated; keep the painted light exact elsewhere
    smooth = cv2.GaussianBlur(filled, (k, k), sigma)
    a = np.clip(den / 0.6, 0, 1)[..., None]
    return local * a + smooth * (1 - a) if known.any() else smooth


def clean_mask(img: np.ndarray, valid: np.ndarray, texel_m: float, max_de: float = 24.0, dark: float = 22.0) -> np.ndarray:
    """Painted texels that are plainly the surface's own material: near its median colour, not in
    a deep shadow, away from strong edges (figure halos, props) - safe to copy and to light from."""
    if not valid.any():
        return valid
    u8 = np.clip(img, 0, 255).astype(np.uint8)
    s = max(1.0, 0.012 / texel_m)
    lab = cv2.cvtColor(cv2.GaussianBlur(u8, (0, 0), s), cv2.COLOR_BGR2LAB).astype(np.float32)
    med = np.median(lab[valid], axis=0)
    # colour judged on chroma only: the painted light may brighten or dim the material freely
    dc = np.hypot(lab[..., 1] - med[1], lab[..., 2] - med[2])
    # a shadow is darker than the material's light around it, not than a global median
    v = valid.astype(np.float32)
    big = max(3.0, 0.25 / texel_m)
    kb = int(big * 3) | 1
    local_l = cv2.GaussianBlur(lab[..., 0] * v, (kb, kb), big) / np.maximum(cv2.GaussianBlur(v, (kb, kb), big), 1e-3)
    ok = valid & (dc < max_de * 0.75) & (lab[..., 0] > local_l - dark)
    g = cv2.GaussianBlur(lab[..., 0], (0, 0), max(1.0, 0.006 / texel_m))
    mag = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    if ok.sum() > 100:
        thr = np.percentile(mag[ok], 96)
        edge = cv2.dilate((mag > thr * 1.6).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        ok &= ~edge
    r = max(1, int(round(0.01 / texel_m)))
    ok = cv2.erode(ok.astype(np.uint8), np.ones((2 * r + 1, 2 * r + 1), np.uint8)) > 0
    return ok if ok.sum() > 0.05 * valid.sum() else valid


def _integral_full(valid: np.ndarray, ph: int, pw: int) -> np.ndarray:
    """Top-left corners (y, x) whose ph x pw window is entirely valid."""
    ii = cv2.integral(valid.astype(np.uint8))
    h, w = valid.shape
    if h < ph or w < pw:
        return np.zeros((0, 2), int)
    s = ii[ph:, pw:] - ii[:-ph, pw:] - ii[ph:, :-pw] + ii[:-ph, :-pw]
    ys, xs = np.nonzero(s[: h - ph + 1, : w - pw + 1] >= ph * pw)
    return np.stack([ys, xs], 1)


def quilt(
    detail: np.ndarray,
    known: np.ndarray,
    target: np.ndarray,
    src_detail: np.ndarray,
    src_valid: np.ndarray,
    patch: int,
    overlap: int,
    rng: np.random.Generator,
    candidates: int = 40,
    phase_x: int | None = None,
    phase_y: int | None = None,
    lock_x: bool = False,
    lock_y: bool = False,
) -> np.ndarray:
    """Fill `target` texels of `detail` with patches of `src_detail`.

    phase_x / phase_y: pattern period (texels) the source offset must respect along that axis.
    lock_x / lock_y: source must come from the same column (row) phase - boards stay aligned.
    """
    out = detail.astype(np.float32).copy()
    filled = known.copy()
    h, w = target.shape
    corners = _integral_full(src_valid, patch, patch)
    # a thin source still gives real grain: shrink the patch until it fits
    while len(corners) < 8 and patch > 16:
        patch = max(16, int(patch * 0.7))
        overlap = max(4, min(overlap, patch // 3))
        corners = _integral_full(src_valid, patch, patch)
    if len(corners) == 0:
        return out
    ph, pw = patch, patch
    step = patch - overlap
    if len(corners) > 400_000:
        corners = corners[rng.choice(len(corners), 400_000, replace=False)]
    sh, sw = src_detail.shape[:2]
    groups: dict[int, np.ndarray] = {}
    lock_axis, lock_period = None, None
    if lock_x:
        lock_axis, lock_period = 1, phase_x or 1
    elif lock_y:
        lock_axis, lock_period = 0, phase_y or 1
    if lock_axis is not None and lock_period > 1:
        res = corners[:, lock_axis] % lock_period
        order = np.argsort(res, kind="stable")
        res_sorted = res[order]
        bounds = np.searchsorted(res_sorted, np.arange(lock_period + 1))
        for r in range(lock_period):
            groups[r] = corners[order[bounds[r] : bounds[r + 1]]]
    tgt_rows = np.nonzero(target.any(axis=1))[0]
    tgt_cols = np.nonzero(target.any(axis=0))[0]
    if len(tgt_rows) == 0:
        return out
    y_start = max(0, tgt_rows.min() - overlap)
    x_start = max(0, tgt_cols.min() - overlap)
    ys = list(range(y_start, max(y_start + 1, tgt_rows.max() + 1), step))
    xs = list(range(x_start, max(x_start + 1, tgt_cols.max() + 1), step))
    ti = cv2.integral(target.astype(np.uint8))
    for y in ys:
        y = min(y, h - ph) if h >= ph else 0
        for x in xs:
            x = min(x, w - pw) if w >= pw else 0
            y1, x1 = min(h, y + ph), min(w, x + pw)
            if ti[y1, x1] - ti[y, x1] - ti[y1, x] + ti[y, x] == 0:
                continue
            bh, bw = y1 - y, x1 - x
            win_f = filled[y:y1, x:x1]
            win = out[y:y1, x:x1]
            # candidate sources
            pool = corners
            if groups:
                want = (x if lock_axis == 1 else y) % lock_period
                # nearest residue class that has sources (a texel or two of phase slip is invisible)
                for dr in (0, 1, -1, 2, -2, 3, -3):
                    g = groups.get((want + dr) % lock_period)
                    if g is not None and len(g):
                        pool = g
                        break
            elif lock_axis is not None:
                coord = min(x, sw - pw) if lock_axis == 1 else min(y, sh - ph)
                near = np.abs(corners[:, lock_axis] - coord) <= 2
                if near.any():
                    pool = corners[near]
            pick = pool[rng.integers(0, len(pool), min(candidates, len(pool)))]
            best, best_err = None, np.inf
            m = win_f.astype(np.float32)[..., None]
            msum = float(m.sum())
            for cy, cx in pick:
                cand = src_detail[cy : cy + bh, cx : cx + bw]
                if cand.shape[:2] != (bh, bw):
                    continue
                err = float((((cand - win) ** 2) * m).sum()) / max(msum, 1.0) if msum > 0 else rng.random()
                if err < best_err:
                    best, best_err = cand, err
            if best is None:
                continue
            a = _seam_alpha(best, win, win_f, overlap)[..., None]
            tmask = target[y:y1, x:x1][..., None]
            blended = win * (1 - a) + best * a
            win[:] = np.where(tmask, blended, win)
            filled[y:y1, x:x1] |= target[y:y1, x:x1]
    return out


def _dp_path(err: np.ndarray) -> np.ndarray:
    """Minimum-cost top-to-bottom path through err (rows x cols); returns a column per row."""
    h, w = err.shape
    M = err.astype(np.float64).copy()
    back = np.zeros((h, w), np.int8)
    for i in range(1, h):
        prev = M[i - 1]
        left = np.r_[np.inf, prev[:-1]]
        right = np.r_[prev[1:], np.inf]
        stack = np.stack([left, prev, right])
        k = np.argmin(stack, axis=0)
        M[i] += stack[k, np.arange(w)]
        back[i] = k - 1
    path = np.zeros(h, int)
    path[-1] = int(np.argmin(M[-1]))
    for i in range(h - 1, 0, -1):
        path[i - 1] = np.clip(path[i] + back[i, path[i]], 0, w - 1)
    return path


def _seam_alpha(cand: np.ndarray, win: np.ndarray, have: np.ndarray, ov: int) -> np.ndarray:
    """Where the new patch takes over: beyond a minimum-error cut through the left and top overlaps."""
    bh, bw = have.shape
    take = np.ones((bh, bw), bool)
    e = ((cand - win) ** 2).sum(axis=2) * have
    if ov < bw and have[:, :ov].any():
        p = _dp_path(e[:, :ov])
        take &= np.arange(bw)[None, :] > p[:, None]
    if ov < bh and have[:ov].any():
        p = _dp_path(e[:ov].T)
        take &= np.arange(bh)[:, None] > p[None, :]
    a = cv2.GaussianBlur(take.astype(np.float32), (0, 0), 1.0)
    return np.where(have, a, 1.0)


def estimate_period(detail_gray: np.ndarray, valid: np.ndarray, axis: int, lo: int, hi: int) -> int | None:
    """Dominant repeat along an axis from masked autocorrelation."""
    g = detail_gray.astype(np.float32)
    best, best_l = 0.12, None
    n = g.shape[axis]
    for lag in range(max(2, lo), min(hi, n // 2)):
        if axis == 1:
            a, b, va, vb = g[:, :-lag], g[:, lag:], valid[:, :-lag], valid[:, lag:]
        else:
            a, b, va, vb = g[:-lag], g[lag:], valid[:-lag], valid[lag:]
        m = va & vb
        if m.sum() < 2000:
            continue
        x, y = a[m], b[m]
        x = x - x.mean()
        y = y - y.mean()
        c = float((x * y).mean() / (x.std() * y.std() + 1e-6))
        if c > best:
            best, best_l = c, lag
    return best_l


def complete(
    img: np.ndarray,
    valid: np.ndarray,
    texel_m: float,
    *,
    tone_sigma_m: float = 0.09,
    patch_m: float = 0.16,
    grain: str = "iso",  # iso | cols | rows
    period_m: float | None = None,
    donor: tuple[np.ndarray, np.ndarray] | None = None,
    tone: np.ndarray | None = None,
    seed: int = 0,
    target: np.ndarray | None = None,
    min_own: float = 6.0,
) -> np.ndarray:
    """Rebuild the `target` texels (default: every texel with valid == False).

    img float BGR, valid bool, texel_m metres per texel.
    donor: (detail, valid) to quilt from when the surface has too little of its own paint.
    tone: explicit tone image (h, w, 3) instead of extrapolating the surface's own light.
    grain: "cols" keeps source columns in board phase (boards along t), "rows" along s.
    """
    img = img.astype(np.float32)
    if target is None:
        target = ~valid
    if not target.any():
        return img
    sigma = max(2.0, tone_sigma_m / texel_m)
    clean = clean_mask(img, valid, texel_m)
    own_tone = None
    if valid.any():
        # light from the clean paint; right at the painted edge, the edge's own light (shadows
        # included) fades in so rebuilt texels continue exactly what they touch
        t_clean = tone_field(img, clean, sigma)
        t_all = tone_field(img, valid, max(2.0, 0.02 / texel_m))
        dist = cv2.distanceTransform((~valid).astype(np.uint8), cv2.DIST_L2, 5) * texel_m
        near = np.exp(-dist / 0.035)[..., None]
        own_tone = t_clean + (t_all - t_clean) * near
    T = tone if tone is not None else own_tone
    if T is None:
        raise ValueError("surface has no paint and no explicit tone")
    detail = np.zeros_like(img)
    if valid.any():
        detail[valid] = (img - tone_field(img, valid, sigma))[valid]
    patch = int(np.clip(round(patch_m / texel_m), 24, 256))
    enough = len(_integral_full(clean, patch, patch)) > min_own * 40
    if enough or donor is None:
        src_d, src_v = detail, clean
    else:
        src_d, src_v = donor
    overlap = max(8, patch // 3)
    rng = np.random.default_rng(seed)
    period = int(round(period_m / texel_m)) if period_m else None
    if grain == "cols":
        synth = quilt(detail, valid, target, src_d, src_v, patch, overlap, rng, phase_x=period, lock_x=True)
    elif grain == "rows":
        synth = quilt(detail, valid, target, src_d, src_v, patch, overlap, rng, phase_y=period, lock_y=True)
    else:
        synth = quilt(detail, valid, target, src_d, src_v, patch, overlap, rng)
    # painted texels stay exact; the quilt already feathers its patches into their neighbours
    out = np.where(target[..., None], T + synth, img)
    return np.clip(out, 0, 255)


def high_pass(img: np.ndarray, valid: np.ndarray, texel_m: float, tone_sigma_m: float = 0.09) -> np.ndarray:
    sigma = max(2.0, tone_sigma_m / texel_m)
    return img.astype(np.float32) - tone_field(img, valid, sigma)


def donor_detail(img: np.ndarray, valid: np.ndarray, texel_m: float) -> tuple[np.ndarray, np.ndarray]:
    """Detail layer and its clean-source mask, for lending grain to another surface."""
    clean = clean_mask(img.astype(np.float32), valid, texel_m)
    return high_pass(img, valid, texel_m), clean
