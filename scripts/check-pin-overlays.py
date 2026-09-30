from PIL import Image, ImageDraw, ImageFont
import json
from pathlib import Path

root = Path('public/data/paintings')
out = Path('.cache-crops/pin-check')
out.mkdir(parents=True, exist_ok=True)

skip = {'school-of-athens', 'arnolfini-portrait'}
colors = {
    'figure': (255, 80, 60),
    'object': (80, 180, 255),
    'landscape': (80, 220, 120),
    'architecture': (255, 200, 60),
    'animal': (220, 120, 255),
}

try:
    font_sm = ImageFont.truetype('arial.ttf', 12)
except OSError:
    font_sm = ImageFont.load_default()

for d in sorted(root.iterdir()):
    if not d.is_dir() or d.name in skip:
        continue
    mpath = d / 'manifest.json'
    img_path = d / 'painting.jpg'
    if not mpath.exists() or not img_path.exists():
        continue
    m = json.loads(mpath.read_text(encoding='utf-8'))
    im = Image.open(img_path).convert('RGB')
    max_w = 1400
    if im.width > max_w:
        scale = max_w / im.width
        im = im.resize((max_w, int(im.height * scale)), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(im)
    w, h = im.size
    for e in m['entities']:
        pp = e.get('promptPoint')
        if not pp:
            continue
        u, v = pp
        x, y = u * w, v * h
        col = colors.get(e.get('type'), (255, 255, 255))
        r = 8
        draw.ellipse([x - r, y - r, x + r, y + r], outline=col, width=3)
        draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=col)
        label = e['id']
        bbox = draw.textbbox((0, 0), label, font=font_sm)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx, ty = x + 10, y - 8
        draw.rectangle([tx - 2, ty - 1, tx + tw + 2, ty + th + 1], fill=(0, 0, 0))
        draw.text((tx, ty), label, fill=col, font=font_sm)
    out_path = out / f'{d.name}.jpg'
    im.save(out_path, quality=85)
    print('wrote', out_path, 'entities', len(m['entities']))
print('done')
