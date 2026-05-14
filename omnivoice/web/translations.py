from __future__ import annotations

import json
import os
from pathlib import Path

TRANSLATIONS_FILE = Path(__file__).resolve().parent.parent / "ui_translations.json"
UI_LOCALE = os.getenv("OMNIVOICE_UI_LOCALE", "en").strip().lower() or "en"


def load_ui_translations() -> dict[str, dict[str, str]]:
    if not TRANSLATIONS_FILE.exists():
        return {}
    try:
        return json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def normalize_ui_translations(raw_translations: dict) -> tuple[dict[str, str], dict[str, dict[str, str]], str]:
    if not isinstance(raw_translations, dict):
        return {"en": "English"}, {}, "en"
    if isinstance(raw_translations.get("locales"), dict) and isinstance(raw_translations.get("strings"), dict):
        meta = raw_translations.get("_meta", {})
        fallback = str(meta.get("fallback_locale") or "en") if isinstance(meta, dict) else "en"
        return raw_translations["locales"], raw_translations["strings"], fallback

    locales = {}
    strings: dict[str, dict[str, str]] = {}
    for locale, values in raw_translations.items():
        if locale.startswith("_") or not isinstance(values, dict):
            continue
        locales[locale] = str(values.get("locale.name") or locale)
        for key, value in values.items():
            if key == "locale.name":
                continue
            strings.setdefault(key, {})[locale] = str(value)
    return locales or {"en": "English"}, strings, "en"


UI_TRANSLATIONS = load_ui_translations()
UI_LOCALES, UI_STRINGS, UI_FALLBACK_LOCALE = normalize_ui_translations(UI_TRANSLATIONS)


def normalize_ui_locale(locale: str | None = None) -> str:
    value = (locale or UI_LOCALE).strip().lower()
    if value in UI_LOCALES:
        return value
    return UI_FALLBACK_LOCALE if UI_FALLBACK_LOCALE in UI_LOCALES else "en"


def ui_text_for(locale: str | None, key: str) -> str:
    selected_locale = normalize_ui_locale(locale)
    translations = UI_STRINGS.get(key, {})
    if not isinstance(translations, dict):
        return key
    return translations.get(selected_locale) or translations.get(UI_FALLBACK_LOCALE) or translations.get("en") or key


def ui_text(key: str) -> str:
    return ui_text_for(UI_LOCALE, key)


def ui_locale_choices() -> list[tuple[str, str]]:
    choices = [(label, locale) for locale, label in sorted(UI_LOCALES.items(), key=lambda item: item[1].casefold())]
    return choices or [("English", "en")]
