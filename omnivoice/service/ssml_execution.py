from __future__ import annotations

import logging
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

import numpy as np

from omnivoice.service.audio import apply_audio_effects, to_int16_audio
from omnivoice.service.ssml import (
    DEFAULT_DYNAMIC_VOICE_SAMPLE_LANGUAGE,
    DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT,
    SSMLPlan,
    SSMLUnit,
    SSMLValidationError,
    SSMLVoiceDefinition,
)


IMPLICIT_HANDOFF_MS = 120
SILENCE_THRESHOLD = 192
EDGE_SCAN_MS = 600
EDGE_KEEP_MS = 35
SPEECH_ATTEMPT_SEED_OFFSETS = (0, -1, 1, -2, 2)
MIN_EXPECTED_SPEECH_SECONDS = 0.25
MAX_EXPECTED_SPEECH_SECONDS = 1.0
EXPECTED_SECONDS_PER_CHARACTER = 0.05


@dataclass(frozen=True)
class SSMLVoiceBinding:
    name: str | None = None
    ref_audio: str | None = None
    ref_text: str | None = None
    instruct: str | None = None
    language: str | None = None
    cache_voice_prompt: bool = False
    voice_clone_prompt: Any = None
    generation_seed: int | None = None


@dataclass(frozen=True)
class PreparedSSMLVoice:
    definition: SSMLVoiceDefinition
    binding: SSMLVoiceBinding
    sample_text: str
    sample_language: str | None
    seed: int


GenerateSpeech = Callable[
    [SSMLUnit, SSMLVoiceBinding, float, float, float, float, int],
    tuple[int, np.ndarray],
]
PrepareVoice = Callable[
    [SSMLVoiceDefinition, str, str | None, int, Path],
    SSMLVoiceBinding,
]
ResolveVoice = Callable[[str], SSMLVoiceBinding]
ResolveLanguage = Callable[[str], str]
CommitProfiles = Callable[[list[PreparedSSMLVoice], Path], dict[str, str]]


def _trim_edge(audio: np.ndarray, sample_rate: int, *, leading: bool) -> np.ndarray:
    waveform = to_int16_audio(np.asarray(audio).reshape(-1))
    if waveform.size == 0:
        return waveform
    scan = min(waveform.size, round(sample_rate * EDGE_SCAN_MS / 1000))
    keep = min(scan, round(sample_rate * EDGE_KEEP_MS / 1000))
    section = waveform[:scan] if leading else waveform[-scan:]
    active = np.flatnonzero(np.abs(section.astype(np.int32)) > SILENCE_THRESHOLD)
    if active.size == 0:
        return waveform
    if leading:
        trim = max(0, int(active[0]) - keep)
        return waveform[trim:]
    trailing_silence = scan - int(active[-1]) - 1
    trim = max(0, trailing_silence - keep)
    return waveform if trim == 0 else waveform[:-trim]


def _edge_fade_and_pad(
    audio: np.ndarray,
    sample_rate: int,
    *,
    leading: bool,
    trailing: bool,
    pad_duration: float,
    fade_duration: float,
) -> np.ndarray:
    waveform = to_int16_audio(np.asarray(audio).reshape(-1)).copy()
    if waveform.size:
        fade_samples = min(round(sample_rate * fade_duration), waveform.size)
        if leading and fade_samples:
            waveform[:fade_samples] = (
                waveform[:fade_samples].astype(np.float32)
                * np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
            ).astype(np.int16)
        if trailing and fade_samples:
            waveform[-fade_samples:] = (
                waveform[-fade_samples:].astype(np.float32)
                * np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
            ).astype(np.int16)
    pad_samples = round(sample_rate * pad_duration)
    if leading and pad_samples:
        waveform = np.concatenate((np.zeros(pad_samples, dtype=np.int16), waveform))
    if trailing and pad_samples:
        waveform = np.concatenate((waveform, np.zeros(pad_samples, dtype=np.int16)))
    return waveform


