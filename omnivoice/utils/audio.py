#!/usr/bin/env python3
# Copyright    2026  Xiaomi Corp.        (authors:  Han Zhu)
# Modified by Hangry Labs, 2026.
#
# See ../../LICENSE for clarification regarding multiple authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Audio I/O and processing utilities.

Provides functions for loading, resampling, silence removal,
chunking, cross-fading, and format conversion.

All public functions in this module operate on **numpy float32 arrays**
with shape ``(C, T)`` (channels-first).
"""

import io
import importlib
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch
from pydub import AudioSegment
from pydub.silence import detect_leading_silence, detect_nonsilent, split_on_silence

logger = logging.getLogger(__name__)
RESAMPLE_BACKEND = os.getenv("OMNIVOICE_RESAMPLE_BACKEND", "auto").strip().lower()
_LIBROSA_BACKENDS = {"librosa", "fallback", "no-torchaudio"}
_VALID_RESAMPLE_BACKENDS = {"auto", "torchaudio", *_LIBROSA_BACKENDS}
REFERENCE_LEAD_SILENCE_MS = 100
REFERENCE_TRAIL_SILENCE_MS = 200
REFERENCE_SILENCE_THRESHOLD_DB = -50.0
REFERENCE_EDGE_WARNING_MS = 40

if RESAMPLE_BACKEND not in _VALID_RESAMPLE_BACKENDS:
    choices = ", ".join(sorted(_VALID_RESAMPLE_BACKENDS))
    raise ValueError(f"Unsupported OMNIVOICE_RESAMPLE_BACKEND={RESAMPLE_BACKEND!r}; choose one of: {choices}")


@lru_cache(maxsize=1)
def get_resample_backend() -> str:
    """Resolve the configured backend without requiring torchaudio at import time."""
    if RESAMPLE_BACKEND in _LIBROSA_BACKENDS:
        return "librosa"
    try:
        importlib.import_module("torchaudio")
    except (ImportError, OSError) as exc:
        if RESAMPLE_BACKEND == "torchaudio":
            raise RuntimeError(
                "torchaudio was explicitly selected but could not be loaded. Install the "
                "'omnivoice[torchaudio]' extra or set OMNIVOICE_RESAMPLE_BACKEND=librosa."
            ) from exc
        logger.warning("torchaudio is unavailable; using the Librosa resampling backend: %s", exc)
        return "librosa"
    return "torchaudio"


def resample_audio(data: np.ndarray, orig_freq: int, new_freq: int) -> np.ndarray:
    """Resample channels-first float32 audio with a configurable backend."""
    if orig_freq == new_freq:
        return data
    if get_resample_backend() == "librosa":
        import librosa

        return librosa.resample(data, orig_sr=orig_freq, target_sr=new_freq, axis=-1).astype(
            np.float32,
            copy=False,
        )
    torchaudio = importlib.import_module("torchaudio")
    return torchaudio.functional.resample(
        torch.from_numpy(data),
        orig_freq=orig_freq,
        new_freq=new_freq,
    ).numpy()


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_waveform(audio_path: str):
    """Load audio from a file path, returning (data, sample_rate).

    Tries two backends in order:
    1. soundfile — covers WAV/FLAC/OGG etc., no ffmpeg needed.
    2. librosa — covers MP3/M4A etc. via audioread + ffmpeg.

    Returns:
        (data, sample_rate) where data is a numpy float32 array of
        shape (C, T).
    """
    try:
        data, sr = sf.read(audio_path, dtype="float32", always_2d=True)
        return data.T, sr  # (T, C) → (C, T)
    except Exception:
        # soundfile cannot handle MP3/M4A etc., fall back to librosa.
        import librosa

        data, sr = librosa.load(audio_path, sr=None, mono=False)
        if data.ndim == 1:
            data = data[np.newaxis, :]
        return data, sr


def load_audio(audio_path: str, sampling_rate: int) -> np.ndarray:
    """Load a waveform from file and resample to the target rate.

    Parameters:
        audio_path: path of the audio.
        sampling_rate: target sampling rate.

    Returns:
        Numpy float32 array of shape (1, T).
    """
    data, sr = load_waveform(audio_path)

    if data.shape[0] > 1:
        data = np.mean(data, axis=0, keepdims=True)
    if sr != sampling_rate:
        data = resample_audio(data, orig_freq=sr, new_freq=sampling_rate)

    return data


def load_audio_bytes(raw: bytes, sampling_rate: int) -> np.ndarray:
    """Load audio from in-memory bytes and resample.

    Parameters:
        raw: raw audio file bytes (e.g. from WebDataset).
        sampling_rate: target sampling rate.

    Returns:
        Numpy float32 array of shape (1, T).
    """
    buf = io.BytesIO(raw)

    try:
        data, sr = sf.read(buf, dtype="float32", always_2d=True)
        data = data.T  # (T, C) → (C, T)
    except Exception:
        import librosa

        buf.seek(0)
        data, sr = librosa.load(buf, sr=None, mono=False)
        if data.ndim == 1:
            data = data[np.newaxis, :]

    if data.shape[0] > 1:
        data = np.mean(data, axis=0, keepdims=True)
    if sr != sampling_rate:
        data = resample_audio(data, orig_freq=sr, new_freq=sampling_rate)

    return data


# ---------------------------------------------------------------------------
# Audio processing (all numpy in / numpy out)
# ---------------------------------------------------------------------------


def numpy_to_audiosegment(audio: np.ndarray, sample_rate: int) -> AudioSegment:
    """Convert a numpy float32 array of shape (C, T) to a pydub AudioSegment."""
    audio_int = (audio * 32768.0).clip(-32768, 32767).astype(np.int16)
    if audio_int.shape[0] > 1:
        audio_int = audio_int.T.flatten()  # interleave channels
    return AudioSegment(
        data=audio_int.tobytes(),
        sample_width=2,
        frame_rate=sample_rate,
        channels=audio.shape[0],
    )


def audiosegment_to_numpy(aseg: AudioSegment) -> np.ndarray:
    """Convert a pydub AudioSegment to a numpy float32 array of shape (C, T)."""
    data = np.array(aseg.get_array_of_samples()).astype(np.float32) / 32768.0
    if aseg.channels == 1:
        return data[np.newaxis, :]
    return data.reshape(-1, aseg.channels).T


def edge_silence_durations(
    audio: np.ndarray,
    sampling_rate: int,
    *,
    silence_threshold_db: float = REFERENCE_SILENCE_THRESHOLD_DB,
) -> tuple[int, int]:
    """Measure contiguous leading and trailing silence in milliseconds."""
    if audio.ndim != 2:
        raise ValueError("audio must have shape (channels, samples)")
    if sampling_rate <= 0:
        raise ValueError("sampling_rate must be positive")
    if audio.shape[-1] == 0:
        return 0, 0
    proxy = numpy_to_audiosegment(audio, sampling_rate)
    leading_ms = detect_leading_silence(
        proxy,
        silence_threshold=silence_threshold_db,
        chunk_size=10,
    )
    trailing_ms = detect_leading_silence(
        proxy.reverse(),
        silence_threshold=silence_threshold_db,
        chunk_size=10,
    )
    return int(leading_ms), int(trailing_ms)


def ensure_reference_edge_silence(
    audio: np.ndarray,
    sampling_rate: int,
    *,
    lead_silence_ms: int = REFERENCE_LEAD_SILENCE_MS,
    trail_silence_ms: int = REFERENCE_TRAIL_SILENCE_MS,
) -> tuple[np.ndarray, int, int]:
    """Pad a clone reference to the minimum safe edge-silence durations.

    The original float samples are retained exactly. Returned padding values
    are the number of milliseconds requested at each edge.
    """
    if audio.ndim != 2:
        raise ValueError("audio must have shape (channels, samples)")
    if sampling_rate <= 0:
        raise ValueError("sampling_rate must be positive")
    for name, value in (
        ("lead_silence_ms", lead_silence_ms),
        ("trail_silence_ms", trail_silence_ms),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if audio.shape[-1] == 0:
        return audio, 0, 0

    leading_ms, trailing_ms = edge_silence_durations(audio, sampling_rate)
    add_leading_ms = max(0, int(lead_silence_ms) - leading_ms)
    add_trailing_ms = max(0, int(trail_silence_ms) - trailing_ms)
    if add_leading_ms == 0 and add_trailing_ms == 0:
        return audio, 0, 0

    leading_samples = int(np.ceil(add_leading_ms * sampling_rate / 1000.0))
    trailing_samples = int(np.ceil(add_trailing_ms * sampling_rate / 1000.0))
    padded = np.pad(
        audio,
        ((0, 0), (leading_samples, trailing_samples)),
        mode="constant",
    )
    return padded.astype(audio.dtype, copy=False), add_leading_ms, add_trailing_ms


def analyze_reference_audio(
    audio: np.ndarray,
    sampling_rate: int,
) -> dict[str, Any]:
    """Return stable diagnostics for uploaded or saved clone references."""
    if audio.ndim != 2:
        raise ValueError("audio must have shape (channels, samples)")
    if sampling_rate <= 0:
        raise ValueError("sampling_rate must be positive")
    if audio.shape[-1] == 0:
        raise ValueError("Reference audio contains no samples.")
    if not np.isfinite(audio).all():
        raise ValueError("Reference audio contains non-finite samples.")

    leading_ms, trailing_ms = edge_silence_durations(audio, sampling_rate)
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
    clipped_fraction = float(np.mean(np.abs(audio) >= 0.999))
    duration_seconds = audio.shape[-1] / sampling_rate
    warnings: list[dict[str, str]] = []

    if duration_seconds < 3.0:
        warnings.append(
            {
                "code": "reference_too_short",
                "message": "Reference audio is under 3 seconds; 3-10 seconds of clear speech is recommended.",
            }
        )
    elif duration_seconds > 20.0:
        warnings.append(
            {
                "code": "reference_too_long",
                "message": "Reference audio exceeds 20 seconds and may increase memory use or reduce clone quality.",
            }
        )
    if leading_ms < REFERENCE_EDGE_WARNING_MS:
        warnings.append(
            {
                "code": "reference_starts_on_speech",
                "message": "Reference audio starts without a clean silence boundary; prompt preprocessing can add one.",
            }
        )
    if trailing_ms < REFERENCE_EDGE_WARNING_MS:
        warnings.append(
            {
                "code": "reference_ends_on_speech",
                "message": "Reference audio ends without a clean silence boundary; prompt preprocessing can add one.",
            }
        )
    if rms < 0.0001:
        warnings.append(
            {
                "code": "reference_appears_silent",
                "message": "Reference audio appears silent or too quiet to clone reliably.",
            }
        )
    if peak >= 0.999 and clipped_fraction >= 0.0001:
        warnings.append(
            {
                "code": "reference_may_clip",
                "message": "Reference audio reaches digital full scale and may be clipped.",
            }
        )

    return {
        "duration_seconds": round(duration_seconds, 3),
        "sample_rate": int(sampling_rate),
        "channels": int(audio.shape[0]),
        "peak": round(peak, 6),
        "rms": round(rms, 6),
        "clipped_fraction": round(clipped_fraction, 6),
        "leading_silence_ms": leading_ms,
        "trailing_silence_ms": trailing_ms,
        "recommended_leading_silence_ms": REFERENCE_LEAD_SILENCE_MS,
        "recommended_trailing_silence_ms": REFERENCE_TRAIL_SILENCE_MS,
        "prompt_padding": {
            "leading_ms": max(0, REFERENCE_LEAD_SILENCE_MS - leading_ms),
            "trailing_ms": max(0, REFERENCE_TRAIL_SILENCE_MS - trailing_ms),
        },
        "warnings": warnings,
    }


def analyze_reference_audio_file(audio_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Decode and analyze a clone-reference file without resampling it."""
    data, sampling_rate = load_waveform(str(Path(audio_path)))
    return analyze_reference_audio(np.asarray(data, dtype=np.float32), int(sampling_rate))


