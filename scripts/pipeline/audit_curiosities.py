"""Audit interactive entities vs facts for each curated painting world."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "paintings"

for p in sorted(ROOT.iterdir()):
    if not p.is_dir():
        continue
    m, f = p / "manifest.json", p / "facts.json"
    if not m.exists():
        continue
    man = json.loads(m.read_text(encoding="utf-8"))
    facts = json.loads(f.read_text(encoding="utf-8"))["facts"] if f.exists() else []
    ents = [e for e in man.get("entities", []) if e.get("interactive")]
    eids = {e["id"] for e in ents}
    fids = {x.get("entityId") for x in facts if x.get("entityId")}
    missing = sorted(eids - fids)
    print(f"{p.name}: {len(ents)} entities / {len(facts)} facts; missing={missing or '-'}")
