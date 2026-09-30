"""Artifact cache keyed by pipelineVersion fields in manifest.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def painting_dir(painting_id: str) -> Path:
    return ROOT / "data" / "paintings" / painting_id


def load_manifest(painting_id: str) -> dict:
    path = painting_dir(painting_id) / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def artifact_stale(painting_id: str, artifact: Path, version_key: str) -> bool:
    if not artifact.exists():
        return True
    manifest = load_manifest(painting_id)
    stamp = painting_dir(painting_id) / ".cache" / f"{version_key}.txt"
    if not stamp.exists():
        return True
    expected = manifest.get(version_key, "")
    return stamp.read_text(encoding="utf-8").strip() != str(expected)


def mark_artifact(painting_id: str, version_key: str) -> None:
    manifest = load_manifest(painting_id)
    cache_dir = painting_dir(painting_id) / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{version_key}.txt").write_text(
        str(manifest.get(version_key, "")), encoding="utf-8"
    )