def remove_silence(
    audio: np.ndarray,
    sampling_rate: int,
    mid_sil: int = 300,
    lead_sil: int = 100,
    trail_sil: int = 300,
    keep_mid_sil: int | None = None,
    *,
    preserve_active_edges: bool = False,
    preserve_float: bool = True,
) -> np.ndarray:
    """Shorten long middle silences and trim edge silences.

    Parameters:
        audio: numpy array with shape (C, T).
        sampling_rate: sampling rate of the audio.
        mid_sil: minimum middle-silence duration in ms (0 to skip).
        lead_sil: kept leading silence in ms.
        trail_sil: kept trailing silence in ms.
        keep_mid_sil: maximum total duration kept from each detected middle
            silence. ``None`` preserves the historical two-sided behavior.
        preserve_active_edges: keep nonzero outer-edge samples even when they
            fall below the silence detector threshold.
        preserve_float: slice the original float waveform instead of rebuilding
            it through PCM16. Set to ``False`` for legacy compatibility.

    Returns:
        Numpy array with shape (C, T').
    """
    for name, value in (
        ("mid_sil", mid_sil),
        ("lead_sil", lead_sil),
        ("trail_sil", trail_sil),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, np.integer))
            or value < 0
        ):
            raise ValueError(f"{name} must be a non-negative integer")
    if keep_mid_sil is None:
        keep_mid_sil = 2 * mid_sil
    elif (
        isinstance(keep_mid_sil, bool)
        or not isinstance(keep_mid_sil, (int, np.integer))
        or keep_mid_sil < 0
    ):
        raise ValueError("keep_mid_sil must be a non-negative integer")
    if not isinstance(preserve_active_edges, bool):
        raise TypeError("preserve_active_edges must be a bool")
    if not isinstance(preserve_float, bool):
        raise TypeError("preserve_float must be a bool")
    if audio.ndim != 2:
        raise ValueError("audio must have shape (channels, samples)")
    if audio.shape[-1] == 0:
        return audio

    if not preserve_float:
        wave = numpy_to_audiosegment(audio, sampling_rate)

        if mid_sil > 0:
            non_silent_segs = split_on_silence(
                wave,
                min_silence_len=mid_sil,
                silence_thresh=-50,
                keep_silence=keep_mid_sil // 2,
                seek_step=10,
            )
            wave = AudioSegment.silent(duration=0, frame_rate=sampling_rate)
            for seg in non_silent_segs:
                wave += seg

        wave = remove_silence_edges(wave, lead_sil, trail_sil, -50)
        return audiosegment_to_numpy(wave)

    # Pydub detects millisecond ranges, but retained samples come directly from
    # the original float waveform so voiced audio is never quantized to PCM16.
    detection_proxy = numpy_to_audiosegment(audio, sampling_rate)

    if mid_sil > 0:
        keep_per_side = keep_mid_sil // 2
        output_ranges = [
            [start - keep_per_side, end + keep_per_side]
            for start, end in detect_nonsilent(
                detection_proxy,
                min_silence_len=mid_sil,
                silence_thresh=-50,
                seek_step=10,
            )
        ]
        for current, following in zip(output_ranges, output_ranges[1:]):
            if following[0] < current[1]:
                midpoint = (current[1] + following[0]) // 2
                current[1] = midpoint
                following[0] = midpoint

        sample_ranges = [
            (
                max(0, int(start * sampling_rate / 1000.0)),
                audio.shape[-1]
                if end >= len(detection_proxy)
                else min(audio.shape[-1], int(end * sampling_rate / 1000.0)),
            )
            for start, end in output_ranges
        ]
        if preserve_active_edges:
            first_active = _find_exact_active_edge(audio, from_end=False)
            last_active = _find_exact_active_edge(audio, from_end=True)
            if first_active is not None and last_active is not None:
                if sample_ranges:
                    sample_ranges[0] = (
                        min(sample_ranges[0][0], first_active),
                        sample_ranges[0][1],
                    )
                    sample_ranges[-1] = (
                        sample_ranges[-1][0],
                        max(sample_ranges[-1][1], last_active + 1),
                    )
                else:
                    sample_ranges = [(0, audio.shape[-1])]
        chunks = [
            audio[..., start:end] for start, end in sample_ranges if end > start
        ]
        processed = np.concatenate(chunks, axis=-1) if chunks else audio[..., :0]
    else:
        processed = audio

    if processed.shape[-1] == 0:
        return processed

    edge_proxy = numpy_to_audiosegment(processed, sampling_rate)
    leading_silence = detect_leading_silence(edge_proxy, silence_threshold=-50)
    trailing_silence = detect_leading_silence(
        edge_proxy.reverse(), silence_threshold=-50
    )
    start_sample = int(max(0, leading_silence - lead_sil) * sampling_rate / 1000.0)
    trim_trailing = int(max(0, trailing_silence - trail_sil) * sampling_rate / 1000.0)
    end_sample = max(0, processed.shape[-1] - trim_trailing)
    if preserve_active_edges:
        first_active = _find_exact_active_edge(processed, from_end=False)
        last_active = _find_exact_active_edge(processed, from_end=True)
        if first_active is not None and last_active is not None:
            start_sample = min(start_sample, first_active)
            end_sample = max(end_sample, last_active + 1)
    return processed[..., start_sample:end_sample]


