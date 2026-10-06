from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from omnivoice.service.paths import (
    AUDIO_EXTENSIONS,
    default_upload_roots,
    find_safe_file_by_name,
    safe_existing_file_path,
)

OPENAI_CALL_LOG: list[dict[str, str]] = []
OPENAI_CALL_LOG_LOCK = threading.Lock()
OPENAI_CALL_LOG_LIMIT = 50
PROFILE_INDEX_LOCK = threading.RLock()
LOGGER = logging.getLogger(__name__)


def normalize_profile_name(name: str | None) -> str:
    value = (name or "").strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "-", value)
    value = value.strip("-_")
    if not value:
        raise ValueError("Voice profile name must contain at least one letter or number.")
    if len(value) > 48:
        raise ValueError("Voice profile name must be 48 characters or fewer.")
    return value


def _write_profile_index(profile_dir: Path, profile_index: Path, profiles: dict[str, dict[str, Any]]) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=profile_dir,
            prefix=f".{profile_index.name}.",
            suffix=".tmp",
        ) as output_file:
            temporary_path = Path(output_file.name)
            json.dump(profiles, output_file, indent=2, sort_keys=True)
            output_file.write("\n")
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temporary_path, profile_index)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _resolve_profile_audio_path(profile_index: Path, ref_audio: str) -> tuple[str, bool]:
    profile_dir = profile_index.parent
    current = None
    try:
        current = safe_existing_file_path(
            ref_audio,
            [profile_dir],
            label="Saved profile audio path",
            allowed_extensions=AUDIO_EXTENSIONS,
        )
    except ValueError:
        current = None
    if current is not None:
        return str(current), False

    legacy_filename = Path(ref_audio).name
    try:
        migrated = safe_existing_file_path(
            profile_dir / legacy_filename,
            [profile_dir],
            label="Migrated profile audio path",
            allowed_extensions=AUDIO_EXTENSIONS,
        )
    except ValueError:
        return ref_audio, False
    return str(migrated), True


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
    migrated_count = 0
    for name, profile in raw.items():
        if not isinstance(profile, dict):
            continue
        ref_audio = str(profile.get("ref_audio") or "").strip()
        if not ref_audio:
            continue
        ref_audio, migrated = _resolve_profile_audio_path(profile_index, ref_audio)
        migrated_count += int(migrated)
        raw_seed = profile.get("seed")
        profiles[str(name)] = {
            "ref_audio": ref_audio,
            "ref_text": str(profile.get("ref_text") or ""),
            "language": str(profile.get("language") or ""),
            "seed": "" if raw_seed is None or raw_seed == "" else str(raw_seed),
            "randomize_seed": bool(profile.get("randomize_seed", False)),
        }
    if migrated_count:
        _write_profile_index(profile_index.parent, profile_index, profiles)
        LOGGER.info("Migrated %d saved voice profile path(s) to the persistent data layout.", migrated_count)
    return profiles


def save_openai_voice_profiles(profile_dir: Path, profile_index: Path, profiles: dict[str, dict[str, Any]]) -> None:
    _write_profile_index(profile_dir, profile_index, profiles)


def delete_openai_voice_profile(profile_dir: Path, profile_index: Path, name: str | None) -> str:
    profile_name = normalize_profile_name(name)
    with PROFILE_INDEX_LOCK:
        profiles = load_openai_voice_profiles(profile_index)
        profile = profiles.get(profile_name)
        if not profile:
            raise ValueError(f"OpenAI voice profile '{profile_name}' does not exist.")
        try:
            target = safe_existing_file_path(
                profile.get("ref_audio") or "",
                [profile_dir],
                label="Saved profile audio path",
                allowed_extensions=AUDIO_EXTENSIONS,
            )
            target.unlink()
        except FileNotFoundError:
            LOGGER.debug("Saved voice profile audio was already absent.")
        except OSError as exc:
            raise ValueError(f"Could not delete saved profile audio: {exc}") from exc
        profiles.pop(profile_name, None)
        save_openai_voice_profiles(profile_dir, profile_index, profiles)
    return profile_name


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
        allowed_source_roots or default_upload_roots(),
        label="Uploaded reference audio file",
        allowed_extensions=AUDIO_EXTENSIONS,
    )
    with PROFILE_INDEX_LOCK:
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
        previous_audio = None
        try:
            shutil.copyfile(source, destination)
            profiles = load_openai_voice_profiles(profile_index)
            previous_audio = (profiles.get(profile_name) or {}).get("ref_audio")
            profiles[profile_name] = {
                "ref_audio": str(destination),
                "ref_text": (ref_text or "").strip(),
                "language": (language or "").strip(),
                "seed": "" if randomize_seed else normalize_optional_seed(seed, max_seed),
                "randomize_seed": bool(randomize_seed),
            }
            save_openai_voice_profiles(profile_dir, profile_index, profiles)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        if previous_audio and Path(previous_audio) != destination:
            try:
                old_audio = safe_existing_file_path(
                    previous_audio,
                    [profile_dir],
                    label="Previous saved profile audio path",
                    allowed_extensions=AUDIO_EXTENSIONS,
                )
                old_audio.unlink(missing_ok=True)
            except (OSError, ValueError):
                LOGGER.warning("Could not remove replaced voice profile audio.")
    return profile_name


