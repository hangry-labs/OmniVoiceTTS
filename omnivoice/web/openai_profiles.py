from __future__ import annotations

import html
import json
import re
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr

from omnivoice.service.paths import (
    AUDIO_EXTENSIONS,
    default_gradio_upload_roots,
    find_safe_file_by_name,
    safe_existing_file_path,
)

OPENAI_CALL_LOG: list[dict[str, str]] = []
OPENAI_CALL_LOG_LOCK = threading.Lock()
OPENAI_CALL_LOG_LIMIT = 50


def normalize_profile_name(name: str | None) -> str:
    value = (name or "").strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    value = value.strip("-_")
    if not value:
        raise ValueError("Voice profile name must contain at least one letter or number.")
    if len(value) > 48:
        raise ValueError("Voice profile name must be 48 characters or fewer.")
    return value


def load_openai_voice_profiles(profile_index: Path) -> dict[str, dict[str, Any]]:
    if not profile_index.exists():
        return {}
    try:
        raw = json.loads(profile_index.read_text(encoding="utf-8"))
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


def save_openai_voice_profiles(profile_dir: Path, profile_index: Path, profiles: dict[str, dict[str, Any]]) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_index.write_text(json.dumps(profiles, indent=2, sort_keys=True), encoding="utf-8")


def normalize_optional_seed(seed: int | float | str | None, max_seed: int) -> int | None:
    if seed is None or seed == "":
        return None
    value = int(seed)
    if value < 0 or value > max_seed:
        raise ValueError(f"Seed must be between 0 and {max_seed}.")
    return value


def save_openai_voice_profile(
    profile_dir: Path,
    profile_index: Path,
    max_seed: int,
    name: str,
    audio_path: str | None,
    allowed_source_roots: list[Path] | None = None,
    ref_text: str | None = None,
    language: str | None = None,
    seed: int | float | str | None = 12345,
    randomize_seed: bool = False,
) -> str:
    profile_name = normalize_profile_name(name)
    if not audio_path:
        raise ValueError("Upload a reference audio sample before saving the profile.")
    source = find_safe_file_by_name(
        audio_path,
        allowed_source_roots or default_gradio_upload_roots(),
        label="Uploaded reference audio file",
        allowed_extensions=AUDIO_EXTENSIONS,
    )
    profile_dir.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower() or ".wav"
    if suffix not in {".wav", ".mp3", ".flac", ".ogg", ".m4a"}:
        suffix = ".wav"
    with tempfile.NamedTemporaryFile(
        delete=False,
        dir=profile_dir,
        prefix="voice-",
        suffix=suffix,
    ) as output_file:
        destination = Path(output_file.name)
    shutil.copyfile(source, destination)
    profiles = load_openai_voice_profiles(profile_index)
    profiles[profile_name] = {
        "ref_audio": str(destination),
        "ref_text": (ref_text or "").strip(),
        "language": (language or "").strip(),
        "seed": "" if randomize_seed else normalize_optional_seed(seed, max_seed),
        "randomize_seed": bool(randomize_seed),
    }
    save_openai_voice_profiles(profile_dir, profile_index, profiles)
    return profile_name


def render_openai_voice_profiles(profile_index: Path) -> str:
    profiles = load_openai_voice_profiles(profile_index)
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


def render_openai_voice_profile_table(profile_index: Path) -> str:
    profiles = load_openai_voice_profiles(profile_index)
    lines = [
        "### Saved Voices",
        "",
        "| Delete | Voice | Language | Seed | Transcript |",
        "|---|---|---|---|---|",
    ]
    if not profiles:
        lines.append("|  | No saved voices yet |  |  |  |")
        return "\n".join(lines)
    for name, profile in sorted(profiles.items()):
        language = profile.get("language") or "request/default"
        seed = "random" if profile.get("randomize_seed") else profile.get("seed") or "12345"
        transcript = "yes" if profile.get("ref_text") else "no"
        lines.append(
            "| x | "
            f"`{html.escape(name)}` | "
            f"`{html.escape(str(language))}` | "
            f"`{html.escape(str(seed))}` | "
            f"{transcript} |"
        )
    return "\n".join(lines)


def openai_voice_profile_choices(profile_index: Path) -> list[str]:
    return sorted(load_openai_voice_profiles(profile_index))


def openai_voice_profile_dropdown_update(profile_index: Path, selected: str | None = None):
    choices = openai_voice_profile_choices(profile_index)
    value = selected if selected in choices else None
    return gr.update(choices=choices, value=value)


def save_openai_voice_profile_from_ui(
    profile_dir: Path,
    profile_index: Path,
    max_seed: int,
    allowed_source_roots: list[Path],
    name: str,
    audio_path: str | None,
    ref_text: str | None,
    language: str | None,
    seed: int | float | str | None,
    randomize_seed: bool,
) -> tuple[str, object, str]:
    try:
        profile_name = save_openai_voice_profile(
            profile_dir,
            profile_index,
            max_seed,
            name,
            audio_path,
            allowed_source_roots,
            ref_text,
            language,
            seed,
            randomize_seed,
        )
    except ValueError as exc:
        return f"OpenAI voice profile error: {exc}", openai_voice_profile_dropdown_update(profile_index), render_openai_voice_profile_table(profile_index)
    return f"Saved OpenAI voice profile `{profile_name}`.", openai_voice_profile_dropdown_update(profile_index, profile_name), render_openai_voice_profile_table(profile_index)


def delete_openai_voice_profile_from_ui(profile_dir: Path, profile_index: Path, name: str | None) -> tuple[str, object, str]:
    try:
        profile_name = normalize_profile_name(name)
    except ValueError as exc:
        return f"OpenAI voice profile delete error: {exc}", openai_voice_profile_dropdown_update(profile_index), render_openai_voice_profile_table(profile_index)
    profiles = load_openai_voice_profiles(profile_index)
    profile = profiles.get(profile_name)
    if not profile:
        return f"OpenAI voice profile delete error: `{profile_name}` does not exist.", openai_voice_profile_dropdown_update(profile_index), render_openai_voice_profile_table(profile_index)
    try:
        target = safe_existing_file_path(
            profile.get("ref_audio") or "",
            [profile_dir],
            label="Saved profile audio path",
            allowed_extensions=AUDIO_EXTENSIONS,
        )
        target.unlink()
    except (OSError, ValueError):
        pass
    profiles.pop(profile_name, None)
    save_openai_voice_profiles(profile_dir, profile_index, profiles)
    return f"Deleted OpenAI voice profile `{profile_name}`.", openai_voice_profile_dropdown_update(profile_index), render_openai_voice_profile_table(profile_index)


def append_openai_call_log(payload, tts_payload, profile_source: str) -> None:
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