class SSMLExecutionSession:
    """Request-owned SSML plan execution and SSML-H voice lifecycle."""

    def __init__(
        self,
        *,
        plan: SSMLPlan,
        default_binding: SSMLVoiceBinding,
        request_seed: int,
        request_speed: float,
        request_pitch_semitones: float,
        request_tempo: float,
        request_volume: float,
        normalize: bool,
        pad_duration: float,
        fade_duration: float,
        staging_parent: Path,
        resolve_voice: ResolveVoice,
        resolve_language: ResolveLanguage,
        prepare_voice: PrepareVoice,
        generate_speech: GenerateSpeech,
        commit_profiles: CommitProfiles,
    ) -> None:
        self.plan = plan
        self.default_binding = default_binding
        self.request_seed = request_seed
        self.request_speed = request_speed
        self.request_pitch_semitones = request_pitch_semitones
        self.request_tempo = request_tempo
        self.request_volume = request_volume
        self.normalize = normalize
        self.pad_duration = pad_duration
        self.fade_duration = fade_duration
        self.resolve_voice = resolve_voice
        self.resolve_language = resolve_language
        self.prepare_voice = prepare_voice
        self.generate_speech = generate_speech
        self.commit_profiles_callback = commit_profiles
        staging_parent.mkdir(parents=True, exist_ok=True)
        self.staging_dir = Path(tempfile.mkdtemp(prefix="ssml-h-", dir=staging_parent))
        self.dynamic_voices: dict[str, PreparedSSMLVoice] = {}
        self.resolved_voices: dict[str, SSMLVoiceBinding] = {}
        self.sample_rate: int | None = None
        self.committed_profiles: dict[str, str] = {}
        self._closed = False
        self._committed = False

    def prepare(self) -> None:
        for index, definition in enumerate(self.plan.voice_definitions):
            sample_text, sample_language = self._bootstrap_sample(definition)
            seed = definition.seed if definition.seed is not None else (self.request_seed + index) % (2**32)
            binding = self.prepare_voice(definition, sample_text, sample_language, seed, self.staging_dir)
            self.dynamic_voices[definition.name] = PreparedSSMLVoice(
                definition=definition,
                binding=binding,
                sample_text=sample_text,
                sample_language=sample_language,
                seed=seed,
            )

    def _bootstrap_sample(self, definition: SSMLVoiceDefinition) -> tuple[str, str | None]:
        if definition.sample:
            language = self.resolve_language(definition.sample_language) if definition.sample_language else None
            if language is None and definition.languages:
                language = self.resolve_language(definition.languages[0])
            return definition.sample, language
        return (
            DEFAULT_DYNAMIC_VOICE_SAMPLE_TEXT,
            self.resolve_language(DEFAULT_DYNAMIC_VOICE_SAMPLE_LANGUAGE),
        )

    def _binding_for_unit(self, unit: SSMLUnit) -> SSMLVoiceBinding:
        if not unit.voice:
            return self.default_binding
        dynamic = self.dynamic_voices.get(unit.voice)
        if dynamic is not None:
            return dynamic.binding
        if unit.voice not in self.resolved_voices:
            self.resolved_voices[unit.voice] = self.resolve_voice(unit.voice)
        return self.resolved_voices[unit.voice]

    def _render_speech(self, unit: SSMLUnit, index: int) -> np.ndarray:
        binding = self._binding_for_unit(unit)
        speed = self.request_speed * unit.prosody.rate
        pitch = self.request_pitch_semitones + unit.prosody.pitch_semitones
        tempo = self.request_tempo
        volume = self.request_volume * unit.prosody.volume
        if not 0.5 <= speed <= 1.5:
            raise SSMLValidationError(
                f"Effective speed for SSML unit {index + 1} is {speed:g}; OmniVoiceTTS supports 0.5 to 1.5."
            )
        if not -12.0 <= pitch <= 12.0:
            raise SSMLValidationError(
                f"Effective pitch for SSML unit {index + 1} is {pitch:g}st; OmniVoiceTTS supports -12st to +12st."
            )
        if not 0.5 <= tempo <= 2.0:
            raise SSMLValidationError(
                f"Effective tempo for SSML unit {index + 1} is {tempo:g}; OmniVoiceTTS supports 0.5 to 2.0."
            )
        if not 0.0 <= volume <= 2.0:
            raise SSMLValidationError(
                f"Effective volume for SSML unit {index + 1} is {volume:g}; OmniVoiceTTS supports 0 to 2.0."
            )
        seed = binding.generation_seed
        if seed is None:
            seed = (self.request_seed + len(self.plan.voice_definitions) + index) % (2**32)
        character_count = sum(character.isalnum() for character in unit.text)
        minimum_seconds = min(
            MAX_EXPECTED_SPEECH_SECONDS,
            max(
                MIN_EXPECTED_SPEECH_SECONDS,
                character_count * EXPECTED_SECONDS_PER_CHARACTER / speed,
            ),
        )
        best: tuple[int, np.ndarray] | None = None
        for attempt, seed_offset in enumerate(SPEECH_ATTEMPT_SEED_OFFSETS):
            attempt_seed = (seed + seed_offset) % (2**32)
            sample_rate, waveform = self.generate_speech(
                unit,
                binding,
                speed,
                pitch,
                tempo,
                volume,
                attempt_seed,
            )
            waveform = to_int16_audio(np.asarray(waveform).reshape(-1))
            if best is None or waveform.size / sample_rate > best[1].size / best[0]:
                best = (sample_rate, waveform)
            actual_seconds = waveform.size / sample_rate
            if actual_seconds >= minimum_seconds:
                break
            if attempt + 1 < len(SPEECH_ATTEMPT_SEED_OFFSETS):
                logging.warning(
                    "SSML speech unit %d returned %.3fs for %d alphanumeric characters; "
                    "retrying with a deterministic alternate seed.",
                    index + 1,
                    actual_seconds,
                    character_count,
                )
        assert best is not None
        sample_rate, waveform = best
        if self.sample_rate is None:
            self.sample_rate = sample_rate
        elif sample_rate != self.sample_rate:
            raise RuntimeError("SSML synthesis units returned inconsistent sample rates.")
        return waveform

    def _assembled_chunks(self) -> Iterator[np.ndarray]:
        pending_audio: np.ndarray | None = None
        pending_break_ms: int | None = None
        leading_break_ms = 0
        speech_index = 0
        for unit in self.plan.units:
            if unit.kind == "break":
                if pending_audio is None:
                    leading_break_ms += unit.duration_ms
                else:
                    pending_break_ms = (pending_break_ms or 0) + unit.duration_ms
                continue

            current = self._render_speech(unit, speech_index)
            speech_index += 1
            sample_rate = self.sample_rate or 24_000
            if pending_audio is None:
                if leading_break_ms:
                    yield np.zeros(round(sample_rate * leading_break_ms / 1000), dtype=np.int16)
                    leading_break_ms = 0
                pending_audio = current
                continue

            previous = _trim_edge(pending_audio, sample_rate, leading=False)
            current = _trim_edge(current, sample_rate, leading=True)
            yield previous
            gap_ms = pending_break_ms if pending_break_ms is not None else IMPLICIT_HANDOFF_MS
            if gap_ms:
                yield np.zeros(round(sample_rate * gap_ms / 1000), dtype=np.int16)
            pending_audio = current
            pending_break_ms = None

        sample_rate = self.sample_rate or 24_000
        if pending_audio is not None:
            yield pending_audio
            if pending_break_ms:
                yield np.zeros(round(sample_rate * pending_break_ms / 1000), dtype=np.int16)
        elif leading_break_ms:
            yield np.zeros(round(sample_rate * leading_break_ms / 1000), dtype=np.int16)

    def render_array(self) -> tuple[int, np.ndarray]:
        chunks = list(self._assembled_chunks())
        sample_rate = self.sample_rate or 24_000
        waveform = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.int16)
        waveform = _edge_fade_and_pad(
            waveform,
            sample_rate,
            leading=True,
            trailing=True,
            pad_duration=self.pad_duration,
            fade_duration=self.fade_duration,
        )
        if self.normalize:
            waveform = apply_audio_effects(waveform, sample_rate, normalize=True)
        return sample_rate, waveform

    def iter_chunks(self) -> Iterator[np.ndarray]:
        if self.normalize:
            _sample_rate, waveform = self.render_array()
            yield waveform
            return
        iterator = iter(self._assembled_chunks())
        try:
            pending = next(iterator)
        except StopIteration:
            return
        first = True
        for current in iterator:
            yield _edge_fade_and_pad(
                pending,
                self.sample_rate or 24_000,
                leading=first,
                trailing=False,
                pad_duration=self.pad_duration,
                fade_duration=self.fade_duration,
            )
            first = False
            pending = current
        yield _edge_fade_and_pad(
            pending,
            self.sample_rate or 24_000,
            leading=first,
            trailing=True,
            pad_duration=self.pad_duration,
            fade_duration=self.fade_duration,
        )

    def commit_profiles(self) -> dict[str, str]:
        if self._committed:
            return dict(self.committed_profiles)
        persistent = [
            prepared
            for prepared in self.dynamic_voices.values()
            if prepared.definition.scope == "profile"
        ]
        self.committed_profiles = self.commit_profiles_callback(persistent, self.staging_dir)
        self._committed = True
        return dict(self.committed_profiles)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for prepared in self.dynamic_voices.values():
            prompt = prepared.binding.voice_clone_prompt
            del prompt
        self.dynamic_voices.clear()
        shutil.rmtree(self.staging_dir, ignore_errors=True)
