from __future__ import annotations

import io
import html
import os
import re
import subprocess
import tempfile
import threading
import wave
from datetime import datetime
from pathlib import Path
from typing import Optional

import gradio as gr
import numpy as np
import torch
import uvicorn
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from omnivoice import OmniVoice, OmniVoiceGenerationConfig, __version__
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
}

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


def read_version_file() -> str:
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return APP_VERSION


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


def has_bracket_token(text: str | None) -> bool:
    return bool(BRACKET_TOKEN_PATTERN.search(text or ""))


def validate_voice_design_text(text: str | None, instruct: str | None) -> None:
    if (instruct or "").strip() and has_bracket_token(text):
        raise ValueError(VOICE_DESIGN_BRACKET_TOKEN_MESSAGE)


def nonverbal_tags_markdown() -> str:
    tags = ", ".join(f"`{tag}`" for tag in SUPPORTED_NONVERBAL_TAGS)
    return (
        "### Expressive bracket tags\n\n"
        "OmniVoice can read these bracket tags inside text when using **No Voice Prompt** or **Voice Clone**:\n\n"
        f"{tags}\n\n"
        "Use them inside a sentence or between clauses, not as the first or last thing in the prompt. "
        "Example: `That joke almost worked. [laughter] Maybe the timing was the problem.`\n\n"
        "Do **not** use bracket tags with **Voice Design**. Voice Design is for speaker attributes such as "
        "gender, age, pitch, accent, dialect, or whisper. Combining voice design with bracket tags can produce "
        "unstable non-speech audio, so the UI and API block that combination."
    )


