"""Correct curiosity promptPoints on 2D painting manifests (UV: top-left origin)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path('public/data/paintings')

# paintingId -> { entityId: [u, v] }
CORRECTIONS: dict[str, dict[str, list[float]]] = {
    'birth-of-venus': {
        'venus': [0.52, 0.36],
        'zephyr': [0.14, 0.36],
        'hora': [0.84, 0.42],
        'shell': [0.52, 0.78],
        'roses': [0.34, 0.26],
        'shore': [0.78, 0.78],
        'myrtle': [0.92, 0.38],  # myrtle trees behind Hora, not her gown
        'sea': [0.28, 0.62],
    },
    'primavera': {
        'venus-center': [0.50, 0.38],
        'mercury': [0.08, 0.40],
        'three-graces': [0.28, 0.40],
        'flora': [0.70, 0.42],
        'chloris': [0.82, 0.48],
        'zephyrus': [0.93, 0.38],
        'cupid': [0.50, 0.14],
        'orange-grove': [0.55, 0.10],
        'flowered-meadow': [0.50, 0.88],
    },
    'mona-lisa': {
        'lisa': [0.48, 0.27],
        'smile': [0.48, 0.345],
        'hands': [0.48, 0.84],
        'veil': [0.50, 0.16],
        'landscape': [0.14, 0.30],
        'bridge': [0.86, 0.42],
        'chair-arm': [0.18, 0.72],
        'sfumato': [0.34, 0.32],
    },
    'lady-with-an-ermine': {
        'cecilia': [0.48, 0.28],
        'ermine': [0.58, 0.58],
        'gaze': [0.52, 0.26],
        'hand': [0.40, 0.58],
        'necklace': [0.48, 0.46],
        'sleeve': [0.28, 0.48],
        'dark-ground': [0.86, 0.28],
    },
    'night-watch': {
        'cocq': [0.40, 0.48],
        'ruitenburgh': [0.52, 0.46],
        'girl': [0.30, 0.52],
        'drum': [0.92, 0.68],
        'musket': [0.70, 0.52],  # musketeer to the right, not the lieutenant's hat
        'flag': [0.56, 0.18],
        'archway': [0.48, 0.12],
        'dog': [0.80, 0.84],
        'spotlight': [0.42, 0.48],  # Rembrandt's light on the girl / captains
    },
    'las-meninas': {
        'margarita': [0.48, 0.50],
        'velazquez': [0.22, 0.38],
        'menina-left': [0.38, 0.52],
        'menina-right': [0.60, 0.52],
        'mirror': [0.50, 0.26],
        'canvas': [0.10, 0.40],
        'nieto': [0.62, 0.30],
        'dog': [0.64, 0.82],
        'dwarf': [0.72, 0.58],
    },
    'girl-with-a-pearl-earring': {
        'girl': [0.52, 0.45],
        'pearl': [0.63, 0.54],
        'turban': [0.50, 0.22],
        'gaze': [0.50, 0.40],
        'lips': [0.47, 0.51],
        'dark-ground': [0.88, 0.35],
        'jacket': [0.42, 0.78],
    },
    'garden-of-earthly-delights': {
        'eden': [0.08, 0.48],
        'garden': [0.50, 0.48],
        'hell': [0.86, 0.42],
        'fountain': [0.50, 0.22],
        'pool': [0.50, 0.58],
        'strawberry': [0.38, 0.70],
        'owl': [0.17, 0.36],
        'ears-knife': [0.88, 0.72],
        # creation-exterior is invisible on the open triptych — retargeted below as adam-eve
    },
    'ambassadors': {
        'dinteville': [0.22, 0.30],
        'selve': [0.78, 0.28],
        'skull': [0.50, 0.82],
        'celestial-globe': [0.40, 0.28],
        'sundial': [0.50, 0.32],
        'quadrant': [0.58, 0.28],
        'terrestrial-globe': [0.40, 0.52],
        'lute': [0.58, 0.58],
        'flute-case': [0.52, 0.62],
        'hymnal': [0.64, 0.60],
        'arithmetic-book': [0.46, 0.56],
        'crucifix': [0.06, 0.08],  # top-LEFT behind curtain, not right
        'green-curtain': [0.50, 0.10],
        'dagger': [0.28, 0.52],
        'mosaic-floor': [0.50, 0.92],
        'instruments': [0.50, 0.40],
    },
    'wedding-at-cana': {
        'jesus': [0.50, 0.43],
        'mary': [0.45, 0.43],
        'bride-groom': [0.22, 0.42],  # left end of table, not right
        'musicians': [0.50, 0.68],
        'stone-jars': [0.82, 0.84],
        'feast-table': [0.50, 0.48],
        'classic-architecture': [0.62, 0.10],
        'servants': [0.88, 0.70],
        'steward': [0.65, 0.52],
        'balcony-guests': [0.55, 0.20],
        'silver-vessels': [0.58, 0.48],
        'dogs': [0.48, 0.88],
        'columns': [0.10, 0.38],
        'hourglass-time': [0.55, 0.70],
        'veronese-self': [0.48, 0.66],
    },
    'harvesters': {
        'resting-group': [0.55, 0.56],
        'sleeper': [0.62, 0.60],
        'eaters': [0.50, 0.56],
        'pear-tree': [0.52, 0.28],
        'wheat-field': [0.78, 0.48],
        'standing-wheat': [0.20, 0.48],
        'scythes': [0.18, 0.55],
        'path': [0.34, 0.58],
        'distant-workers': [0.42, 0.40],
        'distant-bay': [0.82, 0.20],
        'church-steeple': [0.16, 0.36],
        'haystacks': [0.70, 0.50],
        'birds': [0.62, 0.08],  # sky, not tree canopy
        'lunch': [0.48, 0.60],
        'wagon-track': [0.40, 0.76],
    },
    'last-supper': {
        # already strong; tiny nudges only
        'jesus': [0.50, 0.355],
        'judas': [0.295, 0.48],
        'spilled-salt': [0.315, 0.545],
        'table': [0.50, 0.60],
        'trinity-window': [0.50, 0.24],
        'coffered-ceiling': [0.50, 0.08],
    },
}


def apply_points(manifest: dict, points: dict[str, list[float]]) -> int:
    n = 0
    for ent in manifest.get('entities', []):
        pid = ent.get('id')
        if pid in points:
            ent['promptPoint'] = points[pid]
            n += 1
    return n


def retarget_garden_creation(manifest: dict, facts_doc: dict | list) -> None:
    """Open triptych has no closed-panel Creation grisaille — retarget to Adam & Eve."""
    for ent in manifest.get('entities', []):
        if ent.get('id') == 'creation-exterior':
            ent['id'] = 'adam-eve'
            ent['type'] = 'figure'
            ent['label'] = 'Adam and Eve'
            ent['promptPoint'] = [0.12, 0.78]
            break
    facts = facts_doc['facts'] if isinstance(facts_doc, dict) and 'facts' in facts_doc else facts_doc
    for f in facts:
        if not isinstance(f, dict):
            continue
        if f.get('id') == 'creation-exterior' or f.get('entityId') == 'creation-exterior':
            f['id'] = 'adam-eve'
            f['entityId'] = 'adam-eve'
            f['title'] = 'Adam and Eve in Eden'
            f['body'] = (
                'In the left panel God presents Eve to Adam in a verdant Paradise filled with '
                'strange animals and a pink fountain — Bosch’s vision of creation before the Fall.'
            )


def main() -> None:
    for painting_id, points in CORRECTIONS.items():
        mpath = ROOT / painting_id / 'manifest.json'
        if not mpath.exists():
            print('missing', mpath)
            continue
        manifest = json.loads(mpath.read_text(encoding='utf-8'))
        n = apply_points(manifest, points)

        if painting_id == 'garden-of-earthly-delights':
            fpath = ROOT / painting_id / 'facts.json'
            facts_doc = json.loads(fpath.read_text(encoding='utf-8'))
            retarget_garden_creation(manifest, facts_doc)
            fpath.write_text(json.dumps(facts_doc, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            n += 1

        mpath.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(f'{painting_id}: updated {n} points')


if __name__ == '__main__':
    main()
