import json
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "data" / "paintings" / "school-of-athens" / "manifest.json"
m = json.loads(path.read_text(encoding="utf-8"))

# UV is fraction of painting (0,0 top-left → 1,1 bottom-right), authored against the fresco.
# World XYZ is derived at runtime from promptPoint via uvPlacement.

def ent(
    id_: str,
    label: str,
    u: float,
    v: float,
    *,
    importance: int = 7,
    evidence: str = "strongly_inferred",
    confidence: float = 0.85,
    type_: str = "figure",
    depth: int = 1,
) -> dict:
    return {
        "id": id_,
        "type": type_,
        "label": label,
        "promptPoint": [round(u, 3), round(v, 3)],
        # Placeholder; runtime uses promptPoint + composition
        "position": [0, 0, 0],
        "scale": [1, 1, 1],
        "depth": depth,
        "importance": importance,
        "interactive": True,
        "confidence": confidence,
        "evidence": evidence,
    }


m["entities"] = [
    # Center pair on the top landing
    ent("plato", "Plato", 0.468, 0.385, importance=10, evidence="observed", confidence=0.95),
    ent("aristotle", "Aristotle", 0.532, 0.385, importance=10, evidence="observed", confidence=0.95),
    ent("timaeus-book", "Timaeus", 0.455, 0.445, importance=6, type_="object", evidence="observed", confidence=0.9),
    ent("ethics-book", "Ethics", 0.545, 0.445, importance=6, type_="object", evidence="observed", confidence=0.9),
    # Left mid — Socrates cluster
    ent("socrates", "Socrates", 0.275, 0.455, importance=9),
    # Lower left — mathematicians
    ent("pythagoras", "Pythagoras", 0.205, 0.705, importance=9, depth=0),
    ent("averroes", "Averroes", 0.155, 0.575, importance=7),
    # Foreground block — Michelangelo / Heraclitus
    ent("heraclitus", "Heraclitus", 0.385, 0.74, importance=9, depth=0),
    # Steps under the central pair
    ent("diogenes", "Diogenes", 0.555, 0.615, importance=8, depth=0),
    # Lower right geometry school
    ent("euclid", "Euclid", 0.715, 0.77, importance=9, depth=0),
    ent("ptolemy", "Ptolemy", 0.78, 0.545, importance=8),
    ent("zoroaster", "Zoroaster", 0.825, 0.50, importance=7),
    ent("raphael-self", "Raphael", 0.905, 0.575, importance=8, evidence="strongly_inferred", confidence=0.9, depth=0),
    # Niches & architecture
    ent("apollo-statue", "Apollo", 0.225, 0.235, importance=7, type_="architecture", depth=3),
    ent("athena-statue", "Athena", 0.775, 0.235, importance=7, type_="architecture", depth=3),
    ent(
        "vault-perspective",
        "The vault",
        0.50,
        0.14,
        importance=8,
        type_="architecture",
        depth=4,
        evidence="observed",
        confidence=0.95,
    ),
    ent(
        "marble-steps",
        "The steps",
        0.50,
        0.84,
        importance=5,
        type_="architecture",
        depth=0,
        evidence="observed",
        confidence=0.95,
    ),
]

masks = {
    "plato": "masks/entity-plato.png",
    "aristotle": "masks/entity-aristotle.png",
    "raphael-self": "masks/entity-raphael-self.png",
}
for e in m["entities"]:
    if e["id"] in masks:
        e["mask"] = masks[e["id"]]

path.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
print(f"entities: {len(m['entities'])}")
