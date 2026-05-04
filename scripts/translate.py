"""Regenerate translation files from strings.json + glossary.

Usage:
    python scripts/translate.py            # regenerate missing/changed locales
    python scripts/translate.py --check    # exit non-zero if drift detected

Requires:
    OPENAI_API_KEY (or set MODEL=anthropic + ANTHROPIC_API_KEY)

The current source hash is recorded in scripts/translation_state.json and
compared on --check. Hassfest's translation schema rejects extra keys, so
the bookkeeping cannot live inside the translation files themselves.
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
STATE_FILE = ROOT / "scripts" / "translation_state.json"


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
    body = json.loads(SOURCE.read_text())
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(canonical).hexdigest()


def _stored_hash() -> str | None:
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text()).get("source_hash")


def translate(locale: str, source_flat: dict[str, str], glossary: dict[str, Any]) -> dict[str, str]:
    if locale == "en":
        return source_flat

    model = os.getenv("MODEL", "openai")
    if model == "openai":
        from openai import OpenAI

        client = OpenAI()
        prompt = (
            "Translate the following Home Assistant integration strings into "
            f"locale {locale!r}. Preserve placeholders (text inside curly "
            f"braces like {{api_keys_url}}), JSON keys, and the glossary "
            f"mappings: {json.dumps(glossary)}. Return JSON only."
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
            f"locale {locale!r}. Keep keys and curly-brace placeholders "
            f"(e.g. {{api_keys_url}}) untouched. Glossary "
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
        # Used by CI when no LLM token is available. Copies the English source
        # verbatim so drift checks pass; maintainers should re-run with a real
        # MODEL before publishing user-facing changes.
        return dict(source_flat)
    raise SystemExit(f"unsupported MODEL={model}")


def main(check: bool) -> int:
    locales = json.loads(LOCALES.read_text())
    glossary = json.loads(GLOSSARY.read_text())
    source = json.loads(SOURCE.read_text())
    source_flat = _flatten(source)
    current_hash = _source_hash()
    stored_hash = _stored_hash()

    if check:
        if stored_hash != current_hash:
            print(
                f"drift: source hash {current_hash} does not match recorded "
                f"{stored_hash}. Re-run scripts/translate.py to regenerate."
            )
            return 1
        missing = [
            locale for locale in locales
            if not (TRANSLATIONS_DIR / f"{locale}.json").exists()
        ]
        if missing:
            print(f"missing translations for: {', '.join(missing)}")
            return 1
        return 0

    for locale in locales:
        out = TRANSLATIONS_DIR / f"{locale}.json"
        translated = translate(locale, source_flat, glossary)
        body = _unflatten(translated)
        out.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n")
        print(f"wrote {out.name}")

    STATE_FILE.write_text(
        json.dumps({"source_hash": current_hash}, indent=2) + "\n"
    )
    print(f"updated {STATE_FILE}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    sys.exit(main(args.check))
