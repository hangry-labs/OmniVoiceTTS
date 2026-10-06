from __future__ import annotations

import gc
import io
import json
import logging
import os
import platform
import random
import re
import sys
import tempfile
import threading
from uuid import uuid4
from collections import OrderedDict
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

import numpy as np
import torch
import uvicorn
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from omnivoice import OmniVoice, OmniVoiceGenerationConfig, __version__
from omnivoice.service.audio import (
    FORMAT_ALIASES,
    OUTPUT_FORMATS,
    SAMPLE_RATE,
    apply_audio_effects,
    audio_to_wav_bytes,
    encode_audio_bytes,
    encode_audio_stream,
    normalize_audio_format,
)
from omnivoice.service.paths import (
    AUDIO_EXTENSIONS,
    default_upload_roots,
    parse_path_roots,
    safe_existing_file_path,
)
from omnivoice.service.schemas import (
    MAX_RANDOM_SEED,
    CacheClearRequest,
    OpenAISpeechRequest,
    PurgeRequest,
    TTSRequest,
    TextNormalizationRequest,
    UIGenerationDefaults,
    VoiceProfileCreateRequest,
)
from omnivoice.service.ssml import (
    SSMLPlan,
    SSMLUnit,
    SSMLValidationError,
    SSMLVoiceDefinition,
    compile_ssml,
    ssml_capabilities,
)
from omnivoice.service.ssml_execution import (
    PreparedSSMLVoice,
    SSMLExecutionSession,
    SSMLVoiceBinding,
)
from omnivoice.service.voice_profiles import (
    append_openai_call_log,
    commit_generated_voice_profiles as _commit_generated_voice_profiles,
    delete_openai_voice_profile as _delete_openai_voice_profile,
    load_openai_voice_profiles as _load_openai_voice_profiles,
    normalize_optional_seed as _normalize_optional_seed,
    normalize_profile_name,
    openai_call_log_payload,
    save_openai_voice_profile as _save_openai_voice_profile,
)
from omnivoice.settings import RuntimeSettingsStore
from omnivoice.standalone_ui.gpu import GPU_MONITOR
from omnivoice.standalone_ui.server import ASSET_DIR, attach_ui
from omnivoice.utils.audio import get_resample_backend
from omnivoice.utils.common import fix_random_seed
from omnivoice.utils.lang_map import LANG_IDS, LANG_NAMES, LANG_NAME_TO_ID, lang_display_name
from omnivoice.utils.text import validate_synthesis_text
from omnivoice.utils.text_normalization import (
    SUPPORTED_NORMALIZATION_LANGUAGES,
    normalize_structured_text,
)


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "y", "on"}


def env_int(name: str, default: int, minimum: int = 1) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    parsed = int(value)
    return max(minimum, parsed)


DEFAULT_MODEL = os.getenv("OMNIVOICE_MODEL", "k2-fsa/OmniVoice")
DEFAULT_DEVICE = os.getenv("OMNIVOICE_DEVICE", "auto")
DEFAULT_ASR_MODEL = os.getenv("OMNIVOICE_ASR_MODEL", "openai/whisper-large-v3-turbo")
DEFAULT_ASR_DEVICE = os.getenv("OMNIVOICE_ASR_DEVICE", "").strip() or None
LOAD_ASR = env_bool("OMNIVOICE_LOAD_ASR", False)
ALLOW_CPU_EAGER_ASR = env_bool("OMNIVOICE_ALLOW_CPU_EAGER_ASR", False)
MAX_CONCURRENT_GENERATIONS = env_int("OMNIVOICE_MAX_CONCURRENT_GENERATIONS", 1)
CPU_MEMORY_WARNING_INTERVAL_SECONDS = env_int("OMNIVOICE_CPU_MEMORY_WARNING_INTERVAL_SECONDS", 300)
EMPTY_CUDA_CACHE_AFTER_REQUEST = env_bool("OMNIVOICE_EMPTY_CUDA_CACHE_AFTER_REQUEST", False)
RESET_CUDA_PEAK_AFTER_CACHE_CLEAR = env_bool("OMNIVOICE_RESET_CUDA_PEAK_AFTER_CACHE_CLEAR", False)
APP_VERSION = os.getenv("APP_VERSION", __version__)
BUILD_ID = os.getenv("BUILD_ID", "stable")
PACKAGE_DIR = Path(__file__).resolve().parent
OPENAI_DEFAULT_CLONE_AUDIO = PACKAGE_DIR / "runtime_assets" / "voices" / "openai_default_voice.mp3"
RUNTIME_SETTINGS = RuntimeSettingsStore()
OPENAI_VOICE_PROFILE_DIR = Path(
    os.getenv("OMNIVOICE_OPENAI_VOICE_PROFILE_DIR", "/app/persistent/voices/openai")
)
OPENAI_VOICE_PROFILE_INDEX = OPENAI_VOICE_PROFILE_DIR / "profiles.json"
REF_AUDIO_SAFE_ROOTS_ENV = os.getenv("OMNIVOICE_ALLOWED_REF_AUDIO_ROOTS", "")
UI_UPLOAD_DIR = Path(os.getenv("OMNIVOICE_UI_UPLOAD_DIR", Path(tempfile.gettempdir()) / "omnivoicetts-ui"))
UI_UPLOAD_LIMIT_BYTES = env_int("OMNIVOICE_UI_UPLOAD_LIMIT_MIB", 64) * 1024 * 1024
UI_UPLOADS: dict[str, Path] = {}
UI_UPLOADS_LOCK = threading.Lock()

OPENAI_MODEL_ALIASES = {
    "omnivoice": "omnivoice",
    "omnivoicetts": "omnivoice",
    "tts-1": "omnivoice",
    "tts-1-hd": "omnivoice",
    "gpt-4o-mini-tts": "omnivoice",
}
OPENAI_MODEL_ID = "omnivoice"
OPENAI_ADVERTISED_MODEL_IDS = [OPENAI_MODEL_ID]
OPENAI_ACCEPTED_MODEL_IDS = list(OPENAI_MODEL_ALIASES)
OPENAI_COMPATIBILITY_MODEL_IDS = [
    model_id for model_id in OPENAI_ACCEPTED_MODEL_IDS if model_id != OPENAI_MODEL_ID
]
OPENAI_VOICE_INSTRUCTIONS = {
    "default": None,
    "auto": None,
    "alloy": "female, young adult, moderate pitch",
    "echo": "male, middle-aged, low pitch",
    "fable": "female, young adult, high pitch",
    "onyx": "male, middle-aged, very low pitch",
    "nova": "female, young adult, high pitch",
    "shimmer": "female, young adult, moderate pitch",
    "benchmark_original_clone": None,
}
OPENAI_CLONE_VOICE_ALIASES = {"default", "alloy", "echo", "fable", "onyx", "nova", "shimmer", "benchmark_original_clone"}

CPU_MEMORY_SCENARIO_RECOMMENDATIONS_MIB = {
    "RV": 2048,
    "DV": 2048,
    "CR-NT": 6144,
    "CR-TX": 2048,
    "SV-NT": 7168,
    "SV-TX": 3072,
}
CPU_MEMORY_SCENARIO_DESCRIPTIONS = {
    "RV": "random/no-prompt voice",
    "DV": "voice design",
    "CR-NT": "direct clone without transcript",
    "CR-TX": "direct clone with transcript",
    "SV-NT": "stored voice without transcript",
    "SV-TX": "stored voice with transcript",
}
CPU_MEMORY_WARNING_LOCK = threading.Lock()
CPU_MEMORY_WARNING_LAST: dict[str, float] = {}

