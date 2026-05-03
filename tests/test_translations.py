"""Translation files must have the same shape as the source."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS_DIR = ROOT / "custom_components" / "solarmatrix" / "translations"
LOCALES_FILE = ROOT / "scripts" / "locales.json"


def _flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            if k == "__source_hash":
                continue
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else k))
    else:
        out[prefix] = type(d).__name__
    return out


def test_all_supported_locales_present():
    expected = set(json.loads(LOCALES_FILE.read_text()))
    have = {p.stem for p in TRANSLATIONS_DIR.glob("*.json")}
    missing = expected - have
    assert not missing, f"missing translations: {sorted(missing)}"


def test_all_translations_match_source_shape():
    source = json.loads((TRANSLATIONS_DIR / "en.json").read_text())
    source_keys = set(_flatten(source).keys())
    for path in TRANSLATIONS_DIR.glob("*.json"):
        body = json.loads(path.read_text())
        keys = set(_flatten(body).keys())
        missing = source_keys - keys
        extra = keys - source_keys
        assert not missing, f"{path.name} missing keys: {sorted(missing)}"
        assert not extra, f"{path.name} has extra keys: {sorted(extra)}"