def coerce_float(value, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


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
        effective_instruct = None
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
            class_temperature=coerce_float(class_temperature, 0.0),
            audio_chunk_duration=coerce_float(audio_chunk_duration, 15.0),
            audio_chunk_threshold=coerce_float(audio_chunk_threshold, 30.0),
        )
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
        return encoded_audio_to_temp_file(waveform, output_format, sample_rate), "Done."
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
            mode = gr.Radio(["No Voice Prompt", "Voice Design", "Voice Clone"], value="No Voice Prompt", label="Mode")
            text = gr.Textbox(
                label="Input Text",
                lines=5,
                value="Hello from OmniVoice. This Docker image includes a browser UI and an HTTP API.",
            )
            with gr.Accordion("Hints and safety notes", open=False):
                gr.Markdown(nonverbal_tags_markdown(), elem_classes="notice-card")
            generate_btn = gr.Button("Generate", variant="primary", elem_id="generate-btn")
            with gr.Accordion("Voice Design Builder (Voice Design mode only)", open=False):
                gr.Markdown(
                    "Voice Design controls speaker attributes only. For expressive bracket tags, switch to "
                    "`No Voice Prompt` or `Voice Clone`."
                )
                language = gr.Dropdown(LANGUAGE_CHOICES, value="Auto", label="Language")
                with gr.Row():
                    design_gender = gr.Dropdown(
                        choices=["No preference"] + VOICE_DESIGN_CATEGORIES["gender"]["options"],
                        value="No preference",
                        label="Gender",
                    )
                    design_age = gr.Dropdown(
                        choices=["No preference"] + VOICE_DESIGN_CATEGORIES["age"]["options"],
                        value="No preference",
                        label="Age",
                    )
                with gr.Row():
                    design_pitch = gr.Dropdown(
                        choices=["No preference"] + VOICE_DESIGN_CATEGORIES["pitch"]["options"],
                        value="No preference",
                        label="Pitch",
                    )
                    design_style = gr.Dropdown(
                        choices=["No preference"] + VOICE_DESIGN_CATEGORIES["style"]["options"],
                        value="No preference",
                        label="Style",
                    )
                with gr.Row():
                    design_english_accent = gr.Dropdown(
                        choices=["No preference"] + VOICE_DESIGN_CATEGORIES["english_accent"]["options"],
                        value="No preference",
                        label="English Accent",
                    )
                    design_chinese_dialect = gr.Dropdown(
                        choices=["No preference"] + VOICE_DESIGN_CATEGORIES["chinese_dialect"]["options"],
                        value="No preference",
                        label="Chinese Dialect",
                    )
            ref_audio = gr.Audio(label="Reference Audio", sources=["upload"], type="filepath")
            ref_text = gr.Textbox(
                label="Reference Text",
                lines=2,
                placeholder="Optional transcript of the reference audio. Leave empty to let ASR transcribe it when available.",
                info=(
                    "Used only for Voice Clone. It tells the model what is spoken in the reference audio, "
                    "which helps separate the sampled voice from the new text you want to generate."
                ),
            )
        with gr.Column(scale=1, elem_classes="output-panel"):
            output_audio = gr.Audio(label="Output Audio", type="filepath", autoplay=True)
            status_box = gr.Textbox(label="Status", lines=2)
            with gr.Row():
                hardware = gr.Dropdown(hardware_choices, value=default_hardware, label="Hardware")
                output_format = gr.Dropdown(
                    choices=[(config["label"], key) for key, config in OUTPUT_FORMATS.items()],
                    value="mp3",
                    label="Output Format",
                )
            with gr.Accordion("Generation Settings", open=False):
                speed = gr.Slider(0.5, 1.5, value=1.0, step=0.05, label="Speed")
                duration = gr.Number(value=None, label="Fixed Duration (seconds)")
                num_step = gr.Slider(4, 64, value=32, step=1, label="Inference Steps")
                guidance_scale = gr.Slider(0.0, 4.0, value=2.0, step=0.1, label="Guidance Scale")
                denoise = gr.Checkbox(value=True, label="Denoise")
                preprocess_prompt = gr.Checkbox(value=True, label="Preprocess Prompt")
                postprocess_output = gr.Checkbox(value=True, label="Postprocess Output")
                with gr.Accordion("Advanced Model Controls", open=False):
                    t_shift = gr.Slider(0.01, 1.0, value=0.1, step=0.01, label="T Shift")
                    layer_penalty_factor = gr.Slider(0.0, 10.0, value=5.0, step=0.1, label="Layer Penalty")
                    position_temperature = gr.Slider(
                        0.0,
                        10.0,
                        value=5.0,
                        step=0.1,
                        label="Position Temperature",
                    )
                    class_temperature = gr.Slider(0.0, 2.0, value=0.0, step=0.05, label="Class Temperature")
                    audio_chunk_duration = gr.Number(value=15.0, label="Long Text Chunk Duration")
                    audio_chunk_threshold = gr.Number(value=30.0, label="Long Text Chunk Threshold")
            with gr.Accordion("Audio Controls", open=False):
                pitch_semitones = gr.Slider(-12, 12, value=0, step=0.5, label="Pitch")
                tempo = gr.Slider(0.5, 2, value=1, step=0.05, label="Tempo")
                volume = gr.Slider(0, 2, value=1, step=0.05, label="Volume")
                loudness_normalize = gr.Checkbox(value=False, label="Normalize Loudness")

    generate_btn.click(
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
        outputs=[output_audio, status_box],
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


def synthesize_payload(payload: TTSRequest) -> tuple[str, int, np.ndarray]:
    try:
        output_format = normalize_output_format(payload.output_format)
        requested_device = resolve_requested_device(payload.device, payload.use_gpu)
        normalize_device(requested_device)
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
    return output_format, sample_rate, waveform


def stream_audio_response(payload: TTSRequest, route_name: str) -> StreamingResponse:
    output_format, sample_rate, waveform = synthesize_payload(payload)
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
    }
    if payload.voice:
        headers["X-OmniVoiceTTS-Requested-Voice"] = payload.voice
    return StreamingResponse(io.BytesIO(audio_bytes), media_type=media_type, headers=headers)


@api.get("/tts/ping")
def ping() -> dict:
    return {"msg": "pong", "type": "OmniVoiceTTS", "version": read_version_file(), "build_id": BUILD_ID}


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
            "wav": {"label": "WAV", "extension": "wav", "media_type": "audio/wav"},
        },
        "compatibility_note": "OmniVoiceTTS currently returns full generated audio for stream compatibility routes.",
    }


@api.post("/tts/stream")
def stream_tts(payload: TTSRequest = Body(...)) -> StreamingResponse:
    if payload.output_format == "wav":
        payload.output_format = "mp3"
    return stream_audio_response(payload, "/tts/stream")


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