def commit_generated_voice_profiles(
    profile_dir: Path,
    profile_index: Path,
    max_seed: int,
    generated_profiles: list[dict[str, Any]],
    allowed_source_roots: list[Path],
) -> dict[str, str]:
    """Atomically publish a completed set of generated SSML-H voice profiles."""
    if not generated_profiles:
        return {}
    normalized: list[tuple[str, dict[str, Any], Path]] = []
    seen: set[str] = set()
    for item in generated_profiles:
        requested_name = str(item.get("name") or "")
        profile_name = normalize_profile_name(requested_name)
        if profile_name in seen:
            raise ValueError(f"Generated voice profile '{profile_name}' is duplicated.")
        seen.add(profile_name)
        source = safe_existing_file_path(
            str(item.get("audio_path") or ""),
            allowed_source_roots,
            label="Generated SSML-H voice audio",
            allowed_extensions=AUDIO_EXTENSIONS,
        )
        normalized.append((profile_name, item, source))

    with PROFILE_INDEX_LOCK:
        profile_dir.mkdir(parents=True, exist_ok=True)
        profiles = load_openai_voice_profiles(profile_index)
        for profile_name, item, _source in normalized:
            if profile_name in profiles and not bool(item.get("replace", False)):
                raise ValueError(
                    f"Voice profile '{profile_name}' already exists. Set replace='true' to replace it."
                )

        destinations: list[Path] = []
        previous_audio_paths: list[str] = []
        published_names: dict[str, str] = {}
        try:
            for profile_name, item, source in normalized:
                suffix = source.suffix.lower() if source.suffix.lower() in AUDIO_EXTENSIONS else ".wav"
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    dir=profile_dir,
                    prefix="voice-",
                    suffix=suffix,
                ) as output_file:
                    destination = Path(output_file.name)
                destinations.append(destination)
                shutil.copyfile(source, destination)
                previous_audio = (profiles.get(profile_name) or {}).get("ref_audio")
                if previous_audio:
                    previous_audio_paths.append(str(previous_audio))
                profiles[profile_name] = {
                    "ref_audio": str(destination),
                    "ref_text": str(item.get("ref_text") or "").strip(),
                    "language": str(item.get("language") or "").strip(),
                    "seed": normalize_optional_seed(item.get("seed"), max_seed),
                    "randomize_seed": False,
                }
                published_names[str(item.get("name") or profile_name)] = profile_name
            save_openai_voice_profiles(profile_dir, profile_index, profiles)
        except Exception:
            for destination in destinations:
                destination.unlink(missing_ok=True)
            raise

        active_paths = {str(item.get("ref_audio") or "") for item in profiles.values()}
        for previous_audio in previous_audio_paths:
            if previous_audio in active_paths:
                continue
            try:
                old_audio = safe_existing_file_path(
                    previous_audio,
                    [profile_dir],
                    label="Previous saved profile audio path",
                    allowed_extensions=AUDIO_EXTENSIONS,
                )
                old_audio.unlink(missing_ok=True)
            except (OSError, ValueError):
                LOGGER.warning("Could not remove replaced SSML-H voice profile audio.")
        return published_names


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


def openai_call_log_payload(limit: int = 20) -> list[dict[str, str]]:
    with OPENAI_CALL_LOG_LOCK:
        return [dict(row) for row in reversed(OPENAI_CALL_LOG[-max(0, limit):])]
