"""
Compress painting.jpg for web + write gallery thumb.webp beside each pack.

  node-free: python scripts/optimize-paintings.py

- painting.jpg: max edge 1600px, JPEG q=84 (GPU-friendly, still crisp on DPR 1.5)
- thumb.webp: max edge 560px, WebP q=78 (gallery / enter-painting rails)
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image

ROOT = Path('public/data/paintings')
PAINT_MAX = 1600
THUMB_MAX = 560


def fit(im: Image.Image, max_edge: int) -> Image.Image:
    w, h = im.size
    m = max(w, h)
    if m <= max_edge:
        return im
    scale = max_edge / m
    return im.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)


def main() -> None:
    rows: list[tuple[str, int, int, int, int]] = []
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir():
            continue
        src = d / 'painting.jpg'
        if not src.exists():
            continue
        before = src.stat().st_size
        im = Image.open(src).convert('RGB')
        paint = fit(im, PAINT_MAX)
        paint.save(src, format='JPEG', quality=84, optimize=True, progressive=True)
        thumb = fit(im, THUMB_MAX)
        thumb_path = d / 'thumb.webp'
        thumb.save(thumb_path, format='WEBP', quality=78, method=4)
        after = src.stat().st_size
        tw = thumb_path.stat().st_size
        rows.append((d.name, before, after, tw, paint.size[0]))
        print(f'{d.name}: painting {before // 1024}KB -> {after // 1024}KB ({paint.size[0]}x{paint.size[1]}); thumb {tw // 1024}KB')
    total_b = sum(r[1] for r in rows)
    total_a = sum(r[2] for r in rows)
    total_t = sum(r[3] for r in rows)
    print(f'\nAll paintings: {total_b // 1024}KB -> {total_a // 1024}KB; thumbs {total_t // 1024}KB')


if __name__ == '__main__':
    main()
