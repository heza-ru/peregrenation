"""Complete museum-density curiosities for all curated worlds (except School of Athens, already full)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAINTINGS = ROOT / "data" / "paintings"


def E(
    eid: str,
    label: str,
    uv: tuple[float, float],
    *,
    etype: str = "figure",
    importance: int = 8,
    depth: int = 1,
    confidence: float = 0.88,
    evidence: str = "observed",
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
        "confidence": confidence,
        "evidence": evidence,
    }


def F(
    fid: str,
    title: str,
    body: str,
    sources: list[str],
    *,
    entity_id: str | None = None,
    category: str = "figure",
    confidence: str = "scholarly_interpretation",
) -> dict:
    out: dict = {
        "id": fid,
        "title": title,
        "body": body,
        "category": category,
        "confidence": confidence,
        "sources": sources,
    }
    if entity_id:
        out["entityId"] = entity_id
    return out


def patch_world(painting_id: str, entities: list[dict], facts: list[dict]) -> None:
    root = PAINTINGS / painting_id
    man_path = root / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man["entities"] = entities
    man["sceneAnalysisVersion"] = "manual-curiosities-v2"
    man_path.write_text(json.dumps(man, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (root / "facts.json").write_text(
        json.dumps({"facts": facts}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    public = ROOT / "public" / "data" / "paintings" / painting_id
    public.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "facts.json"):
        shutil.copy2(root / name, public / name)
    n_ent = len(entities)
    n_fact = len([f for f in facts if f.get("entityId")])
    print(f"{painting_id}: {n_ent} curiosities, {n_fact} entity facts, {len(facts)} total facts")


# —— Last Supper ——
LS = "https://cenacolovinciano.org/en/"
LAST_SUPPER = {
    "entities": [
        E("bartholomew", "Bartholomew", (0.08, 0.48), importance=7),
        E("james-minor", "James the Less", (0.14, 0.48), importance=7),
        E("andrew", "Andrew", (0.2, 0.48), importance=7),
        E("judas", "Judas Iscariot", (0.32, 0.55), importance=10),
        E("peter", "Peter", (0.36, 0.46), importance=9),
        E("john", "John", (0.42, 0.44), importance=9),
        E("jesus", "Jesus", (0.5, 0.42), importance=10),
        E("thomas", "Thomas", (0.56, 0.4), importance=8),
        E("james-major", "James the Greater", (0.6, 0.42), importance=8),
        E("philip", "Philip", (0.66, 0.45), importance=7),
        E("matthew", "Matthew", (0.78, 0.48), importance=7),
        E("thaddeus", "Jude Thaddeus", (0.86, 0.48), importance=7),
        E("simon", "Simon", (0.93, 0.48), importance=7),
        E("table", "The table", (0.5, 0.62), etype="object", importance=8, depth=0),
        E("trinity-window", "Central window", (0.5, 0.22), etype="architecture", importance=8, depth=3),
        E("spilled-salt", "Overturned salt", (0.4, 0.58), etype="object", importance=6, depth=0),
        E("coffered-ceiling", "Coffered ceiling", (0.5, 0.12), etype="architecture", importance=6, depth=4),
    ],
    "facts": [
        F(
            "painting-overview",
            "A supper frozen mid-shock",
            "Leonardo painted The Last Supper on the north wall of the Dominican refectory of Santa Maria delle Grazie in Milan (c. 1495–1498). Christ has just said that one of the Twelve will betray him; the apostles erupt in four groups of three while every architectural line converges on his calm center.",
            [LS],
            category="painting",
            confidence="documented",
        ),
        F(
            "bartholomew",
            "Bartholomew — rising in alarm",
            "At the far left, Bartholomew rises from his seat, hands on the table as if ready to stand. Leonardo turns the leftmost cluster into a wave of physical shock traveling toward Christ.",
            [LS],
            entity_id="bartholomew",
        ),
        F(
            "james-minor",
            "James the Less — hand on Peter’s shoulder",
            "James the Less reaches toward Peter, knitting the left trio together. His gesture is pastoral concern — trying to steady the group before the news fully lands.",
            [LS],
            entity_id="james-minor",
        ),
        F(
            "andrew",
            "Andrew — palms open",
            "Andrew lifts both hands, palms outward: a startled refusal. Leonardo uses open hands across the mural as a grammar of disbelief.",
            [LS],
            entity_id="andrew",
        ),
        F(
            "judas",
            "Judas — purse, shadow, spilled omen",
            "Judas Iscariot (the betrayer) recoils into silhouette, clutching a small purse and reaching toward the same dish as Christ. Near him salt appears overturned — Leonardo tells treachery through light and clutter, not a painted label.",
            [LS],
            entity_id="judas",
        ),
        F(
            "peter",
            "Peter — knife already drawn",
            "Simon Peter leans in aggressively, a knife already in hand — foreshadowing Gethsemane. Impulsive loyalty compressed into one diagonal thrust toward the quiet center.",
            [LS],
            entity_id="peter",
        ),
        F(
            "john",
            "John — the beloved disciple",
            "The youthful figure leaning away from Christ is traditionally John. Leonardo softens him into almost feminine gentleness — a foil to Peter’s force and Judas’s isolation.",
            [LS],
            entity_id="john",
        ),
        F(
            "jesus",
            "Christ as vanishing point",
            "Jesus sits alone at the table’s center, head framed by the brightest window. Arms open toward bread and wine, face resigned rather than theatrical. Orthogonals of the room converge near him — the mural’s calm keystone.",
            [LS],
            entity_id="jesus",
            confidence="documented",
        ),
        F(
            "thomas",
            "Thomas — the upward finger",
            "Thomas raises a finger as if demanding proof — a gesture later readers link to his doubt after the Resurrection. Leonardo seeds the next chapter inside this single meal.",
            [LS],
            entity_id="thomas",
        ),
        F(
            "james-major",
            "James the Greater — arms flung wide",
            "James opens both arms in disbelief, a wide counter-rhythm to Christ’s quieter gesture. Shock made monumental.",
            [LS],
            entity_id="james-major",
        ),
        F(
            "philip",
            "Philip — leaning in to ask",
            "Philip presses forward, almost pleading for clarification. Leonardo’s apostles do not pose; they argue with their bodies.",
            [LS],
            entity_id="philip",
        ),
        F(
            "matthew",
            "Matthew — turning to the end of the table",
            "Matthew turns outward toward Jude and Simon, spreading the news along the right-hand group. Conversation becomes composition.",
            [LS],
            entity_id="matthew",
        ),
        F(
            "thaddeus",
            "Jude Thaddeus — mid-debate",
            "Jude Thaddeus gestures toward Simon, continuing the chain of reaction. The rightmost trio closes the mural’s wave of response.",
            [LS],
            entity_id="thaddeus",
        ),
        F(
            "simon",
            "Simon — the far-right anchor",
            "Simon sits at the far right, hands raised in talk. He brackets the scene with Bartholomew on the opposite end — two anchors of a human storm.",
            [LS],
            entity_id="simon",
        ),
        F(
            "table",
            "A refectory table as stage",
            "White cloth, plates, and glasses sit at dining height inside a real monastery dining hall. Monks eating beneath the mural faced this painted meal daily — Eucharist mirrored at supper time.",
            [LS],
            entity_id="table",
            category="object",
            confidence="documented",
        ),
        F(
            "trinity-window",
            "Three windows, one light",
            "Behind Christ, three openings pour daylight into the hall. The center window doubles as a natural halo while the coffered ceiling and tapestries deepen the illusion of a room beyond the wall.",
            [LS],
            entity_id="trinity-window",
            category="architecture",
        ),
        F(
            "spilled-salt",
            "Salt tipped toward treachery",
            "Near Judas, salt appears overturned — long read as a bad omen. Whether folklore or still-life accident, the cluttered table turns betrayal into something nearly touchable.",
            [LS],
            entity_id="spilled-salt",
            category="object",
        ),
        F(
            "coffered-ceiling",
            "Perspective as theology",
            "The coffered ceiling rushes toward Christ. Leonardo’s perspective is not decoration — it is devotion engineered in geometry, pulling every eye to the same calm face.",
            [LS],
            entity_id="coffered-ceiling",
            category="architecture",
        ),
    ],
}

# —— Arnolfini ——
NG_A = "https://www.nationalgallery.org.uk/paintings/jan-van-eyck-the-arnolfini-portrait"
ARNOLFINI = {
    "entities": [
        E("giovanni", "Giovanni Arnolfini", (0.3, 0.42), importance=10),
        E("bride", "The woman in green", (0.58, 0.45), importance=10),
        E("joined-hands", "Joined hands", (0.42, 0.5), etype="gesture", importance=9),
        E("mirror", "Convex mirror", (0.5, 0.52), etype="object", importance=10, depth=2),
        E("signature", "Van Eyck was here", (0.5, 0.4), etype="inscription", importance=9, depth=2),
        E("chandelier", "Brass chandelier", (0.48, 0.14), etype="object", importance=8, depth=2),
        E("dog", "The dog", (0.48, 0.88), etype="animal", importance=7, depth=0),
        E("clogs", "Discarded clogs", (0.22, 0.82), etype="object", importance=7, depth=0),
        E("oranges", "Oranges on the sill", (0.16, 0.55), etype="object", importance=7, depth=1),
        E("bed", "The red bed", (0.8, 0.55), etype="object", importance=8, depth=1),
        E("rosary", "Crystal rosary", (0.5, 0.48), etype="object", importance=7, depth=2),
        E("brush", "Bedside brush", (0.72, 0.48), etype="object", importance=6, depth=1),
        E("window", "Leadlight window", (0.12, 0.35), etype="architecture", importance=7, depth=2),
        E("carpet", "Oriental carpet", (0.55, 0.72), etype="object", importance=6, depth=0),
        E("fur-robe", "Fur-lined robe", (0.28, 0.55), etype="object", importance=6, depth=1),
    ],
    "facts": [
        F(
            "painting-overview",
            "A room full of witnesses",
            "Jan van Eyck signed and dated this panel 1434. The National Gallery identifies the man as a member of the Arnolfini merchant family; the woman’s exact identity is debated. What is certain is the denseness of the chamber: every surface seems ready to testify.",
            [NG_A],
            category="painting",
            confidence="documented",
        ),
        F(
            "giovanni",
            "The merchant in black",
            "The man raises his right hand in greeting or oath while his left takes the woman’s hand. Tall hat, fur-lined robe, and calm stare mark wealth and civic standing in Bruges’s Italian trading community.",
            [NG_A],
            entity_id="giovanni",
            confidence="documented",
        ),
        F(
            "bride",
            "Green gown, gathered fabric",
            "She wears a lush green dress with fashionably gathered folds at the belly — a style of the period, not proof of pregnancy. Her gaze meets you while her free hand lifts the heavy cloth.",
            [NG_A],
            entity_id="bride",
        ),
        F(
            "joined-hands",
            "Hands as contract",
            "Their joined hands sit at the painting’s rhetorical center. Scholars have read the gesture as marriage, betrothal, or legal pledge — van Eyck leaves the ceremony ambiguous while making the bond unmistakable.",
            [NG_A],
            entity_id="joined-hands",
            category="gesture",
        ),
        F(
            "mirror",
            "The convex witness",
            "The round mirror reflects the couple from behind and two additional figures in the doorway — one likely the painter. Around its frame, tiny Passion scenes turn furniture into theology.",
            [NG_A],
            entity_id="mirror",
            category="object",
            confidence="documented",
        ),
        F(
            "signature",
            "Johannes de eyck fuit hic",
            "Above the mirror van Eyck wrote that he “was here,” 1434 — less a quiet signature than a notarized presence. The painter becomes another witness inside the room you are stepping into.",
            [NG_A],
            entity_id="signature",
            category="inscription",
            confidence="documented",
        ),
        F(
            "chandelier",
            "One candle lit",
            "A brass chandelier hangs with a single burning candle. Interpreters link it to the eye of God, marital fidelity, or the costly lighting of a prosperous house — van Eyck invites several readings at once.",
            [NG_A],
            entity_id="chandelier",
            category="object",
        ),
        F(
            "dog",
            "Fidelity at their feet",
            "The small dog between the couple is often read as loyalty (fides). Van Eyck paints its fur with the same microscopic care as the chandelier’s metal — domestic life elevated to spectacle.",
            [NG_A],
            entity_id="dog",
            category="animal",
        ),
        F(
            "clogs",
            "Shoes left at the threshold",
            "Wooden pattens lie discarded in the foreground. Removing outdoor shoes could signal sacred ground, intimacy, or fine-interior etiquette — another object that behaves like a clue.",
            [NG_A],
            entity_id="clogs",
            category="object",
        ),
        F(
            "oranges",
            "Costly fruit by the window",
            "Oranges rest near the window — luxury imports in northern Europe. They perfume the room with wealth and, for some viewers, with hints of paradise or fertility.",
            [NG_A],
            entity_id="oranges",
            category="object",
        ),
        F(
            "bed",
            "The red marriage bed",
            "A richly draped bed dominates the right side. In fifteenth-century portraits the bed could mark household status as much as private life — furniture as biography.",
            [NG_A],
            entity_id="bed",
            category="object",
        ),
        F(
            "rosary",
            "Crystal beads on the wall",
            "A crystal prayer bead string hangs beside the mirror. Devotion is not background noise here — piety is hung where you can count it.",
            [NG_A],
            entity_id="rosary",
            category="object",
        ),
        F(
            "brush",
            "A brush by the bed",
            "A whisk broom hangs near the bed — domestic order as virtue. Van Eyck’s symbolism often hides inside housekeeping.",
            [NG_A],
            entity_id="brush",
            category="object",
        ),
        F(
            "window",
            "Daylight through leaded glass",
            "The leadlight window pours cool daylight across oranges and fabric. Van Eyck’s oil technique turns glass and air into characters of their own.",
            [NG_A],
            entity_id="window",
            category="architecture",
        ),
        F(
            "carpet",
            "Pattern underfoot",
            "An oriental carpet softens the floor near the bed — another imported luxury. Pattern becomes proof of trade routes ending in this quiet room.",
            [NG_A],
            entity_id="carpet",
            category="object",
        ),
        F(
            "fur-robe",
            "Fur as status",
            "The man’s fur-lined robes advertise merchant wealth without shouting. Texture is van Eyck’s rhetoric: you believe the social rank because you can almost feel the nap.",
            [NG_A],
            entity_id="fur-robe",
            category="object",
        ),
    ],
}

# —— Wedding at Cana ——
LOUVRE = "https://collections.louvre.fr/en/ark:/53355/cl010066872"
CANA = {
    "entities": [
        E("jesus", "Jesus", (0.48, 0.4), importance=10),
        E("mary", "Mary", (0.42, 0.4), importance=9),
        E("bride-groom", "Bride and groom", (0.62, 0.38), importance=8),
        E("musicians", "The musicians", (0.5, 0.55), importance=9),
        E("stone-jars", "Stone water jars", (0.32, 0.78), etype="object", importance=9, depth=0),
        E("feast-table", "Banquet table", (0.5, 0.48), etype="object", importance=8, depth=1),
        E("classic-architecture", "Classical loggia", (0.5, 0.18), etype="architecture", importance=8, depth=4),
        E("servants", "Servants pouring", (0.28, 0.65), importance=8, depth=0),
        E("steward", "The steward", (0.35, 0.55), importance=7),
        E("balcony-guests", "Guests on the balustrade", (0.55, 0.22), importance=6, depth=3),
        E("silver-vessels", "Silver and glassware", (0.55, 0.5), etype="object", importance=7, depth=1),
        E("dogs", "Dogs under the table", (0.45, 0.82), etype="animal", importance=5, depth=0),
        E("columns", "Paired columns", (0.25, 0.3), etype="architecture", importance=6, depth=3),
        E("hourglass-time", "Still-life of time", (0.7, 0.52), etype="object", importance=6, depth=1),
        E("veronese-self", "Painter among players", (0.48, 0.58), importance=8),
    ],
    "facts": [
        F(
            "painting-overview",
            "A miracle the size of a wall",
            "Veronese painted The Wedding Feast at Cana for the refectory of San Giorgio Maggiore in Venice (1563). Now in the Louvre, the canvas is immense — a Venetian banquet dressed as the Gospel miracle where water becomes wine.",
            [LOUVRE],
            category="painting",
            confidence="documented",
        ),
        F(
            "jesus",
            "Christ among the guests",
            "Jesus sits near the center of the long table, marked more by composure than theatrical glow. The miracle unfolds as social theater: divinity visiting a wedding at festival pitch.",
            [LOUVRE],
            entity_id="jesus",
            confidence="documented",
        ),
        F(
            "mary",
            "Mary prompts the miracle",
            "Mary, seated near Christ, is the quiet catalyst — she notices the wine has failed. Veronese keeps her dignified inside a crowd that otherwise threatens to swallow the narrative.",
            [LOUVRE],
            entity_id="mary",
        ),
        F(
            "bride-groom",
            "The bridal pair",
            "Bride and groom occupy places of honor along the feast. Their celebration is the pretext for the first public sign in John’s Gospel — hospitality stretched until heaven intervenes.",
            [LOUVRE],
            entity_id="bride-groom",
        ),
        F(
            "musicians",
            "A foreground orchestra",
            "Musicians play at the lower center of the canvas. The banquet becomes audition and feast at once — Venice hearing itself celebrate.",
            [LOUVRE],
            entity_id="musicians",
        ),
        F(
            "veronese-self",
            "Veronese in the band",
            "Tradition identifies Veronese himself among the string players, with fellow Venetian painters as companions. The miracle scene doubles as a self-portrait of art’s city.",
            [LOUVRE],
            entity_id="veronese-self",
        ),
        F(
            "stone-jars",
            "Jars of new wine",
            "Large stone jars recall vessels of Jewish purification rites that Christ orders filled with water. Servants tip and pour at the lower edge — the miracle made tangible as logistics.",
            [LOUVRE],
            entity_id="stone-jars",
            category="object",
            confidence="documented",
        ),
        F(
            "feast-table",
            "Silver, glass, and appetite",
            "The table groans with vessels, fruit, and ruffled linen. Veronese turns Eucharistic overtones into sensory overload — tasting, seeing, and hearing all at once.",
            [LOUVRE],
            entity_id="feast-table",
            category="object",
        ),
        F(
            "classic-architecture",
            "A stage of columns",
            "Classical colonnades and balustrades lift the feast into fantasy antique grandeur filtered through Venetian taste. Architecture here is pageantry — depth as spectacle.",
            [LOUVRE],
            entity_id="classic-architecture",
            category="architecture",
        ),
        F(
            "servants",
            "Hands that make the miracle work",
            "Servants crouch and pour in the foreground, bridging sacred narrative and kitchen reality. Veronese insists wonders still need people willing to fill jars.",
            [LOUVRE],
            entity_id="servants",
        ),
        F(
            "steward",
            "The steward tastes the wine",
            "The steward who tastes the transformed wine stands for astonished hospitality staff — bureaucracy meeting miracle. John’s Gospel needs this witness to declare the wine better than before.",
            [LOUVRE],
            entity_id="steward",
        ),
        F(
            "balcony-guests",
            "Spectators above the feast",
            "Figures lean from balustrades and terraces, turning the wedding into a public Venetian event. Looking becomes part of the composition’s social physics.",
            [LOUVRE],
            entity_id="balcony-guests",
        ),
        F(
            "silver-vessels",
            "Plate that flashes wealth",
            "Silver and glass catch Veronese’s light like jewelry. Luxury is not background — it is the worldly stage on which a sacred surplus of wine arrives.",
            [LOUVRE],
            entity_id="silver-vessels",
            category="object",
        ),
        F(
            "dogs",
            "Animals under the banquet",
            "Dogs nosing under the table keep the feast grounded in messy life. Even miracles happen in rooms that still smell like kitchens.",
            [LOUVRE],
            entity_id="dogs",
            category="animal",
        ),
        F(
            "columns",
            "Stone order behind revelry",
            "Paired columns and cornices impose classical order on the chaos of guests. Veronese’s architecture frames appetite without scolding it.",
            [LOUVRE],
            entity_id="columns",
            category="architecture",
        ),
        F(
            "hourglass-time",
            "Timekeeping on the table",
            "Still-life details — including timepieces in related banquet traditions — remind viewers that feasts end. Here abundance is urgent: drink while the miracle lasts.",
            [LOUVRE],
            entity_id="hourglass-time",
            category="object",
            confidence="ai_inference",
        ),
    ],
}

# —— Harvesters ——
MET = "https://www.metmuseum.org/art/collection/search/435809"
HARVESTERS = {
    "entities": [
        E("resting-group", "Harvesters at rest", (0.52, 0.58), importance=10),
        E("sleeper", "The sleeper", (0.55, 0.62), importance=8),
        E("eaters", "The noon meal", (0.48, 0.6), importance=8),
        E("pear-tree", "The pear tree", (0.48, 0.38), etype="landscape", importance=9, depth=2),
        E("wheat-field", "Cut wheat field", (0.72, 0.42), etype="landscape", importance=8, depth=2),
        E("standing-wheat", "Standing grain", (0.35, 0.45), etype="landscape", importance=7, depth=2),
        E("scythes", "Scythes and sheaves", (0.6, 0.55), etype="object", importance=8, depth=1),
        E("path", "Village path", (0.28, 0.7), etype="landscape", importance=7, depth=1),
        E("distant-workers", "Figures still working", (0.22, 0.55), importance=7, depth=2),
        E("distant-bay", "Distant water", (0.78, 0.28), etype="landscape", importance=8, depth=4),
        E("church-steeple", "Church in the valley", (0.84, 0.32), etype="architecture", importance=7, depth=4),
        E("haystacks", "Haystacks and ricks", (0.65, 0.35), etype="landscape", importance=6, depth=3),
        E("birds", "Birds in the air", (0.6, 0.2), etype="animal", importance=5, depth=4),
        E("lunch", "Bread and bowls", (0.5, 0.64), etype="object", importance=7, depth=0),
        E("wagon-track", "Cart tracks in dust", (0.4, 0.75), etype="landscape", importance=5, depth=0),
    ],
    "facts": [
        F(
            "painting-overview",
            "August under a pear tree",
            "Bruegel’s Harvesters (1565), now at the Met, belongs to a series of months/seasons panels. Labor, rest, and landscape share equal dignity: the year turns through peasant work rather than court allegory.",
            [MET],
            category="painting",
            confidence="documented",
        ),
        F(
            "resting-group",
            "Bodies finally allowed to stop",
            "Under the tree, harvesters sprawl, eat, and doze. Bruegel refuses heroic posing — exhaustion is the subject, and the field itself seems to breathe around them.",
            [MET],
            entity_id="resting-group",
        ),
        F(
            "sleeper",
            "Sleep as honest labor’s wage",
            "One figure has simply given up to sleep mid-break. Bruegel treats rest without satire or shame — work has a circadian truth.",
            [MET],
            entity_id="sleeper",
        ),
        F(
            "eaters",
            "Sharing the noon meal",
            "Companions eat together in the shade. Community is built as much by bowls passed around as by grain cut in rows.",
            [MET],
            entity_id="eaters",
        ),
        F(
            "pear-tree",
            "Shade as architecture",
            "The pear tree is the painting’s vertical mast — a green canopy that organizes rest against the gold of cut grain. Landscape becomes a room you can enter.",
            [MET],
            entity_id="pear-tree",
            category="landscape",
        ),
        F(
            "wheat-field",
            "A sea of stubble",
            "Cut wheat rolls toward the distance in overlapping planes. Bruegel’s high viewpoint turns agriculture into topography — work measured in acres of light.",
            [MET],
            entity_id="wheat-field",
            category="landscape",
        ),
        F(
            "standing-wheat",
            "Grain still waiting",
            "Uncut grain stands as a warm wall of yellow-green. The harvest is unfinished — time is visible as a boundary between done and not-yet.",
            [MET],
            entity_id="standing-wheat",
            category="landscape",
        ),
        F(
            "scythes",
            "Tools of the month",
            "Scythes, sheaves, and stacked grain mark August’s labor. Instruments are observed as carefully as faces — craft without romance.",
            [MET],
            entity_id="scythes",
            category="object",
        ),
        F(
            "path",
            "A path into village life",
            "A track leads left and down toward houses and figures still at work. Bruegel nests many small stories inside one climate of heat.",
            [MET],
            entity_id="path",
            category="landscape",
        ),
        F(
            "distant-workers",
            "Labor continues beyond the shade",
            "Smaller figures keep harvesting farther off. Rest is local; the season’s work is collective and unfinished.",
            [MET],
            entity_id="distant-workers",
        ),
        F(
            "distant-bay",
            "Cool water far away",
            "Beyond the fields, a pale bay and cliffs open the world. The harvest is local; the horizon reminds you Flanders sits inside a larger geography.",
            [MET],
            entity_id="distant-bay",
            category="landscape",
        ),
        F(
            "church-steeple",
            "A steeple in the haze",
            "A church punctuates the valley — sacred time keeping pace with agricultural time. Bruegel’s peasants live under both calendars at once.",
            [MET],
            entity_id="church-steeple",
            category="architecture",
        ),
        F(
            "haystacks",
            "Ricks of stored summer",
            "Haystacks and ricks punctuate the middle distance — wealth counted in dried grass. Survival architecture, built outdoors.",
            [MET],
            entity_id="haystacks",
            category="landscape",
        ),
        F(
            "birds",
            "Life above the stubble",
            "Birds cut the pale sky. Bruegel’s world is ecological: human harvest shares air with other hungry creatures.",
            [MET],
            entity_id="birds",
            category="animal",
        ),
        F(
            "lunch",
            "Noon meal in the field",
            "Bread, bowls, and simple fare sit among the resting figures. The sacred calendar of seasons is tasted as much as observed.",
            [MET],
            entity_id="lunch",
            category="object",
        ),
        F(
            "wagon-track",
            "Dust roads of August",
            "Cart tracks score the foreground dust. Even empty paths record how grain and people move through the month.",
            [MET],
            entity_id="wagon-track",
            category="landscape",
        ),
    ],
}

# —— Ambassadors ——
NG_B = "https://www.nationalgallery.org.uk/paintings/hans-holbein-the-younger-the-ambassadors"
AMBASSADORS = {
    "entities": [
        E("dinteville", "Jean de Dinteville", (0.28, 0.4), importance=10),
        E("selve", "Georges de Selve", (0.72, 0.4), importance=10),
        E("skull", "Anamorphic skull", (0.5, 0.82), etype="object", importance=10, depth=0),
        E("celestial-globe", "Celestial globe", (0.45, 0.38), etype="object", importance=8, depth=2),
        E("sundial", "Sundial / dials", (0.5, 0.4), etype="object", importance=8, depth=2),
        E("quadrant", "Quadrant", (0.55, 0.38), etype="object", importance=7, depth=2),
        E("terrestrial-globe", "Terrestrial globe", (0.58, 0.52), etype="object", importance=8, depth=1),
        E("lute", "Lute with broken string", (0.6, 0.58), etype="object", importance=9, depth=1),
        E("flute-case", "Case of flutes", (0.52, 0.6), etype="object", importance=6, depth=1),
        E("hymnal", "Open hymnal", (0.55, 0.6), etype="object", importance=8, depth=1),
        E("arithmetic-book", "Book of arithmetic", (0.48, 0.58), etype="object", importance=7, depth=1),
        E("crucifix", "Half-hidden crucifix", (0.9, 0.18), etype="object", importance=8, depth=2),
        E("green-curtain", "Green curtain", (0.85, 0.3), etype="object", importance=6, depth=2),
        E("dagger", "Dinteville’s dagger", (0.3, 0.55), etype="object", importance=6, depth=1),
        E("mosaic-floor", "Cosmati floor", (0.5, 0.88), etype="architecture", importance=7, depth=0),
        E("instruments", "Shelf of instruments", (0.48, 0.45), etype="object", importance=8, depth=1),
    ],
    "facts": [
        F(
            "painting-overview",
            "Two envoys and a distorted death",
            "Holbein painted The Ambassadors in 1533. The National Gallery identifies Jean de Dinteville, French ambassador to England, and Georges de Selve, bishop and envoy. Between them stretches a shelf of worldly learning — and a skull you can only read from the side.",
            [NG_B],
            category="painting",
            confidence="documented",
        ),
        F(
            "dinteville",
            "Dinteville in silk and dagger",
            "Jean de Dinteville, left, wears the luxurious stillness of a court diplomat. Holbein catalogs status through fabrics and a sheathed dagger while the man’s gaze holds you at interview distance.",
            [NG_B],
            entity_id="dinteville",
            confidence="documented",
        ),
        F(
            "selve",
            "Selve in clerical gravity",
            "Georges de Selve, right, balances secular pomp with episcopal restraint. Together the pair embody church and state negotiating a fractured Europe — Reformation politics folded into friendship.",
            [NG_B],
            entity_id="selve",
            confidence="documented",
        ),
        F(
            "skull",
            "Death, stretched across the floor",
            "The famous anamorphic skull only resolves when viewed from an extreme angle. Holbein plants memento mori inside diplomatic display: approach knowledge, then remember you are temporary.",
            [NG_B],
            entity_id="skull",
            category="object",
            confidence="documented",
        ),
        F(
            "celestial-globe",
            "Stars on the upper shelf",
            "A celestial globe sits among the upper instruments — the heavens made portable. Ambassadors claim not only countries, but the sky’s measurable order.",
            [NG_B],
            entity_id="celestial-globe",
            category="object",
        ),
        F(
            "sundial",
            "Time caught in brass",
            "Dials and sundials advertise precision timekeeping. In 1533, mastering hours was political power as much as science.",
            [NG_B],
            entity_id="sundial",
            category="object",
        ),
        F(
            "quadrant",
            "A quadrant for the heavens",
            "The quadrant belongs to the toolkit of astronomy and navigation. Holbein paints expertise as still life — knowledge you could almost adjust.",
            [NG_B],
            entity_id="quadrant",
            category="object",
        ),
        F(
            "terrestrial-globe",
            "A world you can spin",
            "The terrestrial globe advertises geographic mastery — the ambassadors’ century inventing itself as a measurable planet. Empire and curiosity share the same polished sphere.",
            [NG_B],
            entity_id="terrestrial-globe",
            category="object",
        ),
        F(
            "lute",
            "A string that will not play",
            "A lute with a broken string sits among the instruments — often read as discord in the Church or the limits of earthly harmony. Music, like diplomacy, can go out of tune.",
            [NG_B],
            entity_id="lute",
            category="object",
        ),
        F(
            "flute-case",
            "Flutes in their case",
            "A case of flutes continues the musical theme. Harmony is collected, catalogued — and still vulnerable to a single broken course on the lute beside it.",
            [NG_B],
            entity_id="flute-case",
            category="object",
        ),
        F(
            "hymnal",
            "Open pages of Reform",
            "An open hymnal has been linked to Lutheran music — doctrine entering through song. Even the still life argues about Europe’s religious fracture.",
            [NG_B],
            entity_id="hymnal",
            category="object",
        ),
        F(
            "arithmetic-book",
            "Numbers for merchants and minds",
            "A book of arithmetic grounds the lower shelf in practical calculation. Diplomacy runs on ledgers as much as on Latin.",
            [NG_B],
            entity_id="arithmetic-book",
            category="object",
        ),
        F(
            "crucifix",
            "Christ half hidden by the curtain",
            "A silver crucifix peeks from behind the green curtain at upper left. Faith remains in the room, but edged to the margin — a quiet counterweight to instruments and skull.",
            [NG_B],
            entity_id="crucifix",
            category="object",
        ),
        F(
            "green-curtain",
            "The curtain of state",
            "The rich green drape stages the envoys like a court backdrop. Holbein’s theater of diplomacy needs fabric as much as faces.",
            [NG_B],
            entity_id="green-curtain",
            category="object",
        ),
        F(
            "dagger",
            "Steel at the hip",
            "Dinteville’s dagger is ornament and threat in one sheath. Soft power still keeps a blade within reach.",
            [NG_B],
            entity_id="dagger",
            category="object",
        ),
        F(
            "mosaic-floor",
            "Cosmati geometry underfoot",
            "The pavement echoes Cosmati work associated with Westminster Abbey. Sacred geometry grounds the envoys — England’s great church literally under diplomatic feet.",
            [NG_B],
            entity_id="mosaic-floor",
            category="architecture",
        ),
        F(
            "instruments",
            "Shelf of the sciences",
            "Upper and lower shelves stack into a curriculum of astronomy, geometry, music, and measurement. Holbein paints the Renaissance mind as furniture between two living men.",
            [NG_B],
            entity_id="instruments",
            category="object",
            confidence="documented",
        ),
    ],
}


def main() -> None:
    worlds = {
        "last-supper": LAST_SUPPER,
        "arnolfini-portrait": ARNOLFINI,
        "wedding-at-cana": CANA,
        "harvesters": HARVESTERS,
        "ambassadors": AMBASSADORS,
    }
    for pid, data in worlds.items():
        patch_world(pid, data["entities"], data["facts"])

    # School of Athens already complete — report only
    soa = json.loads((PAINTINGS / "school-of-athens" / "manifest.json").read_text(encoding="utf-8"))
    print(
        f"school-of-athens: kept {sum(1 for e in soa['entities'] if e.get('interactive'))} curiosities (already complete)"
    )


if __name__ == "__main__":
    main()