STARTUP_PARAMETER_DEFAULTS = OrderedDict(
    [
        ("APP_VERSION", __version__),
        ("BUILD_ID", "stable"),
        ("BUILD_DATE", ""),
        ("HOST", "0.0.0.0"),
        ("PORT", "7861"),
        ("UVICORN_RELOAD", "0"),
        ("CUDA_VISIBLE_DEVICES", ""),
        ("NVIDIA_VISIBLE_DEVICES", ""),
        ("NVIDIA_DRIVER_CAPABILITIES", ""),
        ("PYTORCH_CUDA_ALLOC_CONF", ""),
        ("HF_HOME", ""),
        ("OMNIVOICE_SETTINGS_PATH", "/app/persistent/app/settings.json"),
        ("HF_HUB_OFFLINE", ""),
        ("TRANSFORMERS_OFFLINE", ""),
        ("HF_TOKEN", ""),
        ("OMNIVOICE_UI_UPLOAD_DIR", str(UI_UPLOAD_DIR)),
        ("OMNIVOICE_UI_UPLOAD_LIMIT_MIB", "64"),
        ("TMPDIR", ""),
        ("OMNIVOICE_MODEL", "k2-fsa/OmniVoice"),
        ("OMNIVOICE_DEVICE", "auto"),
        ("OMNIVOICE_ASR_MODEL", "openai/whisper-large-v3-turbo"),
        ("OMNIVOICE_ASR_DEVICE", ""),
        ("OMNIVOICE_LOAD_ASR", "0"),
        ("OMNIVOICE_ALLOW_CPU_EAGER_ASR", "0"),
        ("OMNIVOICE_MAX_CONCURRENT_GENERATIONS", "1"),
        ("OMNIVOICE_EMPTY_CUDA_CACHE_AFTER_REQUEST", "0"),
        ("OMNIVOICE_RESET_CUDA_PEAK_AFTER_CACHE_CLEAR", "0"),
        ("OMNIVOICE_CPU_MEMORY_WARNING_INTERVAL_SECONDS", "300"),
        ("OMNIVOICE_OPENAI_VOICE_PROFILE_DIR", "/app/persistent/voices/openai"),
        ("OMNIVOICE_ALLOWED_REF_AUDIO_ROOTS", ""),
        ("OMNIVOICE_VOICE_PROMPT_CACHE_LIMIT", "32"),
        ("OMNIVOICE_RESAMPLE_BACKEND", "auto"),
        ("OMNIVOICE_UI_LOCALE", "en"),
    ]
)
SENSITIVE_ENV_NAME_PARTS = ("TOKEN", "SECRET", "PASSWORD", "PASS", "KEY", "CREDENTIAL", "AUTH")

HANGRYLABS_LOGO = r"""
 _   _                              _           _
| | | | __ _ _ __   __ _ _ __ _   _| |    __ _ | |__  ___
| |_| |/ _` | '_ \ / _` | '__| | | | |   / _` || '_ \/ __|
|  _  | (_| | | | | (_| | |  | |_| | |__| (_| || |_) \__ \
|_| |_|\__,_|_| |_|\__, |_|   \__, |_____\__,_||_.__/|___/
                   |___/      |___/
        OmniVoiceTTS
"""

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
GENERATION_SEMAPHORES: dict[str, threading.BoundedSemaphore] = {}
GENERATION_SEMAPHORE_LOCK = threading.Lock()
VOICE_CLONE_PROMPT_CACHE: OrderedDict[tuple[Any, ...], Any] = OrderedDict()
VOICE_CLONE_PROMPT_CACHE_LOCK = threading.Lock()
VOICE_CLONE_PROMPT_CACHE_LIMIT = int(os.getenv("OMNIVOICE_VOICE_PROMPT_CACHE_LIMIT", "32"))
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


def get_cuda_device_diagnostics() -> list[dict[str, Any]]:
    if not torch.cuda.is_available():
        return []
    devices = []
    for index in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(index)
        devices.append(
            {
                "index": index,
                "name": torch.cuda.get_device_name(index),
                "total_memory_bytes": props.total_memory,
                "compute_capability": f"{props.major}.{props.minor}",
                "multiprocessor_count": props.multi_processor_count,
            }
        )
    return devices


def get_runtime_label() -> str:
    cuda_devices = get_cuda_devices()
    if cuda_devices:
        visible = os.getenv("CUDA_VISIBLE_DEVICES", "all")
        device_list = ", ".join(f"{idx}:{name}" for idx, name in enumerate(cuda_devices))
        return f"GPU x{len(cuda_devices)} (visible={visible}) [{device_list}]"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "Apple MPS"
    return "CPU"


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


def ref_audio_allowed_roots() -> list[Path]:
    defaults = [
        OPENAI_VOICE_PROFILE_DIR,
        OPENAI_DEFAULT_CLONE_AUDIO.parent,
        Path("/data"),
        UI_UPLOAD_DIR,
        *default_upload_roots(),
    ]
    return parse_path_roots(REF_AUDIO_SAFE_ROOTS_ENV, defaults)


def validate_ref_audio_path(ref_audio: str | None) -> str | None:
    if not ref_audio:
        return None
    return str(
        safe_existing_file_path(
            ref_audio,
            ref_audio_allowed_roots(),
            label="Reference audio path",
            allowed_extensions=AUDIO_EXTENSIONS,
        )
    )


def get_model(device: str) -> OmniVoice:
    resolved_device = normalize_device(device)
    with MODEL_LOCK:
        if resolved_device not in MODEL_CACHE:
            dtype = torch.float16 if resolved_device.startswith("cuda") else torch.float32
            load_asr = should_eager_load_asr(resolved_device)
            MODEL_CACHE[resolved_device] = OmniVoice.from_pretrained(
                DEFAULT_MODEL,
                device_map=resolved_device,
                dtype=dtype,
                load_asr=load_asr,
                asr_model_name=DEFAULT_ASR_MODEL,
                asr_device=DEFAULT_ASR_DEVICE,
            )
        return MODEL_CACHE[resolved_device]


def should_eager_load_asr(device: str, warn: bool = True) -> bool:
    if not LOAD_ASR:
        return False
    if device == "cpu" and not ALLOW_CPU_EAGER_ASR:
        if warn:
            logging.warning(
                "OMNIVOICE_LOAD_ASR=1 ignored for CPU model preload. "
                "Saved voice profiles with ref_text do not need ASR, and eager Whisper loading can exhaust CPU RAM. "
                "Set OMNIVOICE_ALLOW_CPU_EAGER_ASR=1 to force eager CPU ASR loading."
            )
        return False
    return True


def get_generation_semaphore(device: str) -> threading.BoundedSemaphore:
    with GENERATION_SEMAPHORE_LOCK:
        if device not in GENERATION_SEMAPHORES:
            GENERATION_SEMAPHORES[device] = threading.BoundedSemaphore(MAX_CONCURRENT_GENERATIONS)
        return GENERATION_SEMAPHORES[device]


def cuda_memory_stats() -> list[dict[str, Any]]:
    if not torch.cuda.is_available():
        return []
    stats = []
    for index in range(torch.cuda.device_count()):
        stats.append(
            {
                "device": f"cuda:{index}",
                "name": torch.cuda.get_device_name(index),
                "allocated": torch.cuda.memory_allocated(index),
                "reserved": torch.cuda.memory_reserved(index),
                "max_allocated": torch.cuda.max_memory_allocated(index),
                "max_reserved": torch.cuda.max_memory_reserved(index),
            }
        )
    return stats


def clear_cuda_allocator_cache(reset_peak_stats: bool = False) -> dict[str, Any]:
    before = cuda_memory_stats()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        if reset_peak_stats:
            for index in range(torch.cuda.device_count()):
                torch.cuda.reset_peak_memory_stats(index)
    after = cuda_memory_stats()
    return {"before": before, "after": after}


def read_int_file(path: Path) -> int | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not value or value == "max":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def system_memory_total_bytes() -> int | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None


def system_memory_available_bytes() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, IndexError, ValueError):
        return None
    return None


