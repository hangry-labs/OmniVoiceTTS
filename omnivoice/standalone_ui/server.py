from __future__ import annotations

import html
import json
import mimetypes
import os
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from omnivoice.standalone_ui.gpu import GPU_MONITOR
from omnivoice.web.translations import UI_FALLBACK_LOCALE, UI_LOCALES, UI_STRINGS


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
ENGLISH_CATALOG_PATH = STATIC_DIR / "locales" / "en.json"
REPO_ROOT = PACKAGE_DIR.parents[1]
SOURCE_ASSET_DIR = REPO_ROOT / "assets"
PACKAGED_ASSET_DIR = PACKAGE_DIR / "assets"
ASSET_DIR = SOURCE_ASSET_DIR if SOURCE_ASSET_DIR.is_dir() else PACKAGED_ASSET_DIR

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("font/woff2", ".woff2")

MESSAGE_ALIASES = {
    "locale.label": "ui_language.label",
    "tabs.generate": "generate.label",
    "inference.language": "language.label",
    "inference.device": "hardware.label",
    "inference.outputFormat": "output_format.label",
    "inference.mode": "mode.label",
    "modes.random": "mode.no_voice_prompt",
    "modes.design": "mode.voice_design",
    "modes.clone": "mode.voice_clone",
    "composer.text": "input_text.label",
    "composer.defaultText": "input_text.default",
    "generation.speed": "speed.label",
    "generation.steps": "num_step.label",
    "generation.guidance": "guidance_scale.label",
    "generation.padding": "pad_duration.label",
    "generation.fade": "fade_duration.label",
    "generation.seed": "seed.label",
    "generation.randomSeed": "randomize_seed.label",
    "generation.pitch": "pitch.label",
    "generation.tempo": "tempo.label",
    "generation.volume": "volume.label",
    "generation.normalize": "normalize_loudness.label",
    "clone.audio": "reference_audio.label",
    "clone.transcript": "reference_text.label",
    "output.audio": "output_audio.label",
    "common.stop": "stop_generation.label",
}


def _read_version_file() -> str:
    for version_path in (REPO_ROOT / "VERSION", PACKAGE_DIR / "VERSION"):
        try:
            version = version_path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version:
            return version
    return "0.0.0"


@lru_cache(maxsize=1)
def _english_catalog() -> dict[str, str]:
    payload = json.loads(ENGLISH_CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("The English UI catalog must be a JSON object.")
    return {str(key): str(value) for key, value in payload.items()}


def _message(locale: str, key: str, fallback: str) -> str:
    source_key = MESSAGE_ALIASES.get(key)
    if not source_key:
        return fallback
    translations = UI_STRINGS.get(source_key, {})
    if not isinstance(translations, dict):
        return fallback
    return str(
        translations.get(locale)
        or translations.get(UI_FALLBACK_LOCALE)
        or translations.get("en")
        or fallback
    )


@lru_cache(maxsize=128)
def _locale_catalog(locale: str) -> dict[str, str]:
    english = _english_catalog()
    return {key: _message(locale, key, value) for key, value in english.items()}


def _locale_manifest() -> dict[str, object]:
    locales = [
        {
            "code": code,
            "name": label,
            "path": f"/{code}",
            "direction": "rtl" if code in {"ar", "fa", "he", "ur"} else "ltr",
            "browserLanguage": code,
        }
        for code, label in sorted(UI_LOCALES.items(), key=lambda item: item[1].casefold())
    ]
    default_locale = UI_FALLBACK_LOCALE if UI_FALLBACK_LOCALE in UI_LOCALES else "en"
    return {"defaultLocale": default_locale, "locales": locales}


def _index_response(locale: str) -> HTMLResponse:
    manifest = _locale_manifest()
    locale_entry = next(item for item in manifest["locales"] if item["code"] == locale)
    bootstrap = {
        "locale": locale,
        "defaultLocale": manifest["defaultLocale"],
        "locales": manifest["locales"],
        "storageKey": "omnivoicetts-ui-locale-v1",
        "messages": _locale_catalog(locale),
    }
    bootstrap_json = json.dumps(bootstrap, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    index_html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    rendered = (
        index_html.replace("{{UI_VERSION}}", html.escape(_read_version_file()))
        .replace("{{UI_LOCALE}}", html.escape(locale))
        .replace("{{UI_DIRECTION}}", str(locale_entry["direction"]))
        .replace("{{UI_BOOTSTRAP}}", bootstrap_json)
    )
    return HTMLResponse(rendered, headers={"Cache-Control": "no-cache"})


def attach_ui(*, api_app: FastAPI) -> FastAPI:
    """Attach the offline browser workspace to the existing TTS API."""
    development_assets = os.getenv("OMNIVOICE_UI_DEV", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    manifest = _locale_manifest()
    locale_paths = {str(item["path"]) for item in manifest["locales"]}

    @api_app.middleware("http")
    async def disable_development_asset_cache(request, call_next):
        response = await call_next(request)
        if development_assets and (
            request.url.path == "/"
            or request.url.path in locale_paths
            or request.url.path.startswith("/static/")
            or request.url.path.startswith("/assets/")
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    api_app.mount("/static", StaticFiles(directory=STATIC_DIR), name="ui-static")
    if ASSET_DIR.is_dir():
        api_app.mount("/assets", StaticFiles(directory=ASSET_DIR), name="ui-assets")

    @api_app.get("/", include_in_schema=False)
    async def index() -> HTMLResponse:
        return _index_response(str(manifest["defaultLocale"]))

    def locale_handler(locale: str):
        async def localized_index() -> HTMLResponse:
            return _index_response(locale)

        return localized_index

    for locale_entry in manifest["locales"]:
        locale = str(locale_entry["code"])
        api_app.add_api_route(
            str(locale_entry["path"]),
            locale_handler(locale),
            methods=["GET"],
            include_in_schema=False,
            name=f"ui-{locale}",
        )

    @api_app.get("/system/gpu", tags=["System"], summary="Current GPU telemetry")
    def gpu() -> JSONResponse:
        return JSONResponse(GPU_MONITOR.request_snapshot(), headers={"Cache-Control": "no-store"})

    return api_app