def _find_exact_active_edge(audio: np.ndarray, *, from_end: bool) -> int | None:
    """Return the first sample index containing any exact nonzero channel."""
    active = np.any(audio != 0, axis=0)
    indices = np.flatnonzero(active)
    if indices.size == 0:
        return None
    return int(indices[-1] if from_end else indices[0])


def limit_audio_peak(audio: np.ndarray, peak_limit: float | None) -> np.ndarray:
    """Scale audio only when its absolute peak exceeds *peak_limit*."""
    if peak_limit is None:
        return audio
    if isinstance(peak_limit, bool) or not isinstance(
        peak_limit, (int, float, np.number)
    ):
        raise TypeError("peak_limit must be a real number or None")
    peak_limit = float(peak_limit)
    if not np.isfinite(peak_limit) or not 0 < peak_limit <= 1:
        raise ValueError("peak_limit must be finite and in the range (0, 1]")
    if audio.size == 0:
        return audio
    peak = float(np.max(np.abs(audio)))
    if peak <= peak_limit or peak <= 1e-12:
        return audio
    return audio * (peak_limit / peak)


def remove_silence_edges(
    audio: AudioSegment,
    lead_sil: int = 100,
    trail_sil: int = 300,
    silence_threshold: float = -50,
) -> AudioSegment:
    """Remove edge silences, keeping *lead_sil* / *trail_sil* ms."""
    start_idx = detect_leading_silence(audio, silence_threshold=silence_threshold)
    start_idx = max(0, start_idx - lead_sil)
    audio = audio[start_idx:]

    audio = audio.reverse()
    start_idx = detect_leading_silence(audio, silence_threshold=silence_threshold)
    start_idx = max(0, start_idx - trail_sil)
    audio = audio[start_idx:]
    audio = audio.reverse()

    return audio


