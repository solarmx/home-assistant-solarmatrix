"""Regenerate translation files from strings.json + glossary.

Usage:
    python scripts/translate.py            # regenerate missing/changed locales
    python scripts/translate.py --check    # exit non-zero if drift detected

Requires:
    OPENAI_API_KEY (or set MODEL=anthropic + ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
TRANSLATIONS_DIR = ROOT / "custom_components" / "solarmatrix" / "translations"
SOURCE = TRANSLATIONS_DIR / "en.json"
LOCALES = ROOT / "scripts" / "locales.json"
GLOSSARY = ROOT / "scripts" / "glossary.json"


def _flatten(d: Any, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(d, str):
        out[prefix] = d
    return out


def _unflatten(flat: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in flat.items():
        cursor = out
        parts = k.split(".")
        for p in parts[:-1]:
            cursor = cursor.setdefault(p, {})
        cursor[parts[-1]] = v
    return out


def _source_hash() -> str:
    """Hash the source content, ignoring any prior ``__source_hash`` stamp.

    Computed by canonicalising the JSON without the bookkeeping key so the
    stamp is stable across regen cycles.
    """
    body = json.loads(SOURCE.read_text())
    body.pop("__source_hash", None)
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def translate(locale: str, source_flat: dict[str, str], glossary: dict[str, Any]) -> dict[str, str]:
    """Translate source_flat into locale, respecting glossary pins.

    Implementation note: this script can be run by maintainers offline. The
    actual LLM call lives behind an ``os.system``-able shim so CI doesn't
    need network. For local regen, set MODEL and an API key.
    """
    if locale == "en":
        return source_flat

    model = os.getenv("MODEL", "openai")
    if model == "openai":
        from openai import OpenAI

        client = OpenAI()
        prompt = (
            "Translate the following Home Assistant integration strings into "
            f"locale {locale!r}. Preserve placeholders, JSON keys, and the "
            f"glossary mappings: {json.dumps(glossary)}. Return JSON only."
        )
        body = json.dumps(source_flat, ensure_ascii=False)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"{prompt}\n\n{body}"}],
            response_format={"type": "json_object"},
        )
        return json.loads(resp.choices[0].message.content)
    if model == "anthropic":
        import anthropic

        client = anthropic.Anthropic()
        prompt = (
            "Translate this JSON object's values to "
            f"locale {locale!r}. Keep keys identical. Glossary "
            f"(do not paraphrase pinned terms): {json.dumps(glossary)}. "
            "Return JSON only, no prose."
        )
        body = json.dumps(source_flat, ensure_ascii=False)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            messages=[{"role": "user", "content": f"{prompt}\n\n{body}"}],
        )
        return json.loads(resp.content[0].text)
    if model == "placeholder":
        # Used by maintainers/CI when no LLM token is available. Copies the
        # English source verbatim so the integration is shippable; running
        # maintainers should re-run with ``MODEL=openai`` or ``anthropic``.
        return dict(source_flat)
    raise SystemExit(f"unsupported MODEL={model}")


def main(check: bool) -> int:
    locales = json.loads(LOCALES.read_text())
    glossary = json.loads(GLOSSARY.read_text())
    source = json.loads(SOURCE.read_text())
    source_flat = _flatten(source)
    src_hash = _source_hash()
    drift = False

    for locale in locales:
        out = TRANSLATIONS_DIR / f"{locale}.json"
        if out.exists():
            existing = json.loads(out.read_text())
            stamp = existing.get("__source_hash")
            if stamp == src_hash and not check:
                continue
            if stamp == src_hash and check:
                continue
            if check:
                drift = True
                print(f"drift detected for {locale}")
                continue

        if check:
            drift = True
            print(f"missing translation for {locale}")
            continue

        translated = translate(locale, source_flat, glossary)
        body = _unflatten(translated)
        body["__source_hash"] = src_hash
        out.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n")
        print(f"wrote {out.name}")

    return 1 if drift else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    sys.exit(main(args.check))
