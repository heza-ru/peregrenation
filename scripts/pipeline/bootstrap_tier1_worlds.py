"""Author starter manifests + facts for remaining tier-1 curated worlds."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PAINTINGS = ROOT / "data" / "paintings"


def planes(ar: float) -> tuple[float, float]:
    if ar >= 1:
        return 16.0, 16.0 / ar
    return 16.0 * ar, 16.0


def entity(
    eid: str,
    label: str,
    uv: tuple[float, float],
    *,
    etype: str = "figure",
    importance: int = 8,
    depth: int = 1,
) -> dict:
    return {
        "id": eid,
        "type": etype,
        "label": label,
        "promptPoint": [uv[0], uv[1]],
        "position": [0, 0, 0],
        "scale": [1, 1, 1],
        "depth": depth,
        "importance": importance,
        "interactive": True,
        "confidence": 0.9,
        "evidence": "observed",
    }


def hero_layer() -> list[dict]:
    return [
        {
            "id": "hero-painting",
            "label": "Painting plane",
            "depthBand": 0,
            "texture": "painting.jpg",
            "z": 0,
            "parallax": 1,
            "opacity": 1,
            "hero": True,
        }
    ]


def floor_arch() -> list[dict]:
    return [
        {
            "id": "floor",
            "type": "plane",
            "position": [0, -2.2, -1.5],
            "rotation": [-1.35, 0, 0],
            "size": [18, 12],
            "opacity": 0.08,
        }
    ]


WORLDS: dict[str, dict] = {
    "last-supper": {
        "sources": {
            "paintingId": "last-supper",
            "image": {
                "file": "painting.jpg",
                "sourceUrl": "https://commons.wikimedia.org/wiki/File:The_Last_Supper_-_Leonardo_Da_Vinci_-_High_Resolution_32x16.jpg",
                "retrievalUrl": "https://commons.wikimedia.org/wiki/Special:FilePath/The_Last_Supper_-_Leonardo_Da_Vinci_-_High_Resolution_32x16.jpg?width=1920",
                "license": "Public domain (work of Leonardo; photographic reproduction)",
                "credit": "Leonardo da Vinci; file from Wikimedia Commons",
                "retrievedAt": "2026-03-30",
            },
            "references": [
                {
                    "id": "santa-maria-grazie",
                    "title": "The Last Supper",
                    "publisher": "Museo del Cenacolo Vinciano",
                    "url": "https://cenacolovinciano.org/en/",
                }
            ],
        },
        "painting": {
            "title": "The Last Supper",
            "artist": "Leonardo da Vinci",
            "date": "1495–1498",
            "medium": "Tempera and oil on plaster",
            "source": "Santa Maria delle Grazie, Milan",
        },
        "composition": {
            "horizon": 0.38,
            "vanishingPoint": [0.5, 0.38],
            "cameraFov": 42,
        },
        "lighting": {
            "ambient": 0.55,
            "directional": [0.2, 0.8, 0.4],
            "directionalIntensity": 0.7,
            "color": "#f0e6d2",
        },
        "palette": ["#2a2218", "#c9a24a", "#efe6d6", "#5a4a34"],
        "entities": [
            entity("jesus", "Jesus", (0.5, 0.42), importance=10),
            entity("john", "John", (0.43, 0.44), importance=9),
            entity("judas", "Judas", (0.39, 0.52), importance=9),
            entity("peter", "Peter", (0.36, 0.46), importance=8),
            entity("thomas", "Thomas", (0.55, 0.4), importance=7),
            entity("james-major", "James the Greater", (0.58, 0.42), importance=7),
            entity("table", "The table", (0.5, 0.62), etype="object", importance=8, depth=0),
            entity("trinity-window", "Central window", (0.5, 0.22), etype="architecture", importance=7, depth=3),
            entity("spilled-salt", "Overturned salt", (0.4, 0.58), etype="object", importance=6, depth=0),
        ],
        "facts": [
            {
                "id": "painting-overview",
                "title": "A supper frozen mid-shock",
                "body": "Leonardo painted The Last Supper on the north wall of the Dominican refectory of Santa Maria delle Grazie in Milan (c. 1495–1498). Christ has just said that one of the Twelve will betray him; the apostles erupt in clusters of gesture while the room’s perspective locks every line toward his calm center.",
                "category": "painting",
                "confidence": "documented",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
            {
                "id": "jesus-center",
                "entityId": "jesus",
                "title": "Christ as vanishing point",
                "body": "Jesus sits alone at the table’s center, head framed by the brightest window. Leonardo makes his body the architectural keystone: arms open toward bread and wine, face resigned rather than theatrical. Every orthogonals of the room converge near him, so walking the hall still feels pulled to this calm axis.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
            {
                "id": "john-lean",
                "entityId": "john",
                "title": "The beloved disciple",
                "body": "The youthful figure leaning away from Christ is traditionally identified as John. Leonardo softens him into almost feminine gentleness — a foil to Peter’s forceful reach and Judas’s shadowed isolation beside them.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
            {
                "id": "judas-purse",
                "entityId": "judas",
                "title": "Judas in the shadow",
                "body": "Judas recoils into silhouette, clutching a small purse and reaching toward the same dish as Christ. Leonardo refuses a halo-or-no-halo cheat code: betrayal is told through light, posture, and the salt spilled near his elbow.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
            {
                "id": "peter-knife",
                "entityId": "peter",
                "title": "Peter’s restless blade",
                "body": "Peter leans in aggressively, a knife already in hand — foreshadowing the Garden of Gethsemane. Leonardo packs impulsive loyalty into one diagonal thrust toward the calm center.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
            {
                "id": "thomas-finger",
                "entityId": "thomas",
                "title": "Thomas points upward",
                "body": "Thomas raises a finger as if demanding proof — a gesture that later readers link to his doubt after the Resurrection. Leonardo seeds the next chapter of the story inside this single shocked meal.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
            {
                "id": "james-recoil",
                "entityId": "james-major",
                "title": "James flings his arms",
                "body": "James the Greater opens both arms in disbelief, a wide counter-rhythm to Christ’s quieter gesture. The apostles read as four groups of three — keyed to speech, not static lineup.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
            {
                "id": "table-stage",
                "entityId": "table",
                "title": "A refectory table as stage",
                "body": "The white cloth, plates, and glasses sit at dining height inside a real monastery dining hall. Monks eating beneath the mural would have faced the painted meal as a daily mirror of the Eucharist.",
                "category": "object",
                "confidence": "documented",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
            {
                "id": "trinity-window",
                "entityId": "trinity-window",
                "title": "Three windows, one light",
                "body": "Behind Christ, three openings pour daylight into the hall. The center window doubles as a natural halo, while the recession of coffered ceiling and tapestries deepens the illusion of a room beyond the wall.",
                "category": "architecture",
                "confidence": "scholarly_interpretation",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
            {
                "id": "spilled-salt",
                "entityId": "spilled-salt",
                "title": "Salt tipped toward treachery",
                "body": "Near Judas, salt appears overturned — a detail viewers have long read as a bad omen. Whether or not Leonardo meant folklore, the cluttered table turns betrayal into something you could almost brush with your sleeve.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://cenacolovinciano.org/en/"],
            },
        ],
    },
    "arnolfini-portrait": {
        "sources": {
            "paintingId": "arnolfini-portrait",
            "image": {
                "file": "painting.jpg",
                "sourceUrl": "https://commons.wikimedia.org/wiki/File:Van_Eyck_-_Arnolfini_Portrait.jpg",
                "retrievalUrl": "https://commons.wikimedia.org/wiki/Special:FilePath/Van_Eyck_-_Arnolfini_Portrait.jpg?width=1920",
                "license": "Public domain (work of Jan van Eyck; photographic reproduction)",
                "credit": "Jan van Eyck; file from Wikimedia Commons",
                "retrievedAt": "2026-03-30",
            },
            "references": [
                {
                    "id": "ng-arnolfini",
                    "title": "The Arnolfini Portrait",
                    "publisher": "The National Gallery, London",
                    "url": "https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait",
                }
            ],
        },
        "painting": {
            "title": "The Arnolfini Portrait",
            "artist": "Jan van Eyck",
            "date": "1434",
            "medium": "Oil on oak",
            "source": "The National Gallery, London",
        },
        "composition": {
            "horizon": 0.55,
            "vanishingPoint": [0.5, 0.52],
            "cameraFov": 40,
        },
        "lighting": {
            "ambient": 0.5,
            "directional": [0.6, 0.7, 0.3],
            "directionalIntensity": 0.85,
            "color": "#f4ead8",
        },
        "palette": ["#1a1510", "#c9a24a", "#6b3a2a", "#d8c8a8"],
        "entities": [
            entity("giovanni", "Giovanni Arnolfini", (0.3, 0.42), importance=10),
            entity("bride", "Costanza / Giovanna", (0.58, 0.45), importance=10),
            entity("joined-hands", "Joined hands", (0.42, 0.5), etype="gesture", importance=9),
            entity("mirror", "Convex mirror", (0.5, 0.52), etype="object", importance=10, depth=2),
            entity("chandelier", "Brass chandelier", (0.48, 0.14), etype="object", importance=8, depth=2),
            entity("dog", "The dog", (0.48, 0.88), etype="animal", importance=7, depth=0),
            entity("clogs", "Discarded clogs", (0.22, 0.82), etype="object", importance=6, depth=0),
            entity("oranges", "Oranges on the sill", (0.16, 0.55), etype="object", importance=6, depth=1),
            entity("bed", "The red bed", (0.8, 0.55), etype="object", importance=7, depth=1),
            entity("signature", "Van Eyck was here", (0.5, 0.4), etype="inscription", importance=8, depth=2),
        ],
        "facts": [
            {
                "id": "painting-overview",
                "title": "A room full of witnesses",
                "body": "Jan van Eyck signed and dated this panel 1434. The National Gallery identifies the man as a member of the Arnolfini merchant family; the woman’s exact identity is debated. What is certain is the denseness of the chamber: every surface seems ready to testify.",
                "category": "painting",
                "confidence": "documented",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "giovanni",
                "entityId": "giovanni",
                "title": "The merchant in black",
                "body": "The man raises his right hand in a formal greeting or oath while his left takes the woman’s hand. Tall hat, fur-lined robe, and calm stare mark wealth and civic standing in Bruges’s Italian trading community.",
                "category": "figure",
                "confidence": "documented",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "bride",
                "entityId": "bride",
                "title": "Green gown, gathered fabric",
                "body": "The woman wears a lush green dress with fashionably gathered folds at the belly — a style of the period, not proof of pregnancy. Her gaze meets the viewer while her free hand lifts the heavy cloth.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "joined-hands",
                "entityId": "joined-hands",
                "title": "Hands as contract",
                "body": "Their joined hands sit at the painting’s rhetorical center. Scholars have read the gesture as marriage, betrothal, or a legal pledge — van Eyck leaves the precise ceremony ambiguous while making the bond unmistakable.",
                "category": "gesture",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "mirror",
                "entityId": "mirror",
                "title": "The convex witness",
                "body": "The round mirror on the back wall reflects the couple from behind and two additional figures in the doorway — one likely the painter. Around its frame, tiny Passion scenes turn the furniture into theology.",
                "category": "object",
                "confidence": "documented",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "chandelier",
                "entityId": "chandelier",
                "title": "One candle lit",
                "body": "A brass chandelier hangs with a single burning candle. Interpreters link it to the eye of God, marital fidelity, or simply the costly lighting of a prosperous house — van Eyck invites all three readings at once.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "dog",
                "entityId": "dog",
                "title": "Fidelity at their feet",
                "body": "The small dog between the couple is often read as loyalty (fides). Van Eyck paints its fur with the same microscopic care as the chandelier’s metal — domestic life elevated to spectacle.",
                "category": "animal",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "clogs",
                "entityId": "clogs",
                "title": "Shoes left at the threshold",
                "body": "Wooden pattens lie discarded in the foreground. Removing outdoor shoes could signal sacred ground, intimacy, or simply the etiquette of a fine interior — another object that behaves like a clue.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "oranges",
                "entityId": "oranges",
                "title": "Costly fruit by the window",
                "body": "Oranges rest on the chest beneath the window — luxury imports in northern Europe. They perfume the room with wealth and, for some viewers, with hints of paradise or fertility.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "bed",
                "entityId": "bed",
                "title": "The red marriage bed",
                "body": "A richly draped bed dominates the right side of the chamber. In fifteenth-century portraits, the bed could mark household status as much as private life — furniture as biography.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
            {
                "id": "signature",
                "entityId": "signature",
                "title": "Johannes de eyck fuit hic",
                "body": "Above the mirror van Eyck wrote that he “was here,” 1434 — less a quiet signature than a notarized presence. The painter becomes another witness inside the room you are stepping into.",
                "category": "inscription",
                "confidence": "documented",
                "sources": ["https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"],
            },
        ],
    },
    "wedding-at-cana": {
        "sources": {
            "paintingId": "wedding-at-cana",
            "image": {
                "file": "painting.jpg",
                "sourceUrl": "https://commons.wikimedia.org/wiki/File:Paolo_Veronese_008.jpg",
                "retrievalUrl": "https://commons.wikimedia.org/wiki/Special:FilePath/Paolo_Veronese_008.jpg?width=1920",
                "license": "Public domain (work of Paolo Veronese; photographic reproduction)",
                "credit": "Paolo Veronese; file from Wikimedia Commons",
                "retrievedAt": "2026-03-30",
            },
            "references": [
                {
                    "id": "louvre-cana",
                    "title": "The Wedding Feast at Cana",
                    "publisher": "Musée du Louvre",
                    "url": "https://collections.louvre.fr/en/ark:/53355/cl010066872",
                }
            ],
        },
        "painting": {
            "title": "The Wedding at Cana",
            "artist": "Paolo Veronese",
            "date": "1563",
            "medium": "Oil on canvas",
            "source": "Musée du Louvre, Paris",
        },
        "composition": {
            "horizon": 0.42,
            "vanishingPoint": [0.5, 0.4],
            "cameraFov": 48,
        },
        "lighting": {
            "ambient": 0.58,
            "directional": [0.3, 0.9, 0.2],
            "directionalIntensity": 0.75,
            "color": "#f2e8d6",
        },
        "palette": ["#1c1812", "#c9a24a", "#8a2f2f", "#d6c4a0"],
        "entities": [
            entity("jesus", "Jesus", (0.48, 0.4), importance=10),
            entity("mary", "Mary", (0.42, 0.4), importance=9),
            entity("bride-groom", "Bride and groom", (0.62, 0.38), importance=8),
            entity("musicians", "The musicians", (0.5, 0.55), importance=9),
            entity("stone-jars", "Stone water jars", (0.32, 0.78), etype="object", importance=9, depth=0),
            entity("feast-table", "Banquet table", (0.5, 0.48), etype="object", importance=8, depth=1),
            entity("classic-architecture", "Classical loggia", (0.5, 0.18), etype="architecture", importance=7, depth=4),
            entity("servants", "Servants pouring", (0.28, 0.65), importance=7, depth=0),
        ],
        "facts": [
            {
                "id": "painting-overview",
                "title": "A miracle the size of a wall",
                "body": "Veronese painted The Wedding Feast at Cana for the refectory of San Giorgio Maggiore in Venice (1563). Now in the Louvre, the canvas is immense — a Venetian banquet dressed as the Gospel miracle where water becomes wine.",
                "category": "painting",
                "confidence": "documented",
                "sources": ["https://collections.louvre.fr/en/ark:/53355/cl010066872"],
            },
            {
                "id": "jesus",
                "entityId": "jesus",
                "title": "Christ among the guests",
                "body": "Jesus sits near the center of the long table, marked more by composure than by theatrical glow. The miracle unfolds as social theater: divinity visiting a wedding that looks startlingly like Venice at festival pitch.",
                "category": "figure",
                "confidence": "documented",
                "sources": ["https://collections.louvre.fr/en/ark:/53355/cl010066872"],
            },
            {
                "id": "mary",
                "entityId": "mary",
                "title": "Mary prompts the miracle",
                "body": "Mary, seated near Christ, is the quiet catalyst of the story — she notices the wine has failed. Veronese keeps her dignified inside a crowd that otherwise threatens to swallow the narrative whole.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://collections.louvre.fr/en/ark:/53355/cl010066872"],
            },
            {
                "id": "bride-groom",
                "entityId": "bride-groom",
                "title": "The bridal pair",
                "body": "The bride and groom occupy places of honor along the feast. Their celebration is the pretext for the first public sign in John’s Gospel — hospitality stretched until heaven intervenes.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://collections.louvre.fr/en/ark:/53355/cl010066872"],
            },
            {
                "id": "musicians",
                "entityId": "musicians",
                "title": "Veronese among the strings",
                "body": "In the foreground musicians play: tradition identifies Veronese himself among them, with fellow Venetian painters as companions. The banquet becomes a self-portrait of art’s city as much as a biblical feast.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://collections.louvre.fr/en/ark:/53355/cl010066872"],
            },
            {
                "id": "stone-jars",
                "entityId": "stone-jars",
                "title": "Jars of new wine",
                "body": "Large stone jars recall the vessels of Jewish purification rites that Christ orders filled with water. Servants tip and pour at the lower edge — the miracle made tangible as logistics.",
                "category": "object",
                "confidence": "documented",
                "sources": ["https://collections.louvre.fr/en/ark:/53355/cl010066872"],
            },
            {
                "id": "feast-table",
                "entityId": "feast-table",
                "title": "Silver, glass, and appetite",
                "body": "The table groans with vessels, fruit, and ruffled linen. Veronese turns Eucharistic overtones into sensory overload — tasting, seeing, and hearing all at once.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://collections.louvre.fr/en/ark:/53355/cl010066872"],
            },
            {
                "id": "classic-architecture",
                "entityId": "classic-architecture",
                "title": "A stage of columns",
                "body": "Classical colonnades and balustrades lift the feast into a fantasy of antique grandeur filtered through Venetian taste. Architecture here is pageantry — depth as spectacle.",
                "category": "architecture",
                "confidence": "scholarly_interpretation",
                "sources": ["https://collections.louvre.fr/en/ark:/53355/cl010066872"],
            },
            {
                "id": "servants",
                "entityId": "servants",
                "title": "Hands that make the miracle work",
                "body": "Servants crouch and pour in the foreground, bridging sacred narrative and kitchen reality. Veronese insists that wonders still need people willing to fill jars.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://collections.louvre.fr/en/ark:/53355/cl010066872"],
            },
        ],
    },
    "harvesters": {
        "sources": {
            "paintingId": "harvesters",
            "image": {
                "file": "painting.jpg",
                "sourceUrl": "https://commons.wikimedia.org/wiki/File:Pieter_Bruegel_d._%C3%84._002.jpg",
                "retrievalUrl": "https://commons.wikimedia.org/wiki/Special:FilePath/Pieter_Bruegel_d._%C3%84._002.jpg?width=1920",
                "license": "Public domain (work of Pieter Bruegel the Elder; photographic reproduction)",
                "credit": "Pieter Bruegel the Elder; file from Wikimedia Commons",
                "retrievedAt": "2026-03-30",
            },
            "references": [
                {
                    "id": "met-harvesters",
                    "title": "The Harvesters",
                    "publisher": "The Metropolitan Museum of Art",
                    "url": "https://www.metmuseum.org/art/collection/search/435809",
                }
            ],
        },
        "painting": {
            "title": "The Harvesters",
            "artist": "Pieter Bruegel the Elder",
            "date": "1565",
            "medium": "Oil on wood",
            "source": "The Metropolitan Museum of Art, New York",
        },
        "composition": {
            "horizon": 0.42,
            "vanishingPoint": [0.65, 0.4],
            "cameraFov": 46,
        },
        "lighting": {
            "ambient": 0.62,
            "directional": [0.5, 0.85, 0.15],
            "directionalIntensity": 0.8,
            "color": "#f0e2c4",
        },
        "palette": ["#c9a24a", "#6b7a3a", "#d8c090", "#2a2218"],
        "entities": [
            entity("resting-group", "Harvesters at rest", (0.52, 0.58), importance=10),
            entity("pear-tree", "The pear tree", (0.48, 0.38), etype="landscape", importance=8, depth=2),
            entity("wheat-field", "Cut wheat field", (0.72, 0.42), etype="landscape", importance=8, depth=2),
            entity("lunch", "Bread and bowls", (0.5, 0.64), etype="object", importance=7, depth=0),
            entity("path", "Village path", (0.28, 0.7), etype="landscape", importance=6, depth=1),
            entity("distant-bay", "Distant water", (0.78, 0.28), etype="landscape", importance=7, depth=4),
            entity("church-steeple", "Church in the valley", (0.84, 0.32), etype="architecture", importance=6, depth=4),
            entity("scythes", "Scythes and sheaves", (0.6, 0.55), etype="object", importance=7, depth=1),
        ],
        "facts": [
            {
                "id": "painting-overview",
                "title": "August under a pear tree",
                "body": "Bruegel’s Harvesters (1565), now at the Met, belongs to a series of months/seasons panels. Labor, rest, and landscape share equal dignity: the year turns through peasant work rather than court allegory.",
                "category": "painting",
                "confidence": "documented",
                "sources": ["https://www.metmuseum.org/art/collection/search/435809"],
            },
            {
                "id": "resting-group",
                "entityId": "resting-group",
                "title": "Bodies finally allowed to stop",
                "body": "Under the tree, harvesters sprawl, eat, and doze. Bruegel refuses heroic posing — exhaustion is the subject, and the field itself seems to breathe around them.",
                "category": "figure",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.metmuseum.org/art/collection/search/435809"],
            },
            {
                "id": "pear-tree",
                "entityId": "pear-tree",
                "title": "Shade as architecture",
                "body": "The pear tree is the painting’s vertical mast — a green canopy that organizes rest against the gold of cut grain. Landscape becomes a room you can enter.",
                "category": "landscape",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.metmuseum.org/art/collection/search/435809"],
            },
            {
                "id": "wheat-field",
                "entityId": "wheat-field",
                "title": "A sea of stubble",
                "body": "Cut wheat rolls toward the distance in overlapping planes. Bruegel’s high viewpoint turns agriculture into topography — work measured in acres of light.",
                "category": "landscape",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.metmuseum.org/art/collection/search/435809"],
            },
            {
                "id": "lunch",
                "entityId": "lunch",
                "title": "Noon meal in the field",
                "body": "Bread, bowls, and simple fare sit among the resting figures. The sacred calendar of seasons is tasted as much as observed.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.metmuseum.org/art/collection/search/435809"],
            },
            {
                "id": "path",
                "entityId": "path",
                "title": "A path into village life",
                "body": "A track leads the eye left and down toward houses and figures still at work. Bruegel nests many small stories inside one climate of heat.",
                "category": "landscape",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.metmuseum.org/art/collection/search/435809"],
            },
            {
                "id": "distant-bay",
                "entityId": "distant-bay",
                "title": "Cool water far away",
                "body": "Beyond the fields, a pale bay and cliffs open the world. The harvest is local; the horizon reminds you that Flanders sits inside a larger geography.",
                "category": "landscape",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.metmuseum.org/art/collection/search/435809"],
            },
            {
                "id": "church-steeple",
                "entityId": "church-steeple",
                "title": "A steeple in the haze",
                "body": "A church punctuates the valley — sacred time keeping pace with agricultural time. Bruegel’s peasants live under both calendars at once.",
                "category": "architecture",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.metmuseum.org/art/collection/search/435809"],
            },
            {
                "id": "scythes",
                "entityId": "scythes",
                "title": "Tools of the month",
                "body": "Scythes, sheaves, and stacked grain mark August’s labor. The instruments are as carefully observed as faces — the dignity of craft without romance.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.metmuseum.org/art/collection/search/435809"],
            },
        ],
    },
    "ambassadors": {
        "sources": {
            "paintingId": "ambassadors",
            "image": {
                "file": "painting.jpg",
                "sourceUrl": "https://commons.wikimedia.org/wiki/File:Hans_Holbein_the_Younger_-_The_Ambassadors_-_Google_Art_Project.jpg",
                "retrievalUrl": "https://commons.wikimedia.org/wiki/Special:FilePath/Hans_Holbein_the_Younger_-_The_Ambassadors_-_Google_Art_Project.jpg?width=1920",
                "license": "Public domain (work of Hans Holbein the Younger; photographic reproduction)",
                "credit": "Hans Holbein the Younger; file from Wikimedia Commons",
                "retrievedAt": "2026-03-30",
            },
            "references": [
                {
                    "id": "ng-ambassadors",
                    "title": "The Ambassadors",
                    "publisher": "The National Gallery, London",
                    "url": "https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors",
                }
            ],
        },
        "painting": {
            "title": "The Ambassadors",
            "artist": "Hans Holbein the Younger",
            "date": "1533",
            "medium": "Oil on oak",
            "source": "The National Gallery, London",
        },
        "composition": {
            "horizon": 0.48,
            "vanishingPoint": [0.5, 0.45],
            "cameraFov": 40,
        },
        "lighting": {
            "ambient": 0.48,
            "directional": [0.4, 0.75, 0.35],
            "directionalIntensity": 0.9,
            "color": "#efe4d0",
        },
        "palette": ["#1a1510", "#c9a24a", "#2e4a6a", "#d2c2a4"],
        "entities": [
            entity("dinteville", "Jean de Dinteville", (0.28, 0.4), importance=10),
            entity("selve", "Georges de Selve", (0.72, 0.4), importance=10),
            entity("skull", "Anamorphic skull", (0.5, 0.82), etype="object", importance=10, depth=0),
            entity("globe", "Terrestrial globe", (0.58, 0.52), etype="object", importance=8, depth=1),
            entity("lute", "Lute with broken string", (0.6, 0.58), etype="object", importance=8, depth=1),
            entity("instruments", "Scientific instruments", (0.48, 0.45), etype="object", importance=9, depth=1),
            entity("crucifix", "Half-hidden crucifix", (0.9, 0.18), etype="object", importance=7, depth=2),
            entity("mosaic-floor", "Cosmati floor", (0.5, 0.88), etype="architecture", importance=6, depth=0),
            entity("hymnal", "Lutheran hymnal", (0.55, 0.6), etype="object", importance=7, depth=1),
        ],
        "facts": [
            {
                "id": "painting-overview",
                "title": "Two envoys and a distorted death",
                "body": "Holbein painted The Ambassadors in 1533. The National Gallery identifies the standing figures as Jean de Dinteville, French ambassador to England, and Georges de Selve, bishop and envoy. Between them stretches a shelf of worldly learning — and a skull you can only read from the side.",
                "category": "painting",
                "confidence": "documented",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
            {
                "id": "dinteville",
                "entityId": "dinteville",
                "title": "Dinteville in silk and dagger",
                "body": "Jean de Dinteville, left, wears the luxurious stillness of a court diplomat. Holbein catalogs status through fabrics and a sheathed dagger while the man’s gaze holds you at interview distance.",
                "category": "figure",
                "confidence": "documented",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
            {
                "id": "selve",
                "entityId": "selve",
                "title": "Selve in clerical gravity",
                "body": "Georges de Selve, right, balances secular pomp with episcopal restraint. Together the pair embody church and state negotiating a fractured Europe — Reformation politics folded into friendship.",
                "category": "figure",
                "confidence": "documented",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
            {
                "id": "skull",
                "entityId": "skull",
                "title": "Death, stretched across the floor",
                "body": "The famous anamorphic skull only resolves when viewed from an extreme angle. Holbein plants memento mori inside diplomatic display: approach knowledge, then remember you are temporary.",
                "category": "object",
                "confidence": "documented",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
            {
                "id": "globe",
                "entityId": "globe",
                "title": "A world you can spin",
                "body": "Globes and maps advertise geographic mastery — the ambassadors’ century inventing itself as a measurable planet. Empire and curiosity share the same polished sphere.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
            {
                "id": "lute",
                "entityId": "lute",
                "title": "A string that will not play",
                "body": "A lute with a broken string sits among the instruments — often read as discord in the Church or the limits of earthly harmony. Music, like diplomacy, can go out of tune.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
            {
                "id": "instruments",
                "entityId": "instruments",
                "title": "Shelf of the sciences",
                "body": "Sundials, quadrants, and books stack into a curriculum of astronomy and measurement. Holbein paints learning as furniture — knowledge you could almost reach out and adjust.",
                "category": "object",
                "confidence": "documented",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
            {
                "id": "crucifix",
                "entityId": "crucifix",
                "title": "Christ half hidden by the curtain",
                "body": "A silver crucifix peeks from behind the green curtain at upper left. Faith remains in the room, but edged to the margin — a quiet counterweight to instruments and skull.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
            {
                "id": "mosaic-floor",
                "entityId": "mosaic-floor",
                "title": "Cosmati geometry underfoot",
                "body": "The pavement echoes Cosmati work associated with Westminster Abbey. Sacred geometry grounds the envoys — England’s great church literally under diplomatic feet.",
                "category": "architecture",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
            {
                "id": "hymnal",
                "entityId": "hymnal",
                "title": "Open pages of Reform",
                "body": "An open hymnal has been linked to Lutheran music — doctrine entering through song. Even the still life argues about Europe’s religious fracture.",
                "category": "object",
                "confidence": "scholarly_interpretation",
                "sources": ["https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"],
            },
        ],
    },
}


def write_world(painting_id: str, spec: dict) -> None:
    root = PAINTINGS / painting_id
    root.mkdir(parents=True, exist_ok=True)
    img_path = root / "painting.jpg"
    if not img_path.exists():
        raise FileNotFoundError(img_path)
    w, h = Image.open(img_path).size
    ar = w / h
    pw, ph = planes(ar)
    comp = {
        "aspectRatio": round(ar, 3),
        "horizon": spec["composition"]["horizon"],
        "vanishingPoint": spec["composition"]["vanishingPoint"],
        "cameraFov": spec["composition"]["cameraFov"],
        "planeWidth": round(pw, 3),
        "planeHeight": round(ph, 3),
    }
    manifest = {
        "schemaVersion": 1,
        "paintingId": painting_id,
        "pipelineVersion": "0.1.0",
        "sceneAnalysisVersion": "manual-tier1-v1",
        "segmentationVersion": "none",
        "depthVersion": "none",
        "painting": spec["painting"],
        "composition": comp,
        "layers": hero_layer(),
        "entities": spec["entities"],
        "architecture": floor_arch(),
        "lighting": spec["lighting"],
        "palette": spec["palette"],
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (root / "facts.json").write_text(json.dumps({"facts": spec["facts"]}, indent=2) + "\n", encoding="utf-8")
    (root / "sources.json").write_text(json.dumps(spec["sources"], indent=2) + "\n", encoding="utf-8")

    public = ROOT / "public" / "data" / "paintings" / painting_id
    if public.exists():
        shutil.rmtree(public)
    public.mkdir(parents=True)
    for name in ("painting.jpg", "manifest.json", "facts.json", "sources.json"):
        shutil.copy2(root / name, public / name)
    print(f"Wrote {painting_id}: {len(spec['entities'])} entities, {len(spec['facts'])} facts, plane {pw:.2f}x{ph:.2f}")


def main() -> None:
    for painting_id, spec in WORLDS.items():
        write_world(painting_id, spec)


if __name__ == "__main__":
    main()