def cgroup_memory_limit_bytes() -> int | None:
    limit = read_int_file(Path("/sys/fs/cgroup/memory.max"))
    if limit is None:
        limit = read_int_file(Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"))
    total = system_memory_total_bytes()
    if limit is not None and total is not None and limit > total * 10:
        return None
    return limit


def cgroup_memory_current_bytes() -> int | None:
    current = read_int_file(Path("/sys/fs/cgroup/memory.current"))
    if current is None:
        current = read_int_file(Path("/sys/fs/cgroup/memory/memory.usage_in_bytes"))
    return current


def bytes_to_mib(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / (1024 * 1024), 1)


def cpu_memory_stats() -> dict[str, Any]:
    limit = cgroup_memory_limit_bytes()
    current = cgroup_memory_current_bytes()
    if limit is not None and current is not None:
        available = max(0, limit - current)
        source = "cgroup"
    else:
        available = system_memory_available_bytes()
        source = "system"
    return {
        "source": source,
        "limit_bytes": limit,
        "current_bytes": current,
        "available_bytes": available,
        "limit_mib": bytes_to_mib(limit),
        "current_mib": bytes_to_mib(current),
        "available_mib": bytes_to_mib(available),
    }


def redact_startup_parameter(name: str, value: str) -> str:
    if value and any(part in name.upper() for part in SENSITIVE_ENV_NAME_PARTS):
        return "<redacted>"
    return value


def startup_parameter_diagnostics() -> dict[str, dict[str, Any]]:
    names = set(STARTUP_PARAMETER_DEFAULTS)
    for name in os.environ:
        if name.startswith("OMNIVOICE_"):
            names.add(name)
    parameters = OrderedDict()
    for name in sorted(names):
        env_value = os.getenv(name)
        default = STARTUP_PARAMETER_DEFAULTS.get(name, "")
        raw_value = env_value if env_value is not None else default
        parameters[name] = {
            "value": redact_startup_parameter(name, raw_value),
            "source": "env" if env_value is not None else "default",
            "set": env_value is not None,
        }
    return parameters


def should_cache_voice_clone_prompt(ref_audio: str | None) -> bool:
    if not ref_audio:
        return False
    try:
        # ref_audio has already passed safe_existing_file_path in the synthesis boundary.
        # codeql[py/path-injection]
        ref_path = Path(ref_audio).resolve(strict=True)
    except OSError:
        return False
    default_clone_path = None
    try:
        if OPENAI_DEFAULT_CLONE_AUDIO.exists():
            default_clone_path = OPENAI_DEFAULT_CLONE_AUDIO.resolve(strict=True)
    except OSError:
        # The optional default clone asset may not exist in every image variant.
        default_clone_path = None
    if default_clone_path is not None and ref_path == default_clone_path:
        return True
    try:
        return OPENAI_VOICE_PROFILE_DIR.resolve(strict=False) in ref_path.parents
    except OSError:
        return False


def cpu_memory_scenario(payload) -> str:
    has_ref_audio = bool((getattr(payload, "ref_audio", None) or "").strip())
    has_ref_text = bool((getattr(payload, "ref_text", None) or "").strip())
    has_stored_voice = bool(getattr(payload, "cache_voice_prompt", False) or (getattr(payload, "voice_profile", None) or "").strip())
    if has_ref_audio:
        if has_stored_voice:
            return "SV-TX" if has_ref_text else "SV-NT"
        return "CR-TX" if has_ref_text else "CR-NT"
    if (getattr(payload, "instruct", None) or "").strip():
        return "DV"
    return "RV"


def cpu_memory_recommendation_payload() -> dict[str, dict[str, Any]]:
    return {
        code: {
            "description": CPU_MEMORY_SCENARIO_DESCRIPTIONS[code],
            "recommended_mib": mib,
            "recommended_gb": int(mib / 1024),
        }
        for code, mib in CPU_MEMORY_SCENARIO_RECOMMENDATIONS_MIB.items()
    }


def should_emit_cpu_memory_warning(key: str) -> bool:
    now = datetime.now().timestamp()
    with CPU_MEMORY_WARNING_LOCK:
        previous = CPU_MEMORY_WARNING_LAST.get(key, 0)
        if now - previous < CPU_MEMORY_WARNING_INTERVAL_SECONDS:
            return False
        CPU_MEMORY_WARNING_LAST[key] = now
    return True


def warn_if_cpu_memory_tight(payload, route_name: str) -> None:
    try:
        resolved_device = normalize_device(resolve_requested_device(payload.device, payload.use_gpu))
    except RuntimeError:
        return
    if resolved_device != "cpu":
        return
    scenario = cpu_memory_scenario(payload)
    recommended_mib = CPU_MEMORY_SCENARIO_RECOMMENDATIONS_MIB[scenario]
    memory = cpu_memory_stats()
    limit_mib = memory.get("limit_mib")
    available_mib = memory.get("available_mib")
    reasons = []
    if limit_mib is not None and limit_mib < recommended_mib:
        reasons.append(f"container limit {limit_mib:.0f} MiB is below recommended {recommended_mib} MiB")
    if limit_mib is None and available_mib is not None and available_mib < recommended_mib:
        reasons.append(f"available system memory {available_mib:.0f} MiB is below recommended {recommended_mib} MiB")
    if limit_mib is not None and available_mib is not None and available_mib < 512:
        reasons.append(f"container memory headroom is only {available_mib:.0f} MiB")
    if not reasons:
        return
    key = f"{route_name}:{scenario}:{';'.join(reasons)}"
    if not should_emit_cpu_memory_warning(key):
        return
    logging.warning(
        "[cpu-memory] RAM is tight for %s on %s (%s). %s. "
        "OmniVoiceTTS will try to continue, but CPU generation may be killed by Docker/the OS under load. "
        "Provide more RAM, add ref_text for clone/profile requests, or use GPU mode when possible.",
        route_name,
        scenario,
        CPU_MEMORY_SCENARIO_DESCRIPTIONS[scenario],
        "; ".join(reasons),
    )


def voice_clone_prompt_cache_key(
    device: str,
    ref_audio: str,
    ref_text: str | None,
    preprocess_prompt: bool,
) -> tuple[Any, ...]:
    # ref_audio has already passed safe_existing_file_path in the synthesis boundary.
    # codeql[py/path-injection]
    ref_path = Path(ref_audio).resolve(strict=True)
    # codeql[py/path-injection]
    stat = ref_path.stat()
    return (
        device,
        str(ref_path),
        stat.st_size,
        stat.st_mtime_ns,
        ref_text or "",
        bool(preprocess_prompt),
    )


def get_cached_voice_clone_prompt(
    model: OmniVoice,
    device: str,
    ref_audio: str | None,
    ref_text: str | None,
    preprocess_prompt: bool,
    cache_enabled: bool = False,
):
    if not cache_enabled:
        return None
    if not should_cache_voice_clone_prompt(ref_audio):
        return None
    assert ref_audio is not None
    key = voice_clone_prompt_cache_key(device, ref_audio, ref_text, preprocess_prompt)
    with VOICE_CLONE_PROMPT_CACHE_LOCK:
        cached = VOICE_CLONE_PROMPT_CACHE.get(key)
        if cached is not None:
            VOICE_CLONE_PROMPT_CACHE.move_to_end(key)
            return cached
    prompt = model.create_voice_clone_prompt(
        ref_audio=ref_audio,
        ref_text=ref_text or None,
        preprocess_prompt=preprocess_prompt,
    )
    with VOICE_CLONE_PROMPT_CACHE_LOCK:
        VOICE_CLONE_PROMPT_CACHE[key] = prompt
        VOICE_CLONE_PROMPT_CACHE.move_to_end(key)
        while len(VOICE_CLONE_PROMPT_CACHE) > max(0, VOICE_CLONE_PROMPT_CACHE_LIMIT):
            VOICE_CLONE_PROMPT_CACHE.popitem(last=False)
    return prompt


def clear_voice_clone_prompt_cache(device: str | None = None) -> int:
    with VOICE_CLONE_PROMPT_CACHE_LOCK:
        if device is None:
            count = len(VOICE_CLONE_PROMPT_CACHE)
            VOICE_CLONE_PROMPT_CACHE.clear()
            return count
        keys = [key for key in VOICE_CLONE_PROMPT_CACHE if key and key[0] == device]
        for key in keys:
            VOICE_CLONE_PROMPT_CACHE.pop(key, None)
        return len(keys)


def normalize_language(language: str | None) -> str | None:
    value = (language or "").strip()
    if not value or value.lower() == "auto":
        return None
    if value in LANG_IDS:
        return value
    key = value.lower()
    return LANG_NAME_TO_ID.get(key, value)


def resolve_ssml_language(language: str | None) -> str:
    value = (language or "").strip()
    if not value:
        raise ValueError("SSML language must not be empty.")
    normalized = value.replace("_", "-").lower()
    if normalized in LANG_IDS:
        return normalized
    by_name = LANG_NAME_TO_ID.get(normalized)
    if by_name:
        return by_name
    base = normalized.split("-", 1)[0]
    if base in LANG_IDS:
        return base
    raise ValueError(f"Unsupported SSML language '{language}'. Use a language from GET /tts/languages.")


def normalize_output_format(output_format: str | None) -> str:
    return normalize_audio_format(output_format)


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


def resolve_generation_seed(seed, randomize_seed: bool) -> int:
    if randomize_seed:
        return random.randint(0, MAX_RANDOM_SEED)
    value = 42 if seed is None or seed == "" else int(seed)
    if value < 0 or value > MAX_RANDOM_SEED:
        raise ValueError(f"Seed must be between 0 and {MAX_RANDOM_SEED}.")
    return value


def load_openai_voice_profiles() -> dict[str, dict[str, Any]]:
    return _load_openai_voice_profiles(OPENAI_VOICE_PROFILE_INDEX)


def normalize_optional_seed(seed: int | float | str | None) -> int | None:
    return _normalize_optional_seed(seed, MAX_RANDOM_SEED)


def save_openai_voice_profile(
    name: str,
    audio_path: str | None,
    ref_text: str | None = None,
    language: str | None = None,
    seed: int | float | str | None = 12345,
    randomize_seed: bool = False,
) -> str:
    return _save_openai_voice_profile(
        OPENAI_VOICE_PROFILE_DIR,
        OPENAI_VOICE_PROFILE_INDEX,
        MAX_RANDOM_SEED,
        name,
        audio_path,
        [UI_UPLOAD_DIR, *default_upload_roots()],
        ref_text,
        language,
        seed,
        randomize_seed,
    )


def build_generation_config(
    num_step: int = 32,
    guidance_scale: float = 2.0,
    denoise: bool = True,
    preprocess_prompt: bool = True,
    postprocess_output: bool = True,
    pad_duration: float = 0.1,
    fade_duration: float = 0.1,
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
        pad_duration=pad_duration,
        fade_duration=fade_duration,
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
    normalize_text: bool = False,
    cache_voice_prompt: bool = False,
    voice_clone_prompt: Any = None,
) -> tuple[int, np.ndarray]:
    validate_synthesis_text(text)
    validate_voice_design_text(text, instruct)
    safe_ref_audio = validate_ref_audio_path(ref_audio)
    resolved_device = normalize_device(device)
    semaphore = get_generation_semaphore(resolved_device)
    with semaphore:
        model = get_model(resolved_device)
        preprocess_prompt = True if generation_config is None else bool(generation_config.preprocess_prompt)
        resolved_voice_clone_prompt = voice_clone_prompt
        if resolved_voice_clone_prompt is None:
            resolved_voice_clone_prompt = get_cached_voice_clone_prompt(
                model,
                resolved_device,
                safe_ref_audio,
                ref_text,
                preprocess_prompt,
                cache_voice_prompt,
            )
        audios = model.generate(
            text=text.strip(),
            language=normalize_language(language),
            ref_audio=None if resolved_voice_clone_prompt is not None else safe_ref_audio,
            ref_text=None if resolved_voice_clone_prompt is not None else ref_text or None,
            voice_clone_prompt=resolved_voice_clone_prompt,
            instruct=instruct or None,
            duration=duration if duration and duration > 0 else None,
            speed=speed,
            normalize_text=normalize_text,
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
    normalize_text: bool = False,
    cache_voice_prompt: bool = False,
) -> tuple[int, Iterator[np.ndarray]]:
    validate_synthesis_text(text)
    validate_voice_design_text(text, instruct)
    safe_ref_audio = validate_ref_audio_path(ref_audio)
    resolved_device = normalize_device(device)
    semaphore = get_generation_semaphore(resolved_device)
    with semaphore:
        model = get_model(resolved_device)
        preprocess_prompt = True if generation_config is None else bool(generation_config.preprocess_prompt)
        voice_clone_prompt = get_cached_voice_clone_prompt(
            model,
            resolved_device,
            safe_ref_audio,
            ref_text,
            preprocess_prompt,
            cache_voice_prompt,
        )
        sample_rate = int(model.sampling_rate or SAMPLE_RATE)

    def chunk_iterator() -> Iterator[np.ndarray]:
        with semaphore:
            for chunk in model.generate_stream(
                text=text.strip(),
                language=normalize_language(language),
                ref_audio=None if voice_clone_prompt is not None else safe_ref_audio,
                ref_text=None if voice_clone_prompt is not None else ref_text or None,
                voice_clone_prompt=voice_clone_prompt,
                instruct=instruct or None,
                duration=duration if duration and duration > 0 else None,
                speed=speed,
                normalize_text=normalize_text,
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
    default_device = normalize_device(DEFAULT_DEVICE)
    effective_load_asr = should_eager_load_asr(default_device, warn=False)
    return {
        "msg": "pong",
        "type": "OmniVoiceTTS",
        "version": read_version_file(),
        "package_version": APP_VERSION,
        "build_id": BUILD_ID,
        "runtime": get_runtime_label(),
        "device": DEFAULT_DEVICE,
        "resolved_device": default_device,
        "model": DEFAULT_MODEL,
        "sample_rate": SAMPLE_RATE,
        "load_asr": effective_load_asr,
        "requested_load_asr": LOAD_ASR,
        "allow_cpu_eager_asr": ALLOW_CPU_EAGER_ASR,
        "asr_model": DEFAULT_ASR_MODEL if effective_load_asr else None,
        "asr_device": DEFAULT_ASR_DEVICE or default_device,
        "resample_backend": get_resample_backend(),
        "languages": len(LANG_IDS),
        "cuda_memory": cuda_memory_stats(),
        "cpu_memory": cpu_memory_stats() if default_device == "cpu" else None,
        "cpu_memory_recommendations": cpu_memory_recommendation_payload() if default_device == "cpu" else None,
        "max_concurrent_generations": MAX_CONCURRENT_GENERATIONS,
        "empty_cuda_cache_after_request": EMPTY_CUDA_CACHE_AFTER_REQUEST,
        "reset_cuda_peak_after_cache_clear": RESET_CUDA_PEAK_AFTER_CACHE_CLEAR,
        "voice_compatibility": (
            "The voice field accepts saved profiles and OpenAI-style aliases where they can be translated "
            "to OmniVoice auto/design/clone generation; unknown Kokoro speaker ids are ignored."
        ),
        "loaded_model_devices": list(MODEL_CACHE),
        "voice_prompt_cache": {
            "entries": len(VOICE_CLONE_PROMPT_CACHE),
            "limit": VOICE_CLONE_PROMPT_CACHE_LIMIT,
        },
        "persistent_storage": {
            "settings_path": str(RUNTIME_SETTINGS.path),
            "settings_exists": RUNTIME_SETTINGS.path.is_file(),
            "voice_profile_dir": str(OPENAI_VOICE_PROFILE_DIR),
            "voice_profile_index_exists": OPENAI_VOICE_PROFILE_INDEX.exists(),
            "huggingface_home": os.getenv("HF_HOME", ""),
        },
        "output_formats": get_supported_output_formats(),
    }


def get_startup_diagnostics_payload() -> dict[str, Any]:
    try:
        resolved_device = normalize_device(DEFAULT_DEVICE)
        device_error = None
    except RuntimeError as exc:
        resolved_device = None
        device_error = str(exc)
    effective_load_asr = should_eager_load_asr(resolved_device, warn=False) if resolved_device else False
    return {
        "app": {
            "name": "OmniVoiceTTS",
            "version": read_version_file(),
            "package_version": APP_VERSION,
            "build_id": BUILD_ID,
            "build_label": get_build_label(),
        },
        "runtime": {
            "label": get_runtime_label(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
            "resample_backend": get_resample_backend(),
        },
        "hardware": {
            "cuda_available": torch.cuda.is_available(),
            "cuda_visible_devices": os.getenv("CUDA_VISIBLE_DEVICES", ""),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "cuda_devices": get_cuda_device_diagnostics(),
            "mps_available": bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available()),
        },
        "memory": {
            "cpu": cpu_memory_stats(),
            "cuda": cuda_memory_stats(),
        },
        "config": {
            "model": DEFAULT_MODEL,
            "device": DEFAULT_DEVICE,
            "resolved_device": resolved_device,
            "device_error": device_error,
            "load_asr": effective_load_asr,
            "requested_load_asr": LOAD_ASR,
            "allow_cpu_eager_asr": ALLOW_CPU_EAGER_ASR,
            "asr_model": DEFAULT_ASR_MODEL if effective_load_asr else None,
            "asr_device": DEFAULT_ASR_DEVICE or resolved_device,
            "max_concurrent_generations": MAX_CONCURRENT_GENERATIONS,
            "empty_cuda_cache_after_request": EMPTY_CUDA_CACHE_AFTER_REQUEST,
            "reset_cuda_peak_after_cache_clear": RESET_CUDA_PEAK_AFTER_CACHE_CLEAR,
            "cpu_memory_warning_interval_seconds": CPU_MEMORY_WARNING_INTERVAL_SECONDS,
            "voice_prompt_cache_limit": VOICE_CLONE_PROMPT_CACHE_LIMIT,
            "languages": len(LANG_IDS),
            "output_formats": sorted(OUTPUT_FORMATS),
        },
        "startup_parameters": startup_parameter_diagnostics(),
        "paths": {
            "settings_path": str(RUNTIME_SETTINGS.path),
            "settings_exists": RUNTIME_SETTINGS.path.is_file(),
            "openai_voice_profile_dir": str(OPENAI_VOICE_PROFILE_DIR),
            "openai_voice_profile_index_exists": OPENAI_VOICE_PROFILE_INDEX.exists(),
            "brand_asset_dir_exists": ASSET_DIR.exists(),
            "default_clone_audio_exists": OPENAI_DEFAULT_CLONE_AUDIO.exists(),
        },
        "offline": {
            "hf_hub_offline": os.getenv("HF_HUB_OFFLINE", ""),
            "transformers_offline": os.getenv("TRANSFORMERS_OFFLINE", ""),
        },
    }


def log_startup_diagnostics() -> None:
    for line in HANGRYLABS_LOGO.strip("\n").splitlines():
        print(line, flush=True)
    diagnostics = get_startup_diagnostics_payload()
    print(f"[startup] diagnostics={json.dumps(diagnostics, sort_keys=True)}", flush=True)
    if diagnostics["config"]["resolved_device"] == "cpu":
        print(
            f"[startup] cpu_memory_recommendations={json.dumps(cpu_memory_recommendation_payload(), sort_keys=True)}",
            flush=True,
        )


@asynccontextmanager
async def api_lifespan(app: FastAPI):
    log_startup_diagnostics()
    UI_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for stale_upload in UI_UPLOAD_DIR.glob("upload-*"):
        if stale_upload.is_file():
            stale_upload.unlink(missing_ok=True)
    try:
        yield
    finally:
        GPU_MONITOR.close()
        with UI_UPLOADS_LOCK:
            uploads = list(UI_UPLOADS.values())
            UI_UPLOADS.clear()
        for upload in uploads:
            upload.unlink(missing_ok=True)


api = FastAPI(
    title="OmniVoiceTTS API",
    description="HTTP API for Hangry Labs OmniVoiceTTS",
    version=read_version_file(),
    openapi_url="/tts/openapi.json",
    docs_url="/tts/docs",
    redoc_url="/tts/redoc",
    lifespan=api_lifespan,
)

ACCESS_LOGGER = logging.getLogger("omnivoice.access")


@api.middleware("http")
async def log_requests(request, call_next):
    response = await call_next(request)
    message = '%s "%s %s" %s' % (
        request.client.host if request.client else "-",
        request.method,
        request.url.path,
        response.status_code,
    )
    ACCESS_LOGGER.info(message)
    return response


def get_ui_generation_defaults() -> UIGenerationDefaults:
    stored = RUNTIME_SETTINGS.get("ui_generation_defaults", {})
    try:
        return UIGenerationDefaults.model_validate(stored)
    except (TypeError, ValueError):
        return UIGenerationDefaults()


def voice_profile_payloads() -> list[dict[str, Any]]:
    return [
        {
            "id": name,
            "language": profile.get("language") or "",
            "seed": profile.get("seed") or None,
            "randomize_seed": bool(profile.get("randomize_seed", False)),
            "has_transcript": bool((profile.get("ref_text") or "").strip()),
        }
        for name, profile in sorted(load_openai_voice_profiles().items())
    ]


def resolve_ui_upload(upload_token: str) -> Path:
    with UI_UPLOADS_LOCK:
        upload_path = UI_UPLOADS.get(upload_token)
    if upload_path is None or not upload_path.is_file():
        raise ValueError("The temporary reference-audio upload no longer exists.")
    return upload_path


def discard_ui_upload(upload_token: str) -> bool:
    with UI_UPLOADS_LOCK:
        upload_path = UI_UPLOADS.pop(upload_token, None)
    if upload_path is None:
        return False
    upload_path.unlink(missing_ok=True)
    return True


def normalize_openai_model(model: str | None) -> str:
    model_id = (model or OPENAI_MODEL_ID).strip().lower()
    if model_id not in OPENAI_MODEL_ALIASES:
        supported = ", ".join(OPENAI_ACCEPTED_MODEL_IDS)
        raise ValueError(f"Unsupported model '{model}'. Supported OpenAI-compatible model ids: {supported}")
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


def tts_request_has_field(payload: TTSRequest, field_name: str) -> bool:
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


def openai_model_payload(requested_id: str | None = None) -> dict:
    payload = {
        "id": OPENAI_MODEL_ID,
        "object": "model",
        "created": 0,
        "owned_by": "local",
        "root": DEFAULT_MODEL,
        "parent": None,
        "compatibility_aliases": OPENAI_COMPATIBILITY_MODEL_IDS,
        "compatibility_note": (
            "Local OmniVoiceTTS model served through OpenAI-compatible speech routes. "
            "OpenAI-style model names are accepted as request aliases only."
        ),
    }
    if requested_id and requested_id != OPENAI_MODEL_ID:
        payload["requested_id"] = requested_id
        payload["alias_for"] = OPENAI_MODEL_ID
    return payload


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
    ref_audio, ref_text, instruct, profile_source = resolve_openai_voice(payload)
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
        voice_profile=payload.voice_profile,
        language=language,
        ref_audio=ref_audio,
        ref_text=ref_text,
        instruct=instruct,
        speed=payload.speed,
        device=payload.device,
        num_step=payload.num_step,
        pad_duration=payload.pad_duration,
        fade_duration=payload.fade_duration,
        output_format=output_format,
        seed=seed,
        randomize_seed=randomize_seed,
        normalize_text=payload.normalize_text,
        cache_voice_prompt=profile_source.startswith(("profile:", "voice-profile:", "builtin-clone")),
    )


def tts_request_to_openai_speech_request(payload: TTSRequest) -> OpenAISpeechRequest:
    data: dict[str, Any] = {
        "model": "omnivoice",
        "input": payload.text,
        "voice": payload.voice or "auto",
        "response_format": payload.output_format,
        "speed": payload.speed if payload.speed is not None else 1.0,
        "device": payload.device,
        "num_step": payload.num_step,
        "pad_duration": payload.pad_duration,
        "fade_duration": payload.fade_duration,
        "normalize_text": payload.normalize_text,
        "instructions": payload.instruct,
        "ref_audio": payload.ref_audio,
        "ref_text": payload.ref_text,
        "voice_profile": payload.voice_profile,
    }
    for optional_field in ("language", "seed", "randomize_seed"):
        if tts_request_has_field(payload, optional_field):
            data[optional_field] = getattr(payload, optional_field)
    return OpenAISpeechRequest(**data)


def resolve_tts_compatible_voice(payload: TTSRequest) -> TTSRequest:
    voice = (payload.voice or "").strip()
    voice_profile = (payload.voice_profile or "").strip()
    if not voice and not voice_profile:
        return payload

    openai_payload = tts_request_to_openai_speech_request(payload)
    resolved = openai_speech_to_tts_request(openai_payload)
    return payload.model_copy(
        update={
            "ref_audio": resolved.ref_audio,
            "ref_text": resolved.ref_text,
            "instruct": resolved.instruct,
            "language": resolved.language,
            "seed": resolved.seed,
            "randomize_seed": resolved.randomize_seed,
            "cache_voice_prompt": payload.cache_voice_prompt or resolved.cache_voice_prompt,
        }
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
        f"normalize_text={tts_payload.normalize_text!r} "
        f"instructions_present={bool((payload.instructions or '').strip())} "
        f"profile={profile_source!r} "
        f"ref_audio_present={bool(tts_payload.ref_audio)} "
        f"ref_text_present={bool(tts_payload.ref_text)} "
        f"instruct={tts_payload.instruct!r}",
        flush=True,
    )


def ssml_voice_binding_from_payload(payload: TTSRequest, name: str | None = None) -> SSMLVoiceBinding:
    return SSMLVoiceBinding(
        name=name,
        ref_audio=payload.ref_audio,
        ref_text=payload.ref_text,
        instruct=payload.instruct,
        language=normalize_language(payload.language),
        cache_voice_prompt=payload.cache_voice_prompt,
    )


def resolve_ssml_saved_voice(name: str, profiles: dict[str, dict[str, Any]]) -> SSMLVoiceBinding:
    try:
        profile_name = normalize_profile_name(name)
    except ValueError as exc:
        raise ValueError(f"SSML voice '{name}' is not available in this deployment.") from exc
    profile = profiles.get(profile_name)
    if profile:
        return SSMLVoiceBinding(
            name=profile_name,
            ref_audio=profile["ref_audio"],
            ref_text=profile.get("ref_text") or None,
            language=normalize_language(profile.get("language")),
            cache_voice_prompt=True,
        )
    voice_id = name.strip().lower()
    if voice_id not in OPENAI_VOICE_INSTRUCTIONS:
        raise ValueError(
            f"SSML voice '{name}' is not available. Use a saved profile or a voice from GET /tts/voices."
        )
    if voice_id in OPENAI_CLONE_VOICE_ALIASES and OPENAI_DEFAULT_CLONE_AUDIO.exists():
        return SSMLVoiceBinding(
            name=voice_id,
            ref_audio=str(OPENAI_DEFAULT_CLONE_AUDIO),
            cache_voice_prompt=True,
        )
    return SSMLVoiceBinding(
        name=voice_id,
        instruct=OPENAI_VOICE_INSTRUCTIONS.get(voice_id),
    )


def _age_design_value(age: str | None) -> str | None:
    value = (age or "").strip().lower().replace("-", " ")
    if not value:
        return None
    if value.isdigit():
        number = int(value)
        if number <= 0 or number > 150:
            raise ValueError("SSML-H voice age must be between 1 and 150.")
        if number < 13:
            return "child"
        if number < 20:
            return "teenager"
        if number < 35:
            return "young adult"
        if number < 65:
            return "middle-aged"
        return "elderly"
    aliases = {
        "young adult": "young adult",
        "middle aged": "middle-aged",
        "child": "child",
        "teenager": "teenager",
        "elderly": "elderly",
    }
    if value not in aliases:
        raise ValueError(
            "SSML-H voice age must be a positive number, child, teenager, young-adult, middle-aged, or elderly."
        )
    return aliases[value]


def build_ssml_h_voice_instruct(definition: SSMLVoiceDefinition) -> str:
    if definition.description:
        raise ValueError(
            "OmniVoiceTTS does not support free-form h:description. Use gender, age, pitch, style, accent, or dialect."
        )
    if definition.accent and definition.dialect:
        raise ValueError(
            "SSML-H voice definitions cannot combine an English accent with a Chinese dialect."
        )
    values: list[str] = []
    if definition.gender:
        gender = definition.gender.strip().lower()
        if gender not in {"male", "female"}:
            raise ValueError("OmniVoiceTTS SSML-H gender supports male or female.")
        values.append(gender)
    age = _age_design_value(definition.age)
    if age:
        values.append(age)
    if definition.pitch:
        pitch = definition.pitch.strip().lower().replace("-", " ")
        if not pitch.endswith(" pitch"):
            pitch = f"{pitch} pitch"
        if pitch not in VOICE_DESIGN_CATEGORIES["pitch"]["options"]:
            raise ValueError(
                "OmniVoiceTTS SSML-H pitch supports very-low, low, moderate, high, or very-high."
            )
        values.append(pitch)
    if definition.style:
        style = definition.style.strip().lower()
        if style not in VOICE_DESIGN_CATEGORIES["style"]["options"]:
            raise ValueError("OmniVoiceTTS SSML-H style currently supports whisper only.")
        values.append(style)
    if definition.accent:
        accent = definition.accent.strip().lower().replace("-", " ")
        if not accent.endswith(" accent"):
            accent = f"{accent} accent"
        if accent not in VOICE_DESIGN_CATEGORIES["english_accent"]["options"]:
            raise ValueError(
                "Unsupported SSML-H accent for OmniVoiceTTS. See GET /tts/ssml/capabilities."
            )
        values.append(accent)
    if definition.dialect:
        dialect = definition.dialect.strip()
        if dialect not in VOICE_DESIGN_CATEGORIES["chinese_dialect"]["options"]:
            raise ValueError(
                "Unsupported SSML-H Chinese dialect for OmniVoiceTTS. See GET /tts/ssml/capabilities."
            )
        values.append(dialect)
    if not values:
        raise ValueError(
            f"SSML-H voice '{definition.name}' does not contain a voice-design property supported by OmniVoiceTTS."
        )
    return ", ".join(values)


def compile_ssml_request(payload: TTSRequest) -> tuple[SSMLPlan, dict[str, dict[str, Any]]]:
    profiles = load_openai_voice_profiles()
    default_language = None
    if (payload.language or "").strip() and (payload.language or "").strip().lower() != "auto":
        default_language = resolve_ssml_language(payload.language)

    def validate_voice(name: str, _definitions: frozenset[str]) -> None:
        resolve_ssml_saved_voice(name, profiles)

    plan = compile_ssml(
        payload.text,
        payload.input_type,
        default_language=default_language,
        resolve_language=resolve_ssml_language,
        validate_voice=validate_voice,
    )
    aliases = set(OPENAI_VOICE_INSTRUCTIONS)
    for definition in plan.voice_definitions:
        profile_name = normalize_profile_name(definition.name)
        if profile_name in profiles and not (definition.scope == "profile" and definition.replace):
            raise SSMLValidationError(
                f"Voice profile '{profile_name}' already exists. Use scope='profile' replace='true' to replace it."
            )
        if definition.name.lower() in aliases:
            raise SSMLValidationError(
                f"SSML-H voice definition '{definition.name}' conflicts with a built-in voice name."
            )
        for language in definition.languages:
            resolve_ssml_language(language)
        if definition.sample_language:
            resolve_ssml_language(definition.sample_language)
        build_ssml_h_voice_instruct(definition)
    return plan, profiles


def create_ssml_execution_session(
    payload: TTSRequest,
    used_seed: int,
) -> SSMLExecutionSession:
    if payload.duration is not None:
        raise SSMLValidationError(
            "Fixed request duration is not supported for multi-unit SSML. Use prosody rate and breaks instead."
        )
    plan, profiles = compile_ssml_request(payload)
    requested_device = resolve_requested_device(payload.device, payload.use_gpu)
    resolved_device = normalize_device(requested_device)
    config = build_generation_config(
        num_step=payload.num_step,
        guidance_scale=payload.guidance_scale,
        denoise=payload.denoise,
        preprocess_prompt=payload.preprocess_prompt,
        postprocess_output=payload.postprocess_output,
        pad_duration=0.0,
        fade_duration=0.0,
        t_shift=payload.t_shift,
        layer_penalty_factor=payload.layer_penalty_factor,
        position_temperature=payload.position_temperature,
        class_temperature=payload.class_temperature,
        audio_chunk_duration=payload.audio_chunk_duration,
        audio_chunk_threshold=payload.audio_chunk_threshold,
    )

    def resolve_voice(name: str) -> SSMLVoiceBinding:
        return resolve_ssml_saved_voice(name, profiles)

    def prepare_voice(
        definition: SSMLVoiceDefinition,
        sample_text: str,
        sample_language: str | None,
        seed: int,
        staging_dir: Path,
    ) -> SSMLVoiceBinding:
        language = sample_language
        if language is None and definition.languages:
            language = resolve_ssml_language(definition.languages[0])
        instruct = build_ssml_h_voice_instruct(definition)
        fix_random_seed(seed)
        reference_config = replace(config, pad_duration=0.1, fade_duration=0.1)
        sample_rate, waveform = synthesize_array(
            text=sample_text,
            language=language,
            instruct=instruct,
            device=resolved_device,
            generation_config=reference_config,
        )
        audio_path = staging_dir / f"{definition.name}.wav"
        audio_path.write_bytes(audio_to_wav_bytes(waveform, sample_rate))
        safe_audio = validate_ref_audio_path(str(audio_path))
        assert safe_audio is not None
        semaphore = get_generation_semaphore(resolved_device)
        with semaphore:
            model = get_model(resolved_device)
            prompt = model.create_voice_clone_prompt(
                ref_audio=safe_audio,
                ref_text=sample_text,
                preprocess_prompt=payload.preprocess_prompt,
            )
        return SSMLVoiceBinding(
            name=definition.name,
            ref_audio=safe_audio,
            ref_text=sample_text,
            language=language,
            voice_clone_prompt=prompt,
        )

    def generate_speech(
        unit: SSMLUnit,
        binding: SSMLVoiceBinding,
        speed: float,
        pitch: float,
        tempo: float,
        volume: float,
        seed: int,
    ) -> tuple[int, np.ndarray]:
        language = unit.language
        if not unit.language_explicit and binding.language:
            language = binding.language
        fix_random_seed(seed)
        return synthesize_array(
            text=unit.text,
            language=language,
            ref_audio=binding.ref_audio,
            ref_text=binding.ref_text,
            instruct=binding.instruct,
            speed=speed,
            device=resolved_device,
            generation_config=config,
            pitch_semitones=pitch,
            tempo=tempo,
            volume=volume,
            normalize=False,
            cache_voice_prompt=binding.cache_voice_prompt,
            voice_clone_prompt=binding.voice_clone_prompt,
        )

    def commit_profiles(prepared: list[PreparedSSMLVoice], staging_dir: Path) -> dict[str, str]:
        records = [
            {
                "name": item.definition.name,
                "audio_path": item.binding.ref_audio,
                "ref_text": item.sample_text,
                "language": item.sample_language or item.binding.language or "",
                "seed": item.seed,
                "replace": item.definition.replace,
            }
            for item in prepared
        ]
        published = _commit_generated_voice_profiles(
            OPENAI_VOICE_PROFILE_DIR,
            OPENAI_VOICE_PROFILE_INDEX,
            MAX_RANDOM_SEED,
            records,
            [staging_dir],
        )
        if published:
            clear_voice_clone_prompt_cache(resolved_device)
        return published

    session = SSMLExecutionSession(
        plan=plan,
        default_binding=ssml_voice_binding_from_payload(payload),
        request_seed=used_seed,
        request_speed=float(payload.speed or 1.0),
        request_pitch_semitones=payload.pitch_semitones,
        request_tempo=payload.tempo,
        request_volume=payload.volume,
        normalize=payload.normalize,
        pad_duration=payload.pad_duration,
        fade_duration=payload.fade_duration,
        staging_parent=UI_UPLOAD_DIR,
        resolve_voice=resolve_voice,
        resolve_language=resolve_ssml_language,
        prepare_voice=prepare_voice,
        generate_speech=generate_speech,
        commit_profiles=commit_profiles,
    )
    try:
        session.prepare()
    except Exception:
        session.close()
        raise
    return session


def _ssml_headers(
    payload: TTSRequest,
    route_name: str,
    output_format: str,
    sample_rate: int,
    used_seed: int,
    *,
    streaming: bool,
    duration: float | None = None,
) -> dict[str, str]:
    extension = OUTPUT_FORMATS[output_format]["extension"]
    headers = {
        "Content-Disposition": (
            f"inline; filename=omnivoicetts-ssml.{extension}"
            if streaming
            else f"attachment; filename=omnivoicetts-ssml.{extension}"
        ),
        "X-OmniVoiceTTS-Sample-Rate": str(sample_rate),
        "X-OmniVoiceTTS-Route": route_name,
        "X-OmniVoiceTTS-Format": output_format,
        "X-OmniVoiceTTS-Seed": str(used_seed),
        "X-OmniVoiceTTS-Input-Type": payload.input_type,
    }
    if streaming:
        headers["X-OmniVoiceTTS-Streaming"] = "ssml-units"
    if duration is not None:
        headers["X-OmniVoiceTTS-Duration"] = f"{duration:.3f}"
    return headers


def ssml_audio_response(payload: TTSRequest, route_name: str) -> StreamingResponse:
    session: SSMLExecutionSession | None = None
    try:
        output_format = normalize_output_format(payload.output_format)
        used_seed = resolve_generation_seed(payload.seed, payload.randomize_seed)
        session = create_ssml_execution_session(payload, used_seed)
        sample_rate, waveform = session.render_array()
        audio_bytes = encode_audio_bytes(waveform, output_format, sample_rate)
        session.commit_profiles()
        headers = _ssml_headers(
            payload,
            route_name,
            output_format,
            sample_rate,
            used_seed,
            streaming=False,
            duration=len(waveform) / sample_rate if sample_rate else 0,
        )
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type=OUTPUT_FORMATS[output_format]["media_type"],
            headers=headers,
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
    finally:
        if session is not None:
            session.close()
        if EMPTY_CUDA_CACHE_AFTER_REQUEST:
            clear_cuda_allocator_cache(RESET_CUDA_PEAK_AFTER_CACHE_CLEAR)


def ssml_progressive_audio_response(payload: TTSRequest, route_name: str) -> StreamingResponse:
    try:
        requested_format = normalize_output_format(payload.output_format)
        output_format = "mp3" if requested_format == "wav" else requested_format
        used_seed = resolve_generation_seed(payload.seed, payload.randomize_seed)
        session = create_ssml_execution_session(payload, used_seed)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc

    sample_rate = SAMPLE_RATE

    def body() -> Iterator[bytes]:
        completed = False
        try:
            yield from encode_audio_stream(session.iter_chunks(), output_format, sample_rate)
            completed = True
            session.commit_profiles()
        finally:
            if not completed:
                logging.info("SSML stream ended before completion; staged SSML-H profiles were not published.")
            session.close()
            if EMPTY_CUDA_CACHE_AFTER_REQUEST:
                clear_cuda_allocator_cache(RESET_CUDA_PEAK_AFTER_CACHE_CLEAR)

    return StreamingResponse(
        body(),
        media_type=OUTPUT_FORMATS[output_format]["media_type"],
        headers=_ssml_headers(
            payload,
            route_name,
            output_format,
            sample_rate,
            used_seed,
            streaming=True,
        ),
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
            pad_duration=payload.pad_duration,
            fade_duration=payload.fade_duration,
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
            normalize_text=payload.normalize_text,
            cache_voice_prompt=payload.cache_voice_prompt,
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
            pad_duration=payload.pad_duration,
            fade_duration=payload.fade_duration,
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
            normalize_text=payload.normalize_text,
            cache_voice_prompt=payload.cache_voice_prompt,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
    return output_format, sample_rate, chunks, used_seed


def stream_audio_response(payload: TTSRequest, route_name: str) -> StreamingResponse:
    try:
        payload = resolve_tts_compatible_voice(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    warn_if_cpu_memory_tight(payload, route_name)
    if payload.input_type != "text":
        return ssml_audio_response(payload, route_name)
    try:
        output_format, sample_rate, waveform, used_seed = synthesize_payload(payload)
        try:
            audio_bytes = encode_audio_bytes(waveform, output_format, sample_rate)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if EMPTY_CUDA_CACHE_AFTER_REQUEST:
            clear_cuda_allocator_cache(RESET_CUDA_PEAK_AFTER_CACHE_CLEAR)
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
    if payload.voice_profile:
        headers["X-OmniVoiceTTS-Voice-Profile"] = payload.voice_profile
    return StreamingResponse(io.BytesIO(audio_bytes), media_type=media_type, headers=headers)


def progressive_audio_response(payload: TTSRequest, route_name: str) -> StreamingResponse:
    try:
        payload = resolve_tts_compatible_voice(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    warn_if_cpu_memory_tight(payload, route_name)
    if payload.input_type != "text":
        return ssml_progressive_audio_response(payload, route_name)
    output_format, sample_rate, chunks, used_seed = synthesize_payload_chunks(payload)
    extension = OUTPUT_FORMATS[output_format]["extension"]
    media_type = OUTPUT_FORMATS[output_format]["media_type"]

    def body() -> Iterator[bytes]:
        try:
            yield from encode_audio_stream(chunks, output_format, sample_rate)
        finally:
            if EMPTY_CUDA_CACHE_AFTER_REQUEST:
                clear_cuda_allocator_cache(RESET_CUDA_PEAK_AFTER_CACHE_CLEAR)

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
    if payload.voice_profile:
        headers["X-OmniVoiceTTS-Voice-Profile"] = payload.voice_profile
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
        "data": [openai_model_payload(model_id) for model_id in OPENAI_ADVERTISED_MODEL_IDS],
    }


@api.get("/v1/models/{model_id}")
def openai_model(model_id: str) -> dict:
    try:
        normalized_model_id = normalize_openai_model(model_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    requested_model_id = (model_id or OPENAI_MODEL_ID).strip().lower()
    return openai_model_payload(requested_model_id if requested_model_id != normalized_model_id else None)


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


@api.post("/ui/reference-audio", include_in_schema=False)
async def upload_ui_reference_audio(audio: UploadFile = File(...)) -> dict[str, str]:
    suffix = Path(audio.filename or "").suffix.lower()
    if suffix not in AUDIO_EXTENSIONS:
        supported = ", ".join(sorted(AUDIO_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Reference audio must use one of: {supported}.")
    token = uuid4().hex
    UI_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_path = UI_UPLOAD_DIR / f"upload-{token}{suffix}"
    total = 0
    try:
        with upload_path.open("xb") as output:
            while chunk := await audio.read(1024 * 1024):
                total += len(chunk)
                if total > UI_UPLOAD_LIMIT_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Reference audio exceeds the {UI_UPLOAD_LIMIT_BYTES // (1024 * 1024)} MiB upload limit.",
                    )
                output.write(chunk)
    except Exception:
        upload_path.unlink(missing_ok=True)
        raise
    finally:
        await audio.close()
    if total == 0:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Reference audio is empty.")
    with UI_UPLOADS_LOCK:
        UI_UPLOADS[token] = upload_path
    return {"token": token, "path": str(upload_path), "name": Path(audio.filename or upload_path.name).name}


@api.delete("/ui/reference-audio/{upload_token}", include_in_schema=False)
def delete_ui_reference_audio(upload_token: str) -> dict[str, bool]:
    return {"deleted": discard_ui_upload(upload_token)}


@api.get("/tts/voice-profiles", tags=["Voices"])
def voice_profiles() -> dict[str, Any]:
    profiles = voice_profile_payloads()
    return {"object": "list", "data": profiles, "count": len(profiles)}


@api.post("/tts/voice-profiles", tags=["Voices"])
def create_voice_profile(payload: VoiceProfileCreateRequest) -> dict[str, Any]:
    try:
        upload_path = resolve_ui_upload(payload.upload_token)
        profile_name = save_openai_voice_profile(
            payload.name,
            str(upload_path),
            payload.ref_text,
            payload.language,
            payload.seed,
            payload.randomize_seed,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        discard_ui_upload(payload.upload_token)
    clear_voice_clone_prompt_cache()
    profile = next(item for item in voice_profile_payloads() if item["id"] == profile_name)
    return profile


@api.delete("/tts/voice-profiles/{profile_name}", tags=["Voices"])
def delete_voice_profile(profile_name: str) -> dict[str, str]:
    try:
        deleted = _delete_openai_voice_profile(
            OPENAI_VOICE_PROFILE_DIR,
            OPENAI_VOICE_PROFILE_INDEX,
            profile_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    clear_voice_clone_prompt_cache()
    return {"deleted": deleted}


@api.get("/tts/openai-calls", tags=["OpenAI compatibility"])
def openai_calls() -> dict[str, Any]:
    calls = openai_call_log_payload()
    return {"object": "list", "data": calls, "count": len(calls)}


@api.get("/system/settings", tags=["System"])
def system_settings() -> dict[str, Any]:
    return {"generation_defaults": get_ui_generation_defaults().model_dump()}


@api.put("/system/settings/generation-defaults", tags=["System"])
def save_generation_defaults(payload: UIGenerationDefaults) -> dict[str, Any]:
    defaults = payload.model_dump()
    RUNTIME_SETTINGS.set("ui_generation_defaults", defaults)
    return {"generation_defaults": defaults}


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
        "normalize_text": False,
        "output_formats": {"default": "wav", "available": get_supported_output_formats()},
    }


@api.get("/tts/formats")
def formats() -> dict:
    return {"default": "wav", "formats": get_supported_output_formats(), "aliases": FORMAT_ALIASES}


@api.get("/tts/languages")
def languages() -> dict:
    language_options = sorted(
        (
            {"id": LANG_NAME_TO_ID[name], "name": lang_display_name(name)}
            for name in LANG_NAMES
        ),
        key=lambda language: language["name"].casefold(),
    )
    return {
        "count": len(LANG_IDS),
        "language_ids": sorted(LANG_IDS),
        "language_names": sorted(lang_display_name(name) for name in LANG_NAMES),
        "languages": language_options,
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
    voice_rows = [
        {"id": "auto", "name": "No Voice Prompt", "language": "auto", "language_name": "Any supported language"},
        {"id": "voice-design", "name": "Voice Design", "language": "multi", "language_name": "Any supported language"},
        {"id": "voice-clone", "name": "Voice Clone", "language": "multi", "language_name": "Any supported language"},
    ]
    for voice_id in sorted(OPENAI_VOICE_INSTRUCTIONS):
        if voice_id == "auto":
            continue
        profile_type = "clone" if voice_id in OPENAI_CLONE_VOICE_ALIASES and OPENAI_DEFAULT_CLONE_AUDIO.exists() else "design"
        voice_rows.append(
            {
                "id": voice_id,
                "name": f"OpenAI alias: {voice_id}",
                "language": "multi",
                "language_name": "Any supported language",
                "profile_type": profile_type,
            }
        )
    for name, profile in sorted(load_openai_voice_profiles().items()):
        language = profile.get("language") or "request/default"
        voice_rows.append(
            {
                "id": name,
                "name": f"Saved voice: {name}",
                "language": language,
                "language_name": language,
                "profile_type": "clone",
            }
        )
    return {
        "voices": voice_rows,
        "compatibility_note": (
            "The voice field accepts saved profile names and OpenAI-style aliases on /tts/generate, "
            "/tts/convert, /tts/stream, and /tts/stream-chunks. Unknown Kokoro speaker ids are accepted "
            "for compatibility but ignored."
        ),
    }


@api.get("/tts/voice-design/options")
def voice_design_options() -> dict:
    return voice_design_options_payload()


@api.get("/tts/ssml/capabilities", tags=["SSML-H"])
def get_ssml_capabilities() -> dict:
    capabilities = ssml_capabilities()
    capabilities["ssml_h"]["voice_design"] = voice_design_options_payload()
    capabilities["ssml_h"]["persistent_profiles"] = True
    return capabilities


@api.post("/tts/text/normalize", tags=["Text"])
def preview_text_normalization(payload: TextNormalizationRequest = Body(...)) -> dict[str, object]:
    result = normalize_structured_text(payload.text, payload.language)
    response = result.model_dump()
    response["supported_languages"] = list(SUPPORTED_NORMALIZATION_LANGUAGES)
    return response


@api.post("/tts/metrics")
def metrics(payload: TTSRequest = Body(...)) -> dict:
    text = payload.text or ""
    if payload.input_type != "text":
        try:
            resolved = resolve_tts_compatible_voice(payload)
            plan, _profiles = compile_ssml_request(resolved)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        spoken_text = " ".join(unit.text for unit in plan.units if unit.kind == "speech")
        return {
            "voice": payload.voice or "auto",
            "language": payload.language,
            "input_type": payload.input_type,
            "metrics": {
                "source_characters": len(text),
                "spoken_characters": len(spoken_text),
                "words": len(spoken_text.split()),
                "speech_units": sum(unit.kind == "speech" for unit in plan.units),
                "break_units": sum(unit.kind == "break" for unit in plan.units),
                "break_ms": sum(unit.duration_ms for unit in plan.units if unit.kind == "break"),
                "voice_definitions": len(plan.voice_definitions),
                "voices": list(plan.voices),
                "languages": list(plan.languages),
            },
        }
    normalization = normalize_structured_text(text, payload.language) if payload.normalize_text else None
    spoken_text = normalization.normalized if normalization is not None else text
    return {
        "voice": payload.voice or "auto",
        "language": payload.language,
        "input_type": payload.input_type,
        "text_normalization": normalization.model_dump() if normalization is not None else None,
        "metrics": {
            "characters": len(text),
            "spoken_characters": len(spoken_text),
            "words": len(spoken_text.split()),
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


@api.post("/tts/cache/clear")
def clear_cache(payload: CacheClearRequest | None = Body(None)) -> dict:
    reset_peak_stats = payload.reset_peak_stats if payload else RESET_CUDA_PEAK_AFTER_CACHE_CLEAR
    result = clear_cuda_allocator_cache(reset_peak_stats)
    return {
        "msg": "cuda allocator cache cleared",
        "unloaded_models": False,
        "cleared_voice_prompt_cache": False,
        **result,
    }


@api.post("/tts/purge")
def purge_models(payload: PurgeRequest | None = Body(None)) -> dict:
    requested_device = payload.device if payload else None
    if requested_device:
        try:
            device = normalize_device(requested_device)
        except RuntimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        purged = []
        if device in MODEL_CACHE:
            del MODEL_CACHE[device]
            purged = [device]
        purged_voice_prompts = clear_voice_clone_prompt_cache(device)
        cache_clear = clear_cuda_allocator_cache(RESET_CUDA_PEAK_AFTER_CACHE_CLEAR)
        return {
            "purged": purged,
            "purged_voice_prompts": purged_voice_prompts,
            "remaining_model_devices": list(MODEL_CACHE),
            "cuda_cache_clear": cache_clear,
        }
    purged = list(MODEL_CACHE)
    MODEL_CACHE.clear()
    purged_voice_prompts = clear_voice_clone_prompt_cache()
    cache_clear = clear_cuda_allocator_cache(RESET_CUDA_PEAK_AFTER_CACHE_CLEAR)
    return {
        "purged": purged,
        "purged_voice_prompts": purged_voice_prompts,
        "remaining_model_devices": [],
        "cuda_cache_clear": cache_clear,
    }


app = attach_ui(api_app=api)


def main() -> None:
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7861"))
    reload_enabled = os.getenv("UVICORN_RELOAD", "0").lower() in {"1", "true", "yes"}
    uvicorn.run("omnivoice.app:app", host=host, port=port, reload=reload_enabled, access_log=False)


if __name__ == "__main__":
    main()