def fade_and_pad_audio(
    audio: np.ndarray,
    pad_duration: float = 0.1,
    fade_duration: float = 0.1,
    sample_rate: int = 24000,
) -> np.ndarray:
    """Apply fade-in/out and pad with silence to prevent clicks.

    Args:
        audio: numpy array of shape (C, T).
        pad_duration: silence padding duration per side (seconds).
        fade_duration: fade curve duration (seconds).
        sample_rate: audio sampling rate.

    Returns:
        Processed numpy array of shape (C, T_new).
    """
    if audio.shape[-1] == 0:
        return audio

    fade_samples = int(fade_duration * sample_rate)
    pad_samples = int(pad_duration * sample_rate)

    processed = audio.copy()

    if fade_samples > 0:
        k = min(fade_samples, processed.shape[-1] // 2)
        if k > 0:
            fade_in = np.linspace(0, 1, k, dtype=np.float32)[np.newaxis, :]
            processed[..., :k] *= fade_in

            fade_out = np.linspace(1, 0, k, dtype=np.float32)[np.newaxis, :]
            processed[..., -k:] *= fade_out

    if pad_samples > 0:
        silence = np.zeros(
            (processed.shape[0], pad_samples),
            dtype=processed.dtype,
        )
        processed = np.concatenate([silence, processed, silence], axis=-1)

    return processed


def trim_long_audio(
    audio: np.ndarray,
    sampling_rate: int,
    max_duration: float = 15.0,
    min_duration: float = 3.0,
    trim_threshold: float = 20.0,
) -> np.ndarray:
    """Trim audio to <= *max_duration* by splitting at the largest silence gap.

    Only trims when the audio exceeds *trim_threshold* seconds.

    Args:
        audio: numpy array of shape (C, T).
        sampling_rate: audio sampling rate.
        max_duration: maximum duration in seconds.
        min_duration: minimum duration in seconds.
        trim_threshold: only trim if audio is longer than this (seconds).

    Returns:
        Trimmed numpy array.
    """
    duration = audio.shape[-1] / sampling_rate
    if duration <= trim_threshold:
        return audio

    seg = numpy_to_audiosegment(audio, sampling_rate)
    nonsilent = detect_nonsilent(
        seg, min_silence_len=100, silence_thresh=-40, seek_step=10
    )
    if not nonsilent:
        return audio

    max_ms = int(max_duration * 1000)
    min_ms = int(min_duration * 1000)

    best_split = 0
    for start, end in nonsilent:
        if start > best_split and start <= max_ms:
            best_split = start
        if end > max_ms:
            break

    if best_split < min_ms:
        best_split = min(max_ms, len(seg))

    trimmed = seg[:best_split]
    return audiosegment_to_numpy(trimmed)


def cross_fade_chunks(
    chunks: list[np.ndarray],
    sample_rate: int,
    silence_duration: float = 0.3,
) -> np.ndarray:
    """Concatenate audio chunks with silence gaps and cross-fade at boundaries.

    Args:
        chunks: list of numpy arrays, each (C, T).
        sample_rate: audio sample rate.
        silence_duration: total silence gap duration in seconds.

    Returns:
        Merged numpy array (C, T_total).
    """
    if len(chunks) == 1:
        return chunks[0]

    total_n = int(silence_duration * sample_rate)
    fade_n = total_n // 3
    silence_n = fade_n
    merged = chunks[0].copy()

    for chunk in chunks[1:]:
        parts = [merged]

        fout_n = min(fade_n, merged.shape[-1])
        if fout_n > 0:
            w_out = np.linspace(1, 0, fout_n, dtype=np.float32)[np.newaxis, :]
            parts[-1][..., -fout_n:] *= w_out

        parts.append(np.zeros((chunks[0].shape[0], silence_n), dtype=np.float32))

        fade_in = chunk.copy()
        fin_n = min(fade_n, fade_in.shape[-1])
        if fin_n > 0:
            w_in = np.linspace(0, 1, fin_n, dtype=np.float32)[np.newaxis, :]
            fade_in[..., :fin_n] *= w_in

        parts.append(fade_in)
        merged = np.concatenate(parts, axis=-1)

    return merged
