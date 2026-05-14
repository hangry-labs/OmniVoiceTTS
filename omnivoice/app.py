from __future__ import annotations

import io
import html
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import threading
import wave
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

import gradio as gr
import numpy as np
import torch
import uvicorn
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from omnivoice import OmniVoice, OmniVoiceGenerationConfig, __version__
from omnivoice.utils.common import fix_random_seed
from omnivoice.utils.lang_map import LANG_IDS, LANG_NAMES, LANG_NAME_TO_ID, lang_display_name

DEFAULT_MODEL = os.getenv("OMNIVOICE_MODEL", "k2-fsa/OmniVoice")
DEFAULT_DEVICE = os.getenv("OMNIVOICE_DEVICE", "auto")
DEFAULT_ASR_MODEL = os.getenv("OMNIVOICE_ASR_MODEL", "openai/whisper-large-v3-turbo")
LOAD_ASR = os.getenv("OMNIVOICE_LOAD_ASR", "1").lower() in {"1", "true", "yes", "y"}
APP_VERSION = os.getenv("APP_VERSION", __version__)
BUILD_ID = os.getenv("BUILD_ID", "stable")
SAMPLE_RATE = 24000
ASSET_DIR = Path(__file__).resolve().parent.parent / "hangrylabs"
BRAND_ASSET_BASE = "/assets/hangrylabs"
TRANSLATIONS_FILE = Path(__file__).resolve().parent / "ui_translations.json"
UI_LOCALE = os.getenv("OMNIVOICE_UI_LOCALE", "en").strip().lower() or "en"
PACKAGE_DIR = Path(__file__).resolve().parent
OPENAI_DEFAULT_CLONE_AUDIO = PACKAGE_DIR / "assets" / "openai_default_voice.mp3"
OPENAI_VOICE_PROFILE_DIR = Path(os.getenv("OMNIVOICE_OPENAI_VOICE_PROFILE_DIR", "/app/openai_voice_profiles"))
OPENAI_VOICE_PROFILE_INDEX = OPENAI_VOICE_PROFILE_DIR / "profiles.json"

OUTPUT_FORMATS = {
    "wav": {
        "label": "WAV",
        "extension": "wav",
        "media_type": "audio/wav",
        "ffmpeg_args": None,
    },
    "mp3": {
        "label": "MP3",
        "extension": "mp3",
        "media_type": "audio/mpeg",
        "ffmpeg_args": ["-f", "mp3", "-codec:a", "libmp3lame", "-b:a", "192k"],
    },
    "flac": {
        "label": "FLAC",
        "extension": "flac",
        "media_type": "audio/flac",
        "ffmpeg_args": ["-f", "flac", "-codec:a", "flac"],
    },
    "ogg": {
        "label": "OGG Vorbis",
        "extension": "ogg",
        "media_type": "audio/ogg",
        "ffmpeg_args": ["-f", "ogg", "-codec:a", "libvorbis", "-q:a", "5"],
    },
}
FORMAT_ALIASES = {
    ".wav": "wav",
    ".mp3": "mp3",
    ".flac": "flac",
    ".ogg": "ogg",
    "mpeg": "mp3",
    "vorbis": "ogg",
    "opus": "ogg",
}
OPENAI_MODEL_ALIASES = {
    "omnivoice": "omnivoice",
    "omnivoicetts": "omnivoice",
    "tts-1": "omnivoice",
    "tts-1-hd": "omnivoice",
    "gpt-4o-mini-tts": "omnivoice",
}
OPENAI_MODEL_IDS = ["omnivoice", "tts-1", "tts-1-hd", "gpt-4o-mini-tts"]
OPENAI_VOICE_INSTRUCTIONS = {
    "default": None,
    "auto": None,
    "alloy": "female, young adult, moderate pitch",
    "echo": "male, middle-aged, low pitch",
    "fable": "female, young adult, high pitch",
    "onyx": "male, middle-aged, very low pitch",
    "nova": "female, young adult, high pitch",
    "shimmer": "female, young adult, moderate pitch",
}
OPENAI_CLONE_VOICE_ALIASES = {"default", "alloy", "echo", "fable", "onyx", "nova", "shimmer"}

BRACKET_TOKEN_PATTERN = re.compile(r"\[[^\]\r\n]{1,80}\]")
SUPPORTED_NONVERBAL_TAGS = [
    "[laughter]",
    "[sigh]",
    "[confirmation-en]",
    "[question-en]",
    "[question-ah]",
    "[question-oh]",
    "[question-ei]",
    "[question-yi]",
    "[surprise-ah]",
    "[surprise-oh]",
    "[surprise-wa]",
    "[surprise-yo]",
    "[dissatisfaction-hnn]",
]
VOICE_DESIGN_BRACKET_TOKEN_MESSAGE = (
    "Voice Design does not support bracket tags such as [laughter] or [sigh]. "
    "Use No Voice Prompt or Voice Clone for expressive bracket tags, or remove the bracket tag when using Voice Design."
)

MODEL_CACHE: dict[str, OmniVoice] = {}
MODEL_LOCK = threading.Lock()
UI_CANCEL_EVENT = threading.Event()
UI_STREAM_LOCK = threading.Lock()
UI_STREAM_GENERATION = 0
GPU_HISTORY: dict[int, list[int]] = {}
OPENAI_CALL_LOG: list[dict[str, str]] = []
OPENAI_CALL_LOG_LOCK = threading.Lock()
OPENAI_CALL_LOG_LIMIT = 50


def next_ui_stream_generation() -> int:
    global UI_STREAM_GENERATION
    with UI_STREAM_LOCK:
        UI_STREAM_GENERATION += 1
        return UI_STREAM_GENERATION


def is_current_ui_stream_generation(stream_generation: int) -> bool:
    with UI_STREAM_LOCK:
        return stream_generation == UI_STREAM_GENERATION


def stop_active_ui_stream():
    UI_CANCEL_EVENT.set()
    next_ui_stream_generation()
    return SAMPLE_RATE, np.zeros(1, dtype=np.int16)


def read_gpu_stats() -> list[dict[str, float | int | str]]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []

    rows = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 7:
            continue
        try:
            rows.append(
                {
                    "index": int(float(parts[0])),
                    "name": parts[1],
                    "utilization": int(float(parts[2])),
                    "memory_used": int(float(parts[3])),
                    "memory_total": int(float(parts[4])),
                    "temperature": int(float(parts[5])),
                    "power": float(parts[6]),
                }
            )
        except ValueError:
            continue
    return rows


def gpu_monitor_html() -> str:
    stats = read_gpu_stats()
    if not stats:
        return """
<div class="gpu-monitor">
  <div class="gpu-monitor-title">GPU Monitor</div>
  <div class="gpu-monitor-muted">nvidia-smi unavailable</div>
</div>
"""

    cards = []
    for item in stats:
        index = int(item["index"])
        usage = int(item["utilization"])
        history = GPU_HISTORY.setdefault(index, [])
        history.append(usage)
        del history[:-60]
        points = gpu_history_points(history)
        mem_used = float(item["memory_used"]) / 1024
        mem_total = float(item["memory_total"]) / 1024
        mem_pct = 0 if mem_total <= 0 else min(100, max(0, mem_used / mem_total * 100))
        cards.append(
            f"""
  <div class="gpu-card">
    <div class="gpu-card-head">
      <strong>GPU {index}</strong>
      <span>{html.escape(str(item["name"]))}</span>
    </div>
    <div class="gpu-metric-row">
      <span>Load</span>
      <strong>{usage}%</strong>
    </div>
    <div class="gpu-bar"><span style="width:{usage}%"></span></div>
    <svg class="gpu-sparkline" viewBox="0 0 180 44" preserveAspectRatio="none" aria-hidden="true">
      <polyline points="{points}" fill="none" stroke="#ff8a1f" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" />
    </svg>
    <div class="gpu-metric-row">
      <span>VRAM</span>
      <strong>{mem_used:.1f}/{mem_total:.1f} GB</strong>
    </div>
    <div class="gpu-bar gpu-vram"><span style="width:{mem_pct:.1f}%"></span></div>
    <div class="gpu-foot">
      <span>{int(item["temperature"])} C</span>
      <span>{float(item["power"]):.0f} W</span>
    </div>
  </div>
"""
        )

    return f"""
<div class="gpu-monitor">
  <div class="gpu-monitor-title">GPU Monitor</div>
  {''.join(cards)}
</div>
"""


def gpu_history_points(values: list[int], width: int = 180, height: int = 44) -> str:
    if not values:
        return f"0,{height} {width},{height}"
    if len(values) == 1:
        y = height - (values[0] / 100 * height)
        return f"0,{y:.1f} {width},{y:.1f}"
    return " ".join(
        f"{i * width / (len(values) - 1):.1f},{height - (value / 100 * height):.1f}"
        for i, value in enumerate(values)
    )

VOICE_DESIGN_CATEGORIES = {
    "gender": {
        "label": "Gender",
        "options": ["male", "female"],
    },
    "age": {
        "label": "Age",
        "options": ["child", "teenager", "young adult", "middle-aged", "elderly"],
    },
    "pitch": {
        "label": "Pitch",
        "options": ["very low pitch", "low pitch", "moderate pitch", "high pitch", "very high pitch"],
    },
    "style": {
        "label": "Style",
        "options": ["whisper"],
    },
    "english_accent": {
        "label": "English Accent",
        "options": [
            "american accent",
            "australian accent",
            "british accent",
            "chinese accent",
            "canadian accent",
            "indian accent",
            "korean accent",
            "portuguese accent",
            "russian accent",
            "japanese accent",
        ],
        "note": "Only effective for English speech.",
    },
    "chinese_dialect": {
        "label": "Chinese Dialect",
        "options": [
            "河南话",
            "陕西话",
            "四川话",
            "贵州话",
            "云南话",
            "桂林话",
            "济南话",
            "石家庄话",
            "甘肃话",
            "宁夏话",
            "青岛话",
            "东北话",
        ],
        "note": "Only effective for Chinese speech.",
    },
}

MAX_RANDOM_SEED = 2**32 - 1


def read_version_file() -> str:
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return APP_VERSION


def load_ui_translations() -> dict[str, dict[str, str]]:
    if not TRANSLATIONS_FILE.exists():
        return {}
    try:
        return json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


UI_TRANSLATIONS = load_ui_translations()


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


def get_build_label() -> str:
    build_date = os.getenv("BUILD_DATE", "").strip()
    if build_date:
        return normalize_build_label(build_date)
    build_date_file = Path(__file__).resolve().parent.parent / "BUILD_DATE"
    if build_date_file.exists():
        return normalize_build_label(build_date_file.read_text(encoding="utf-8").strip())
    timestamp = Path(__file__).stat().st_mtime
    return datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y %H:%M:%S")


