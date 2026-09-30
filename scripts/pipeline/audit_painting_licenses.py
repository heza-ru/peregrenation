"""Audit Wikimedia Commons license metadata for curated painting sources."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

TITLES = {
    "school-of-athens": "File:The School of Athens by Raffaello Sanzio da Urbino.jpg",
    "last-supper": "File:The Last Supper - Leonardo Da Vinci - High Resolution 32x16.jpg",
    "arnolfini-portrait": "File:Van Eyck - Arnolfini Portrait.jpg",
    "wedding-at-cana": "File:Paolo Veronese 008.jpg",
    "harvesters": "File:Pieter Bruegel d. Ä. 002.jpg",
    "ambassadors": "File:Hans Holbein the Younger - The Ambassadors - Google Art Project.jpg",
}


def strip_html(v: str) -> str:
    v = re.sub(r"<[^>]+>", " ", v)
    return re.sub(r"\s+", " ", v).strip()


def meta_get(meta: dict, key: str) -> str:
    return strip_html((meta.get(key) or {}).get("value") or "")


def fetch(title: str) -> dict:
    q = urllib.parse.urlencode(
        {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "extmetadata|url|size|mime",
            "format": "json",
        }
    )
    url = "https://commons.wikimedia.org/w/api.php?" + q
    req = urllib.request.Request(url, headers={"User-Agent": "PeregrenationBot/0.1 (license audit; local authoring)"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def main() -> None:
    out: dict[str, dict] = {}
    for pid, title in TITLES.items():
        data = fetch(title)
        page = next(iter(data["query"]["pages"].values()))
        if "missing" in page:
            out[pid] = {"ok": False, "error": "missing", "title": title}
            print(f"{pid}: MISSING")
            continue
        ii = page["imageinfo"][0]
        meta = ii.get("extmetadata") or {}
        license_short = meta_get(meta, "LicenseShortName")
        copyrighted = meta_get(meta, "Copyrighted")
        license_code = meta_get(meta, "License")
        pd = license_short.lower() in {"public domain", "pd", "cc0"} or license_code.lower() in {
            "pd",
            "cc0",
            "cc-zero",
        }
        if copyrighted.lower() == "false":
            pd = True
        record = {
            "ok": pd,
            "commonsTitle": title,
            "commonsUrl": "https://commons.wikimedia.org/wiki/" + title.replace(" ", "_"),
            "licenseShortName": license_short,
            "license": license_code,
            "usageTerms": meta_get(meta, "UsageTerms"),
            "copyrighted": copyrighted,
            "artist": meta_get(meta, "Artist")[:200],
            "credit": meta_get(meta, "Credit")[:240],
            "attributionRequired": meta_get(meta, "AttributionRequired"),
            "mime": ii.get("mime"),
            "width": ii.get("width"),
            "height": ii.get("height"),
        }
        out[pid] = record
        flag = "PD" if pd else "NOT PD"
        print(f"{pid}: {flag} | {license_short or license_code} | copyrighted={copyrighted}")
        time.sleep(1.25)

    report = ROOT / "data" / "paintings" / "license-audit.json"
    report.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {report}")
    bad = [k for k, v in out.items() if not v.get("ok")]
    if bad:
        raise SystemExit(f"Non-PD sources: {', '.join(bad)}")


if __name__ == "__main__":
    main()
