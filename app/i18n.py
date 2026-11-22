"""JSON-backed translations and request language negotiation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LOCALE_DIR = Path(__file__).resolve().parent / "locales"
SUPPORTED_LOCALES = ("ru", "en", "zh")
DEFAULT_LOCALE = "en"
LANGUAGE_COOKIE = "lang"
LANGUAGE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
LANGUAGES = (
    {"code": "ru", "label": "RU"},
    {"code": "en", "label": "EN"},
    {"code": "zh", "label": "中文"},
)


@lru_cache(maxsize=None)
def _load_locale(locale: str) -> dict[str, str]:
    with (LOCALE_DIR / f"{locale}.json").open(encoding="utf-8") as locale_file:
        return json.load(locale_file)


def is_supported(locale: str | None) -> bool:
    """Return whether a locale can be used for the site."""
    return locale is not None and locale.lower() in SUPPORTED_LOCALES


def translate(locale: str, key: str, **values: object) -> str:
    """Translate a key, falling back to English and then to the key itself."""
    text = _load_locale(locale).get(key) or _load_locale(DEFAULT_LOCALE).get(key) or key
    return text.format(**values) if values else text


def _from_accept_language(header: str | None) -> str | None:
    if not header:
        return None

    choices: list[tuple[float, int, str]] = []
    for position, part in enumerate(header.split(",")):
        code, *parameters = part.strip().split(";")
        language = code.strip().lower().split("-")[0]
        if language not in SUPPORTED_LOCALES:
            continue
        quality = 1.0
        for parameter in parameters:
            name, _, value = parameter.strip().partition("=")
            if name == "q":
                try:
                    quality = float(value)
                except ValueError:
                    quality = 0.0
        if quality > 0:
            choices.append((-quality, position, language))
    return min(choices)[2] if choices else None


def resolve_locale(
    requested: str | None,
    stored: str | None,
    accept_language: str | None,
) -> str:
    """Choose query language, then cookie, then browser language, then English."""
    for candidate in (requested, stored):
        if candidate is not None and is_supported(candidate):
            return candidate.lower()
    return _from_accept_language(accept_language) or DEFAULT_LOCALE