def normalize_build_label(value: str) -> str:
    value = value.strip()
    for date_format in ("%d.%m.%Y %H:%M:%S", "%d:%m:%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, date_format).strftime("%d.%m.%Y %H:%M:%S")
        except ValueError:
            continue
    return value


def get_cuda_devices() -> list[str]:
    if not torch.cuda.is_available():
        return []
    return [torch.cuda.get_device_name(idx) for idx in range(torch.cuda.device_count())]


def get_runtime_label() -> str:
    cuda_devices = get_cuda_devices()
    if cuda_devices:
        visible = os.getenv("CUDA_VISIBLE_DEVICES", "all")
        device_list = ", ".join(f"{idx}:{name}" for idx, name in enumerate(cuda_devices))
        return f"GPU x{len(cuda_devices)} (visible={visible}) [{device_list}]"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "Apple MPS"
    return "CPU"


def get_banner_runtime_html() -> str:
    version = html.escape(read_version_file())
    build = html.escape(get_build_label())
    cuda_devices = get_cuda_devices()
    if cuda_devices:
        visible = os.getenv("CUDA_VISIBLE_DEVICES", "").strip()
        visible_ids = [part.strip() for part in visible.split(",") if part.strip()] if visible and visible.lower() != "all" else []
        gpu_lines = []
        for idx, name in enumerate(cuda_devices):
            display_idx = visible_ids[idx] if idx < len(visible_ids) else str(idx)
            gpu_lines.append(f"{html.escape(display_idx)} : {html.escape(name)}")
        hardware = "GPUs :<br>" + "<br>".join(gpu_lines)
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        hardware = "Runtime : Apple MPS"
    else:
        hardware = "Runtime : CPU"
    return f"v{version} | Build {build}<br>{hardware}"


def get_hardware_choices() -> list[tuple[str, str]]:
    choices = [("Auto", "auto"), ("CPU", "cpu")]
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        choices.append(("Apple MPS", "mps"))
    for idx, name in enumerate(get_cuda_devices()):
        choices.append((f"GPU {idx} ({name})", f"cuda:{idx}"))
    return choices


def normalize_device(device: str | None) -> str:
    hardware = (device or "auto").strip().lower()
    if hardware == "auto":
        if get_cuda_devices():
            return "cuda:0"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    if hardware in {"gpu", "cuda"}:
        hardware = "cuda:0"
    if hardware == "cpu":
        return "cpu"
    if hardware == "mps":
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        raise RuntimeError("MPS device requested but MPS is not available")
    if hardware.startswith("cuda"):
        cuda_devices = get_cuda_devices()
        if not cuda_devices:
            raise RuntimeError("CUDA device requested but CUDA is not available")
        try:
            device_index = int(hardware.split(":", 1)[1])
        except (IndexError, ValueError) as exc:
            raise RuntimeError(f"Unsupported device '{device}'. Use auto, cpu, mps, or cuda:N.") from exc
        if device_index < 0 or device_index >= len(cuda_devices):
            raise RuntimeError(
                f"CUDA device index {device_index} is not available. "
                f"Visible CUDA devices: 0-{len(cuda_devices) - 1}."
            )
        return f"cuda:{device_index}"
    raise RuntimeError(f"Unsupported device '{device}'. Use auto, cpu, mps, or cuda:N.")


def resolve_requested_device(device: str, use_gpu: Optional[bool] = None) -> str:
    if use_gpu is True:
        return "auto"
    if use_gpu is False:
        return "cpu"
    return device


def get_model(device: str) -> OmniVoice:
    resolved_device = normalize_device(device)
    with MODEL_LOCK:
        if resolved_device not in MODEL_CACHE:
            dtype = torch.float16 if resolved_device.startswith("cuda") else torch.float32
            MODEL_CACHE[resolved_device] = OmniVoice.from_pretrained(
                DEFAULT_MODEL,
                device_map=resolved_device,
                dtype=dtype,
                load_asr=LOAD_ASR,
                asr_model_name=DEFAULT_ASR_MODEL,
            )
        return MODEL_CACHE[resolved_device]


def normalize_language(language: str | None) -> str | None:
    value = (language or "").strip()
    if not value or value.lower() == "auto":
        return None
    if value in LANG_IDS:
        return value
    key = value.lower()
    return LANG_NAME_TO_ID.get(key, value)


def normalize_output_format(output_format: str | None) -> str:
    normalized = (output_format or "wav").strip().lower()
    normalized = FORMAT_ALIASES.get(normalized, normalized)
    if normalized not in OUTPUT_FORMATS:
        supported = ", ".join(OUTPUT_FORMATS)
        raise ValueError(f"Unsupported output format '{output_format}'. Supported formats: {supported}")
    return normalized


def voice_design_options_payload() -> dict:
    return {
        "categories": [
            {
                "id": key,
                "label": category["label"],
                "options": category["options"],
                "note": category.get("note"),
            }
            for key, category in VOICE_DESIGN_CATEGORIES.items()
        ],
        "separator": ", ",
    }


def build_voice_design_instruct(*selected_options: str | None, manual_instruct: str | None = None) -> str | None:
    parts = [
        str(option).strip()
        for option in selected_options
        if option and str(option).strip() and str(option).strip().lower() not in {"auto", "no preference"}
    ]
    manual_value = (manual_instruct or "").strip()
    if manual_value:
        parts.append(manual_value)
    if not parts:
        return None
    return ", ".join(parts)


def build_auto_voice_instruct(text: str | None) -> tuple[str | None, str | None]:
    if has_bracket_token(text):
        return None, "True no-prompt mode used because expressive bracket tags are present."
    return None, "True no-prompt mode used."


def has_bracket_token(text: str | None) -> bool:
    return bool(BRACKET_TOKEN_PATTERN.search(text or ""))


def validate_voice_design_text(text: str | None, instruct: str | None) -> None:
    if (instruct or "").strip() and has_bracket_token(text):
        raise ValueError(VOICE_DESIGN_BRACKET_TOKEN_MESSAGE)


def nonverbal_tags_markdown() -> str:
    tags = ", ".join(f"`{tag}`" for tag in SUPPORTED_NONVERBAL_TAGS)
    return nonverbal_tags_markdown_for(UI_LOCALE)


def nonverbal_tags_markdown_for(locale: str | None) -> str:
    tags = ", ".join(f"`{tag}`" for tag in SUPPORTED_NONVERBAL_TAGS)
    return (
        f"### {ui_text_for(locale, 'nonverbal.title')}\n\n"
        f"{ui_text_for(locale, 'nonverbal.intro')}\n\n"
        f"{tags}\n\n"
        f"{ui_text_for(locale, 'nonverbal.placement')}\n\n"
        f"{ui_text_for(locale, 'nonverbal.warning')}"
    )


def mode_choices_for(locale: str | None) -> list[tuple[str, str]]:
    return [
        (ui_text_for(locale, "mode.no_voice_prompt"), "No Voice Prompt"),
        (ui_text_for(locale, "mode.voice_design"), "Voice Design"),
        (ui_text_for(locale, "mode.voice_clone"), "Voice Clone"),
    ]


def default_input_values() -> set[str]:
    defaults = UI_STRINGS.get("input_text.default", {})
    if not isinstance(defaults, dict):
        return set()
    return {str(value).strip() for value in defaults.values() if str(value).strip()}


def input_text_update_for(locale: str | None, current_text: str | None):
    update = gr.update(label=ui_text_for(locale, "input_text.label"))
    current = (current_text or "").strip()
    if not current or current in default_input_values():
        update["value"] = ui_text_for(locale, "input_text.default")
    return update


def ui_locale_updates(locale: str, current_mode: str, current_text: str):
    selected_locale = normalize_ui_locale(locale)
    stable_mode = current_mode if current_mode in {"No Voice Prompt", "Voice Design", "Voice Clone"} else "No Voice Prompt"
    return (
        gr.update(label=ui_text_for(selected_locale, "mode.label"), choices=mode_choices_for(selected_locale), value=stable_mode),
        gr.update(label=ui_text_for(selected_locale, "ui_language.label")),
        input_text_update_for(selected_locale, current_text),
        nonverbal_tags_markdown_for(selected_locale),
        gr.update(value=ui_text_for(selected_locale, "generate.label")),
        ui_text_for(selected_locale, "voice_design.note"),
        gr.update(label=ui_text_for(selected_locale, "language.label"), choices=language_choices_for(selected_locale)),
        gr.update(label=ui_text_for(selected_locale, "design.gender"), choices=design_choices_for(selected_locale, "gender")),
        gr.update(label=ui_text_for(selected_locale, "design.age"), choices=design_choices_for(selected_locale, "age")),
        gr.update(label=ui_text_for(selected_locale, "design.pitch"), choices=design_choices_for(selected_locale, "pitch")),
        gr.update(label=ui_text_for(selected_locale, "design.style"), choices=design_choices_for(selected_locale, "style")),
        gr.update(label=ui_text_for(selected_locale, "design.english_accent"), choices=design_choices_for(selected_locale, "english_accent")),
        gr.update(label=ui_text_for(selected_locale, "design.chinese_dialect"), choices=design_choices_for(selected_locale, "chinese_dialect")),
        gr.update(label=ui_text_for(selected_locale, "reference_audio.label")),
        gr.update(
            label=ui_text_for(selected_locale, "reference_text.label"),
            placeholder=ui_text_for(selected_locale, "reference_text.placeholder"),
            info=ui_text_for(selected_locale, "reference_text.info"),
        ),
        gr.update(label=ui_text_for(selected_locale, "output_audio.label")),
        gr.update(label=ui_text_for(selected_locale, "status.label")),
        gr.update(label=ui_text_for(selected_locale, "hardware.label"), choices=hardware_choices_for(selected_locale)),
        gr.update(label=ui_text_for(selected_locale, "output_format.label")),
        gr.update(label=ui_text_for(selected_locale, "speed.label"), info=ui_text_for(selected_locale, "speed.info")),
        gr.update(label=ui_text_for(selected_locale, "duration.label"), info=ui_text_for(selected_locale, "duration.info")),
        gr.update(label=ui_text_for(selected_locale, "num_step.label"), info=ui_text_for(selected_locale, "num_step.info")),
        gr.update(label=ui_text_for(selected_locale, "guidance_scale.label"), info=ui_text_for(selected_locale, "guidance_scale.info")),
        gr.update(label=ui_text_for(selected_locale, "denoise.label"), info=ui_text_for(selected_locale, "denoise.info")),
        gr.update(label=ui_text_for(selected_locale, "preprocess_prompt.label"), info=ui_text_for(selected_locale, "preprocess_prompt.info")),
        gr.update(label=ui_text_for(selected_locale, "postprocess_output.label"), info=ui_text_for(selected_locale, "postprocess_output.info")),
        gr.update(label=ui_text_for(selected_locale, "t_shift.label"), info=ui_text_for(selected_locale, "t_shift.info")),
        gr.update(label=ui_text_for(selected_locale, "layer_penalty.label"), info=ui_text_for(selected_locale, "layer_penalty.info")),
        gr.update(label=ui_text_for(selected_locale, "position_temperature.label"), info=ui_text_for(selected_locale, "position_temperature.info")),
        gr.update(label=ui_text_for(selected_locale, "class_temperature.label"), info=ui_text_for(selected_locale, "class_temperature.info")),
        gr.update(label=ui_text_for(selected_locale, "seed.label"), info=ui_text_for(selected_locale, "seed.info")),
        gr.update(label=ui_text_for(selected_locale, "randomize_seed.label"), info=ui_text_for(selected_locale, "randomize_seed.info")),
        gr.update(label=ui_text_for(selected_locale, "audio_chunk_duration.label"), info=ui_text_for(selected_locale, "audio_chunk_duration.info")),
        gr.update(label=ui_text_for(selected_locale, "audio_chunk_threshold.label"), info=ui_text_for(selected_locale, "audio_chunk_threshold.info")),
        gr.update(label=ui_text_for(selected_locale, "pitch.label"), info=ui_text_for(selected_locale, "pitch.info")),
        gr.update(label=ui_text_for(selected_locale, "tempo.label"), info=ui_text_for(selected_locale, "tempo.info")),
        gr.update(label=ui_text_for(selected_locale, "volume.label"), info=ui_text_for(selected_locale, "volume.info")),
        gr.update(label=ui_text_for(selected_locale, "normalize_loudness.label"), info=ui_text_for(selected_locale, "normalize_loudness.info")),
    )


def coerce_float(value, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def resolve_generation_seed(seed, randomize_seed: bool) -> int:
    if randomize_seed:
        return random.randint(0, MAX_RANDOM_SEED)
    value = 42 if seed is None or seed == "" else int(seed)
    if value < 0 or value > MAX_RANDOM_SEED:
        raise ValueError(f"Seed must be between 0 and {MAX_RANDOM_SEED}.")
    return value


def normalize_profile_name(name: str | None) -> str:
    value = (name or "").strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    value = value.strip("-_")
    if not value:
        raise ValueError("Voice profile name must contain at least one letter or number.")
    if len(value) > 48:
        raise ValueError("Voice profile name must be 48 characters or fewer.")
    return value


def load_openai_voice_profiles() -> dict[str, dict[str, Any]]:
    if not OPENAI_VOICE_PROFILE_INDEX.exists():
        return {}
    try:
        raw = json.loads(OPENAI_VOICE_PROFILE_INDEX.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    profiles = {}
    for name, profile in raw.items():
        if not isinstance(profile, dict):
            continue
        ref_audio = str(profile.get("ref_audio") or "").strip()
        if not ref_audio:
            continue
        raw_seed = profile.get("seed")
        profiles[str(name)] = {
            "ref_audio": ref_audio,
            "ref_text": str(profile.get("ref_text") or ""),
            "language": str(profile.get("language") or ""),
            "seed": "" if raw_seed is None or raw_seed == "" else str(raw_seed),
            "randomize_seed": bool(profile.get("randomize_seed", False)),
        }
    return profiles


def save_openai_voice_profiles(profiles: dict[str, dict[str, Any]]) -> None:
    OPENAI_VOICE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    OPENAI_VOICE_PROFILE_INDEX.write_text(json.dumps(profiles, indent=2, sort_keys=True), encoding="utf-8")


def normalize_optional_seed(seed: int | float | str | None) -> int | None:
    if seed is None or seed == "":
        return None
    value = int(seed)
    if value < 0 or value > MAX_RANDOM_SEED:
        raise ValueError(f"Seed must be between 0 and {MAX_RANDOM_SEED}.")
    return value


def save_openai_voice_profile(
    name: str,
    audio_path: str | None,
    ref_text: str | None = None,
    language: str | None = None,
    seed: int | float | str | None = 12345,
    randomize_seed: bool = False,
) -> str:
    profile_name = normalize_profile_name(name)
    if not audio_path:
        raise ValueError("Upload a reference audio sample before saving the profile.")
    source = Path(audio_path)
    if not source.exists():
        raise ValueError("Uploaded reference audio file is no longer available.")
    OPENAI_VOICE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower() or ".wav"
    if suffix not in {".wav", ".mp3", ".flac", ".ogg", ".m4a"}:
        suffix = ".wav"
    destination = OPENAI_VOICE_PROFILE_DIR / f"{profile_name}{suffix}"
    shutil.copyfile(source, destination)
    profiles = load_openai_voice_profiles()
    profiles[profile_name] = {
        "ref_audio": str(destination),
        "ref_text": (ref_text or "").strip(),
        "language": (language or "").strip(),
        "seed": "" if randomize_seed else normalize_optional_seed(seed),
        "randomize_seed": bool(randomize_seed),
    }
    save_openai_voice_profiles(profiles)
    return profile_name


def render_openai_voice_profiles() -> str:
    profiles = load_openai_voice_profiles()
    lines = [
        "### OpenAI Voice Profiles",
        "",
        "Create a profile here, then use its name as the OpenAI TTS voice in OpenWebUI. Additional request parameters are optional and only needed when you want to override the saved profile defaults.",
        "",
        "Built-in clone aliases: `default`, `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`.",
    ]
    if profiles:
        lines.extend(["", "Saved profiles:"])
        for name, profile in sorted(profiles.items()):
            has_text = "yes" if profile.get("ref_text") else "no"
            language = profile.get("language") or "request/default"
            seed = "random" if profile.get("randomize_seed") else profile.get("seed") or "12345"
            lines.append(f"- `{name}`: language: `{language}` | seed: `{seed}` | transcript: {has_text}")
    else:
        lines.extend(["", "No custom profiles saved yet."])
    lines.extend(
        [
            "",
            "Optional override example:",
            "",
            "```json",
            '{ "voice_profile": "my-voice", "language": "English", "seed": 12345, "randomize_seed": false }',
            "```",
        ]
    )
    return "\n".join(lines)


def save_openai_voice_profile_from_ui(
    name: str,
    audio_path: str | None,
    ref_text: str | None,
    language: str | None,
    seed: int | float | str | None,
    randomize_seed: bool,
) -> tuple[str, str]:
    try:
        profile_name = save_openai_voice_profile(name, audio_path, ref_text, language, seed, randomize_seed)
    except ValueError as exc:
        return f"OpenAI voice profile error: {exc}", render_openai_voice_profiles()
    return f"Saved OpenAI voice profile `{profile_name}`.", render_openai_voice_profiles()


def append_openai_call_log(payload: OpenAISpeechRequest, tts_payload: TTSRequest, profile_source: str) -> None:
    row = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "model": payload.model,
        "voice": payload.voice,
        "profile": profile_source,
        "format": payload.response_format,
        "language": tts_payload.language or "auto",
        "seed": "" if tts_payload.seed is None else str(tts_payload.seed),
        "randomize": str(bool(tts_payload.randomize_seed)).lower(),
        "ref_audio": "yes" if tts_payload.ref_audio else "no",
        "instructions": "yes" if (payload.instructions or "").strip() else "no",
    }
    with OPENAI_CALL_LOG_LOCK:
        OPENAI_CALL_LOG.append(row)
        del OPENAI_CALL_LOG[:-OPENAI_CALL_LOG_LIMIT]


def render_openai_call_log() -> str:
    with OPENAI_CALL_LOG_LOCK:
        rows = list(reversed(OPENAI_CALL_LOG))
    lines = [
        "### Recent OpenAI Calls",
        "",
        "Prompt text is intentionally not logged here.",
        "",
    ]
    if not rows:
        lines.append("No OpenAI-compatible speech calls observed since this server started.")
        return "\n".join(lines)
    lines.append("| Time | Model | Voice | Profile | Language | Format | Seed | Random | Ref | Instructions |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for row in rows[:20]:
        values = [
            row["time"],
            row["model"],
            row["voice"],
            row["profile"],
            row["language"],
            row["format"],
            row["seed"] or "-",
            row["randomize"],
            row["ref_audio"],
            row["instructions"],
        ]
        escaped = [html.escape(value) for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def to_int16_audio(audio: np.ndarray) -> np.ndarray:
    if audio.dtype == np.int16:
        return audio
    return (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)


def audio_to_wav_bytes(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> bytes:
    audio_int16 = to_int16_audio(audio)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    return buffer.getvalue()


def atempo_filters(multiplier: float) -> list[str]:
    filters = []
    current = multiplier
    while current > 2.0:
        filters.append("atempo=2.0")
        current /= 2.0
    while current < 0.5:
        filters.append("atempo=0.5")
        current /= 0.5
    filters.append(f"atempo={current:.6f}")
    return filters


def build_audio_effect_filters(
    sample_rate: int,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> list[str]:
    filters = []
    if abs(pitch_semitones) > 0.001:
        pitch_factor = 2 ** (pitch_semitones / 12)
        shifted_rate = max(1, int(round(sample_rate * pitch_factor)))
        filters.extend([f"asetrate={shifted_rate}", f"aresample={sample_rate}"])
        filters.extend(atempo_filters(1 / pitch_factor))
    if abs(tempo - 1.0) > 0.001:
        filters.extend(atempo_filters(tempo))
    if abs(volume - 1.0) > 0.001:
        filters.append(f"volume={volume:.6f}")
    if normalize:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    return filters


def apply_audio_effects(
    audio: np.ndarray,
    sample_rate: int,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> np.ndarray:
    filters = build_audio_effect_filters(sample_rate, pitch_semitones, tempo, volume, normalize)
    if not filters or audio.size == 0:
        return to_int16_audio(audio)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "wav",
        "-i",
        "pipe:0",
        "-af",
        ",".join(filters),
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "pipe:1",
    ]
    try:
        result = subprocess.run(
            command,
            input=audio_to_wav_bytes(audio, sample_rate),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for pitch, tempo, volume, or normalization controls") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed to apply audio controls: {stderr}") from exc
    return np.frombuffer(result.stdout, dtype="<i2").astype(np.int16, copy=True)


def encode_audio_bytes(audio: np.ndarray, output_format: str = "wav", sample_rate: int = SAMPLE_RATE) -> bytes:
    normalized_format = normalize_output_format(output_format)
    wav_bytes = audio_to_wav_bytes(audio, sample_rate)
    ffmpeg_args = OUTPUT_FORMATS[normalized_format]["ffmpeg_args"]
    if ffmpeg_args is None:
        return wav_bytes
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "wav",
        "-i",
        "pipe:0",
        *ffmpeg_args,
        "pipe:1",
    ]
    try:
        result = subprocess.run(
            command,
            input=wav_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for non-WAV output formats") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg failed to encode {normalized_format}: {stderr}") from exc
    return result.stdout


def encode_audio_stream(
    chunks: Iterator[np.ndarray],
    output_format: str = "mp3",
    sample_rate: int = SAMPLE_RATE,
) -> Iterator[bytes]:
    normalized_format = normalize_output_format(output_format)
    ffmpeg_args = OUTPUT_FORMATS[normalized_format]["ffmpeg_args"]
    if ffmpeg_args is None:
        for chunk in chunks:
            yield audio_to_wav_bytes(chunk, sample_rate)
        return

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-i",
        "pipe:0",
        *ffmpeg_args,
        "pipe:1",
    ]
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"ffmpeg is required to stream {normalized_format}") from exc

    writer_error: list[BaseException] = []

    def write_chunks() -> None:
        assert process.stdin is not None
        try:
            for chunk in chunks:
                process.stdin.write(to_int16_audio(chunk).tobytes())
                process.stdin.flush()
        except BaseException as exc:  # noqa: BLE001 - surfaced after ffmpeg exits.
            writer_error.append(exc)
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass

    writer = threading.Thread(target=write_chunks, daemon=True)
    writer.start()

    assert process.stdout is not None
    while True:
        data = process.stdout.read(65536)
        if data:
            yield data
            continue
        if process.poll() is not None:
            break

    writer.join()
    stderr = process.stderr.read().decode("utf-8", errors="replace").strip() if process.stderr else ""
    return_code = process.wait()
    if writer_error:
        raise RuntimeError(f"Audio streaming failed: {writer_error[0]}")
    if return_code != 0:
        raise RuntimeError(f"ffmpeg failed to stream {normalized_format}: {stderr}")


def encoded_audio_to_temp_file(audio: np.ndarray, output_format: str, sample_rate: int) -> str:
    normalized_format = normalize_output_format(output_format)
    extension = OUTPUT_FORMATS[normalized_format]["extension"]
    audio_bytes = encode_audio_bytes(audio, normalized_format, sample_rate)
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as file:
        file.write(audio_bytes)
        return file.name


def build_generation_config(
    num_step: int = 32,
    guidance_scale: float = 2.0,
    denoise: bool = True,
    preprocess_prompt: bool = True,
    postprocess_output: bool = True,
    t_shift: float = 0.1,
    layer_penalty_factor: float = 5.0,
    position_temperature: float = 5.0,
    class_temperature: float = 0.0,
    audio_chunk_duration: float = 15.0,
    audio_chunk_threshold: float = 30.0,
) -> OmniVoiceGenerationConfig:
    return OmniVoiceGenerationConfig(
        num_step=num_step,
        guidance_scale=guidance_scale,
        denoise=denoise,
        preprocess_prompt=preprocess_prompt,
        postprocess_output=postprocess_output,
        t_shift=t_shift,
        layer_penalty_factor=layer_penalty_factor,
        position_temperature=position_temperature,
        class_temperature=class_temperature,
        audio_chunk_duration=audio_chunk_duration,
        audio_chunk_threshold=audio_chunk_threshold,
    )


def synthesize_array(
    text: str,
    language: str | None = None,
    ref_audio: str | None = None,
    ref_text: str | None = None,
    instruct: str | None = None,
    duration: float | None = None,
    speed: float | None = 1.0,
    device: str = "auto",
    generation_config: OmniVoiceGenerationConfig | None = None,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> tuple[int, np.ndarray]:
    if not (text or "").strip():
        raise ValueError("Text must not be empty")
    validate_voice_design_text(text, instruct)
    model = get_model(device)
    audios = model.generate(
        text=text.strip(),
        language=normalize_language(language),
        ref_audio=ref_audio or None,
        ref_text=ref_text or None,
        instruct=instruct or None,
        duration=duration if duration and duration > 0 else None,
        speed=speed,
        generation_config=generation_config,
    )
    sample_rate = int(model.sampling_rate or SAMPLE_RATE)
    waveform = apply_audio_effects(
        audios[0],
        sample_rate,
        pitch_semitones,
        tempo,
        volume,
        normalize,
    )
    return sample_rate, waveform


def synthesize_chunks(
    text: str,
    language: str | None = None,
    ref_audio: str | None = None,
    ref_text: str | None = None,
    instruct: str | None = None,
    duration: float | None = None,
    speed: float | None = 1.0,
    device: str = "auto",
    generation_config: OmniVoiceGenerationConfig | None = None,
    pitch_semitones: float = 0.0,
    tempo: float = 1.0,
    volume: float = 1.0,
    normalize: bool = False,
) -> tuple[int, Iterator[np.ndarray]]:
    if not (text or "").strip():
        raise ValueError("Text must not be empty")
    validate_voice_design_text(text, instruct)
    model = get_model(device)
    sample_rate = int(model.sampling_rate or SAMPLE_RATE)

    def chunk_iterator() -> Iterator[np.ndarray]:
        for chunk in model.generate_stream(
            text=text.strip(),
            language=normalize_language(language),
            ref_audio=ref_audio or None,
            ref_text=ref_text or None,
            instruct=instruct or None,
            duration=duration if duration and duration > 0 else None,
            speed=speed,
            generation_config=generation_config,
        ):
            yield apply_audio_effects(
                chunk,
                sample_rate,
                pitch_semitones,
                tempo,
                volume,
                normalize,
            )

    return sample_rate, chunk_iterator()


def synthesize_file(
    text,
    language,
    ref_audio,
    ref_text,
    mode,
    num_step,
    guidance_scale,
    speed,
    duration,
    device,
    output_format,
    denoise,
    preprocess_prompt,
    postprocess_output,
    t_shift,
    layer_penalty_factor,
    position_temperature,
    class_temperature,
    seed,
    randomize_seed,
    audio_chunk_duration,
    audio_chunk_threshold,
    pitch_semitones,
    tempo,
    volume,
    normalize,
    design_gender,
    design_age,
    design_pitch,
    design_style,
    design_english_accent,
    design_chinese_dialect,
):
    try:
        UI_CANCEL_EVENT.clear()
        used_seed = resolve_generation_seed(seed, bool(randomize_seed))
        fix_random_seed(used_seed)
        effective_instruct = None
        profile_status = None
        effective_class_temperature = coerce_float(class_temperature, 0.0)
        if mode == "No Voice Prompt":
            effective_instruct, profile_status = build_auto_voice_instruct(text)
            effective_class_temperature = 0.0
        if mode == "Voice Design":
            effective_instruct = build_voice_design_instruct(
                design_gender,
                design_age,
                design_pitch,
                design_style,
                design_english_accent,
                design_chinese_dialect,
            )
            validate_voice_design_text(text, effective_instruct)
        config = build_generation_config(
            num_step=int(num_step),
            guidance_scale=float(guidance_scale),
            denoise=bool(denoise),
            preprocess_prompt=bool(preprocess_prompt),
            postprocess_output=bool(postprocess_output),
            t_shift=coerce_float(t_shift, 0.1),
            layer_penalty_factor=coerce_float(layer_penalty_factor, 5.0),
            position_temperature=coerce_float(position_temperature, 5.0),
            class_temperature=effective_class_temperature,
            audio_chunk_duration=coerce_float(audio_chunk_duration, 15.0),
            audio_chunk_threshold=coerce_float(audio_chunk_threshold, 30.0),
        )
        config.cancel_event = UI_CANCEL_EVENT
        clone_ref_audio = ref_audio if mode == "Voice Clone" else None
        sample_rate, waveform = synthesize_array(
            text=text,
            language=language,
            ref_audio=clone_ref_audio,
            ref_text=ref_text,
            instruct=effective_instruct,
            duration=float(duration) if duration else None,
            speed=float(speed) if speed else None,
            device=device,
            generation_config=config,
            pitch_semitones=float(pitch_semitones),
            tempo=float(tempo),
            volume=float(volume),
            normalize=bool(normalize),
        )
        status = f"Done. Seed: {used_seed}."
        if profile_status:
            status = f"{status} {profile_status}"
        return encoded_audio_to_temp_file(waveform, output_format, sample_rate), status, used_seed
    except RuntimeError as exc:
        if str(exc) == "Generation cancelled.":
            return None, "Generation cancelled.", gr.skip()
        raise gr.Error(f"{type(exc).__name__}: {exc}") from exc
    except Exception as exc:
        raise gr.Error(f"{type(exc).__name__}: {exc}") from exc


def synthesize_file_streaming(
    text,
    language,
    ref_audio,
    ref_text,
    mode,
    num_step,
    guidance_scale,
    speed,
    duration,
    device,
    output_format,
    denoise,
    preprocess_prompt,
    postprocess_output,
    t_shift,
    layer_penalty_factor,
    position_temperature,
    class_temperature,
    seed,
    randomize_seed,
    audio_chunk_duration,
    audio_chunk_threshold,
    pitch_semitones,
    tempo,
    volume,
    normalize,
    design_gender,
    design_age,
    design_pitch,
    design_style,
    design_english_accent,
    design_chinese_dialect,
):
    try:
        stream_generation = next_ui_stream_generation()
        UI_CANCEL_EVENT.clear()
        used_seed = resolve_generation_seed(seed, bool(randomize_seed))
        fix_random_seed(used_seed)
        yield (SAMPLE_RATE, np.zeros(1, dtype=np.int16)), f"Preparing stream. Seed: {used_seed}.", used_seed
        effective_instruct = None
        profile_status = None
        effective_class_temperature = coerce_float(class_temperature, 0.0)
        if mode == "No Voice Prompt":
            effective_instruct, profile_status = build_auto_voice_instruct(text)
            effective_class_temperature = 0.0
        if mode == "Voice Design":
            effective_instruct = build_voice_design_instruct(
                design_gender,
                design_age,
                design_pitch,
                design_style,
                design_english_accent,
                design_chinese_dialect,
            )
            validate_voice_design_text(text, effective_instruct)
        config = build_generation_config(
            num_step=int(num_step),
            guidance_scale=float(guidance_scale),
            denoise=bool(denoise),
            preprocess_prompt=bool(preprocess_prompt),
            postprocess_output=bool(postprocess_output),
            t_shift=coerce_float(t_shift, 0.1),
            layer_penalty_factor=coerce_float(layer_penalty_factor, 5.0),
            position_temperature=coerce_float(position_temperature, 5.0),
            class_temperature=effective_class_temperature,
            audio_chunk_duration=coerce_float(audio_chunk_duration, 15.0),
            audio_chunk_threshold=coerce_float(audio_chunk_threshold, 30.0),
        )
        config.cancel_event = UI_CANCEL_EVENT
        clone_ref_audio = ref_audio if mode == "Voice Clone" else None
        sample_rate, chunks = synthesize_chunks(
            text=text,
            language=language,
            ref_audio=clone_ref_audio,
            ref_text=ref_text,
            instruct=effective_instruct,
            duration=float(duration) if duration else None,
            speed=float(speed) if speed else None,
            device=device,
            generation_config=config,
            pitch_semitones=float(pitch_semitones),
            tempo=float(tempo),
            volume=float(volume),
            normalize=bool(normalize),
        )
        for index, chunk in enumerate(chunks, start=1):
            if not is_current_ui_stream_generation(stream_generation):
                return
            status = f"Streaming chunk {index}."
            if index == 1 and profile_status:
                status = f"{status} Seed: {used_seed}. {profile_status}"
            elif index == 1:
                status = f"{status} Seed: {used_seed}."
            yield (sample_rate, to_int16_audio(chunk)), status, gr.skip()
        if is_current_ui_stream_generation(stream_generation):
            yield gr.skip(), "Streaming complete.", gr.skip()
    except RuntimeError as exc:
        if str(exc) == "Generation cancelled.":
            yield gr.skip(), "Generation cancelled.", gr.skip()
            return
        raise gr.Error(f"{type(exc).__name__}: {exc}") from exc
    except Exception as exc:
        raise gr.Error(f"{type(exc).__name__}: {exc}") from exc


def get_supported_output_formats() -> dict[str, dict[str, str]]:
    return {
        key: {
            "label": config["label"],
            "extension": config["extension"],
            "media_type": config["media_type"],
        }
        for key, config in OUTPUT_FORMATS.items()
    }


def get_status_payload() -> dict:
    return {
        "msg": "pong",
        "type": "OmniVoiceTTS",
        "version": read_version_file(),
        "package_version": APP_VERSION,
        "build_id": BUILD_ID,
        "runtime": get_runtime_label(),
        "device": DEFAULT_DEVICE,
        "model": DEFAULT_MODEL,
        "sample_rate": SAMPLE_RATE,
        "load_asr": LOAD_ASR,
        "asr_model": DEFAULT_ASR_MODEL if LOAD_ASR else None,
        "languages": len(LANG_IDS),
        "voice_compatibility": "Kokoro-compatible voice fields are accepted but translated to OmniVoice auto/design/clone generation.",
        "loaded_model_devices": list(MODEL_CACHE),
        "output_formats": get_supported_output_formats(),
    }


LANGUAGE_CHOICES = [("Auto", "Auto")] + sorted((lang_display_name(name), name) for name in LANG_NAMES)
hardware_choices = get_hardware_choices()
hardware_values = {value for _, value in hardware_choices}
default_hardware = DEFAULT_DEVICE if DEFAULT_DEVICE in hardware_values else "auto"


def language_choices_for(locale: str | None) -> list[tuple[str, str]]:
    return [(ui_text_for(locale, "option.auto"), "Auto")] + sorted(
        (lang_display_name(name), name) for name in LANG_NAMES
    )


def design_choices_for(locale: str | None, category: str) -> list[tuple[str, str]]:
    return [(ui_text_for(locale, "option.no_preference"), "No preference")] + [
        (option, option) for option in VOICE_DESIGN_CATEGORIES[category]["options"]
    ]


def hardware_choices_for(locale: str | None) -> list[tuple[str, str]]:
    choices = []
    for label, value in hardware_choices:
        if value == "auto":
            label = ui_text_for(locale, "option.auto")
        elif value == "cpu":
            label = ui_text_for(locale, "hardware.cpu")
        choices.append((label, value))
    return choices


def current_language_choices() -> list[tuple[str, str]]:
    return language_choices_for(UI_LOCALE)


def current_design_choices(category: str) -> list[tuple[str, str]]:
    return design_choices_for(UI_LOCALE, category)


def current_hardware_choices() -> list[tuple[str, str]]:
    return hardware_choices_for(UI_LOCALE)

APP_CSS = f"""
:root {{
    --brand-cream: #fff3e7;
    --brand-muted: rgba(255, 243, 231, 0.72);
}}

.brand-hero {{
    overflow: hidden;
    position: relative;
    width: calc(100% + 24px);
    min-height: 330px;
    box-sizing: border-box;
    margin: 0 -12px 18px;
    padding: 22px;
    border: 1px solid rgba(255, 176, 118, 0.24);
    border-radius: 16px;
    background:
        linear-gradient(115deg, rgba(8, 5, 3, 0.96) 0%, rgba(20, 9, 2, 0.86) 48%, rgba(255, 107, 0, 0.24) 100%),
        url("{BRAND_ASSET_BASE}/banner.jpg") center / cover no-repeat;
    box-shadow: 0 28px 70px rgba(0, 0, 0, 0.58), inset 0 1px 0 rgba(255, 255, 255, 0.08);
}}

.brand-nav {{
    position: relative;
    z-index: 1;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 42px;
}}

.brand-lockup {{
    display: flex;
    align-items: center;
    gap: 18px;
    min-width: 0;
}}

.brand-logo-wrap img {{
    display: block;
    width: 96px;
    height: 96px;
    object-fit: contain;
    border-radius: 18px;
    box-shadow: 0 0 0 1px rgba(255, 176, 118, 0.24), 0 18px 34px rgba(0, 0, 0, 0.42);
}}

.brand-name {{
    color: var(--brand-cream);
    font-size: 1.02rem;
    font-weight: 800;
    line-height: 1.08;
}}

.brand-subname {{
    margin-top: 3px;
    color: var(--brand-muted);
    font-size: 0.82rem;
}}

.brand-links {{
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
    padding-top: 0px;
    margin-right: 90px;
}}

.brand-links a {{
    display: inline-flex;
    align-items: center;
    position: relative;
    overflow: hidden;
    min-height: 34px;
    padding: 7px 12px;
    border: 1px solid rgba(255, 176, 118, 0.28);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.065);
    color: var(--brand-cream) !important;
    font-size: 0.84rem;
    font-weight: 700;
    text-decoration: none !important;
    backdrop-filter: blur(8px);
    transform: translateY(0);
    transition: transform 150ms ease, border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
}}

.brand-links a:hover {{
    transform: translateY(-2px);
    border-color: rgba(255, 176, 118, 0.55);
    background: rgba(255, 255, 255, 0.11);
    box-shadow: 0 12px 26px rgba(0, 0, 0, 0.28);
}}

.brand-links a:first-child {{
    border-color: rgba(255, 107, 0, 0.72);
    background: linear-gradient(135deg, #ff6b00, #ff9a3d);
    color: #180a02 !important;
    box-shadow: 0 0 0 rgba(255, 107, 0, 0.0);
    animation: examples-pulse 2.8s ease-in-out infinite;
}}

.brand-links a:first-child::after {{
    content: "";
    position: absolute;
    inset: -45% -70%;
    background: linear-gradient(115deg, transparent 42%, rgba(255, 255, 255, 0.58) 50%, transparent 58%);
    transform: translateX(-90%);
    animation: examples-shine 3.8s ease-in-out infinite;
    pointer-events: none;
}}

.brand-links a:first-child:hover {{
    background: linear-gradient(135deg, #ff7a12, #ffb066);
    box-shadow: 0 14px 30px rgba(255, 107, 0, 0.30);
}}

@keyframes examples-pulse {{
    0%, 100% {{
        box-shadow: 0 0 0 rgba(255, 107, 0, 0.0);
    }}
    50% {{
        box-shadow: 0 0 22px rgba(255, 107, 0, 0.34);
    }}
}}

@keyframes examples-shine {{
    0%, 58% {{
        transform: translateX(-90%);
    }}
    72%, 100% {{
        transform: translateX(90%);
    }}
}}

.brand-copy {{
    position: relative;
    z-index: 1;
    max-width: 760px;
}}

.brand-copy h1 {{
    margin: 0 0 12px;
    color: var(--brand-cream);
    font-size: clamp(2.4rem, 6vw, 5.15rem);
    line-height: 0.92;
}}

.brand-copy p {{
    max-width: 660px;
    margin: 0;
    color: var(--brand-muted);
    font-size: 1.04rem;
    line-height: 1.6;
}}

.brand-pills {{
    position: relative;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    margin-top: 24px;
}}

.brand-pills span {{
    position: relative;
    padding: 7px 11px;
    padding-left: 27px;
    border: 1px solid rgba(255, 176, 118, 0.24);
    border-radius: 999px;
    background: linear-gradient(135deg, rgba(255, 107, 0, 0.16), rgba(0, 0, 0, 0.34));
    color: var(--brand-cream);
    font-size: 0.82rem;
    font-weight: 750;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 8px 18px rgba(0, 0, 0, 0.22);
}}

.brand-pills span::before {{
    content: "";
    position: absolute;
    left: 11px;
    top: 50%;
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: linear-gradient(135deg, #ff6b00, #ffb076);
    box-shadow: 0 0 10px rgba(255, 107, 0, 0.45);
    transform: translateY(-50%);
}}

.gpu-monitor {{
    margin: 10px 0 4px;
    padding: 12px;
    border: 1px solid rgba(255, 176, 118, 0.22);
    border-radius: 10px;
    background: linear-gradient(135deg, rgba(22, 12, 6, 0.95), rgba(7, 7, 8, 0.96));
    color: #fff3e7;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 12px 24px rgba(0, 0, 0, 0.20);
}}

.gpu-monitor-title {{
    margin-bottom: 9px;
    font-size: 0.86rem;
    font-weight: 800;
    letter-spacing: 0.02em;
}}

.gpu-monitor-muted {{
    color: rgba(255, 243, 231, 0.68);
    font-size: 0.86rem;
}}

.gpu-card + .gpu-card {{
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid rgba(255, 176, 118, 0.15);
}}

.gpu-card-head {{
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
}}

.gpu-card-head strong {{
    color: #ffb066;
}}

.gpu-card-head span,
.gpu-metric-row span,
.gpu-foot span {{
    color: rgba(255, 243, 231, 0.68);
    font-size: 0.78rem;
}}

.gpu-metric-row,
.gpu-foot {{
    display: flex;
    justify-content: space-between;
    gap: 10px;
    font-size: 0.82rem;
}}

.gpu-bar {{
    overflow: hidden;
    height: 7px;
    margin: 5px 0 8px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.09);
}}

.gpu-bar span {{
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #ff6b00, #ffb066);
}}

.gpu-vram span {{
    background: linear-gradient(90deg, #ffb066, #ffe0bd);
}}

.gpu-sparkline {{
    display: block;
    width: 100%;
    height: 44px;
    margin-bottom: 8px;
    border-radius: 8px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.02));
}}

#build-badge {{
    position: absolute;
    right: 120px;
    bottom: 10px;
    z-index: 3;
    min-width: max-content;
    background: rgba(8, 5, 3, 0.76);
    color: var(--brand-cream);
    border: 1px solid rgba(255, 176, 118, 0.24);
    border-radius: 8px;
    padding: 7px 9px;
    font-size: 10.5px;
    line-height: 1.35;
    font-family: Arial, sans-serif;
    text-align: left;
    backdrop-filter: blur(8px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
}}

@media (max-width: 760px) {{
    .brand-hero {{
        width: 100%;
        min-height: 0;
        margin: 0 0 18px;
        padding: 16px;
        border-radius: 12px;
    }}

    .brand-nav {{
        align-items: flex-start;
        flex-direction: column;
        margin-bottom: 30px;
    }}

    .brand-links {{
        justify-content: flex-start;
        padding-top: 0;
        margin-right: 0;
    }}

    .brand-copy h1 {{
        font-size: 2.45rem;
    }}

    #build-badge {{
        position: relative;
        top: auto;
        right: auto;
        display: inline-block;
        min-width: 0;
        margin-top: 14px;
    }}
}}
"""

BRAND_HEADER_HTML = f"""
<section class="brand-hero">
    <div class="brand-nav">
        <div class="brand-lockup">
            <div class="brand-logo-wrap">
                <img src="{BRAND_ASSET_BASE}/logo_small.png" alt="Hangry Labs logo">
            </div>
            <div>
                <div class="brand-name">Hangry Labs</div>
                <div class="brand-subname">Local voice tools</div>
            </div>
        </div>
        <nav class="brand-links" aria-label="Project links">
            <a href="https://hangry-labs.github.io/OmniVoiceTTS/examples/" target="_blank" rel="noreferrer">Voice examples</a>
            <a href="https://github.com/Hangry-Labs/OmniVoiceTTS" target="_blank" rel="noreferrer">GitHub</a>
            <a href="https://hub.docker.com/r/hangrylabs/omnivoicetts/tags" target="_blank" rel="noreferrer">Docker Hub</a>
            <a href="/tts/docs" target="_blank" rel="noreferrer">API docs</a>
        </nav>
    </div>
    <div class="brand-copy">
        <h1>OmniVoiceTTS</h1>
        <p>
            Massively multilingual text-to-speech with voice design, voice cloning,
            local generation, and an HTTP API in the same Docker image.
        </p>
    </div>
    <div class="brand-pills" aria-label="Capabilities">
        <span>600+ languages</span>
        <span>Voice design</span>
        <span>Voice clone</span>
        <span>Offline baked image</span>
    </div>
    <div id="build-badge">{get_banner_runtime_html()}</div>
</section>
"""

with gr.Blocks(title="OmniVoiceTTS") as ui:
    gr.HTML(f"<style>{APP_CSS}</style>")
    gr.HTML(BRAND_HEADER_HTML)
    with gr.Row(elem_classes="app-grid"):
        with gr.Column(scale=1, elem_classes="control-panel"):
            with gr.Row():
                mode = gr.Radio(
                    mode_choices_for(UI_LOCALE),
                    value="No Voice Prompt",
                    label=ui_text("mode.label"),
                    scale=2,
                )
                ui_locale = gr.Dropdown(
                    ui_locale_choices(),
                    value=normalize_ui_locale(UI_LOCALE),
                    label=ui_text("ui_language.label"),
                    scale=1,
                )
            text = gr.Textbox(
                label=ui_text("input_text.label"),
                lines=5,
                value=ui_text("input_text.default"),
            )
            with gr.Accordion(ui_text("hints.title"), open=False):
                hints_markdown = gr.Markdown(nonverbal_tags_markdown(), elem_classes="notice-card")
            generate_btn = gr.Button(ui_text("generate.label"), variant="primary", elem_id="generate-btn")
            with gr.Accordion(ui_text("voice_design.title"), open=False):
                voice_design_note = gr.Markdown(ui_text("voice_design.note"))
                language = gr.Dropdown(current_language_choices(), value="Auto", label=ui_text("language.label"))
                with gr.Row():
                    design_gender = gr.Dropdown(
                        choices=current_design_choices("gender"),
                        value="No preference",
                        label=ui_text("design.gender"),
                    )
                    design_age = gr.Dropdown(
                        choices=current_design_choices("age"),
                        value="No preference",
                        label=ui_text("design.age"),
                    )
                with gr.Row():
                    design_pitch = gr.Dropdown(
                        choices=current_design_choices("pitch"),
                        value="No preference",
                        label=ui_text("design.pitch"),
                    )
                    design_style = gr.Dropdown(
                        choices=current_design_choices("style"),
                        value="No preference",
                        label=ui_text("design.style"),
                    )
                with gr.Row():
                    design_english_accent = gr.Dropdown(
                        choices=current_design_choices("english_accent"),
                        value="No preference",
                        label=ui_text("design.english_accent"),
                    )
                    design_chinese_dialect = gr.Dropdown(
                        choices=current_design_choices("chinese_dialect"),
                        value="No preference",
                        label=ui_text("design.chinese_dialect"),
                    )
            ref_audio = gr.Audio(label=ui_text("reference_audio.label"), sources=["upload"], type="filepath")
            ref_text = gr.Textbox(
                label=ui_text("reference_text.label"),
                lines=2,
                placeholder=ui_text("reference_text.placeholder"),
                info=ui_text("reference_text.info"),
            )
        with gr.Column(scale=1, elem_classes="output-panel"):
            with gr.Tabs():
                with gr.Tab("Generate"):
                    output_audio = gr.Audio(label=ui_text("output_audio.label"), type="filepath", autoplay=True, streaming=False)
                with gr.Tab("Stream"):
                    output_stream = gr.Audio(label="Output Audio Stream", interactive=False, streaming=True, autoplay=True)
                    with gr.Row():
                        stream_btn = gr.Button("Stream", variant="primary")
                        stop_generation_btn = gr.Button(ui_text("stop_generation.label"), variant="stop")
                with gr.Tab("OpenAI"):
                    gr.Markdown(
                        "Create local clone profiles for OpenAI-compatible tools. "
                        "In OpenWebUI, set the TTS voice to the saved profile name. "
                        "Additional parameters are only needed when you want to override profile defaults."
                    )
                    openai_profile_name = gr.Textbox(
                        label="Voice profile name",
                        placeholder="my-voice",
                        info="Use letters, numbers, dash, or underscore. The saved name is normalized for API use.",
                    )
                    openai_profile_audio = gr.Audio(
                        label="Reference audio sample",
                        sources=["upload"],
                        type="filepath",
                    )
                    openai_profile_text = gr.Textbox(
                        label="Reference transcript",
                        lines=2,
                        placeholder="Optional transcript for the uploaded reference audio.",
                    )
                    openai_profile_language = gr.Dropdown(
                        choices=LANGUAGE_CHOICES,
                        value="english",
                        label="Default language",
                        info="Used when the OpenAI request does not send a language override.",
                    )
                    with gr.Row():
                        openai_profile_seed = gr.Number(
                            value=12345,
                            minimum=0,
                            maximum=MAX_RANDOM_SEED,
                            precision=0,
                            label="Default seed",
                            info="Used for stable profile playback unless a request overrides it.",
                        )
                        openai_profile_randomize_seed = gr.Checkbox(
                            value=False,
                            label="Randomize seed by default",
                            info="Leave off for repeatable profile behavior.",
                        )
                    openai_profile_save = gr.Button("Save OpenAI Voice Profile", variant="primary")
                    openai_profile_status = gr.Textbox(label="OpenAI profile status", lines=2)
                    openai_profile_overview = gr.Markdown(render_openai_voice_profiles())
                    openai_log_refresh = gr.Button("Refresh OpenAI Call Log")
                    openai_call_log = gr.Markdown(render_openai_call_log())
            status_box = gr.Textbox(label=ui_text("status.label"), lines=2)
            with gr.Row():
                hardware = gr.Dropdown(current_hardware_choices(), value=default_hardware, label=ui_text("hardware.label"))
                output_format = gr.Dropdown(
                    choices=[(config["label"], key) for key, config in OUTPUT_FORMATS.items()],
                    value="mp3",
                    label=ui_text("output_format.label"),
                )
            gpu_monitor = gr.HTML(gpu_monitor_html())
            with gr.Accordion(ui_text("generation_settings.title"), open=False):
                speed = gr.Slider(0.5, 1.5, value=1.0, step=0.05, label=ui_text("speed.label"), info=ui_text("speed.info"))
                duration = gr.Number(value=None, label=ui_text("duration.label"), info=ui_text("duration.info"))
                num_step = gr.Slider(4, 64, value=32, step=1, label=ui_text("num_step.label"), info=ui_text("num_step.info"))
                guidance_scale = gr.Slider(0.0, 4.0, value=2.0, step=0.1, label=ui_text("guidance_scale.label"), info=ui_text("guidance_scale.info"))
                denoise = gr.Checkbox(value=True, label=ui_text("denoise.label"), info=ui_text("denoise.info"))
                preprocess_prompt = gr.Checkbox(value=True, label=ui_text("preprocess_prompt.label"), info=ui_text("preprocess_prompt.info"))
                postprocess_output = gr.Checkbox(value=True, label=ui_text("postprocess_output.label"), info=ui_text("postprocess_output.info"))
                with gr.Accordion(ui_text("advanced_controls.title"), open=False):
                    t_shift = gr.Slider(0.01, 1.0, value=0.1, step=0.01, label=ui_text("t_shift.label"), info=ui_text("t_shift.info"))
                    layer_penalty_factor = gr.Slider(0.0, 10.0, value=5.0, step=0.1, label=ui_text("layer_penalty.label"), info=ui_text("layer_penalty.info"))
                    position_temperature = gr.Slider(
                        0.0,
                        10.0,
                        value=5.0,
                        step=0.1,
                        label=ui_text("position_temperature.label"),
                        info=ui_text("position_temperature.info"),
                    )
                    class_temperature = gr.Slider(0.0, 2.0, value=0.0, step=0.05, label=ui_text("class_temperature.label"), info=ui_text("class_temperature.info"))
                    with gr.Row():
                        seed = gr.Number(value=42, minimum=0, maximum=MAX_RANDOM_SEED, precision=0, label=ui_text("seed.label"), info=ui_text("seed.info"))
                        randomize_seed = gr.Checkbox(value=True, label=ui_text("randomize_seed.label"), info=ui_text("randomize_seed.info"))
                    audio_chunk_duration = gr.Number(value=15.0, label=ui_text("audio_chunk_duration.label"), info=ui_text("audio_chunk_duration.info"))
                    audio_chunk_threshold = gr.Number(value=30.0, label=ui_text("audio_chunk_threshold.label"), info=ui_text("audio_chunk_threshold.info"))
            with gr.Accordion(ui_text("audio_controls.title"), open=False):
                pitch_semitones = gr.Slider(-12, 12, value=0, step=0.5, label=ui_text("pitch.label"), info=ui_text("pitch.info"))
                tempo = gr.Slider(0.5, 2, value=1, step=0.05, label=ui_text("tempo.label"), info=ui_text("tempo.info"))
                volume = gr.Slider(0, 2, value=1, step=0.05, label=ui_text("volume.label"), info=ui_text("volume.info"))
                loudness_normalize = gr.Checkbox(value=False, label=ui_text("normalize_loudness.label"), info=ui_text("normalize_loudness.info"))

    ui_locale.change(
        fn=ui_locale_updates,
        inputs=[ui_locale, mode, text],
        outputs=[
            mode,
            ui_locale,
            text,
            hints_markdown,
            generate_btn,
            voice_design_note,
            language,
            design_gender,
            design_age,
            design_pitch,
            design_style,
            design_english_accent,
            design_chinese_dialect,
            ref_audio,
            ref_text,
            output_audio,
            status_box,
            hardware,
            output_format,
            speed,
            duration,
            num_step,
            guidance_scale,
            denoise,
            preprocess_prompt,
            postprocess_output,
            t_shift,
            layer_penalty_factor,
            position_temperature,
            class_temperature,
            seed,
            randomize_seed,
            audio_chunk_duration,
            audio_chunk_threshold,
            pitch_semitones,
            tempo,
            volume,
            loudness_normalize,
        ],
    )

    gpu_timer = gr.Timer(value=1.0)
    gpu_timer.tick(
        fn=gpu_monitor_html,
        outputs=gpu_monitor,
        queue=False,
    )

    openai_profile_save.click(
        fn=save_openai_voice_profile_from_ui,
        inputs=[
            openai_profile_name,
            openai_profile_audio,
            openai_profile_text,
            openai_profile_language,
            openai_profile_seed,
            openai_profile_randomize_seed,
        ],
        outputs=[openai_profile_status, openai_profile_overview],
    )
    openai_log_refresh.click(
        fn=render_openai_call_log,
        outputs=openai_call_log,
        queue=False,
    )

    seed.input(
        fn=lambda: False,
        outputs=randomize_seed,
        queue=False,
    )

    generate_event = generate_btn.click(
        fn=synthesize_file,
        inputs=[
            text,
            language,
            ref_audio,
            ref_text,
            mode,
            num_step,
            guidance_scale,
            speed,
            duration,
            hardware,
            output_format,
            denoise,
            preprocess_prompt,
            postprocess_output,
            t_shift,
            layer_penalty_factor,
            position_temperature,
            class_temperature,
            seed,
            randomize_seed,
            audio_chunk_duration,
            audio_chunk_threshold,
            pitch_semitones,
            tempo,
            volume,
            loudness_normalize,
            design_gender,
            design_age,
            design_pitch,
            design_style,
            design_english_accent,
            design_chinese_dialect,
        ],
        outputs=[output_audio, status_box, seed],
    )

    output_stream.pause(
        fn=lambda: "Playback paused. Use Stop Generation to cancel ongoing synthesis.",
        outputs=status_box,
    )

    output_stream.stop(
        fn=lambda: "Playback stopped. Use Stop Generation to cancel ongoing synthesis.",
        outputs=status_box,
    )

    stream_btn.click(fn=stop_active_ui_stream, outputs=[output_stream], queue=False)
    stream_event = stream_btn.click(
        fn=synthesize_file_streaming,
        inputs=[
            text,
            language,
            ref_audio,
            ref_text,
            mode,
            num_step,
            guidance_scale,
            speed,
            duration,
            hardware,
            output_format,
            denoise,
            preprocess_prompt,
            postprocess_output,
            t_shift,
            layer_penalty_factor,
            position_temperature,
            class_temperature,
            seed,
            randomize_seed,
            audio_chunk_duration,
            audio_chunk_threshold,
            pitch_semitones,
            tempo,
            volume,
            loudness_normalize,
            design_gender,
            design_age,
            design_pitch,
            design_style,
            design_english_accent,
            design_chinese_dialect,
        ],
        outputs=[output_stream, status_box, seed],
        trigger_mode="always_last",
    )

    stop_generation_btn.click(
        fn=stop_active_ui_stream,
        outputs=[output_stream],
        cancels=[stream_event],
        queue=False,
    )

api = FastAPI(
    title="OmniVoiceTTS API",
    description="HTTP API for Hangry Labs OmniVoiceTTS",
    version=read_version_file(),
    openapi_url="/tts/openapi.json",
    docs_url="/tts/docs",
    redoc_url="/tts/redoc",
)

if ASSET_DIR.exists():
    api.mount(BRAND_ASSET_BASE, StaticFiles(directory=ASSET_DIR), name="hangrylabs-assets")


class TTSRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str = Field(..., min_length=1, description="Text to synthesize.")
    voice: Optional[str] = Field(
        None,
        description="Kokoro-compatible voice field. Accepted for compatibility; OmniVoice uses ref_audio/instruct/auto voice instead.",
    )
    language: Optional[str] = Field(None, description="Language name or id. Omit for auto/language-agnostic mode.")
    ref_audio: Optional[str] = Field(None, description="Reference audio path inside the container for voice cloning.")
    ref_text: Optional[str] = Field(None, description="Transcript for ref_audio. If omitted, ASR may load on demand.")
    instruct: Optional[str] = Field(
        None,
        description=(
            "Voice design instruction, for example 'female, low pitch'. Do not combine with bracket expression "
            "tags in text; use ref_audio voice cloning or omit instruct for [laughter]/[sigh]-style tags."
        ),
    )
    speed: Optional[float] = Field(1.0, ge=0.5, le=1.5, description="Speech speed multiplier.")
    duration: Optional[float] = Field(None, gt=0.0, description="Fixed output duration in seconds. Overrides speed.")
    device: str = Field("auto", description="auto, cpu, mps, or cuda:N.")
    use_gpu: Optional[bool] = Field(None, description="Kokoro-compatible legacy switch. Prefer device.")
    num_step: int = Field(32, ge=4, le=64, description="Diffusion decoding steps.")
    guidance_scale: float = Field(2.0, ge=0.0, le=4.0, description="Classifier-free guidance scale.")
    denoise: bool = Field(True, description="Use denoising prompt when applicable.")
    preprocess_prompt: bool = Field(True, description="Trim/remove silence from reference prompt audio.")
    postprocess_output: bool = Field(True, description="Remove long silences and fade/pad generated audio.")
    t_shift: float = Field(0.1, gt=0.0, le=1.0, description="Time-step shift for the noise schedule.")
    layer_penalty_factor: float = Field(5.0, ge=0.0, le=20.0, description="Penalty encouraging lower codebook layers to unmask first.")
    position_temperature: float = Field(5.0, ge=0.0, le=20.0, description="Temperature for mask-position selection.")
    class_temperature: float = Field(0.0, ge=0.0, le=5.0, description="Temperature for token sampling.")
    seed: Optional[int] = Field(None, ge=0, le=MAX_RANDOM_SEED, description="Optional random seed for reproducible generation.")
    randomize_seed: bool = Field(False, description="Generate and use a random seed for this request.")
    audio_chunk_duration: float = Field(15.0, ge=0.0, le=120.0, description="Target chunk duration for long text.")
    audio_chunk_threshold: float = Field(30.0, ge=0.0, le=300.0, description="Estimated duration threshold before long-text chunking activates.")
    pitch_semitones: float = Field(0.0, ge=-12.0, le=12.0, description="Post-synthesis pitch shift.")
    tempo: float = Field(1.0, ge=0.5, le=2.0, description="Post-synthesis tempo multiplier.")
    volume: float = Field(1.0, ge=0.0, le=2.0, description="Output volume multiplier.")
    normalize: bool = Field(False, description="Apply ffmpeg loudness normalization.")
    output_format: str = Field(
        "wav",
        alias="format",
        validation_alias=AliasChoices("format", "output_format", "response_format"),
        description="wav, mp3, flac, or ogg.",
    )


class PurgeRequest(BaseModel):
    device: Optional[str] = Field(None, description="Optional cached model device to clear. Omit to clear all.")


class OpenAISpeechRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model: str = Field("omnivoice", description="OpenAI-style model id. Accepted aliases include omnivoice, tts-1, and tts-1-hd.")
    input: str = Field(..., min_length=1, description="Text to synthesize.")
    voice: str = Field("default", description="OpenAI-style voice id. Compatibility aliases map to local OmniVoice clone/design behavior.")
    response_format: str = Field("mp3", description="mp3, wav, flac, or ogg. opus is accepted as an ogg alias.")
    speed: float = Field(1.0, ge=0.5, le=1.5, description="Speech speed multiplier.")
    language: Optional[str] = Field(None, description="Optional OmniVoice extension: language name or id.")
    seed: Optional[int] = Field(None, ge=0, le=MAX_RANDOM_SEED, description="Optional OmniVoice extension: fixed generation seed.")
    randomize_seed: bool = Field(False, description="Optional OmniVoice extension: generate a random seed.")
    device: str = Field("auto", description="Optional OmniVoice extension: auto, cpu, mps, or cuda:N.")
    instructions: Optional[str] = Field(None, description="Optional OmniVoice extension: explicit voice-design instruction.")
    ref_audio: Optional[str] = Field(None, description="Optional OmniVoice extension: reference audio path for stable voice cloning.")
    ref_text: Optional[str] = Field(None, description="Optional OmniVoice extension: transcript for ref_audio.")
    voice_profile: Optional[str] = Field(None, description="Optional OmniVoice extension: saved OpenAI voice profile name.")


def normalize_openai_model(model: str | None) -> str:
    model_id = (model or "omnivoice").strip().lower()
    if model_id not in OPENAI_MODEL_ALIASES:
        supported = ", ".join(OPENAI_MODEL_IDS)
        raise ValueError(f"Unsupported model '{model}'. Supported OpenAI-compatible models: {supported}")
    return OPENAI_MODEL_ALIASES[model_id]


def openai_voice_instruction(voice: str | None, instructions: str | None = None) -> str | None:
    manual_instruction = (instructions or "").strip()
    if manual_instruction:
        return manual_instruction
    voice_id = (voice or "default").strip().lower()
    if not voice_id:
        return None
    return OPENAI_VOICE_INSTRUCTIONS.get(voice_id)


def openai_request_has_field(payload: OpenAISpeechRequest, field_name: str) -> bool:
    return field_name in getattr(payload, "model_fields_set", set())


def openai_profile_from_payload(payload: OpenAISpeechRequest) -> tuple[str | None, dict[str, Any] | None, str | None]:
    if (payload.ref_audio or "").strip():
        return None, None, None

    profiles = load_openai_voice_profiles()
    requested_profile = (payload.voice_profile or "").strip()
    if requested_profile:
        profile_name = normalize_profile_name(requested_profile)
        profile = profiles.get(profile_name)
        if not profile:
            raise ValueError(f"OpenAI voice profile '{requested_profile}' does not exist.")
        return profile_name, profile, f"profile:{profile_name}"

    if (payload.instructions or "").strip():
        return None, None, None

    voice_id = (payload.voice or "default").strip().lower()
    try:
        profile_name = normalize_profile_name(voice_id)
    except ValueError:
        return None, None, None
    profile = profiles.get(profile_name)
    if profile:
        return profile_name, profile, f"voice-profile:{profile_name}"
    return None, None, None


def resolve_openai_voice(
    payload: OpenAISpeechRequest,
) -> tuple[str | None, str | None, str | None, str]:
    explicit_ref_audio = (payload.ref_audio or "").strip()
    if explicit_ref_audio:
        return explicit_ref_audio, (payload.ref_text or None), None, "request-ref-audio"

    _, profile, profile_source = openai_profile_from_payload(payload)
    if profile and profile_source:
        return profile["ref_audio"], profile.get("ref_text") or None, None, profile_source

    manual_instruction = (payload.instructions or "").strip()
    if manual_instruction:
        return None, None, manual_instruction, "request-instructions"

    voice_id = (payload.voice or "default").strip().lower()
    if voice_id in OPENAI_CLONE_VOICE_ALIASES and OPENAI_DEFAULT_CLONE_AUDIO.exists():
        return str(OPENAI_DEFAULT_CLONE_AUDIO), None, None, "builtin-clone"

    return None, None, openai_voice_instruction(payload.voice), "voice-design"


def openai_model_payload(model_id: str) -> dict:
    return {
        "id": model_id,
        "object": "model",
        "created": 0,
        "owned_by": "hangrylabs",
    }


def openai_voice_payload(voice_id: str) -> dict:
    is_clone_profile = voice_id in OPENAI_CLONE_VOICE_ALIASES and OPENAI_DEFAULT_CLONE_AUDIO.exists()
    return {
        "id": voice_id,
        "object": "voice",
        "owned_by": "hangrylabs",
        "profile_type": "clone" if is_clone_profile else "design",
        "compatibility_note": "Local OmniVoiceTTS compatibility voice alias, not an OpenAI-hosted voice.",
    }


def openai_voice_payloads() -> list[dict]:
    voices = [openai_voice_payload(voice_id) for voice_id in OPENAI_VOICE_INSTRUCTIONS]
    for name in sorted(load_openai_voice_profiles()):
        voices.append(
            {
                "id": name,
                "object": "voice",
                "owned_by": "local",
                "profile_type": "clone",
                "compatibility_note": "User-created local OmniVoiceTTS clone profile.",
            }
        )
    return voices


def openai_speech_to_tts_request(payload: OpenAISpeechRequest) -> TTSRequest:
    normalize_openai_model(payload.model)
    output_format = normalize_output_format(payload.response_format)
    ref_audio, ref_text, instruct, _ = resolve_openai_voice(payload)
    _, profile, _ = openai_profile_from_payload(payload)
    if instruct:
        validate_voice_design_text(payload.input, instruct)
    language = payload.language
    if profile and not openai_request_has_field(payload, "language"):
        language = profile.get("language") or None
    randomize_seed = payload.randomize_seed
    if profile and not openai_request_has_field(payload, "randomize_seed"):
        randomize_seed = bool(profile.get("randomize_seed", False))
    seed = payload.seed
    if profile and not openai_request_has_field(payload, "seed") and not randomize_seed:
        seed = normalize_optional_seed(profile.get("seed")) or 12345
    if seed is None and ref_audio and not randomize_seed:
        seed = 12345
    return TTSRequest(
        text=payload.input,
        voice=payload.voice,
        language=language,
        ref_audio=ref_audio,
        ref_text=ref_text,
        instruct=instruct,
        speed=payload.speed,
        device=payload.device,
        output_format=output_format,
        seed=seed,
        randomize_seed=randomize_seed,
    )


def log_openai_speech_request(payload: OpenAISpeechRequest, tts_payload: TTSRequest) -> None:
    _, _, _, profile_source = resolve_openai_voice(payload)
    append_openai_call_log(payload, tts_payload, profile_source)
    print(
        "[openai-speech] "
        f"model={payload.model!r} "
        f"voice={payload.voice!r} "
        f"format={payload.response_format!r} "
        f"language={tts_payload.language!r} "
        f"seed={tts_payload.seed!r} "
        f"randomize_seed={tts_payload.randomize_seed!r} "
        f"instructions_present={bool((payload.instructions or '').strip())} "
        f"profile={profile_source!r} "
        f"ref_audio_present={bool(tts_payload.ref_audio)} "
        f"ref_text_present={bool(tts_payload.ref_text)} "
        f"instruct={tts_payload.instruct!r}",
        flush=True,
    )


def synthesize_payload(payload: TTSRequest) -> tuple[str, int, np.ndarray, int]:
    try:
        output_format = normalize_output_format(payload.output_format)
        requested_device = resolve_requested_device(payload.device, payload.use_gpu)
        normalize_device(requested_device)
        used_seed = resolve_generation_seed(payload.seed, payload.randomize_seed)
        fix_random_seed(used_seed)
        config = build_generation_config(
            num_step=payload.num_step,
            guidance_scale=payload.guidance_scale,
            denoise=payload.denoise,
            preprocess_prompt=payload.preprocess_prompt,
            postprocess_output=payload.postprocess_output,
            t_shift=payload.t_shift,
            layer_penalty_factor=payload.layer_penalty_factor,
            position_temperature=payload.position_temperature,
            class_temperature=payload.class_temperature,
            audio_chunk_duration=payload.audio_chunk_duration,
            audio_chunk_threshold=payload.audio_chunk_threshold,
        )
        sample_rate, waveform = synthesize_array(
            text=payload.text,
            language=payload.language,
            ref_audio=payload.ref_audio,
            ref_text=payload.ref_text,
            instruct=payload.instruct,
            duration=payload.duration,
            speed=payload.speed,
            device=requested_device,
            generation_config=config,
            pitch_semitones=payload.pitch_semitones,
            tempo=payload.tempo,
            volume=payload.volume,
            normalize=payload.normalize,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
    return output_format, sample_rate, waveform, used_seed


def synthesize_payload_chunks(payload: TTSRequest) -> tuple[str, int, Iterator[np.ndarray], int]:
    try:
        requested_format = normalize_output_format(payload.output_format)
        output_format = "mp3" if requested_format == "wav" else requested_format
        requested_device = resolve_requested_device(payload.device, payload.use_gpu)
        normalize_device(requested_device)
        used_seed = resolve_generation_seed(payload.seed, payload.randomize_seed)
        fix_random_seed(used_seed)
        config = build_generation_config(
            num_step=payload.num_step,
            guidance_scale=payload.guidance_scale,
            denoise=payload.denoise,
            preprocess_prompt=payload.preprocess_prompt,
            postprocess_output=payload.postprocess_output,
            t_shift=payload.t_shift,
            layer_penalty_factor=payload.layer_penalty_factor,
            position_temperature=payload.position_temperature,
            class_temperature=payload.class_temperature,
            audio_chunk_duration=payload.audio_chunk_duration,
            audio_chunk_threshold=payload.audio_chunk_threshold,
        )
        sample_rate, chunks = synthesize_chunks(
            text=payload.text,
            language=payload.language,
            ref_audio=payload.ref_audio,
            ref_text=payload.ref_text,
            instruct=payload.instruct,
            duration=payload.duration,
            speed=payload.speed,
            device=requested_device,
            generation_config=config,
            pitch_semitones=payload.pitch_semitones,
            tempo=payload.tempo,
            volume=payload.volume,
            normalize=payload.normalize,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
    return output_format, sample_rate, chunks, used_seed


def stream_audio_response(payload: TTSRequest, route_name: str) -> StreamingResponse:
    output_format, sample_rate, waveform, used_seed = synthesize_payload(payload)
    try:
        audio_bytes = encode_audio_bytes(waveform, output_format, sample_rate)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    extension = OUTPUT_FORMATS[output_format]["extension"]
    media_type = OUTPUT_FORMATS[output_format]["media_type"]
    duration = len(waveform) / sample_rate if sample_rate else 0
    headers = {
        "Content-Disposition": f"attachment; filename=omnivoicetts.{extension}",
        "X-OmniVoiceTTS-Sample-Rate": str(sample_rate),
        "X-OmniVoiceTTS-Duration": f"{duration:.3f}",
        "X-OmniVoiceTTS-Route": route_name,
        "X-OmniVoiceTTS-Format": output_format,
        "X-OmniVoiceTTS-Seed": str(used_seed),
    }
    if payload.voice:
        headers["X-OmniVoiceTTS-Requested-Voice"] = payload.voice
    return StreamingResponse(io.BytesIO(audio_bytes), media_type=media_type, headers=headers)


def progressive_audio_response(payload: TTSRequest, route_name: str) -> StreamingResponse:
    output_format, sample_rate, chunks, used_seed = synthesize_payload_chunks(payload)
    extension = OUTPUT_FORMATS[output_format]["extension"]
    media_type = OUTPUT_FORMATS[output_format]["media_type"]

    def body() -> Iterator[bytes]:
        yield from encode_audio_stream(chunks, output_format, sample_rate)

    headers = {
        "Content-Disposition": f"inline; filename=omnivoicetts-stream.{extension}",
        "X-OmniVoiceTTS-Sample-Rate": str(sample_rate),
        "X-OmniVoiceTTS-Route": route_name,
        "X-OmniVoiceTTS-Format": output_format,
        "X-OmniVoiceTTS-Streaming": "progressive-chunks",
        "X-OmniVoiceTTS-Seed": str(used_seed),
    }
    if payload.voice:
        headers["X-OmniVoiceTTS-Requested-Voice"] = payload.voice
    return StreamingResponse(body(), media_type=media_type, headers=headers)


@api.get("/tts/ping")
def ping() -> dict:
    return {"msg": "pong", "type": "OmniVoiceTTS", "version": read_version_file(), "build_id": BUILD_ID}


@api.get("/v1")
@api.get("/v1/")
def openai_index() -> dict:
    return {
        "object": "api",
        "name": "OmniVoiceTTS OpenAI-compatible API",
        "version": read_version_file(),
        "endpoints": ["/v1/models", "/v1/audio/speech"],
    }


@api.get("/v1/models")
def openai_models() -> dict:
    return {
        "object": "list",
        "data": [openai_model_payload(model_id) for model_id in OPENAI_MODEL_IDS],
    }


@api.get("/v1/models/{model_id}")
def openai_model(model_id: str) -> dict:
    try:
        normalize_openai_model(model_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return openai_model_payload(model_id)


@api.get("/v1/audio/models")
def openai_audio_models() -> dict:
    return openai_models()


@api.get("/v1/audio/voices")
def openai_audio_voices() -> dict:
    return {
        "object": "list",
        "data": openai_voice_payloads(),
    }


@api.post("/v1/audio/speech")
def openai_audio_speech(payload: OpenAISpeechRequest = Body(...)) -> StreamingResponse:
    try:
        tts_payload = openai_speech_to_tts_request(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_openai_speech_request(payload, tts_payload)
    return stream_audio_response(tts_payload, "/v1/audio/speech")


@api.get("/tts/status")
def status() -> dict:
    return get_status_payload()


@api.get("/tts/defaults")
def defaults() -> dict:
    return {
        "text": "Hello from OmniVoiceTTS.",
        "voice": "auto",
        "language": None,
        "device": "auto",
        "speed": 1.0,
        "num_step": 32,
        "guidance_scale": 2.0,
        "output_formats": {"default": "wav", "available": get_supported_output_formats()},
    }


@api.get("/tts/formats")
def formats() -> dict:
    return {"default": "wav", "formats": get_supported_output_formats(), "aliases": FORMAT_ALIASES}


@api.get("/tts/languages")
def languages() -> dict:
    return {
        "count": len(LANG_IDS),
        "language_ids": sorted(LANG_IDS),
        "language_names": sorted(lang_display_name(name) for name in LANG_NAMES),
    }


@api.get("/tts/speakers")
def speakers(language: str = "auto") -> dict:
    return {
        "language": language,
        "language_name": language,
        "speakers": ["auto", "voice-design", "voice-clone"],
        "compatibility_note": "OmniVoice does not use fixed Kokoro-style speaker ids.",
    }


@api.get("/tts/voices")
def voices() -> dict:
    return {
        "voices": [
            {"id": "auto", "name": "No Voice Prompt", "language": "auto", "language_name": "Any supported language"},
            {"id": "voice-design", "name": "Voice Design", "language": "multi", "language_name": "Any supported language"},
            {"id": "voice-clone", "name": "Voice Clone", "language": "multi", "language_name": "Any supported language"},
        ],
        "compatibility_note": "Kokoro voice ids in requests are accepted but ignored unless translated by a future compatibility profile.",
    }


@api.get("/tts/voice-design/options")
def voice_design_options() -> dict:
    return voice_design_options_payload()


@api.post("/tts/metrics")
def metrics(payload: TTSRequest = Body(...)) -> dict:
    text = payload.text or ""
    return {
        "voice": payload.voice or "auto",
        "language": payload.language,
        "metrics": {
            "characters": len(text),
            "words": len(text.split()),
        },
    }


@api.post("/tts/generate")
def generate_tts(payload: TTSRequest = Body(...)) -> StreamingResponse:
    return stream_audio_response(payload, "/tts/generate")


@api.post("/tts/convert")
def convert(payload: TTSRequest = Body(...)) -> StreamingResponse:
    return stream_audio_response(payload, "/tts/convert")


@api.get("/tts/stream-formats")
def stream_formats() -> dict:
    return {
        "default": "mp3",
        "formats": {
            "mp3": {"label": "MP3", "extension": "mp3", "media_type": "audio/mpeg"},
            "flac": {"label": "FLAC", "extension": "flac", "media_type": "audio/flac"},
            "ogg": {"label": "OGG Vorbis", "extension": "ogg", "media_type": "audio/ogg"},
        },
        "compatibility_note": "Progressive streaming emits encoded audio after each generated text chunk. WAV requests are streamed as MP3 because independent WAV files cannot be concatenated into one valid live stream.",
    }


@api.post("/tts/stream")
def stream_tts(payload: TTSRequest = Body(...)) -> StreamingResponse:
    return progressive_audio_response(payload, "/tts/stream")


@api.post("/tts/stream-chunks")
def stream_chunks_tts(payload: TTSRequest = Body(...)) -> StreamingResponse:
    return progressive_audio_response(payload, "/tts/stream-chunks")


@api.post("/tts/purge")
def purge_models(payload: PurgeRequest | None = Body(None)) -> dict:
    requested_device = payload.device if payload else None
    if requested_device:
        try:
            device = normalize_device(requested_device)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if device not in MODEL_CACHE:
            return {"purged": [], "remaining_model_devices": list(MODEL_CACHE)}
        del MODEL_CACHE[device]
        return {"purged": [device], "remaining_model_devices": list(MODEL_CACHE)}
    purged = list(MODEL_CACHE)
    MODEL_CACHE.clear()
    return {"purged": purged, "remaining_model_devices": []}


app = gr.mount_gradio_app(api, ui, path="/")


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7861"))
    reload_enabled = os.getenv("UVICORN_RELOAD", "0").lower() in {"1", "true", "yes"}
    uvicorn.run("omnivoice.app:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
