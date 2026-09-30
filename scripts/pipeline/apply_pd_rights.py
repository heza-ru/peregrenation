"""Write verified public-domain rights into each painting sources.json from license-audit.json."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "data" / "paintings" / "license-audit.json"

# Human rights notes (artwork + Commons file status)
NOTES = {
    "school-of-athens": {
        "artistDeathYear": 1520,
        "workPublicDomainReason": "Raphael died in 1520; the fresco is in the public domain worldwide.",
        "reproductionNote": "Wikimedia Commons marks this photographic reproduction Public domain (copyrighted=False).",
    },
    "last-supper": {
        "artistDeathYear": 1519,
        "workPublicDomainReason": "Leonardo da Vinci died in 1519; the mural is in the public domain worldwide.",
        "reproductionNote": "Wikimedia Commons marks this photographic reproduction Public domain (copyrighted=False).",
    },
    "arnolfini-portrait": {
        "artistDeathYear": 1441,
        "workPublicDomainReason": "Jan van Eyck died in 1441; the painting is in the public domain worldwide.",
        "reproductionNote": "Wikimedia Commons marks this National Gallery, London reproduction Public domain (copyrighted=False).",
    },
    "wedding-at-cana": {
        "artistDeathYear": 1588,
        "workPublicDomainReason": "Paolo Veronese died in 1588; the painting is in the public domain worldwide.",
        "reproductionNote": "Wikimedia Commons marks this photographic reproduction Public domain (copyrighted=False).",
    },
    "harvesters": {
        "artistDeathYear": 1569,
        "workPublicDomainReason": "Pieter Bruegel the Elder died in 1569; the painting is in the public domain worldwide.",
        "reproductionNote": "Wikimedia Commons marks this Yorck Project reproduction Public domain (copyrighted=False).",
    },
    "ambassadors": {
        "artistDeathYear": 1543,
        "workPublicDomainReason": "Hans Holbein the Younger died in 1543; the painting is in the public domain worldwide.",
        "reproductionNote": "Wikimedia Commons marks this Google Arts & Culture reproduction Public domain (copyrighted=False).",
    },
}


def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    for pid, note in NOTES.items():
        a = audit[pid]
        if not a.get("ok"):
            raise SystemExit(f"{pid} is not public domain according to audit")
        path = ROOT / "data" / "paintings" / pid / "sources.json"
        src = json.loads(path.read_text(encoding="utf-8"))
        image = src.setdefault("image", {})
        image["license"] = "Public domain"
        image["licenseShortName"] = a.get("licenseShortName") or "Public domain"
        image["commonsLicense"] = a.get("license") or "pd"
        image["copyrighted"] = False
        image["commonsTitle"] = a.get("commonsTitle")
        image["commonsUrl"] = a.get("commonsUrl")
        image["rights"] = {
            "status": "public_domain",
            "verifiedVia": "Wikimedia Commons extmetadata",
            "verifiedAt": "2026-03-30",
            **note,
        }
        if a.get("credit"):
            image["credit"] = a["credit"][:300]
        path.write_text(json.dumps(src, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        public = ROOT / "public" / "data" / "paintings" / pid / "sources.json"
        public.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, public)
        print(f"Updated rights: {pid}")


if __name__ == "__main__":
    main()
